# 🧪 GUÍA DE TESTING - PASOS 4-6

## Objetivo
Verificar que PASOS 4-6 funcionan correctamente:
1. ✅ Endpoint REST expone /api/analytics/clusters/
2. ✅ Frontend muestra tabla con 1,403 pólizas
3. ✅ Mapeo automático de cluster → nivel de riesgo

---

## 📋 Requisitos Previos

### Backend Configurado
```bash
# Verificar que analytics está en INSTALLED_APPS
grep -n "analytics" c:\Users\luisg\sigepol-backend\sigepol\settings.py

# Resultado esperado:
# INSTALLED_APPS = [..., 'analytics', ...]
```

### URL Configurada
```bash
# Verificar que /api/analytics/ está en URLs
grep -n "analytics" c:\Users\luisg\sigepol-backend\sigepol\urls.py

# Resultado esperado:
# path("api/analytics/", include("analytics.urls"))
```

### Dataset Disponible
```bash
# Verificar que dataset existe
ls -la c:\Users\luisg\sigepol-backend\ml_data\

# Resultado esperado:
# dataset_completo.parquet (existe)
# dataset_completo.csv (existe)
# dataset_completo.json (existe)
```

---

## 🚀 PASO 1: Iniciar Backend

### Abrir Terminal 1 (PowerShell)
```powershell
cd c:\Users\luisg\sigepol-backend

# Activar entorno virtual (si está configurado)
# .\venv\Scripts\Activate.ps1

# Validar Django
python manage.py check

# Resultado esperado:
# System check identified no issues (0 silenced).
```

### Iniciar servidor Django
```powershell
python manage.py runserver

# Resultado esperado:
# Starting development server at http://127.0.0.1:8000/
# Quit the server with CTRL-BREAK.
```

---

## 🚀 PASO 2: Iniciar Frontend

### Abrir Terminal 2 (PowerShell)
```powershell
cd c:\Users\luisg\sigepol-backend\frontend

# Instalar dependencias (si es necesario)
npm install

# Iniciar React
npm start

# Resultado esperado:
# Compiled successfully!
# You can now view sigepol in the browser.
# Local: http://localhost:3000
```

---

## 🧪 PASO 3: Probar Endpoint REST

### Opción A: cURL (Terminal 3)
```bash
# Nota: Reemplaza <TOKEN> con un token JWT válido

curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/analytics/clusters/

# O sin autenticación (si está configurado)
curl http://localhost:8000/api/analytics/clusters/

# Resultado esperado:
# {
#   "total_polizas": 1403,
#   "clusters_identificados": 5,
#   "data": [
#     {
#       "numero_poliza": "X-P-125623",
#       "cliente_nombre": "LANDAETA RIVERA MIGUEL",
#       "monto_uf": 14.32,
#       "estado": "VIGENTE",
#       "total_cobranzas": 1,
#       "total_alertas": 0,
#       "cluster": 2,
#       "nivel_riesgo": "BAJO",
#       "tasa_mora": 0.5
#     },
#     ...
#   ]
# }
```

### Opción B: Postman
```
1. Abrir Postman
2. GET http://localhost:8000/api/analytics/clusters/
3. Headers:
   - Authorization: Bearer <TOKEN>
4. Send
5. Verificar response con 1,403 registros
```

### Opción C: Python Script
```python
import requests
import json

# Obtener token (si es necesario)
login_response = requests.post(
    'http://localhost:8000/api/auth/login/',
    json={'username': 'admin', 'password': 'password'}
)
token = login_response.json()['access']

# Hacer request
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(
    'http://localhost:8000/api/analytics/clusters/',
    headers=headers
)

# Mostrar resultado
print(json.dumps(response.json(), indent=2))
```

---

## 🎨 PASO 4: Probar Frontend

### Navegar a Analytics
```
1. Abrir navegador: http://localhost:3000
2. Iniciar sesión (si es requerido)
3. Navegar a Analytics (menú lateral o URL: /analytics)
```

