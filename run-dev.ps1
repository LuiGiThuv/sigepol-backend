# Script para desarrollo: activa el venv y arranca Django
# Uso: ejecutar desde la raíz del proyecto
# PowerShell: .\run-dev.ps1

Write-Output "Activando virtualenv .venv..."
& "${PWD}\.venv\Scripts\Activate.ps1"

Write-Output "Usando python:"
python -c "import sys; print(sys.executable)"

Write-Output "Arrancando servidor Django (http://127.0.0.1:8000)..."
& "${PWD}\.venv\Scripts\python.exe" manage.py runserver
