# Proyecto de Análisis Financiero y Videos de YouTube

Este proyecto es una suite completa de herramientas para el análisis financiero automatizado que combina múltiples APIs para obtener datos de mercado, analizar videos de YouTube con contenido financiero, y generar informes detallados.

## 📋 Descripción General

El proyecto consta de tres componentes principales:

1. **Análisis de Videos de YouTube** (`api_youtube.py`) - Busca y analiza videos financieros de pre-mercado usando IA
2. **Análisis Financiero Automatizado** (`financial_api.py`) - Recopila datos financieros de múltiples fuentes y genera informes
3. **Asistente Financiero por Chat** (`chat.py`) - Chatbot inteligente para consultas financieras

## 🚀 Características Principales

### 📺 Análisis de Videos Financieros
- Búsqueda automática del video más reciente de análisis pre-mercado en canales específicos de YouTube
- Análisis avanzado del contenido del video usando Google Gemini 2.5-flash
- Extracción de información financiera clave: tendencias, datos gráficos, noticias relevantes
- Generación de informes estructurados en formato Markdown

### 📊 Análisis Financiero Integral
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

### 🤖 Asistente Financiero Inteligente
- Chat interactivo con Google Gemini
- Herramientas especializadas para búsqueda financiera y análisis de portafolios
- Configuración avanzada de "pensamiento" para análisis complejos
- Conteo de tokens y optimización de respuestas

## 📁 Estructura del Proyecto

```
Proyecto google/
├── api_youtube.py              # Análisis de videos de YouTube
├── financial_api.py            # API financiera principal
├── chat.py                     # Asistente de chat financiero
├── requirements.txt            # Dependencias del proyecto
├── Informacion_mercado/        # Informes generados
│   ├── AAPL_analisis_financiero.md
│   ├── AMZN_analisis_financiero.md
│   ├── GOOGL_analisis_financiero.md
│   ├── MSFT_analisis_financiero.md
│   ├── TSLA_analisis_financiero.md
│   └── informe_video.md        # Análisis del video más reciente
└── README.md                   # Este archivo
```

## 🔧 Configuración e Instalación

### Prerrequisitos
- Python 3.7 o superior
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

### 2. Análisis Financiero de Empresas

```bash
python financial_api.py
```

**Funcionalidades:**
- Análisis automático de múltiples empresas (AAPL, MSFT, GOOGL, AMZN, TSLA)
- Verificación previa de todas las APIs
- Generación de informes individuales y consolidados
- Pausa estratégica entre consultas para respetar límites de API

**Ejemplo de salida:**
```
--- Iniciando verificación previa de APIs ---
✅ ESTADO: ÉXITO en Alpha Vantage
✅ ESTADO: ÉXITO en Financial Modeling Prep
✅ ESTADO: ÉXITO en Finnhub

Procesando datos para AAPL...
✅ Informe consolidado generado exitosamente en analisis_financiero_consolidado.md
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
