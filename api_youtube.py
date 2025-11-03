import datetime
import time
import unicodedata
from typing import List, Optional, cast

import googleapiclient.discovery
import googleapiclient.errors
import google.generativeai as genai

from database import get_clientes_activos
from storage_manager import StorageManager
from config import (
    YOUTUBE_API_KEY,
    GEMINI_API_KEY,
    CHANNEL_ID_XTB,
    CONSULTA_BUSQUEDA,
    validate_configuration,
)


GEMINI_MODEL = "gemini-2.5-flash"
ARCHIVO_PREMERCADO = "informe_video_premercado.md"
ARCHIVO_VISION_MERCADO = "vision de mercado.md"

VISION_SEMANAL_QUERY = "🌐 EN VIVO. VISIÓN semanal de MERCADOS"
CIERRE_SEMANAL_QUERY = "🔒 EN VIVO. Cierre SEMANAL de los MERCADOS"
VISION_SEMANAL_DIAS = {0, 4}  # lunes y viernes


PROMPT_PREMERCADO = """Eres un experto Analista Financiero de Pre-Mercado altamente cualificado y con una profunda comprensión de los mercados globales, la macroeconomía y los eventos noticiosos. Tu objetivo es procesar y analizar rigurosamente contenido audiovisual para derivar información accionable.

Se te proporcionará un video (multimodal, incluyendo datos visuales y textuales) de análisis financiero de pre-mercado. Este video contendrá discusiones, gráficos (ej. velas, volumen, indicadores técnicos), tablas de datos, visualizaciones financieras y menciones de noticias. Tu tarea es interpretar este contenido como un experto en el dominio financiero, aprovechando la comprensión conjunta de texto y elementos visuales.

Genera un informe completo y conciso de análisis financiero de pre-mercado. Para ello, sigue un proceso de razonamiento paso a paso, examinando críticamente la información y su interconexión:

Analiza en detalle todos los gráficos y tablas presentados en el video (ej. gráficos de velas, volúmenes de transacción, indicadores de rendimiento). Extrae los puntos de datos clave, patrones significativos, tendencias y cualquier anomalía relevante para el análisis pre-mercado. Identifica los activos, sectores o mercados específicos a los que se refieren.

A partir del contenido del video (auditivo y visual), identifica y explica las tendencias financieras macroeconómicas actuales y emergentes que se discuten. Esto incluye factores como políticas de bancos centrales, tasas de inflación, datos de empleo, crecimiento del PIB, y flujos de capital, explicando su significado para el mercado.

Sintetiza las noticias y eventos clave (ej. anuncios de resultados, eventos geopolíticos, declaraciones de autoridades económicas) que se mencionan o visualizan en el video. Evalúa la relación directa e indirecta entre estas noticias y las tendencias macroeconómicas identificadas, así como su posible impacto en la apertura o dirección del mercado.

Integra coherentemente todos los hallazgos de los pasos anteriores. Ofrece una síntesis del panorama pre-mercado, incluyendo perspectivas sobre la posible apertura del mercado, la volatilidad esperada, los movimientos sectoriales/accionarios clave y los riesgos u oportunidades a corto plazo.

Entrega el informe en formato Markdown, estructurado con los siguientes encabezados y subsecciones. Sé directo, informativo y evita cualquier introducción o cierre superfluo.

# Informe de Análisis Financiero Pre-Mercado

## I. Resumen Ejecutivo
(Síntesis concisa de los hallazgos más importantes, destacando las implicaciones clave para la apertura del mercado.)

## II. Análisis de Datos y Gráficos

### 2.1. Puntos de Datos Clave y Observaciones Gráficas
(Descripción y análisis de los datos numéricos y patrones visuales extraídos. Incluye referencias a activos o indicadores específicos.)

### 2.2. Patrones, Tendencias y Anomalías
(Interpretación de tendencias a corto plazo, formaciones relevantes en gráficos o cualquier desviación significativa.)

## III. Contexto Macroeconómico

### 3.1. Tendencias Macroeconómicas Identificadas
(Detalle y explicación de las principales tendencias macroeconómicas discutidas.)

### 3.2. Vínculo con Datos de Mercado
(Análisis de cómo las tendencias macroeconómicas se reflejan o impactan los datos y gráficos observados.)

## IV. Impacto de Noticias y Eventos

### 4.1. Noticias y Eventos Relevantes
(Listado y explicación concisa de las noticias/eventos clave con su relevancia para el mercado.)

### 4.2. Conexión Noticia-Macro-Mercado
(Análisis de cómo estas noticias interactúan con las tendencias macroeconómicas y los posibles movimientos del mercado.)

## V. Perspectivas Pre-Mercado y Puntos Clave

### 5.1. Expectativas de Apertura y Movimientos Anticipados
(Pronósticos fundamentados sobre la posible dirección y volatilidad del mercado al abrir.)

### 5.2. Factores Críticos a Monitorear
(Lista de elementos o eventos específicos que deben ser observados de cerca durante la sesión.)

Omite estrictamente cualquier información no relevante o superflua del video, como saludos iniciales o finales del presentador, comentarios personales ajenos al análisis, pausas, chistes, auto-promociones o cualquier contenido que no contribuya directamente al análisis financiero solicitado en el informe. Concéntrate únicamente en la información de valor para el informe y la comprensión del mercado."""


