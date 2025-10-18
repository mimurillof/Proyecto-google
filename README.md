# Proyecto de Análisis Financiero Multi-Cliente

Sistema escalable de análisis financiero que procesa portfolios dinámicos de múltiples clientes desde Supabase, generando informes personalizados organizados por cliente.

## 📋 Descripción General

El proyecto consta de tres componentes principales:

1. **Análisis de Videos de YouTube** (`api_youtube.py`) - Analiza videos financieros de pre-mercado usando IA
2. **Análisis Financiero Multi-Cliente** (`financial_api.py`) - Procesa portfolios dinámicos desde Supabase para múltiples clientes
3. **Asistente Financiero por Chat** (`chat.py`) - Chatbot inteligente para consultas financieras
4. **Orquestador** (`orchestrator.py`) - Ejecuta los procesos secuencialmente

## ⭐ Novedades v2.1

- ✅ **Normalización Automática de Tickers**: Convierte BTCUSD→BTC-USD, NVD.F→NVDA automáticamente
- ✅ **Videos en Carpetas de Clientes**: Informes de YouTube se guardan en carpeta de cada cliente
- ✅ **Sin Archivos Locales**: Todo se guarda directamente en Supabase Storage
- ✅ **Multi-Cliente Escalable**: Procesa portfolios de N clientes desde Supabase
- ✅ **Portfolios Dinámicos**: Lee assets desde base de datos (no hardcodeado)
- ✅ **Almacenamiento por Cliente**: Cada cliente tiene su carpeta `portfolio-files/{user_id}/`
- ✅ **Modo Demo**: Testing sin base de datos real

## 🚀 Características Principales

### 📺 Análisis de Videos Financieros
- Búsqueda automática del video más reciente de análisis pre-mercado en canales específicos de YouTube
- Análisis avanzado del contenido del video usando Google Gemini 2.5-flash
- Extracción de información financiera clave: tendencias, datos gráficos, noticias relevantes
- **NUEVO:** Subida automática a carpeta de cada cliente en Supabase Storage
- Generación de informes estructurados en formato Markdown

### 📊 Análisis Financiero Integral
- **NUEVO: Normalización automática de tickers**:
  - Criptomonedas: `BTCUSD` → `BTC-USD`
  - Commodities: `PAXGUSD` → `PAXG-USD`
  - Mercados internacionales: `NVD.F` → `NVDA`
- **Múltiples fuentes de datos**:
  - Alpha Vantage (precios diarios e intradía)
  - Financial Modeling Prep (estados financieros, perfiles de empresa)
  - Yahoo Finance (datos históricos)
  - Finnhub (noticias y cotizaciones)
- **Análisis completo de empresas**:
  - Perfil corporativo y datos generales
  - Estados financieros (ingresos, balance, flujo de caja)
  - Precios históricos e indicadores técnicos
  - Noticias recientes y eventos relevantes
- **Generación de informes consolidados** para múltiples empresas
- **Almacenamiento organizado por cliente** en Supabase Storage

### 🤖 Asistente Financiero Inteligente
- Chat interactivo con Google Gemini
- Herramientas especializadas para búsqueda financiera y análisis de portafolios
- Configuración avanzada de "pensamiento" para análisis complejos
- Conteo de tokens y optimización de respuestas

## 📁 Estructura del Proyecto

```
Proyecto google/
├── api_youtube.py              # Análisis de videos de YouTube
├── financial_api.py            # API financiera principal (v2.1)
├── chat.py                     # Asistente de chat financiero
├── orchestrator.py             # Orquestador de procesos
├── database.py                 # Gestión de base de datos Supabase
├── storage_manager.py          # Gestión de almacenamiento Supabase
├── config.py                   # Configuración centralizada
├── requirements.txt            # Dependencias del proyecto
├── logs/                       # Logs de ejecución del orchestrator
├── MEJORAS_V2.1.md            # Documentación de mejoras v2.1
├── RESUMEN_CAMBIOS.md         # Resumen de cambios v2.0
└── README.md                   # Este archivo

Supabase Storage (portfolio-files):
├── {cliente_id_1}/
│   ├── NVDA_analisis_financiero.md        # Normalizado de NVD.F
│   ├── BTC-USD_analisis_financiero.md     # Normalizado de BTCUSD
│   ├── informe_consolidado.md
│   └── informe_video_premercado.md
├── {cliente_id_2}/
│   └── ...
```

