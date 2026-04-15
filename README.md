# MoveSmart

![Alt Text](assets/flow_chart.png)

Streamlit app for exploring U.S. CBSA (metro) recommendations using a merged census, health, crime, walkability, and weather panel. The **modeling dataset** is built by Python loaders under `src/`, then merged in `src/final_dataset_loader.py`.

## Main application

| Entry point | Role |
|-------------|------|
| **`app.py`** | Streamlit UI (`streamlit run app.py`). Reads **`data/final/Final_Enriched_Dataset.csv`**. |

Other Python modules (`src/recommender.py`, `src/visualizations.py`, `src/rag_explanation.py`) are imported by the app. Clustering used in the final dataset lives in **`models/cluster_model.py`**.

---

## Repository layout

```
movesmart/
├── app.py                      # Streamlit app (main UI)
├── data/
│   ├── raw/                    # Source files (not in git); obtain locally (see Step 0)
│   ├── processed/              # Per-source CBSA tables (loader outputs)
│   ├── evaluation/             # Stores evaluation results and analysis
│   └── final/                  # Final_Base_Dataset.csv, Final_Enriched_Dataset.csv
├── exploratory_notebooks/
│   └── 06_evaluation.ipynb     # Evaluation notebook for recommender system (semantic search, summary generation and explanation generation)
├── models/
│   └── cluster_model.py        # KMeans / PCA; used by final_dataset_loader
├── scripts/
│   ├── run_pipeline.ps1        # Windows: orchestrates loaders (+ optional weather)
│   └── run_pipeline.sh         # POSIX: same
├── src/
│   ├── census_data_loader.py
│   ├── crime_data_loader.py
│   ├── places_data_loader.py
│   ├── walkability_data_loader.py
│   ├── weather_data_loader.py  # slow; normally skipped (use Weather_Data.csv)
│   ├── final_dataset_loader.py # merges processed → final + scores + clusters
│   ├── standardize_scores.py   # score columns (imported by final_dataset_loader)
│   ├── recommender.py
│   ├── visualizations.py
│   ├── wiki_text_loader.py     # Calls Wikipedia/Wikivoyage APIs and uses LLM to write CBSA metro/micro summaries to data/processed/
│   ├── semantic_search.py      # Embeds CBSA summaries into ChromaDB and semantic-searches that index for user queries
│   └── rag_explanation.py      # Uses LLM + retrieved context to explain why recommended places match user preferences
├── requirements.txt
└── Makefile
```

---

## Setup

**Python 3.10+** recommended (uses `list[str]` / modern typing in several modules).

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux / Git Bash:**

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Optional Census API key (better rate limits): set `CENSUS_API_KEY` in your shell (for example `$env:CENSUS_API_KEY='…'` in PowerShell) before running the census loader. The loader also runs without a key.