PROMPT_VISION_SEMANAL = """Actúa como estratega jefe de mercados globales con foco en perspectivas semanales. Recibirás el video multimodal "Visión semanal de mercados" y debes construir un informe que integre visión macro, drivers sectoriales, riesgos y oportunidades tácticas.

Redacta en Markdown utilizando esta estructura:

# Visión Semanal de Mercados

## Resumen Ejecutivo
- Conecta los mensajes clave del video con el posicionamiento para la semana.

## Tendencias Globales y Macroeconómicas
- Identifica macro-temas y explica su impacto esperado.

## Sectores y Activos Relevantes
- Destaca activos, índices, divisas o commodities discutidos y su tesis operativa.

## Catalizadores Próximos
- Enumera eventos o publicaciones que se deben monitorear.

## Estrategia Operativa
- Señala oportunidades, riesgos y recomendaciones tácticas.

Omite saludos o autopromoción del presentador y prioriza información accionable."""


PROMPT_CIERRE_SEMANAL = """Eres un analista senior responsable del informe "Cierre semanal de los mercados". Debes sintetizar resultados de la semana, drivers que explican los movimientos y qué prepara el terreno para la próxima.

Responde en Markdown con la siguiente estructura:

# Cierre Semanal de Mercados

## Resumen Numérico
- Resume movimientos semanales clave (índices, divisas, commodities) mencionados.

## Drivers Principales
- Explica factores macro, corporativos o geopolíticos destacados.

## Lecciones de la Semana
- Lista aprendizajes o señales relevantes para la estrategia.

## Repercusiones Futuras
- Describe cómo los eventos de la semana condicionan la próxima.

## Checklist para la Próxima Semana
- Detalla elementos que el equipo debe vigilar.

Sé directo, preciso y deja fuera cualquier comentario no financiero del presentador."""


def limpiar_texto_busqueda(texto: str) -> str:
    """Normaliza un texto eliminando signos y diacríticos para comparaciones flexibles."""
    if not texto:
        return ""

    normalizado = unicodedata.normalize("NFKD", texto)
    filtrado = "".join(
        ch for ch in normalizado if ch.isalnum() or ch.isspace() or ch in ".-"
    )
    return " ".join(filtrado.lower().split())


