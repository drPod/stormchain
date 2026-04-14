"""Risk scoring model and XGBoost classifier for airport pair risk."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, average_precision_score, classification_report,
    confusion_matrix, precision_recall_curve, roc_curve,
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PROCESSED_DIR, MODEL_DIR, FIGURES_DIR,
    BTS_TRAIN_YEARS, BTS_TEST_YEAR, RANDOM_STATE,
)


# ---------------------------------------------------------------------------
# Risk Scoring
# ---------------------------------------------------------------------------

def compute_risk_scores(pairs_df: pd.DataFrame) -> pd.DataFrame:
    """Compute composite risk score for each airport pair by month."""
    cache_path = MODEL_DIR / "risk_scores.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    df = pairs_df.copy()

    # Normalize features to [0, 1] range for weighted combination
    score_features = [
        "joint_weather_delay_prob",
        "joint_delay_15_prob",
        "conditional_delay_prob",
        "precip_correlation",
        "thunderstorm_co_occurrence",
        "severe_weather_co_occurrence",
        # New features from methodology fixes
        "ifr_co_occurrence",
        "missed_connection_prob",
        "duty_violation_risk",
        "fatigue_exposure",
    ]

    # Add combined weather risk if available
    if "combined_weather_risk" in df.columns:
        score_features.append("combined_weather_risk")

    for feat in score_features:
        if feat in df.columns:
            col = df[feat].fillna(0)
            mn, mx = col.min(), col.max()
            if mx > mn:
                df[f"{feat}_norm"] = (col - mn) / (mx - mn)
            else:
                df[f"{feat}_norm"] = 0

    # Weights — covers all 4 PDF objectives
    weights = {
        # Objective 1: Delay propagation
        "joint_weather_delay_prob_norm": 0.15,
        "conditional_delay_prob_norm": 0.15,
        "thunderstorm_co_occurrence_norm": 0.08,
        "severe_weather_co_occurrence_norm": 0.05,
        "precip_correlation_norm": 0.05,
        "joint_delay_15_prob_norm": 0.07,
        "combined_weather_risk_norm": 0.05,
        "ifr_co_occurrence_norm": 0.05,
        # Objective 2: Duty time violations
        "duty_violation_risk_norm": 0.10,
        # Objective 3: Missed connections
        "missed_connection_prob_norm": 0.15,
        # Objective 4: Fatigue risk
        "fatigue_exposure_norm": 0.10,
    }

    df["risk_score"] = 0.0
    for feat, w in weights.items():
        if feat in df.columns:
            df["risk_score"] += w * df[feat]

    # Scale to 0-100
    mn, mx = df["risk_score"].min(), df["risk_score"].max()
    if mx > mn:
        df["risk_score"] = 100 * (df["risk_score"] - mn) / (mx - mn)

    # Rank
    df["risk_rank"] = df["risk_score"].rank(ascending=False, method="min").astype(int)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    print(f"Saved risk scores ({len(df):,} rows) to {cache_path}")
    return df


# ---------------------------------------------------------------------------
# XGBoost Classifier
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    # Pair-level features
    "joint_weather_delay_prob", "joint_delay_15_prob", "conditional_delay_prob",
    "precip_correlation", "wind_correlation",
    "thunderstorm_co_occurrence", "severe_weather_co_occurrence",
    "distance_ab", "latitude_diff", "longitude_diff",
    "same_region", "tornado_alley_pair", "hurricane_pair", "winter_storm_pair",
    "month_sin", "month_cos",
    "combined_weather_risk", "max_weather_risk",
    # Airport-level stats
    "weather_delay_rate_a", "weather_delay_rate_b",
    "weather_delay_mean_a", "weather_delay_mean_b",
    "delay_rate_15_a", "delay_rate_15_b",
    "cancellation_rate_a", "cancellation_rate_b",
    # Sequence-level features
    "connection_minutes", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "inbound_arr_time", "outbound_dep_time",
]

# Weather features to include if available
WEATHER_FEATURE_PREFIXES = ["wx_a_", "wx_b_", "wx_dfw_"]


def get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Get available feature columns from the DataFrame."""
    available = [c for c in FEATURE_COLS if c in df.columns]
    # Add weather columns
    for prefix in WEATHER_FEATURE_PREFIXES:
        available += [c for c in df.columns if c.startswith(prefix) and df[c].dtype in [np.float64, np.float32, np.int64, np.int32, float, int]]
    return list(set(available))


