#!/usr/bin/env bash
set -o errexit

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Building frontend with Node.js..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    echo "Installing Node dependencies..."
    npm install
    echo "Running npm build..."
    npm run build
    echo "Frontend build complete!"
    cd ..
    
    # Verificar que dist existe
    if [ -d "frontend/dist" ]; then
        echo "✓ Frontend dist directory exists"
        ls -la frontend/dist/ | head -20
    else
        echo "⚠️  Frontend dist directory not found!"
    fi
else
    echo "⚠️  Frontend directory or package.json not found"
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput --verbosity 2

echo "Running migrations..."
python manage.py migrate

echo "Build complete!"
