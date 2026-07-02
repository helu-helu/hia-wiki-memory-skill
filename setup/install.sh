#!/bin/bash
echo "==================================================="
echo "  Hia Wiki Memory - Khoi chay trinh cai dat"
echo "==================================================="

cd "$(dirname "$0")/.."

if ! command -v python3 &> /dev/null
then
    echo "[Loi] Python3 chua duoc cai dat hoac chua them vao PATH."
    echo "Vui long cai dat Python 3.10+ de tiep tuc."
    exit 1
fi

echo "Dang khoi dong setup_env.py..."
python3 setup/setup_env.py
