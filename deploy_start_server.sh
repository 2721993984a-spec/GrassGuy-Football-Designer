#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

mkdir -p output/images output/pdf output/excel logs

python -m pip install -r requirements.txt
python -m streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