def buscar_video_reciente_en_canal(api_key: str, channel_id: str, query: str, max_results: int = 5) -> Optional[str]:
    """Devuelve la URL del video más reciente que coincide con la búsqueda."""
    api_service_name = "youtube"
    api_version = "v3"

    try:
        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, developerKey=api_key
        )

        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            q=query,
            order="date",
            type="video",
            maxResults=max(1, min(max_results, 50)),
        )
        response = request.execute()

        if "error" in response:
            error_details = response["error"]["errors"][0]
            print("---------------------------------------------------------")
            print("¡ERROR! La API de YouTube devolvió el siguiente mensaje:")
            print(f"  Razón: {error_details.get('reason')}")
            print(f"  Mensaje: {error_details.get('message')}")
            print("---------------------------------------------------------")
            return None

        items = response.get("items", [])
        if not items:
            return None

        criterio = limpiar_texto_busqueda(query)
        for item in items:
            titulo = item.get("snippet", {}).get("title", "")
            titulo_limpio = limpiar_texto_busqueda(titulo)
            if not criterio or criterio in titulo_limpio:
                video_id = item["id"]["videoId"]
                return f"https://www.youtube.com/watch?v={video_id}"

        # Si ninguno coincide exactamente con el criterio, devolver el más reciente
        video_id = items[0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
        return None

    except googleapiclient.errors.HttpError as e:
        print("---------------------------------------------------------")
        print("¡ERROR HTTP! No se pudo conectar con la API.")
        print(f"Detalles: {e.reason} - {e.error_details}")
        print("---------------------------------------------------------")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado en el script: {e}")
        return None


def buscar_video_reciente_con_fallback(api_key: str, channel_id: str, consultas: List[str]) -> Optional[str]:
    """Intenta varias consultas hasta localizar un video."""
    for idx, consulta in enumerate(consultas, start=1):
        if not consulta:
            continue
        url = buscar_video_reciente_en_canal(api_key, channel_id, consulta)
        if url:
            if idx > 1:
                print(
                    f"⚠️  Video encontrado utilizando consulta alternativa '{consulta}'."
                )
            return url
    return None


def analizar_video_con_gemini(gemini_api_key: str, video_url: str, prompt: str) -> Optional[str]:
    """Analiza un video de YouTube usando Gemini con el prompt indicado."""
    try:
        genai.configure(api_key=gemini_api_key)  # type: ignore[attr-defined]

        print("Enviando video a Gemini para análisis...")
        print("Esto puede tomar algunos minutos...")

        model = genai.GenerativeModel(GEMINI_MODEL)  # type: ignore[attr-defined]
        response = model.generate_content([video_url, prompt])
        return response.text

    except Exception as e:
        print("---------------------------------------------------------")
        print("¡ERROR! No se pudo analizar el video con Gemini.")
        print(f"Detalles del error: {e}")
        print("---------------------------------------------------------")
        return None


def esperar_intervalo(segundos: int, ultimo_intento: Optional[float]) -> None:
    """Bloquea la ejecución hasta cumplir el intervalo deseado entre peticiones."""
    if ultimo_intento is None:
        return

    restante = segundos - (time.time() - ultimo_intento)
    if restante > 0:
        print(f"Esperando {int(restante)} segundos antes del siguiente análisis...")
        time.sleep(restante)


def subir_informe_para_clientes(clientes, contenido: str, nombre_archivo: str) -> None:
    """Sube el contenido dado al storage de Supabase para cada cliente activo."""
    if not clientes:
        print("⚠️  No se encontraron clientes activos en la base de datos. Se omite la subida.")
        return

    storage = StorageManager()
    print(f"\n📊 Subiendo '{nombre_archivo}' para {len(clientes)} clientes activos...\n")

    exitosos = 0
    fallidos = 0

    for idx, cliente in enumerate(clientes, 1):
        print(f"[{idx}/{len(clientes)}] Subiendo para cliente: {cliente.nombre_completo} ({cliente.user_id})...")
        try:
            exito = storage.subir_texto(
                contenido_texto=contenido,
                nombre_archivo=nombre_archivo,
                cliente_id=cliente.user_id,
                content_type="text/markdown; charset=utf-8",
            )
        except Exception as err:
            exito = False
            print(f"    ❌ Error inesperado: {err}")

        if exito:
            exitosos += 1
            print(f"    ✅ Subido exitosamente a carpeta: {cliente.user_id}/")
        else:
            fallidos += 1
            print(f"    ❌ Error al subir para cliente {cliente.user_id}")

    print("\n" + "=" * 60)
    print("RESUMEN DE SUBIDA")
    print("=" * 60)
    print(f"✅ Exitosos: {exitosos}")
    print(f"❌ Fallidos: {fallidos}")
    print("=" * 60)


def crear_informe_vision_mercado(resultados: List[dict]) -> str:
    """Construye el Markdown consolidado para 'vision de mercado.md'."""
    lineas: List[str] = ["# Informe Visión de Mercado", ""]

    for indice, resultado in enumerate(resultados):
        lineas.extend(
            [
                f"## {resultado['titulo']}",
                f"- Video analizado: {resultado['url']}",
                "",
                resultado["analisis"].strip(),
            ]
        )

        if indice < len(resultados) - 1:
            lineas.extend(["", "---", ""])

    return "\n".join(lineas).strip()


def es_dia_vision_semanal(fecha: Optional[datetime.datetime] = None) -> bool:
    """Determina si se debe procesar la visión semanal para la fecha dada."""
    ref = fecha or datetime.datetime.now()
    return ref.weekday() in VISION_SEMANAL_DIAS


def main():
    print("✅ Configuración cargada desde .env")

    if not validate_configuration():
        print("❌ Error: Configuración incompleta. Verifica tu archivo .env")
        raise SystemExit(1)

    clientes = get_clientes_activos()
    ultimo_intento: Optional[float] = None

    if YOUTUBE_API_KEY is None or CHANNEL_ID_XTB is None or GEMINI_API_KEY is None:
        print("❌ Error: claves críticas no disponibles tras la validación.")
        raise SystemExit(1)

    youtube_key = cast(str, YOUTUBE_API_KEY)
    channel_id = cast(str, CHANNEL_ID_XTB)
    gemini_key = cast(str, GEMINI_API_KEY)
    consulta_premercado = CONSULTA_BUSQUEDA or ""

    if not consulta_premercado:
        print("⚠️  CONSULTA_BUSQUEDA no está configurada. Se utilizará búsqueda vacía.")

    print("Buscando el video de pre-mercado más reciente...")
    url_premercado = buscar_video_reciente_en_canal(
        youtube_key, channel_id, consulta_premercado
    )

    if url_premercado:
        print(f"\nÉxito. Se encontró el video de pre-mercado: {url_premercado}")
        print("\n" + "=" * 60)
        print("INICIANDO ANÁLISIS DE PRE-MERCADO CON GEMINI")
        print("=" * 60)

        analisis_premercado = analizar_video_con_gemini(
            gemini_key, url_premercado, PROMPT_PREMERCADO
        )
        ultimo_intento = time.time()

        if analisis_premercado:
            print("\n" + "=" * 60)
            print("ANÁLISIS FINANCIERO PRE-MERCADO COMPLETADO")
            print("=" * 60)
            subir_informe_para_clientes(clientes, analisis_premercado, ARCHIVO_PREMERCADO)
        else:
            print("\nNo se pudo completar el análisis de pre-mercado con Gemini.")
    else:
        print("\nNo se encontró el video de pre-mercado. Se omite el análisis diario.")

    if not es_dia_vision_semanal():
        print("\nHoy no corresponde procesar 'Visión de Mercado'.")
        return

    print("\n" + "=" * 60)
    print("INICIANDO BLOQUE VISIÓN DE MERCADO")
    print("=" * 60)

    configuraciones_semana = [
        {
            "titulo": VISION_SEMANAL_QUERY,
            "consultas": [
                VISION_SEMANAL_QUERY,
                "EN VIVO. VISIÓN semanal de los MERCADOS",
                "VISIÓN semanal de MERCADOS",
                "vision semanal mercados",
            ],
            "prompt": PROMPT_VISION_SEMANAL,
        },
        {
            "titulo": CIERRE_SEMANAL_QUERY,
            "consultas": [
                CIERRE_SEMANAL_QUERY,
                "EN VIVO. Cierre SEMANAL de los MERCADOS",
                "Cierre SEMANAL de los MERCADOS",
                "cierre semanal mercados",
            ],
            "prompt": PROMPT_CIERRE_SEMANAL,
        },
    ]

    resultados: List[dict] = []

    for indice, configuracion in enumerate(configuraciones_semana):
        esperar_intervalo(30, ultimo_intento)

        titulo = configuracion["titulo"]
        print(f"\nBuscando el video '{titulo}'...")

        url_video = buscar_video_reciente_con_fallback(
            youtube_key, channel_id, configuracion["consultas"]
        )

        if not url_video:
            print(f"⚠️  No se encontró un video coincidente para '{titulo}'.")
            continue

        print(f"Video localizado: {url_video}")
        analisis = analizar_video_con_gemini(
            gemini_key, url_video, configuracion["prompt"]
        )
        ultimo_intento = time.time()

        if analisis:
            resultados.append(
                {"titulo": titulo, "url": url_video, "analisis": analisis}
            )
        else:
            print(f"⚠️  No se pudo obtener el análisis de '{titulo}'.")

    if not resultados:
        print("\nNo se generaron análisis para 'Visión de Mercado'.")
        return

    informe_vision = crear_informe_vision_mercado(resultados)
    subir_informe_para_clientes(clientes, informe_vision, ARCHIVO_VISION_MERCADO)


if __name__ == "__main__":
    main()