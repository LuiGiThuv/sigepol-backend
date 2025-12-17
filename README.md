# SIGEPOL - Desarrollo (rápido)

Instrucciones rápidas para puesta en marcha local.

## Preparar entorno (Windows PowerShell)

1. Crear y activar el entorno virtual (si no existe):

```powershell
python -m venv .venv
& '.\.venv\Scripts\Activate.ps1'
```

2. Verificar que estás usando el python del venv:

```powershell
python -c "import sys; print(sys.executable)"
# Debe mostrar: C:\Users\<tu_usuario>\sigepol-backend\.venv\Scripts\python.exe
```

3. Instalar dependencias (si es la primera vez o después de actualizar `requirements.txt`):

```powershell
pip install -r requirements.txt
```

## Arrancar backend (Django)

Tienes dos opciones:

- Ejecutar explícitamente el python del venv (recomendado):

```powershell
& '.\.venv\Scripts\python.exe' manage.py runserver
```

- O activar el venv y usar `python`:

```powershell
& '.\.venv\Scripts\Activate.ps1'
python manage.py runserver
```

Para evitar equivocaciones puedes usar el script `run-dev.ps1` que se incluye en la raíz del proyecto. Ejecuta desde PowerShell:

```powershell
./run-dev.ps1
```

Este script activará el venv e iniciará el servidor Django.

## Arrancar frontend (Vite)

1. Abrir otra terminal PowerShell y situarse en la carpeta `frontend`:

```powershell
cd frontend
```

2. Instalar dependencias (si no lo has hecho) y ejecutar dev server:

```powershell
npm install
npm run dev
```

El dev server de Vite suele arrancar en `http://localhost:5173/` (si ese puerto está ocupado probará otro). Si no ves la app, confirma que:
- El backend corre (`http://127.0.0.1:8000/`).
- Estás autenticado en la app (el frontend redirige al login si no hay token).

## Notas / Problemas comunes
- Si ves `ModuleNotFoundError: No module named 'django'`, significa que el `python` usado no pertenece al venv. Usa el comando recomendado para forzar el python del venv.
- Si pip muestra `Defaulting to user installation`, activa el venv antes de instalar para evitar instalaciones en la carpeta de usuario.
- Añade dependencias nuevas a `requirements.txt` con la versión (por ejemplo `openpyxl==3.1.5`) para que otros puedan reproducir el entorno.

---

## 🚀 Big Data Module - FASE 2 (Actualizado 9 Dic)

**Status:** ✅ PASO 1-4 COMPLETADOS | ⏳ PASO 5 Próximo

### PASO 3: ETL Pipeline ✅
```bash
POST /api/bigdata/generate-dataset/
# Carga Excel/CSV → dataset_maestro.parquet (15,100 rows)
# Tests: 8/8 PASSING
```

### PASO 4a: Preprocessing Pipeline ✅
```bash
POST /api/bigdata/preprocessing/
# Normaliza datos → dataset_processed.parquet (9D features normalizados)
# Tests: 9/9 PASSING
```

### PASO 4b: ML Training (K-Means) ✅
```bash
POST /api/bigdata/train-kmeans/
# Auto k-selection + Silhouette Score → Modelo ML entrenado
# Tests: 6/6 PASSING
# Archivo: bigdata/train_kmeans.py (203 líneas)
```

### Documentación Completa
- `BIGDATA_MODULE_SUMMARY.md` - Overview completo
- `PASO4_VALIDACION_COMPLETA.md` - Validación técnica detallada
- `PASO4_COMPLETADO.md` - Resumen ejecutivo

---

Si quieres, puedo añadir un alias o un `Makefile`/`ps1` adicional para arrancar frontend + backend en paralelo.
