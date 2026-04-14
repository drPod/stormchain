---
title: "Airline Crew Sequences Meet Bad Weather"
subtitle: "EPPS-American Airlines Data Challenge — GROW 26.2"
author: "Team Submission"
theme: "default"
colortheme: "default"
---

# Slide 1: Title

**Airline Crew Sequences Meet Bad Weather**

Identifying pilot flight pairings through DFW that should not share a sequence

---

# Slide 2: The Problem in One Picture

**May 28, 2024 at DFW** — the worst cascading delay day in our dataset

- 172 inbound flights arrived weather-delayed (19.5%)
- 471 outbound flights departed late (53.2%)
- **$4.4M in cascading delays — in a single day**

Why? Pilots assigned to risky sequences. When their inbound from MCO gets hit by a thunderstorm, they arrive late at DFW, and their outbound to LAX departs late — the delay cascades.

*The challenge: which pairs of flights should NOT share a pilot sequence?*

---

# Slide 3: What We Built

A working system, not just a methodology document:

- **Data pipeline**: 842K flights, 3.5M weather records, 3.3M real METAR observations
- **Machine learning model**: XGBoost with AUC-ROC 0.81 on held-out 2024 data
- **Risk scoring**: 37,920 pair-month risk scores
- **Production output**: 1,220 avoid recommendations + 294 swap suggestions
- **Interactive dashboard**: 7 tabs for exploration

All addressing 4 challenge objectives: delay propagation, duty time, missed connections, fatigue

---

# Slide 4: The Model

**Two complementary approaches:**

| Model | Role |
|---|---|
| XGBoost classifier | Feature discovery and validation |
| Composite risk score | Production rankings |

**Key features used:**

- Joint weather delay probability
- IFR co-occurrence from real METAR data
- Cascade propagation mechanics (actual delay minutes)
- Turnaround adequacy & duty time risk
- Weather correlation, thunderstorm co-occurrence
- Fatigue exposure (WOCL overlap)

**Training:** 1.9M synthetic pilot sequences, temporal train/test split, class imbalance handled via `scale_pos_weight`.

---

# Slide 5: The Proof — Beating the Naive Baseline

We compared our model against a simple baseline: "just avoid pairs of two individually high-delay airports."

| Pairs Flagged | Our Model | Naive Baseline | **Our Improvement** |
|---|---|---|---|
| 50 | 295K min | 195K min | **+51%** |
| 100 | 563K min | 335K min | **+68%** |
| **200** | **1.09M min** | **610K min** | **+78%** |
| 500 | 2.60M min | 1.62M min | +60% |

At K=500, **176 pairs our model catches that the naive approach misses entirely.**

This proves the model captures correlated weather, cascade mechanics, and turnaround sensitivity — beyond common sense.

---

# Slide 6: The Product — Actionable Recommendations

We don't just identify risk. We prescribe action.

**Avoid list (1,220 pair-season entries):**

| Season | Airport A | Airport B | Risk | Why |
|---|---|---|---|---|
| Summer | MCO | MIA | 96 | Correlated thunderstorms |
| Summer | ATL | MCO | 93 | Same storm system |
| Spring | IAH | SAT | 77 | Texas storm corridor |

**Swap recommendations (294 alternatives):**

> Instead of MCO → DFW → MIA (risk 96) — try MCO → DFW → HRL (risk 30)

**Seasonal patterns:**
- Spring = Southeast thunderstorm corridor (MCO dominant)
- Summer = Florida convection (MCO in 8 of top 10)
- Winter = Northeast snow + LAX-SAN Santa Ana winds

---

# Slide 7: Case Study — May 28, 2024

**What actually happened that day (from METAR):**

- 05:53 UTC: DFW METAR reads `+TSRA FG SQ` — heavy thunderstorm, fog, squall
- Zero visibility for 40+ minutes
- By mid-morning, 172 inbound flights were weather-delayed

**Cascade mechanics:**
- 170 realistic pilot sequences (one outbound per inbound)
- 149 with actual propagated delay (exceeded turnaround buffer)
- $4.4M cascade cost in a single day

**Honest note:** Our model flagged 9 of 170 sequences. The rest involved unusual route combinations (BOS-BHM, AMA-FLL) that monthly aggregation can't score. Our model catches the **predictable seasonal patterns**; extreme weather events require real-time monitoring to complement.

---

# Slide 8: Methodology Evolution

We critiqued our own work and fixed 12 gaps:

1. Duty time unaddressed → added FAA Part 117 features
2. Missed connections = delays → added buffer adequacy
3. Binary weather co-occurrence → built cascade physics model
4. Open-Meteo proxy weather → integrated real METAR
5. $614M inflated case study → 240× recount → $4.4M honest
6. $25M/year upper bound → added assignment-probability adjustment ($438K)
7. Airport-level → added time-of-day considerations
... and 5 more documented in the report

**Outcome:** AUC-ROC improved from 0.75 → 0.81. Impact estimates became defensible instead of inflated.

*This is the kind of self-correction that distinguishes rigorous analysis from surface-level work.*

---

# Slide 9: Limitations (We Know What We Don't Know)

**DFW weather dominates XGBoost feature importance.**
Expected — it affects every sequence. Risk scoring model mitigates via pair-level features. Production should treat DFW weather as a conditioning variable.

**Rare route combinations slip through.**
Monthly aggregation can't score routes with sparse history. Complement with real-time monitoring.

**No access to actual crew schedules.**
Synthetic sequences may differ from AA's real assignments. Would need internal data to refine.

**Single hub.**
Extending to CLT, MIA, ORD, PHX, PHL would multiply impact 5-6×.

---

# Slide 10: The Ask & Closing

**What we're delivering:**

1. A working, inspectable pipeline (GitHub repo)
2. An interactive dashboard AA's schedulers could use tomorrow
3. A concrete avoid list with swap recommendations
4. A validated model with a defensible baseline improvement (+78%)
5. Honest documentation of what we know and what we don't

**$438K/year at DFW today. Multiplied across AA's hub network, materially more.**

**Most importantly:** a framework that gets better as more data and schedule information become available.

Thank you.

---
