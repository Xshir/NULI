# NULI — Factory AI Copilot Dashboard
**National Student AI Challenge 2026 | Micron Track**
Lead Developer: Muhammad Haashir Islam
Team: Charlene Tan Ying Jie, Gabriel Lim Jun Hong, Avril Michellina (TP BME)

---

## What This App Does

NULI is a Streamlit-based factory monitoring dashboard that:
- Generates synthetic multi-format equipment logs (JSON, XML, CSV, TEXT, SYSLOG, KV) simulating real semiconductor fab data
- Normalises and fuses data across 12 formats using a confidence-scoring engine
- Detects anomalies and drift in real-time using a dynamic threshold
- Uses a local LLM (via Ollama) to perform root cause analysis and generate mitigation plans
- Provides an AI Copilot chat interface for querying live factory data

---

## Prerequisites

Install these on your **local machine** before anything else.

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | Latest | Must be running |
| Ollama | Latest | Must be running as a background service |
| llama3 model | — | Pull via `ollama pull llama3` |

### Verify Ollama is ready
```bash
ollama list
```
You should see `llama3:latest` in the list. If not:
```bash
ollama pull llama3
```

---

## Project File Structure

```
your-project-folder/
│
├── app.py                  # Main Streamlit application
├── Configuration.py        # All constants, colours, thresholds, model config
├── Dockerfile              # Docker build instructions
├── requirements.txt        # Python dependencies
│
├── micron_logo.png         # Required — place in root folder
├── tp_logo.png             # Required — place in root folder
└── ael_logo.png            # Required — place in root folder
```

> **Note:** If any logo file is missing, the app will show a warning but will still run.

---

## Configuration

Before launching, open `Configuration.py` and verify these values:

```python
# LLM Settings — must match exactly what `ollama list` shows
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME  = "llama3:latest"

# Thresholds
THRESHOLD_CRITICAL = <your value>   # Pressure value that triggers ALARM
BASELINE_DEFAULT   = <your value>   # Normal operating baseline
```

> **Important:** `host.docker.internal` is the correct hostname when running inside Docker on Windows/Mac. Do not change it to `localhost`.

---

## Launching the App

### Step 1 — Make sure Ollama is running

Ollama must be bound to all interfaces so Docker can reach it. Open PowerShell and run:

```powershell
$env:OLLAMA_HOST="0.0.0.0"
ollama serve
```

> **Or** set it permanently: Go to **System Environment Variables** → New → `OLLAMA_HOST` = `0.0.0.0`, then restart Ollama.

### Step 2 — Build the Docker image

Open a terminal in your project folder:

```bash
docker build -t nuli-app .
```

### Step 3 — Run the container

```bash
docker run -p 8501:8501 nuli-app
```

### Step 4 — Open the app

Go to your browser and navigate to:
```
http://localhost:8501
```

---

## Using the App

### Module 1 — Cover Page
Displays project branding and team information. No interaction needed.

### Module 2 — Data Ingestion Engine
1. Select a **Failure Profile**: Normal Ops / Slow Leak / Sudden Burst / Ghost Fault
2. Set **Failure Severity** (slider)
3. Set **Log Length** (number of cycles to generate)
4. Click **GENERATE SYNTHETIC PAYLOAD** — this produces 12 format variants for 2 vendors
5. Expand the payload viewer to inspect raw logs
6. Click **PUSH TO FACTORY DASHBOARD** to proceed

### Module 3 — Factory Dashboard
1. Set the **Ingestion Batch Size** (how many log cycles to process)
2. Click **INITIATE DATA NORMALIZATION** — this fuses all 12 formats per cycle and calls the LLM for any anomalies
3. Once complete, you will see:
   - **Drift & Anomaly Matrix** — interactive Plotly time-series chart
   - **Executive Macro Mitigation Plan** — click button to generate via LLM
   - **KPI Metrics** — Tool Availability, Drift Events, Estimated Scrap
   - **Unified Intelligence Schema** — full normalised data table (SEMI E30/GEM format)
   - **Export CSV** — download the normalised dataset
   - **Factory AI Copilot** — chat interface for querying the live data

---

## Known Issues & Things to Note

### LLM Timeout
The local LLM (llama3) can be slow, especially on first load or with many anomalies. All `requests.post()` calls should use `timeout=60` (not 15). If you see timeout errors, check this in `app.py`.

### Empty AI Response
If the Copilot returns `"AI core returned no content"`, it means:
- Ollama is reachable but the model name is wrong — run `ollama list` and match `MODEL_NAME` in `Configuration.py` exactly
- The model returned an error — the app will now show the actual Ollama error message for diagnosis

### Docker Cannot Reach Ollama
If you see `Connection error: HTTPConnectionPool(host='host.docker.internal'...)`:
- Ollama is not running, or it is bound to `127.0.0.1` only
- Fix: set `OLLAMA_HOST=0.0.0.0` before starting Ollama (see Step 1 above)

### Slow First Run
The first `INITIATE DATA NORMALIZATION` after launching Docker will be slow because:
- Docker pulls dependencies on first build
- Ollama loads the model into RAM on first inference (~10–30 seconds)
Subsequent runs in the same session will be faster due to caching.

### Resetting the App
Click **CLEAR MEMORY & RESET** in the sidebar. This wipes the SQLite database and all session state, giving you a clean slate.

### Logo Files
If `micron_logo.png`, `tp_logo.png`, or `ael_logo.png` are missing from the project folder, the Cover Page will show a placeholder message. The rest of the app is unaffected.

---

## Architecture Overview

```
Docker Container (Streamlit)
        │
        │  HTTP POST to port 11434
        ▼
host.docker.internal ──► Ollama (running on local machine)
                                │
                                ▼
                         llama3:latest model
```

Data flow inside the app:
```
Generate Logs (12 formats × 2 vendors)
        │
        ▼
robust_parse() — extracts timestamp, tool_id, value per format
        │
        ▼
Confidence Scoring — majority vote across 6 format parsers
        │
        ▼
LLM RCA — calls Ollama for ALARM events only (cached per event)
        │
        ▼
SQLite Storage — persists normalised batch to /tmp/factory_logs.db
        │
        ▼
Dashboard — chart, metrics, table, copilot chat
```

---

## Quick Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Connection error: Read timed out` | LLM too slow | Increase all `timeout=` values to `60` |
| `Raw keys: ['error']` | Wrong model name | Run `ollama list`, update `MODEL_NAME` in `Configuration.py` |
| `Connection refused` on port 11434 | Ollama not running | Run `ollama serve` with `OLLAMA_HOST=0.0.0.0` |
| Logos not showing | Missing image files | Place `.png` files in the same folder as `app.py` |
| Dashboard shows "Awaiting data stream" | No data generated yet | Go to Simulation Engine and generate a payload first |
| App crashes on `active_batch` SQL error | Corrupt/empty DB | Click **CLEAR MEMORY & RESET** in sidebar |
