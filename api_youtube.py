# 2.  **Obtener una clave de API de YouTube:** Si aún no la tienes, sigue los pasos que mencionaste:
#     *   Ve a la [Consola de Google Cloud](https://console.cloud.google.com/).
#     *   Crea un nuevo proyecto o selecciona uno existente.
#     *   Habilita la API de Datos de YouTube v3 para tu proyecto.
#     *   Crea credenciales (una clave de API).
# 3.  **Reemplazar `"TU_CLAVE_DE_API"`** en el script con tu clave de API real.
#
# **Explicación del script:**
#
# *   Importa la biblioteca `googleapiclient.discovery`.
# *   Define la función `buscar_video_reciente_en_canal` que encapsula la lógica de búsqueda.
# *   Dentro de la función, se construye el objeto de servicio de YouTube utilizando tu clave de API.
# *   Se crea la solicitud `youtube.search().list()` con los parámetros exactos que especificaste:
#     *   `part="snippet"`: Para obtener la información básica.
#     *   `channelId=channel_id`: Para restringir la búsqueda al canal especificado.
#     *   `q=query`: Para buscar la cadena de texto en el título.
#     *   `order="date"`: **Este es el parámetro clave para obtener el video más reciente.**
#     *   `type="video"`: Para asegurar que solo se busquen videos.
#     *   `maxResults=1`: Para obtener solo el primer resultado (el más reciente).
# *   Se ejecuta la solicitud y se obtiene la respuesta.
# *   Se verifica si la lista `items` en la respuesta no está vacía.
# *   Si hay resultados, se extrae el `videoId` del primer elemento (que es el más reciente).
# *   Se construye la URL completa del video utilizando el `videoId`.
# *   La función devuelve la URL del video o `None` si no se encontraron resultados.
# *   En la parte principal del script (`if __name__ == "__main__":`), se definen tu clave de API, el ID del canal de XTB y la consulta de búsqueda.
# *   Se llama a la función `buscar_video_reciente_en_canal` con estos parámetros.
# *   Finalmente, se imprime la URL del video encontrado o un mensaje indicando que no se encontró ninguno.
#
# Este script sigue exactamente los pasos que describiste para encontrar el video más reciente con el título específico en el canal de XTB LATAM.

import googleapiclient.discovery
import googleapiclient.errors
import google.generativeai as genai
import os
import io
import tempfile
from supabase import create_client, Client
from config import (
    YOUTUBE_API_KEY, GEMINI_API_KEY, 
    SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE, SUPABASE_BUCKET_NAME, SUPABASE_BASE_PREFIX,
    CHANNEL_ID_XTB, CONSULTA_BUSQUEDA,
    validate_configuration
)

