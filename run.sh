#!/bin/bash

set -euo pipefail

echo "Starting Visual Search AI Service..."

UV_CMD="${UV_CMD:-uv}"

if ! command -v "$UV_CMD" >/dev/null 2>&1; then
    echo "uv is required but not installed. See https://docs.astral.sh/uv/getting-started/installation/."
    exit 1
fi

select_python_cmd() {
    local candidates=("python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            local version
            if version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null); then
                local major=${version%%.*}
                local minor=${version#*.}
                if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ] && [ "$minor" -le 11 ]; then
                    PYTHON_CMD="$cmd"
                    return 0
                fi
            fi
        fi
    done
    return 1
}

if ! select_python_cmd; then
    echo "Could not find a Python 3.8–3.11 interpreter. Please install a supported Python (e.g., 3.10 or 3.11) and rerun this script."
    exit 1
fi

if [ ! -x "venv/bin/python" ]; then
    echo "Creating virtual environment with $PYTHON_CMD..."
    "$PYTHON_CMD" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

VENV_PYTHON="$(pwd)/venv/bin/python"

echo "Installing Python dependencies..."
"$UV_CMD" pip install --python "$VENV_PYTHON" -r requirements.txt

echo "Installing PyTorch (CUDA-aware)..."
"$VENV_PYTHON" scripts/install_pytorch.py

echo "Ensuring catalog directory exists..."
mkdir -p data/catalog

if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

echo "Starting backend server..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 5

echo "Starting frontend server..."
(cd frontend && npm start) &
FRONTEND_PID=$!

echo "\nServices started!"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