**GeoPandas:** On some Windows setups, `pip install geopandas` is enough; if install fails, use [OSGeo4W](https://trac.osgeo.org/osgeo4w/) or a Conda environment with `geopandas` from conda-forge.

---

## Data pipeline (reproducible order)

All commands assume the **repository root** as the current working directory.

### Step 0 — Raw inputs (`data/raw/`)

| Loader | Required paths (defaults in code) |
|--------|-------------------------------------|
| **Census** | `data/raw/2023_Gaz_cbsa_national.txt` (Census CBSA gazetteer). ACS tables are fetched from **api.census.gov** (optional `CENSUS_API_KEY`). |
| **Crime** | `data/raw/FBI_Crime_Data_By_City_with_Counties.csv`, `data/raw/ZIP_CBSA_122023.csv` |
| **PLACES** | `data/raw/PLACES__Census_Tract_Data_(GIS_Friendly_Format),_2025_release_20260314.csv` (or your tract file with the same column expectations), **`data/raw/shapefiles/tl_2023_us_cbsa.shp`** plus sidecars (`.dbf`, `.shx`, `.prj`, …). |
| **Walkability** | `data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv` |
| **Weather** | *Skipped for normal reproduction* — use committed **`data/processed/Weather_Data.csv`**. Full rebuild uses the gazetteer + thousands of NOAA downloads (many hours). |
| **Wiki text** | `data/raw/list2_2023.xlsx` (cities by CBSA/metro/micro). Fetches Wikipedia/Wikivoyage intro text and uses Bedrock to write per–metro/micro summaries under **`data/processed/`** (slow; optional). |

### Step 1 — Build processed CBSA tables

Run in this order (census first is conventional; crime/places/walkability only depend on raw files, not on each other):

```powershell
# Windows PowerShell (from repo root)
python -m src.census_data_loader
python -m src.crime_data_loader
python -m src.places_data_loader
python -m src.walkability_data_loader
```

**Skip weather** and keep using the repo’s `data/processed/Weather_Data.csv`. Do **not** run `weather_data_loader` unless you intend to wait for a full NOAA pull.

If you must rebuild weather:

```powershell
python -m src.weather_data_loader
```

That writes **`data/processed/Weather_Data.csv`** (and uses `data/raw/weather/noaa_monthly_normals/` as a cache).

**Skip wiki text** and keep using the repo’s **`data/processed/cbsa_wiki_wikivoyage_summaries_df.csv`** (or generate it once and reuse). Do **not** run `wiki_text_loader` unless you intend to wait for many Wikipedia/Wikivoyage API calls plus Bedrock summarization per CBSA.

If you must rebuild wiki summaries:

```powershell
python src/wiki_text_loader.py
```

### Step 2 — Final dataset (merge + imputation + scores + clusters)

```powershell
python -m src.final_dataset_loader
```

**Outputs:**

| File | Description |
|------|-------------|
| `data/processed/Census_Data.csv` | Census loader |
| `data/processed/Crime_Data.csv` | Crime loader |
| `data/processed/Places_Data.csv` | PLACES loader |
| `data/processed/Walkability_Data.csv` | Walkability loader |
| `data/processed/Weather_Data.csv` | Weather loader (or committed copy) |
| `data/processed/cbsa_wiki_wikivoyage_summaries_df.csv` | Wiki text loader (Wikipedia/Wikivoyage + Bedrock summaries per CBSA;) |
| `data/final/Final_Base_Dataset.csv` | Merged + imputed base |
| `data/final/Final_Enriched_Dataset.csv` | Base + feature/composite scores + cluster columns (**app input**) |

---

## One-shot scripts

**Windows:**

```powershell
.\scripts\run_pipeline.ps1
# Full weather rebuild (slow):
.\scripts\run_pipeline.ps1 -IncludeWeather
```

**Git Bash / WSL / macOS / Linux:**

```bash
bash scripts/run_pipeline.sh
INCLUDE_WEATHER=1 bash scripts/run_pipeline.sh   # slow
```

**Make** (if `make` is available):

```bash
make install
make pipeline-no-weather   # recommended
make pipeline              # includes weather
make app                   # streamlit run app.py
```

---

## Run the Streamlit app

```powershell
streamlit run app.py
```

Ensure **`data/final/Final_Enriched_Dataset.csv`** exists (run `final_dataset_loader` after the processed inputs exist).

If this is your first run (or `chroma_db/` is empty), build the semantic search index once:

```powershell
python src/semantic_search.py
```

---

## Dependencies (by concern)

| Area | Packages |
|------|----------|
| App | `streamlit`, `plotly`, `pandas`, `numpy` |
| Census / crime / walkability / weather HTTP | `requests`, `urllib3` |
| PLACES spatial join | `geopandas` (+ GDAL stack via pip or conda) |
| Clustering + scaling in `models/cluster_model.py` | `scikit-learn` |
| Semantic search in recommender | `chromadb`, `sentence-transformers` |
| Bedrock-backed explanation generation | `boto3` (`app.py`, `src/rag_explanation.py`) |

---

## Gen AI Use
Cursor was used sporatically throughout this project. Specifically it was used to help set up the framework of the data_loader files but many edits were made outside of the initial set up from Cursor so unable to attribute specific line by line to Cursor.

## License / data provenance

Respect terms of use for Census API, CDC PLACES, FBI crime statistics, EPA Smart Location Database, and NOAA normals when redistributing derived files.

---

## Addendum: AWS / Bedrock setup for explanation features

The "Why this city?" explanation flow uses Amazon Bedrock.

### Required AWS access

- Bedrock Runtime permission: `bedrock:InvokeModel`
- Model access enabled in Bedrock console for: `anthropic.claude-3-haiku-20240307-v1:0`
- Region: `us-east-1`

### Credential setup (do not commit secrets)

Use one of the options below:


**Option A — Environment variables (temporary credentials)**

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...   
export AWS_REGION=us-east-1
```

**Option B — Streamlit secrets (local machine only)**

Create `.streamlit/secrets.toml` locally (never commit):

```toml
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
AWS_SESSION_TOKEN="..."  # optional
AWS_REGION="us-east-1"
```

### Security checklist

- Never hardcode `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `AWS_SESSION_TOKEN` in source files.
- If credentials were ever committed in code history, rotate/revoke them immediately.

---