## 🔧 Configuración e Instalación

### Prerrequisitos
- Python 3.7 o superior
- Cuenta de Supabase con tablas `users`, `portfolios`, `assets`
- Bucket de Supabase Storage: `portfolio-files`
- Claves API de:
  - Google Cloud (YouTube Data API v3)
  - Google AI Studio (Gemini API)
  - Alpha Vantage
  - Financial Modeling Prep
  - Finnhub

### Instalación

1. **Clonar o descargar el proyecto**
```bash
git clone [URL_DEL_REPOSITORIO]
cd "Proyecto google"
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar claves API**

**Para api_youtube.py:**
```python
TU_API_KEY = "tu_clave_youtube_api"
GEMINI_API_KEY = "tu_clave_gemini_api"
```

**Para financial_api.py:**
```python
ALPHA_VANTAGE_API_KEY = 'tu_clave_alpha_vantage'
FMP_API_KEY = 'tu_clave_fmp'
FINNHUB_API_KEY = 'tu_clave_finnhub'
```

**Para chat.py:**
```bash
# Configurar variable de entorno
export GOOGLE_API_KEY="tu_clave_gemini_api"
```

## 🎯 Uso

### 1. Análisis de Videos de YouTube

```bash
python api_youtube.py
```

**Funcionalidades:**
- Busca automáticamente el video más reciente con "PRE MERCADO" en el canal XTB LATAM
- Analiza el contenido usando IA avanzada
- Genera un informe detallado en `Informacion_mercado/informe_video.md`

**Ejemplo de salida:**
```
✅ Se encontró el video más reciente: https://www.youtube.com/watch?v=VIDEO_ID
🧠 Activando análisis con Gemini...
✅ Análisis guardado en: Informacion_mercado/informe_video.md
```

### 2. Análisis Financiero Multi-Cliente (NUEVO v2.0)

**Opción A: Procesar todos los clientes activos**
```bash
python financial_api.py
```

**Opción B: Procesar un cliente específico**
```bash
python financial_api.py <user_id>
```

**Opción C: Modo demo (sin base de datos)**
```bash
python financial_api.py --demo
```

**Funcionalidades:**
- Lee portfolios dinámicamente desde Supabase (tablas: users, portfolios, assets)
- Procesa múltiples clientes y múltiples portfolios por cliente
- Genera informes individuales por ticker y consolidados por cliente
- Guarda archivos organizados: `portfolio-files/{user_id}/`
- Modo demo para testing sin afectar la base de datos real

**Ejemplo de salida:**
```
🚀 API FINANCIERA MULTI-CLIENTE - SISTEMA ESCALABLE

============================================================
VERIFICACIÓN PREVIA DE APIs
============================================================
✅ ESTADO: ÉXITO en Alpha Vantage
✅ ESTADO: ÉXITO en Financial Modeling Prep
✅ ESTADO: ÉXITO en Finnhub

🌐 Modo: Todos los Clientes Activos
📊 Total de clientes activos a procesar: 3

🎯 PROCESANDO CLIENTE: Juan Pérez
📂 Total de Portfolios: 2
📊 Total de Assets: 8
🎯 Tickers únicos: 5

[1/5] Procesando AAPL...
✅ Informe de AAPL guardado exitosamente
✅ Informe consolidado guardado exitosamente
```

**Estructura de Base de Datos Requerida:**
```
users (user_id, first_name, last_name, email)
portfolios (portfolio_id, user_id, portfolio_name, description)
assets (asset_id, portfolio_id, asset_symbol, quantity, acquisition_price)
```

### 3. Asistente Financiero por Chat

```bash
python chat.py
```

**Funcionalidades:**
- Chat interactivo con IA especializada en finanzas
- Análisis automático de complejidad de consultas
- Herramientas integradas para búsqueda financiera
- Conteo de tokens en tiempo real

**Ejemplo de uso:**
```
Tú: ¿Cuál es la diferencia entre un bono y una acción?
Asistente: [Respuesta detallada sobre bonos vs acciones]

