# Mejoras v2.1 - Sistema Multi-Cliente

## 🔧 Problemas Corregidos

### 1. ✅ Normalización Automática de Tickers

**Problema:** Los tickers en la base de datos tenían formatos inconsistentes que causaban errores al consultar las APIs:
- `BTCUSD` → API no encontraba datos (debería ser `BTC-USD`)
- `PAXGUSD` → API no encontraba datos (debería ser `PAXG-USD`)  
- `NVD.F` → API no encontraba datos (debería ser `NVDA`)

**Solución Implementada:**

Se agregó la función `normalizar_ticker()` en `financial_api.py` que:

1. **Mapeo de Criptomonedas:** Convierte formatos como `BTCUSD` → `BTC-USD`
   - Soporta: BTC, ETH, ADA, SOL, DOT, DOGE, MATIC, XRP, LINK, LTC, UNI, XLM

2. **Mapeo de Commodities:** Convierte formatos como `PAXGUSD` → `PAXG-USD`
   - Soporta: PAXG, GOLD, SILVER, XAU, XAG

3. **Remoción de Sufijos de Mercado:** Elimina sufijos internacionales
   - `.F` (Frankfurt) → `NVD.F` → `NVDA`
   - `.DE`, `.L`, `.PA`, `.AS`, `.MI`, `.MC`, `.SW`, `.TO`, `.AX`, `.HK`, `.T`

4. **Mapeo Específico:** Para tickers conocidos problemáticos
   - `NVD.F` → `NVDA`
   - `GOOGL.F` → `GOOGL`
   - `AAPL.F` → `AAPL`

**Logs Informativos:**
```
🔄 Ticker normalizado (crypto): BTCUSD -> BTC-USD
🔄 Ticker normalizado (commodity): PAXGUSD -> PAXG-USD
🔄 Ticker normalizado (sufijo): NVD.F -> NVDA
```

---

### 2. ✅ Videos de YouTube en Carpetas de Clientes

**Problema:** Los informes de videos de YouTube se guardaban en una carpeta genérica en lugar de organizarse por cliente.

**Solución Implementada:**

Modificaciones en `api_youtube.py`:

1. **Nueva Importación:** Ahora usa `StorageManager` y `get_clientes_activos()`
2. **Procesamiento Multi-Cliente:** El informe se sube a la carpeta de cada cliente activo
3. **Sin Archivos Locales:** Todo se sube directamente a Supabase Storage

**Estructura de Archivos Resultante:**
```
portfolio-files/
├── {cliente_id_1}/
│   ├── AAPL_analisis_financiero.md
│   ├── GOOGL_analisis_financiero.md
│   ├── informe_consolidado.md
│   └── informe_video_premercado.md  ← NUEVO
├── {cliente_id_2}/
│   ├── ...
│   └── informe_video_premercado.md  ← NUEVO
```

**Logs Informativos:**
```
📊 Subiendo informe para 2 clientes activos...

[1/2] Subiendo para cliente: Miguel Angel Murillo Frias...
    ✅ Subido exitosamente a carpeta: 238ff453-ab78-42de-9b54-a63980ff56e3/

[2/2] Subiendo para cliente: Juan Pérez...
    ✅ Subido exitosamente a carpeta: abc123.../

RESUMEN DE SUBIDA
✅ Exitosos: 2
❌ Fallidos: 0
```

---

### 3. ✅ Eliminación de Archivos Locales

**Problema:** El sistema podía crear archivos locales durante el deployment.

**Solución Implementada:**

1. **`api_youtube.py`:** 
   - ❌ ANTES: Usaba `open()` para guardar `informe_video.md` localmente
   - ✅ AHORA: Usa `StorageManager.subir_texto()` directamente a Supabase

2. **`financial_api.py`:** 
   - ✅ YA CORRECTO: Siempre usó `StorageManager` sin archivos locales

3. **`orchestrator.py`:** 
   - ✅ CORRECTO: Solo guarda logs locales en carpeta `logs/` (necesario para debugging)

**Resultado:** Cero archivos de datos guardados localmente, todo en Supabase Storage.

---

## 📊 Funcionalidades Verificadas

### Sistema Multi-Cliente

✅ **Base de Datos:**
- Lee de tablas: `users` → `portfolios` → `assets`
- Carga lazy de portfolios y assets
- Soporte para múltiples portfolios por cliente
- Dataclasses: `Cliente`, `Portfolio`, `Asset`

✅ **Storage Manager:**
- Organización por cliente: `portfolio-files/{user_id}/`
- Operaciones: subir, descargar, listar, eliminar
- Manejo automático de upsert
- Sin dependencia de archivos temporales