def compute_stratified_risk(pairs_df: pd.DataFrame, flights_df: pd.DataFrame) -> None:
    """Compute risk scores stratified by DFW weather state.

    Splits days into DFW-clear and DFW-impacted, then shows which pairs
    are risky in each regime. This isolates pair-level signal from hub noise.
    """
    from config import DFW_IATA
    flights = flights_df.copy()
    flights["date"] = flights["FlightDate"].dt.normalize()

    # Classify each day: DFW impacted or clear
    dfw_flights = flights[(flights["Origin"] == DFW_IATA) | (flights["Dest"] == DFW_IATA)]
    dfw_daily = dfw_flights.groupby("date").agg(
        dfw_weather_delays=("WeatherDelay", lambda x: (x > 0).sum()),
    ).reset_index()
    dfw_daily["dfw_impacted"] = dfw_daily["dfw_weather_delays"] > 0

    impacted_dates = set(dfw_daily[dfw_daily["dfw_impacted"]]["date"])
    clear_dates = set(dfw_daily[~dfw_daily["dfw_impacted"]]["date"])

    print(f"\nDFW Weather Stratification:")
    print(f"  Impacted days: {len(impacted_dates)}")
    print(f"  Clear days: {len(clear_dates)}")

    # For each pair, compute risk on clear days vs impacted days
    # Using the existing pair features which are monthly averages,
    # we can't directly stratify. Instead, we analyze the cascade data.
    cascade_path = SIMULATION_DIR / "cascade_propagation.parquet"
    if not cascade_path.exists():
        print("  Cascade data not available for stratification")
        return

    cascades = pd.read_parquet(cascade_path)
    print(f"  Top 10 pairs on DFW-CLEAR days (inherent pair risk):")
    # This would need date-level cascade data; for now, note the limitation
    print(f"  [Stratification requires date-level cascade data — noted as future work]")

    # Save a summary of DFW weather impact
    summary = pd.DataFrame({
        "metric": ["DFW impacted days", "DFW clear days", "% impacted",
                   "Avg delays on impacted days", "Avg delays on clear days"],
        "value": [
            len(impacted_dates), len(clear_dates),
            len(impacted_dates) / max(len(impacted_dates) + len(clear_dates), 1) * 100,
            dfw_daily[dfw_daily["dfw_impacted"]]["dfw_weather_delays"].mean(),
            dfw_daily[~dfw_daily["dfw_impacted"]]["dfw_weather_delays"].mean(),
        ]
    })
    summary.to_csv(MODEL_DIR / "dfw_stratification.csv", index=False)
    print(f"  Saved DFW stratification summary")


def train_xgboost(enriched_sequences: pd.DataFrame) -> dict:
    """Train XGBoost on enriched sequence data with temporal split."""
    feature_cols = get_feature_cols(enriched_sequences)
    target = "cascading_delay"

    if target not in enriched_sequences.columns:
        raise ValueError(f"Target column '{target}' not found")

    print(f"Using {len(feature_cols)} features")

    # Temporal split
    train_mask = enriched_sequences["year"].isin(BTS_TRAIN_YEARS)
    test_mask = enriched_sequences["year"] == BTS_TEST_YEAR

    train_df = enriched_sequences[train_mask].copy()
    test_df = enriched_sequences[test_mask].copy()

    # Further split test into val (first half) and test (second half)
    test_df["month_num"] = test_df["month"]
    val_mask = test_df["month_num"] <= 6
    val_df = test_df[val_mask].copy()
    test_final_df = test_df[~val_mask].copy()

    print(f"Train: {len(train_df):,}  Val: {len(val_df):,}  Test: {len(test_final_df):,}")
    print(f"Train positive rate: {train_df[target].mean():.4f}")

    # Prepare data
    X_train = train_df[feature_cols].fillna(0)
    y_train = train_df[target]
    X_val = val_df[feature_cols].fillna(0)
    y_val = val_df[target]
    X_test = test_final_df[feature_cols].fillna(0)
    y_test = test_final_df[target]

    # Handle class imbalance
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos = neg_count / max(pos_count, 1)

    print(f"Class ratio: {neg_count}:{pos_count} (scale_pos_weight={scale_pos:.1f})")

    # Train
    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="aucpr",
        early_stopping_rounds=50,
        random_state=RANDOM_STATE,
        verbosity=1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    # Evaluate on test set
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    metrics = {}
    try:
        metrics["auc_roc"] = roc_auc_score(y_test, y_pred_proba)
    except ValueError:
        metrics["auc_roc"] = 0
    try:
        metrics["auc_pr"] = average_precision_score(y_test, y_pred_proba)
    except ValueError:
        metrics["auc_pr"] = 0

    metrics["classification_report"] = classification_report(y_test, y_pred, output_dict=True)
    metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()

    print(f"\nTest AUC-ROC: {metrics['auc_roc']:.4f}")
    print(f"Test AUC-PR: {metrics['auc_pr']:.4f}")
    print(f"\n{classification_report(y_test, y_pred)}")

    # Feature importance
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    print("\nTop 20 features:")
    print(importance.head(20).to_string(index=False))

    # Save artifacts
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_DIR / "xgb_model.json"))
    importance.to_csv(MODEL_DIR / "feature_importance.csv", index=False)

    # Save predictions for visualization
    test_results = test_final_df[["date", "airport_a", "airport_b", "month", target]].copy()
    test_results["predicted_proba"] = y_pred_proba
    test_results["predicted"] = y_pred
    test_results.to_parquet(MODEL_DIR / "test_predictions.parquet", index=False)

    # ROC and PR curve data
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    precision, recall, _ = precision_recall_curve(y_test, y_pred_proba)

    roc_data = pd.DataFrame({"fpr": fpr, "tpr": tpr})
    pr_data = pd.DataFrame({"precision": precision[:len(recall)], "recall": recall})
    roc_data.to_parquet(MODEL_DIR / "roc_curve.parquet", index=False)
    pr_data.to_parquet(MODEL_DIR / "pr_curve.parquet", index=False)

    return {
        "model": model,
        "metrics": metrics,
        "importance": importance,
        "feature_cols": feature_cols,
    }


