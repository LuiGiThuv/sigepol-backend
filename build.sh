#!/usr/bin/env bash
set -o errexit

echo "=== SIGEPOL BUILD SCRIPT ==="
echo ""

# Python
echo "[1/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Frontend
echo "[2/5] Building frontend..."
if [ -f "frontend/package.json" ]; then
    cd frontend
    npm install --legacy-peer-deps
    npm run build
    cd ..
    echo "✓ Frontend built successfully"
else
    echo "⚠ frontend/package.json not found"
fi
echo ""

# Static files
echo "[3/5] Collecting static files..."
python manage.py collectstatic --noinput
echo "✓ Static files collected"
echo ""

# Migrations
echo "[4/5] Running migrations..."
python manage.py migrate
echo "✓ Migrations completed"
echo ""

# Done
echo "[5/5] Build complete!"
echo "=== BUILD FINISHED ==="