### Verificar TAB 1: "📊 Pólizas & Riesgo"

#### 4 Risk Cards
```
Buscar estas tarjetas:
✅ BAJO     (verde, 580, 41%)
⚠️ MEDIO    (naranja, 420, 30%)
🔴 ALTO     (rojo, 300, 21%)
🚨 CRÍTICO  (morado, 103, 7%)
```

**Verificación**:
- [ ] 4 tarjetas visibles
- [ ] Números suman 1,403
- [ ] Colores correctos
- [ ] Porcentajes se ven

#### Tabla "Pólizas Clasificadas"
```
Columnas esperadas:
[Póliza] [Cliente] [Monto UF] [Cobranzas] [Alertas] [Mora %] [Cluster] [Nivel Riesgo]

Ejemplo de fila:
X-P-125623 | LANDAETA RIVERA... | $14.32 | 1 | 0 | 50.0% | C2 | BAJO
```

**Verificación**:
- [ ] 8 columnas presentes
- [ ] Datos se cargan sin errores
- [ ] Tabla tiene scroll horizontal (si pantalla pequeña)
- [ ] Filas con bordes de color según riesgo

#### Filtro por Riesgo
```
Dropdown con opciones:
- Mostrar Todos (1403)
- BAJO (580)
- MEDIO (420)
- ALTO (300)
- CRÍTICO (103)
```

**Verificación**:
- [ ] Dropdown aparece
- [ ] Cambiar a "BAJO" muestra solo 580 filas
- [ ] Cambiar a "CRÍTICO" muestra solo 103 filas
- [ ] Cambiar a "Mostrar Todos" vuelve a 1,403
- [ ] Números en dropdown coinciden con tarjetas

### Verificar TAB 2: "📈 Estadísticas"

#### Resumen
```
[Total Pólizas: 1403] [Clusters: 5] [Estado ML: ✅]
```

**Verificación**:
- [ ] Números correctos
- [ ] Estado ML muestra ✅

#### Gráfico Pie
```
Debe mostrar distribución de pólizas por cluster
Colores: #8884d8, #82ca9d, #ffc658, #ff7c7c, #8dd1e1
```

**Verificación**:
- [ ] Gráfico se renderiza
- [ ] 5 slices (un cluster por slice)
- [ ] Labels muestran "C1", "C2", etc.

#### Tabla de Clusters
```
[Cluster] [Pólizas] [%] [Monto Prom] [Tasa Pago] [Alertas] [Riesgo]
C1        280      20% $15.32      85%        2        BAJO
...
```

**Verificación**:
- [ ] Tabla con 5 filas (5 clusters)
- [ ] Números suman correctamente
- [ ] Nivel de riesgo en última columna

### Verificar TAB 3: "🧹 Calidad"

#### Medidor
```
[Datos Limpios: ████████░░ 85%]
```

**Verificación**:
- [ ] Medidor visible
- [ ] Porcentaje entre 0-100%

#### Issues Grid
```
✅ Total Pólizas: 1403
🔴 Datos No Confiables: 0
🟡 Sin Cobranzas: 5
🟡 Sin Vigencia: 0
```

**Verificación**:
- [ ] 4 tarjetas de issues
- [ ] Números son realistas

---

## ✅ CHECKLIST DE TESTING

### PASO 4: Endpoint REST
- [ ] Django server inicia sin errores
- [ ] Endpoint /api/analytics/clusters/ responde (200 OK)
- [ ] Response incluye "total_polizas": 1403
- [ ] Response incluye "clusters_identificados": 5
- [ ] Array "data" tiene 1,403 elementos
- [ ] Cada elemento tiene campos: numero_poliza, cluster, nivel_riesgo
- [ ] nivel_riesgo es uno de: BAJO, MEDIO, ALTO, CRÍTICO
- [ ] No hay errores en logs de Django

