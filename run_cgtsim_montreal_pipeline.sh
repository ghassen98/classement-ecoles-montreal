#!/usr/bin/env bash
set -euo pipefail

# Pipeline one-shot:
# 1) Fusion CGTSIM + Montreal
# 2) Validation structurelle
# 3) Controle qualite metier

CGTSIM_SOURCE="${1:-data/cgtsim_classement.csv}"
OUT_GEOJSON="${2:-ecoles.geojson}"
QA_REPORT="${3:-qa_report.json}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

CGTSIM_PDF_URL="${CGTSIM_PDF_URL:-https://www.cgtsim.qc.ca/wp-content/uploads/2023/02/2022_EMD_Classification-des-ecoles-1.pdf}"

MONTREAL_SOURCE="${MONTREAL_SOURCE:-https://donnees.montreal.ca/dataset/763fe3b8-cdc3-4b8a-bbbd-a0a9bc587c56/resource/5ca7cdb8-f86f-4038-b5a8-657446c75427/download/lieux_d_interet.geojson}"
MONTREAL_FILTER_FIELD="${MONTREAL_FILTER_FIELD:-Catégorie}"
MONTREAL_FILTER_VALUE="${MONTREAL_FILTER_VALUE:-Établissement scolaire}"
MONTREAL_FILTER_MODE="${MONTREAL_FILTER_MODE:-equals}"
FUZZY_THRESHOLD="${FUZZY_THRESHOLD:-0.86}"
UNMATCHED_OUT="${UNMATCHED_OUT:-unmatched_cgtsim_montreal.csv}"

if [[ ! -f "$CGTSIM_SOURCE" ]]; then
  echo "[info] Source CGTSIM introuvable: $CGTSIM_SOURCE"
  echo "[info] Generation depuis la source CGTSIM en ligne"
  mkdir -p "$(dirname "$CGTSIM_SOURCE")"
  "$PYTHON_BIN" extract_cgtsim_pdf_to_csv.py \
    --pdf-url "$CGTSIM_PDF_URL" \
    --out "$CGTSIM_SOURCE"
fi

echo "[1/3] Fusion CGTSIM + Montreal"
"$PYTHON_BIN" build_cgtsim_montreal_geojson.py \
  --cgtsim "$CGTSIM_SOURCE" \
  --montreal "$MONTREAL_SOURCE" \
  --montreal-filter-field "$MONTREAL_FILTER_FIELD" \
  --montreal-filter-value "$MONTREAL_FILTER_VALUE" \
  --montreal-filter-mode "$MONTREAL_FILTER_MODE" \
  --fuzzy-threshold "$FUZZY_THRESHOLD" \
  --out "$OUT_GEOJSON" \
  --unmatched-out "$UNMATCHED_OUT"

echo "[2/3] Validation GeoJSON"
"$PYTHON_BIN" validate_geojson.py "$OUT_GEOJSON"

echo "[3/3] Controle qualite metier"
"$PYTHON_BIN" control_data_quality.py "$OUT_GEOJSON" --report-json "$QA_REPORT"

echo "Pipeline termine"
echo "- GeoJSON: $OUT_GEOJSON"
echo "- Unmatched: $UNMATCHED_OUT"
echo "- QA report: $QA_REPORT"