✅ **Financial API:**
- Procesamiento secuencial de clientes
- Normalización automática de tickers
- Pausas entre requests para respetar límites de API
- Informe consolidado por cliente
- Modo demo con portfolio hardcodeado

✅ **YouTube API:**
- Búsqueda de videos más recientes
- Análisis con Gemini Flash 2.5
- Subida multi-cliente automática
- Manejo de errores y validación

✅ **Orchestrator:**
- Ejecución secuencial: `api_youtube.py` → `financial_api.py`
- Logs detallados por paso
- Configuración UTF-8 para Windows
- Manejo de errores y timeouts

---

## 🚀 Modo de Uso

### Procesamiento Financiero

```bash
# Procesar todos los clientes activos
python financial_api.py

# Procesar un cliente específico
python financial_api.py <user_id>

# Modo demo (sin base de datos)
python financial_api.py --demo
```

### Videos de YouTube

```bash
# Procesa automáticamente para todos los clientes
python api_youtube.py
```

### Orquestador Completo

```bash
# Ejecuta ambos procesos secuencialmente
python orchestrator.py
```

---

## 📁 Estructura de Archivos en Supabase

```
portfolio-files/
├── 238ff453-ab78-42de-9b54-a63980ff56e3/
│   ├── .gitkeep
│   ├── NVDA_analisis_financiero.md          ← Normalizado de NVD.F
│   ├── BTC-USD_analisis_financiero.md       ← Normalizado de BTCUSD
│   ├── PAXG-USD_analisis_financiero.md      ← Normalizado de PAXGUSD
│   ├── informe_consolidado.md
│   └── informe_video_premercado.md
├── otro-cliente-uuid/
│   └── ...
```

---

## 🔍 Ejemplos de Normalización

| Ticker BD | Ticker Normalizado | Tipo |
|-----------|-------------------|------|
| `BTCUSD` | `BTC-USD` | Crypto |
| `ETHUSD` | `ETH-USD` | Crypto |
| `PAXGUSD` | `PAXG-USD` | Commodity |
| `NVD.F` | `NVDA` | Mercado (Frankfurt) |
| `AAPL.DE` | `AAPL` | Mercado (Alemania) |
| `GOOGL.F` | `GOOGL` | Mercado (Frankfurt) |
| `NVDA` | `NVDA` | Sin cambios |

---

## ⚙️ Variables de Entorno Requeridas

```env
# YouTube & Gemini
YOUTUBE_API_KEY=...
GEMINI_API_KEY=...
CHANNEL_ID_XTB=...
CONSULTA_BUSQUEDA=...

# Financial APIs
ALPHA_VANTAGE_API_KEY=...
FMP_API_KEY=...
FINNHUB_API_KEY=...

# Supabase
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE=...
SUPABASE_BUCKET_NAME=portfolio-files

# Configuración
DIAS_HISTORICOS=365
```

---

## 📝 Logging y Debugging

### Logs de Normalización
```python
logger.info(f"🔄 Ticker normalizado (crypto): BTCUSD -> BTC-USD")
logger.info(f"🔄 Ticker normalizado (sufijo): NVD.F -> NVDA")
logger.debug(f"✓ Ticker sin cambios: NVDA")
```

### Logs de Storage
```python
logger.info(f"✅ Archivo creado: bucket='portfolio-files', path='238ff.../NVDA_analisis_financiero.md'")
```

### Logs del Orchestrator
Archivos en carpeta `logs/` con formato:
```
20251018_082934_financial_api.log
20251018_082934_api_youtube.log
```

---

## 🎯 Próximos Pasos Sugeridos

1. **✅ COMPLETADO** - Normalización de tickers
2. **✅ COMPLETADO** - Videos de YouTube en carpetas de clientes
3. **✅ COMPLETADO** - Eliminación de archivos locales
4. **Pendiente** - Añadir más mapeos de tickers según necesidad
5. **Pendiente** - Implementar caché de datos para reducir llamadas API
6. **Pendiente** - Dashboard web para visualizar informes
7. **Pendiente** - Notificaciones por email cuando se generan informes
8. **Pendiente** - Scheduler automático (cron job para ejecutar orchestrator)

---

## 📌 Notas Técnicas

- **Python:** 3.7+
- **Dependencias:** supabase, yfinance, pandas, requests, google-generativeai
- **Límites API:** Pausas de 15 segundos entre tickers para respetar límites
- **Encoding:** UTF-8 configurado para Windows
- **Storage:** Sin archivos temporales permanentes, todo en memoria
- **Database:** Lazy loading de relaciones para optimizar queries

---

**Versión:** 2.1  
**Fecha:** 18 de octubre de 2025  
**Estado:** ✅ Producción