def update_risk_weights_from_importance(
    pairs_df: pd.DataFrame,
    importance_df: pd.DataFrame,
) -> pd.DataFrame:
    """Refine risk score weights using XGBoost feature importance."""
    # Map feature importance back to risk score components
    importance_map = {
        "joint_weather_delay_prob": "joint_weather_delay_prob_norm",
        "conditional_delay_prob": "conditional_delay_prob_norm",
        "thunderstorm_co_occurrence": "thunderstorm_co_occurrence_norm",
        "severe_weather_co_occurrence": "severe_weather_co_occurrence_norm",
        "precip_correlation": "precip_correlation_norm",
        "joint_delay_15_prob": "joint_delay_15_prob_norm",
        "combined_weather_risk": "combined_weather_risk_norm",
    }

    imp_dict = importance_df.set_index("feature")["importance"].to_dict()
    weights = {}
    total = 0
    for feat, norm_feat in importance_map.items():
        w = imp_dict.get(feat, 0.01)
        weights[norm_feat] = w
        total += w

    # Normalize to sum to 1
    for k in weights:
        weights[k] /= total

    print("Updated risk weights from XGBoost importance:")
    for k, v in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v:.4f}")

    # Recompute risk scores
    df = pairs_df.copy()
    for feat in importance_map.values():
        if feat not in df.columns:
            col = feat.replace("_norm", "")
            if col in df.columns:
                c = df[col].fillna(0)
                mn, mx = c.min(), c.max()
                if mx > mn:
                    df[feat] = (c - mn) / (mx - mn)
                else:
                    df[feat] = 0

    df["risk_score"] = sum(
        weights.get(f, 0) * df.get(f, 0) for f in weights
    )

    mn, mx = df["risk_score"].min(), df["risk_score"].max()
    if mx > mn:
        df["risk_score"] = 100 * (df["risk_score"] - mn) / (mx - mn)

    df["risk_rank"] = df["risk_score"].rank(ascending=False, method="min").astype(int)

    cache_path = MODEL_DIR / "risk_scores.parquet"
    df.to_parquet(cache_path, index=False)
    print(f"Updated risk scores saved to {cache_path}")
    return df


if __name__ == "__main__":
    from src.data_processing import load_flights, load_weather, compute_daily_weather, load_airports
    from src.feature_engineering import compute_pair_features, enrich_sequences_with_features
    from src.data_processing import build_synthetic_sequences

    flights = load_flights()
    weather = load_weather()
    daily_weather = compute_daily_weather(weather)
    airports = load_airports()

    print("Computing pair features ...")
    pairs = compute_pair_features(flights, daily_weather, airports)

    print("\nComputing risk scores ...")
    risk_scores = compute_risk_scores(pairs)
    print(f"\nTop 20 riskiest pairs overall:")
    top = risk_scores.nlargest(20, "risk_score")[
        ["airport_a", "airport_b", "month", "risk_score", "risk_rank"]
    ]
    print(top.to_string(index=False))

    print("\nBuilding synthetic sequences ...")
    sequences = build_synthetic_sequences(flights)

    print("\nEnriching sequences ...")
    enriched = enrich_sequences_with_features(sequences, pairs, daily_weather)

    print("\nTraining XGBoost ...")
    result = train_xgboost(enriched)

    print("\nUpdating risk weights from importance ...")
    updated_scores = update_risk_weights_from_importance(pairs, result["importance"])
