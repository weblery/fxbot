#!/bin/bash
# FOREXBOT Batch Resampling Script
# Processes all M1 data files in the data/ folder

PYTHON="/Users/Calvin/Desktop/FOREXBOT/venv/bin/python"
DATA_DIR="data"

echo "🚀 Starting Batch Resampling..."

# List of files to process
FILES=(
    "XAUUSDm_M1_202101030000_202605012057.csv"
    "BTCUSDm_M1_202101010000_202605012113.csv"
    "GBPJPYm_M1_202101030000_202605012058.csv"
    "AUDJPYm_M1_202101030000_202605012058.csv"
    "CHFJPYm_M1_202101030000_202605012058.csv"
    "CADJPYm_M1_202101030000_202605012058.csv"
    "AUDUSDm_M1_202101030000_202605012057.csv"
    "USDCADm_M1_202101030000_202605012058.csv"
    "NZDUSDm_M1_202101030000_202605012058.csv"
    "USDCHFm_M1_202101030000_202605012058.csv"
)

for FILE in "${FILES[@]}"; do
    if [ -f "$DATA_DIR/$FILE" ]; then
        SYMBOL=$(echo "$FILE" | cut -d'm' -f1)
        echo "⚙️ Processing $SYMBOL..."
        $PYTHON scripts/resample_m1.py "$DATA_DIR/$FILE" --symbol "$SYMBOL"
    else
        echo "⚠️ Skipping $FILE (Not found)"
    fi
done

echo "✅ Batch Resampling Complete!"