Tú: Analiza mi portafolio: 60% AAPL, 30% MSFT, 10% GOOGL
🧠 Activando pensamiento profundo para análisis complejo...
Asistente: [Análisis detallado del portafolio]
```

## 📊 Informes Generados

### Análisis de Videos (`informe_video.md`)
- **Resumen Ejecutivo**: Síntesis de hallazgos clave
- **Análisis de Datos y Gráficos**: Interpretación de elementos visuales
- **Contexto Macroeconómico**: Tendencias y factores económicos
- **Impacto de Noticias**: Conexión entre eventos y mercados
- **Perspectivas Pre-Mercado**: Expectativas y factores críticos

### Análisis Financiero de Empresas (`*_analisis_financiero.md`)
- **Perfil Corporativo**: Información general de la empresa
- **Estados Financieros**: Análisis de ingresos, balance y flujo de caja
- **Datos de Precios**: Históricos y tendencias
- **Noticias Recientes**: Eventos relevantes para la empresa

## 🔑 APIs Utilizadas

| API | Propósito | Datos Obtenidos |
|-----|-----------|-----------------|
| **YouTube Data API v3** | Búsqueda de videos | Videos de análisis financiero |
| **Google Gemini** | Análisis de IA | Interpretación de contenido multimodal |
| **Alpha Vantage** | Datos de mercado | Precios diarios e intradía |
| **Financial Modeling Prep** | Datos fundamentales | Estados financieros, perfiles |
| **Yahoo Finance** | Precios históricos | Datos de mercado alternativos |
| **Finnhub** | Noticias financieras | Noticias corporativas y cotizaciones |

## ⚙️ Configuración Avanzada

### Personalización de Empresas
En `financial_api.py`, modifica la lista de empresas a analizar:
```python
tickers_a_procesar = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META']
```

### Configuración de Períodos
Ajusta el rango de fechas para datos históricos:
```python
DIAS_HISTORICOS = 30  # Últimos 30 días
```

### Canal de YouTube Personalizado
Cambia el canal objetivo en `api_youtube.py`:
```python
CHANNEL_ID_XTB = "ID_DEL_CANAL_DESEADO"
CONSULTA_BUSQUEDA = "término de búsqueda"
```

## 🛠️ Mantenimiento y Límites

### Límites de API
- **Alpha Vantage**: 500 llamadas/día (plan gratuito)
- **Financial Modeling Prep**: 250 llamadas/día (plan gratuito)
- **Finnhub**: 60 llamadas/minuto (plan gratuito)
- **YouTube API**: 10,000 unidades/día
- **Gemini API**: Límites según plan

### Pausas Estratégicas
El sistema incluye pausas de 15 segundos entre consultas para respetar los límites de las APIs.

### Verificación de Estado
Todas las APIs se verifican antes de la ejecución para asegurar disponibilidad.

## 🐛 Solución de Problemas

### Errores Comunes

1. **Error de API Key**
   ```
   Error: La variable de entorno GOOGLE_API_KEY no ha sido configurada
   ```
   **Solución**: Configurar correctamente las variables de entorno o claves en el código

2. **Límite de API Excedido**
   ```
   Error HTTP! No se pudo conectar con la API. Detalles: 403 Forbidden
   ```
   **Solución**: Esperar el reset diario del límite o actualizar el plan de API

3. **Video No Encontrado**
   ```
   No se encontró el video. Revisa el mensaje de error de la API
   ```
   **Solución**: Verificar que el canal y términos de búsqueda sean correctos

## 📈 Casos de Uso

### Para Traders e Inversores
- Análisis automático de contenido pre-mercado
- Seguimiento de múltiples empresas
- Alertas de noticias relevantes

### Para Analistas Financieros
- Informes consolidados automatizados
- Análisis de tendencias históricas
- Integración de múltiples fuentes de datos

### Para Investigadores
- Recopilación sistemática de datos financieros
- Análisis de correlaciones entre noticias y precios
- Generación de datasets para análisis cuantitativo

## 🤝 Contribuciones

Para contribuir al proyecto:
1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está disponible bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

## ⚠️ Disclaimer

Este proyecto es para fines educativos y de investigación. La información financiera generada no constituye asesoramiento de inversión. Siempre consulta con profesionales financieros antes de tomar decisiones de inversión.

---

**Última actualización**: Julio 2025
**Versión**: 1.0.0
**Mantenedor**: [Tu nombre]