### PASO 5: Tabla en Frontend
- [ ] Analytics.jsx se carga sin errores
- [ ] 4 risk cards visibles
- [ ] Números de tarjetas coinciden con totales
- [ ] Tabla "Pólizas Clasificadas" aparece
- [ ] Tabla tiene 1,403 filas (o primeras 50 con scroll)
- [ ] Filtro por riesgo funciona
- [ ] Colores de filas corresponden a riesgo
- [ ] Responsive design funciona (redimensionar ventana)

### PASO 6: Mapeo de Riesgo
- [ ] Cada póliza tiene un nivel_riesgo asignado
- [ ] nivel_riesgo valores: BAJO, MEDIO, ALTO, CRÍTICO
- [ ] Pólizas con alta mora están marcadas CRÍTICO/ALTO
- [ ] Pólizas sin alertas están marcadas BAJO/MEDIO
- [ ] Reglas de negocio se aplican correctamente:
  - [ ] tasa_mora > 50% → CRÍTICO
  - [ ] alertas > 5 → CRÍTICO
  - [ ] tasa_mora > 30% → ALTO
  - [ ] alertas > 2 → ALTO
  - [ ] etc.

---

## 🐛 Troubleshooting

### Problema: "404 Not Found" en /api/analytics/clusters/

**Causa**: URL no configurada
```bash
# Verificar:
1. 'analytics' está en INSTALLED_APPS
2. path("api/analytics/", include("analytics.urls")) en urls.py
3. Reiniciar servidor Django
```

### Problema: "500 Internal Server Error"

**Causa**: Error en backend
```bash
# Revisar logs:
python manage.py runserver
# Buscar traceback en la salida
```

**Solución común**:
```bash
# Verificar que dataset existe
ls ml_data/dataset_completo.parquet

# Si no existe, regenerar:
python prepare_dataset_ml_v2.py
```

### Problema: Tabla vacía en Frontend

**Causa**: No hay autenticación o error en request
```bash
# Verificar en console del navegador (F12)
# Buscar error en Network tab
# GET /api/analytics/clusters/ → Status?

# Solución: Verificar token JWT
```

### Problema: "CORS Error"

**Causa**: Frontend no puede acceder al backend
```python
# En sigepol/settings.py, verificar:
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

---

## 📊 Métricas de Validación

### Expected Output

| Métrica | Valor Esperado | Actual | ✅/❌ |
|---------|---|---|---|
| Total pólizas | 1,403 | | |
| Clusters | 5 | | |
| Riesgo BAJO | ~580 | | |
| Riesgo MEDIO | ~420 | | |
| Riesgo ALTO | ~300 | | |
| Riesgo CRÍTICO | ~103 | | |
| Response time | < 1s | | |
| Tabla rows | 1,403 | | |
| Filtro funciona | Sí | | |

---

## 📝 Reporte de Testing

Después de completar testing, documentar:

```markdown
## PASOS 4-6 Testing Report

### Backend
- [ ] Endpoint responds: ✅
- [ ] Response format correct: ✅
- [ ] All 1,403 records present: ✅
- [ ] Risk levels assigned: ✅
- [ ] No errors in logs: ✅

### Frontend
- [ ] Analytics page loads: ✅
- [ ] Risk cards visible: ✅
- [ ] Table shows data: ✅
- [ ] Filters work: ✅
- [ ] Colors correct: ✅
- [ ] Responsive: ✅

### Risk Mapping
- [ ] CRÍTICO level correct: ✅
- [ ] ALTO level correct: ✅
- [ ] MEDIO level correct: ✅
- [ ] BAJO level correct: ✅

### Overall Status: ✅ PASS
```

---

## 🎯 Siguiente Paso

Si todo testing pasa:
1. Entrenar modelos ML en Google Colab
2. Descargar kmeans_sigepol.pkl y scaler_sigepol.pkl
3. Colocar en analytics/ml/
4. Reiniciar servidor
5. Endpoint comenzará a predecir clusters

---

## 📞 Contacto

Si hay problemas:
1. Revisar logs en terminal
2. Verificar configuración en settings.py
3. Ejecutar `python manage.py check`
4. Revisar console del navegador (F12)