def buscar_video_reciente_en_canal(api_key, channel_id, query):
    """
    Busca el video más reciente en un canal específico de YouTube
    que coincida con una consulta de búsqueda en el título.

    Args:
        api_key (str): Tu clave de API de YouTube.
        channel_id (str): El ID del canal de YouTube donde buscar.
        query (str): La cadena de texto a buscar en el título del video.

    Returns:
        str or None: La URL del video más reciente encontrado, o None si no se encuentra ninguno.
    """
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
            maxResults=1,
        )
        response = request.execute()

        # --- NUEVA VERIFICACIÓN DE ERRORES ---
        # Revisa si la respuesta de la API contiene un objeto de error
        if 'error' in response:
            error_details = response['error']['errors'][0]
            print("---------------------------------------------------------")
            print("¡ERROR! La API de YouTube devolvió el siguiente mensaje:")
            print(f"  Razón: {error_details.get('reason')}")
            print(f"  Mensaje: {error_details.get('message')}")
            print("---------------------------------------------------------")
            return None

        items = response.get("items", [])
        if items:
            video_id = items[0]["id"]["videoId"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return video_url
        else:
            return None

    # Este bloque atrapará errores a nivel de HTTP (ej. 403 Forbidden)
    except googleapiclient.errors.HttpError as e:
        print("---------------------------------------------------------")
        print(f"¡ERROR HTTP! No se pudo conectar con la API.")
        print(f"Detalles: {e.reason} - {e.error_details}")
        print("---------------------------------------------------------")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado en el script: {e}")
        return None

def analizar_video_con_gemini(gemini_api_key, video_url):
    """
    Analiza un video de YouTube usando Gemini 2.5-flash.
    
    Args:
        gemini_api_key (str): Tu clave de API de Gemini.
        video_url (str): La URL del video de YouTube a analizar.
    
    Returns:
        str or None: El análisis del video generado por Gemini, o None si hay error.
    """
    
    # Prompt especializado para análisis financiero de pre-mercado
    prompt_analisis = """Eres un experto Analista Financiero de Pre-Mercado altamente cualificado y con una profunda comprensión de los mercados globales, la macroeconomía y los eventos noticiosos. Tu objetivo es procesar y analizar rigurosamente contenido audiovisual para derivar información accionable.

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

    try:
        # Configurar la API key
        genai.configure(api_key=gemini_api_key)
        
        print("Enviando video a Gemini para análisis...")
        print("Esto puede tomar algunos minutos...")
        
        # Crear el modelo
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Realizar la solicitud a Gemini
        response = model.generate_content([video_url, prompt_analisis])
        
        return response.text
        
    except Exception as e:
        print("---------------------------------------------------------")
        print(f"¡ERROR! No se pudo analizar el video con Gemini.")
        print(f"Detalles del error: {e}")
        print("---------------------------------------------------------")
        return None

# --- Supabase helpers ---
def existe_archivo_en_supabase(nombre_archivo_remoto):
    """
    Verifica si un archivo existe en el bucket/prefijo configurado.

    Returns:
        bool: True si existe, False si no existe o en error.
    """
    try:
        supabase_key = SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY
        supabase: Client = create_client(SUPABASE_URL, supabase_key)
        carpeta = SUPABASE_BASE_PREFIX or ""
        # Listar en la carpeta (o raíz si vacío) y buscar por nombre
        if carpeta:
            items = supabase.storage.from_(SUPABASE_BUCKET_NAME).list(path=carpeta)
        else:
            items = supabase.storage.from_(SUPABASE_BUCKET_NAME).list()
        if not items:
            return False
        return any(getattr(it, "name", None) == nombre_archivo_remoto or (isinstance(it, dict) and it.get("name") == nombre_archivo_remoto) for it in items)
    except Exception:
        # En caso de duda, retornamos False y dejamos que upsert maneje creación/actualización
        return False

def subir_texto_a_supabase(contenido_texto, nombre_archivo_remoto):
    """
    Sube contenido de texto directamente (sin crear archivo local) a Supabase Storage
    utilizando variables de entorno:
      - SUPABASE_URL
      - SUPABASE_ANON_KEY
      - SUPABASE_BUCKET
      - SUPABASE_FOLDER (opcional)

    Args:
        contenido_texto (str): Contenido a subir en formato texto.
        nombre_archivo_remoto (str): Nombre del archivo remoto (sin carpeta).

    Returns:
        bool: True si subió correctamente, False en caso contrario.
    """
    supabase_url = SUPABASE_URL
    supabase_key = SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY
    supabase_bucket = SUPABASE_BUCKET_NAME
    supabase_folder = SUPABASE_BASE_PREFIX

    if not supabase_url or not supabase_key or not supabase_bucket:
        print("---------------------------------------------------------")
        print("Faltan configuraciones de Supabase.")
        print("Verifica tu archivo .env y que contenga todas las variables de Supabase.")
        print("---------------------------------------------------------")
        return False

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        ruta_remota = f"{supabase_folder}/{nombre_archivo_remoto}" if supabase_folder else nombre_archivo_remoto

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp:
                tmp.write(contenido_texto)
                temp_path = tmp.name

            ya_existia = existe_archivo_en_supabase(nombre_archivo_remoto)

            _ = supabase.storage.from_(supabase_bucket).upload(
                path=ruta_remota,
                file=temp_path,
                file_options={
                    "cacheControl": "3600",
                    "upsert": "true",
                    "contentType": "text/markdown; charset=utf-8",
                },
            )

            accion = "actualizado" if ya_existia else "creado"
            print(f"\n✅ Archivo {accion} en Supabase: bucket='{supabase_bucket}', path='{ruta_remota}'")
            return True
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
    except Exception as e:
        print("---------------------------------------------------------")
        print("¡ERROR! No se pudo subir el archivo a Supabase.")
        print(f"Detalles del error: {e}")
        print("---------------------------------------------------------")
        return False

# --- Configuración ---
# Las claves API se cargan desde el archivo .env a través del módulo config
# Las variables ya están cargadas desde el módulo config
print("✅ Configuración cargada desde .env")

# Validar configuración al inicio
if not validate_configuration():
    print("❌ Error: Configuración incompleta. Verifica tu archivo .env")
    exit(1)

# --- Ejecutar la búsqueda ---
print("Buscando el video más reciente...")
url_video_encontrado = buscar_video_reciente_en_canal(YOUTUBE_API_KEY, CHANNEL_ID_XTB, CONSULTA_BUSQUEDA)

# --- Mostrar el resultado y analizar con Gemini ---
if url_video_encontrado:
    print(f"\nÉxito. Se encontró el video más reciente: {url_video_encontrado}")
    
    # Analizar el video con Gemini
    print("\n" + "="*60)
    print("INICIANDO ANÁLISIS CON GEMINI")
    print("="*60)
    
    analisis_gemini = analizar_video_con_gemini(GEMINI_API_KEY, url_video_encontrado)
    
    if analisis_gemini:
        print("\n" + "="*60)
        print("ANÁLISIS FINANCIERO PRE-MERCADO COMPLETADO")
        print("="*60)
        print(analisis_gemini)

        # Subir directamente a Supabase Storage (sin escribir archivo local)
        print("\nSubiendo informe a Supabase Storage...")
        nombre_remoto = "informe_video.md"
        exito = subir_texto_a_supabase(analisis_gemini, nombre_remoto)
        if not exito:
            print("No se pudo subir el informe a Supabase. Verifica configuración y permisos.")
        
    else:
        print("\nNo se pudo completar el análisis con Gemini. Revisa tu clave API y conexión.")
        
else:
    print(f"\nNo se encontró el video. Revisa el mensaje de error de la API de arriba.")
    print("Asegúrate de que la API de YouTube v3 esté habilitada en tu proyecto de Google Cloud.")