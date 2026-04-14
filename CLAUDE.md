# CLAUDE.md

## Project
EPPS-American Airlines Data Challenge — identifying risky airport pair sequences through DFW.

## Development Patterns

### Research Log
When identifying problems, methodology gaps, or making significant decisions, add them to `docs/methodology_evolution.md`. Document: what the problem was, why it matters, and how we solved it. This iterative record may be referenced in the report or presentation.

### Virtual Environment
Always use the project venv: `.venv/bin/python`, `.venv/bin/streamlit`, etc.
Set `PYTHONPATH=/Users/darshpoddar/Coding/ds-challenge` when running scripts from the project root.

### Kaggle Auth
Uses `KAGGLE_API_TOKEN` env var loaded from `.env` via python-dotenv.

### Data Caching
All processed data is cached as parquet in `data/processed/`. Delete the parquet file to force recomputation. Weather data is cached per airport-year in `data/raw/weather/`.

### Running the Pipeline
```bash
PYTHONPATH=. .venv/bin/python run_pipeline.py
```

### Dashboard
```bash
PYTHONPATH=. .venv/bin/streamlit run app/streamlit_app.py
```
