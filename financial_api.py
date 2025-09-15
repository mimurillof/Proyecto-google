import requests
import pandas as pd
import json # Para pretty print si es necesario
import yfinance as yf
import datetime
import time
import os
import tempfile
from supabase import create_client, Client
from config import (
    ALPHA_VANTAGE_API_KEY, FMP_API_KEY, FINNHUB_API_KEY, DEFAULT_TICKER, DIAS_HISTORICOS,
    SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE, SUPABASE_BUCKET_NAME, SUPABASE_BASE_PREFIX
)

# --- 1. Configuración Global ---
# Las claves API se cargan desde el archivo .env a través del módulo config
print("✅ Claves API financieras cargadas desde .env")

# Símbolo de la empresa a analizar
TICKER = DEFAULT_TICKER

# Rango de fechas para datos históricos de precios y noticias
FECHA_FIN = datetime.date.today()
FECHA_INICIO = FECHA_FIN - datetime.timedelta(days=DIAS_HISTORICOS)

# --- 2. Funciones de Acceso a APIs ---

def get_alpha_vantage_daily_prices(ticker, api_key, output_size='compact'):
    """
    Obtiene datos de precios diarios de Alpha Vantage.
    'compact' para los últimos 100 días, 'full' para 20+ años (puede estar limitado en plan gratuito).
    """
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize={output_size}&apikey={api_key}"
    print(f"Llamando a Alpha Vantage (Daily): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status() # Lanza una excepción para errores HTTP
        data = response.json()
        if "Time Series (Daily)" in data:
            df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
            df = df.rename(columns={
                '1. open': 'Open', '2. high': 'High', '3. low': 'Low',
                '4. close': 'Close', '5. volume': 'Volume'
            })
            df.index = pd.to_datetime(df.index)
            df = df.sort_index(ascending=True)
            return df
        else:
            print(f"Error o límite alcanzado en Alpha Vantage (Daily): {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Alpha Vantage (Daily): {e}")
        return None

def get_alpha_vantage_intraday_prices(ticker, api_key, interval='5min', output_size='compact'):
    """
    Obtiene datos de precios intradía de Alpha Vantage (para posible pre-mercado).
    Los datos de pre-mercado suelen requerir interval=1min y/o el parámetro 'extended_hours' si está disponible.
    En planes gratuitos, esto puede ser limitado.
    """
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={interval}&outputsize={output_size}&apikey={api_key}"
    print(f"Llamando a Alpha Vantage (Intraday): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if f"Time Series ({interval})" in data:
            df = pd.DataFrame.from_dict(data[f"Time Series ({interval})"], orient='index')
            df = df.rename(columns={
                '1. open': 'Open', '2. high': 'High', '3. low': 'Low',
                '4. close': 'Close', '5. volume': 'Volume'
            })
            df.index = pd.to_datetime(df.index)
            df = df.sort_index(ascending=True)
            return df
        else:
            print(f"Error o límite alcanzado en Alpha Vantage (Intraday): {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Alpha Vantage (Intraday): {e}")
        return None

def get_fmp_company_profile(ticker, api_key):
    """
    Obtiene el perfil general de la empresa de FMP.
    """
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
    print(f"Llamando a FMP (Profile): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and data[0]:
            return data[0]
        else:
            print(f"Error o datos no encontrados en FMP (Profile): {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con FMP (Profile): {e}")
        return None

def get_fmp_financial_statements(ticker, api_key, statement_type, limit=1):
    """
    Obtiene estados financieros (balance-sheet-statement, income-statement, cash-flow-statement) de FMP.
    """
    url = f"https://financialmodelingprep.com/api/v3/{statement_type}/{ticker}?limit={limit}&apikey={api_key}"
    print(f"Llamando a FMP ({statement_type}): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            # Convertir la lista de dicts a DataFrame y establecer 'date' como índice
            df = pd.DataFrame(data).set_index('date')
            # Ordenar por fecha ascendente para análisis de tendencias
            df = df.sort_index(ascending=True)
            return df
        else:
            print(f"Error o datos no encontrados en FMP ({statement_type}): {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con FMP ({statement_type}): {e}")
        return None

def get_yfinance_historical_data(ticker, start_date, end_date):
    """
    Obtiene datos históricos de precios de Yahoo Finance usando yfinance.
    """
    print(f"Llamando a yfinance para {ticker} de {start_date} a {end_date}")
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        if not data.empty:
            return data
        else:
            print(f"No se encontraron datos históricos de yfinance para {ticker} en el rango especificado.")
            return None
    except Exception as e:
        print(f"Error al obtener datos de yfinance para {ticker}: {e}")
        return None

def get_finnhub_quote(ticker, api_key):
    """
    Obtiene una cotización simple de Finnhub. Ideal para una verificación rápida.
    """
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"
    print(f"Verificando Finnhub (Quote): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Una respuesta de error suele ser un diccionario con una clave 'error'.
        if data and 'error' not in data and 'c' in data:
            return True
        else:
            print(f"Error en la verificación de Finnhub. Respuesta: {data}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Finnhub (Quote): {e}")
        return False
    except json.JSONDecodeError:
        print(f"Error al decodificar la respuesta JSON de Finnhub (Quote). Respuesta: {response.text}")
        return False

def get_finnhub_company_news(ticker, api_key, start_date, end_date):
    """
    Obtiene noticias de la empresa de Finnhub.
    Finnhub requiere fechas en formato 'YYYY-MM-DD'.
    """
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&token={api_key}"
    print(f"Llamando a Finnhub (Company News): {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            # Convertir la lista de dicts a DataFrame
            df = pd.DataFrame(data)
            # Convertir timestamp a fecha legible
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
            df = df.sort_values(by='datetime', ascending=False) # Últimas noticias primero
            return df
        else:
            print(f"No se encontraron noticias de Finnhub para {ticker} en el rango especificado o error: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Finnhub (Company News): {e}")
        return None

# --- 3. Verificación Previa de APIs ---
def check_api_status(test_ticker, av_key, fmp_key, finnhub_key):
    """
    Realiza una verificación rápida en todas las APIs para asegurarse de que funcionan.
    """
    print("--- Iniciando verificación previa de APIs ---")
    apis_ok = True

    # 1. Verificar Alpha Vantage
    # Usamos una llamada simple para verificar. 'compact' es suficiente.
    # Esta función ya imprime errores detallados si falla.
    print("\nVerificando Alpha Vantage...")
    av_check = get_alpha_vantage_daily_prices(test_ticker, av_key, output_size='compact')
    if av_check is None:
        print("ESTADO: FALLO en Alpha Vantage.")
        apis_ok = False
    else:
        print("ESTADO: ÉXITO en Alpha Vantage.")

    # 2. Verificar Financial Modeling Prep (FMP)
    print("\nVerificando Financial Modeling Prep...")
    fmp_check = get_fmp_company_profile(test_ticker, fmp_key)
    if fmp_check is None:
        print("ESTADO: FALLO en Financial Modeling Prep.")
        apis_ok = False
    else:
        print("ESTADO: ÉXITO en Financial Modeling Prep.")

    # 3. Verificar Finnhub
    print("\nVerificando Finnhub...")
    finnhub_check = get_finnhub_quote(test_ticker, finnhub_key)
    if not finnhub_check:
        print("ESTADO: FALLO en Finnhub.")
        apis_ok = False
    else:
        print("ESTADO: ÉXITO en Finnhub.")

    print("\n--- Verificación previa de APIs completada ---")
    if not apis_ok:
        print("\nADVERTENCIA: Una o más APIs fallaron la verificación. El script no continuará.")
    
    return apis_ok

# --- 4. Generación de la Salida Estructurada ---

def generate_markdown_report(ticker, profile, daily_prices_av, intraday_prices_av,
                             income_statement_fmp, balance_sheet_fmp, cash_flow_fmp,
                             daily_prices_yf, finnhub_news):
    """
    Genera un informe en formato Markdown con los datos recopilados.
    """
    report = f"# Análisis Financiero de {ticker}\n\n"
    report += f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "---\n\n"

    # 1. Perfil y Datos Generales (FMP)
    report += "## 1. Perfil y Datos Generales (FMP)\n"
    if profile:
        report += f"* **Nombre de la Empresa:** {profile.get('companyName', 'N/A')}\n"
        report += f"* **Símbolo:** {profile.get('symbol', 'N/A')}\n"
        report += f"* **Sector:** {profile.get('sector', 'N/A')}\n"
        report += f"* **Industria:** {profile.get('industry', 'N/A')}\n"
        report += f"* **Capitalización de Mercado:** ${profile.get('mktCap', 'N/A'):,.2f}\n"
        report += f"* **Moneda:** {profile.get('currency', 'N/A')}\n"
        report += f"* **Último Precio de Cierre (FMP):** ${profile.get('price', 'N/A')}\n"
        report += f"* **Descripción:** {profile.get('description', 'N/A')[:500]}...\n" # Limitar descripción
    else:
        report += "No se pudo obtener el perfil de la empresa.\n"
    report += "\n"

    # 2. Datos Fundamentales Clave (FMP)
    report += "## 2. Datos Fundamentales Clave (FMP - Último Reporte Anual)\n"

    # Estado de Resultados
    if income_statement_fmp is not None and not income_statement_fmp.empty:
        report += "### 2.1. Estado de Resultados (Income Statement)\n"
        # Seleccionar algunas columnas clave que contribuyen a las etiquetas
        desired_cols_is = ['revenue', 'costOfRevenue', 'grossProfit', 'operatingIncome', 'netIncome', 'eps']
        available_cols_is = [col for col in desired_cols_is if col in income_statement_fmp.columns]
        if available_cols_is:
            report += income_statement_fmp[available_cols_is].to_markdown() + "\n\n"
        else:
            report += "Columnas esperadas no encontradas. Mostrando primeras 6 columnas disponibles:\n"
            report += income_statement_fmp.iloc[:, :6].to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Estado de Resultados.\n"

    # Balance General
    if balance_sheet_fmp is not None and not balance_sheet_fmp.empty:
        report += "### 2.2. Balance General (Balance Sheet)\n"
        desired_cols_bs = ['cashAndCashEquivalents', 'totalCurrentAssets', 'totalAssets', 'totalCurrentLiabilities', 'totalLiabilities', 'totalEquity']
        available_cols_bs = [col for col in desired_cols_bs if col in balance_sheet_fmp.columns]
        if available_cols_bs:
            report += balance_sheet_fmp[available_cols_bs].to_markdown() + "\n\n"
        else:
            report += "Columnas esperadas no encontradas. Mostrando primeras 6 columnas disponibles:\n"
            report += balance_sheet_fmp.iloc[:, :6].to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Balance General.\n"

    # Flujo de Caja
    if cash_flow_fmp is not None and not cash_flow_fmp.empty:
        report += "### 2.3. Flujo de Caja (Cash Flow Statement)\n"
        desired_cols_cf = ['netIncome', 'depreciationAndAmortization', 'changesInWorkingCapital', 'cashFlowFromOperatingActivities', 'capitalExpenditure', 'cashFlowFromFinancingActivities']
        available_cols_cf = [col for col in desired_cols_cf if col in cash_flow_fmp.columns]
        if available_cols_cf:
            report += cash_flow_fmp[available_cols_cf].to_markdown() + "\n\n"
        else:
            report += "Columnas esperadas no encontradas. Mostrando primeras 6 columnas disponibles:\n"
            report += cash_flow_fmp.iloc[:, :6].to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Flujo de Caja.\n"

    # 3. Datos Históricos de Precios e Indicadores (Alpha Vantage / yfinance)
    report += "## 3. Datos Históricos de Precios e Indicadores\n"

    # Datos diarios de Alpha Vantage
    if daily_prices_av is not None and not daily_prices_av.empty:
        report += f"### 3.1. Precios Diarios (Alpha Vantage - Últimos {min(len(daily_prices_av), DIAS_HISTORICOS)} Días)\n"
        report += daily_prices_av.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios de Alpha Vantage.\n"

    # Datos intradía de Alpha Vantage (posible pre-mercado)
    if intraday_prices_av is not None and not intraday_prices_av.empty:
        report += "### 3.2. Precios Intradía (Alpha Vantage - Intervalo de 5min - Últimas 100 barras)\n"
        report += "_Nota: La disponibilidad de datos de pre-mercado específicos depende del plan gratuito y configuración de la API._\n"
        report += intraday_prices_av.tail(100).to_markdown() + "\n\n" # Mostrar las últimas 100 filas
    else:
        report += "No se pudieron obtener los precios intradía de Alpha Vantage (Verificar si el plan gratuito incluye pre-mercado).\n"

    # Datos diarios de yfinance (como alternativa/comparación)
    if daily_prices_yf is not None and not daily_prices_yf.empty:
        report += f"### 3.3. Precios Diarios (yfinance - Últimos {min(len(daily_prices_yf), DIAS_HISTORICOS)} Días)\n"
        report += daily_prices_yf.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios de yfinance.\n"

    # 4. Noticias Recientes y Eventos (Finnhub)
    report += "## 4. Noticias Recientes y Eventos (Finnhub)\n"
    if finnhub_news is not None and not finnhub_news.empty:
        report += "### 4.1. Últimas Noticias de la Empresa\n"
        # Mostrar algunas columnas clave como 'datetime', 'headline', 'source', 'url'
        cols_news = ['datetime', 'headline', 'source', 'url']
        report += finnhub_news[cols_news].head(10).to_markdown(index=False) + "\n\n" # Mostrar las 10 últimas noticias
    else:
        report += f"No se pudieron obtener noticias recientes de Finnhub para {ticker}.\n"


    report += "---\n\n"
    report += "_Análisis generado automáticamente. Los datos pueden variar según la disponibilidad de la API y los límites del plan gratuito._\n"
    return report

# --- 5. Función Principal de Ejecución ---

# --- Supabase helpers (mismos que api_youtube.py) ---
def _supabase_client() -> Client:
    key = SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY
    return create_client(SUPABASE_URL, key)

def existe_archivo_en_supabase(nombre_archivo_remoto: str) -> bool:
    try:
        client = _supabase_client()
        carpeta = SUPABASE_BASE_PREFIX or ""
        if carpeta:
            items = client.storage.from_(SUPABASE_BUCKET_NAME).list(path=carpeta)
        else:
            items = client.storage.from_(SUPABASE_BUCKET_NAME).list()
        if not items:
            return False
        return any(getattr(it, "name", None) == nombre_archivo_remoto or (isinstance(it, dict) and it.get("name") == nombre_archivo_remoto) for it in items)
    except Exception:
        return False

def subir_texto_a_supabase(contenido_texto: str, nombre_archivo_remoto: str) -> bool:
    try:
        client = _supabase_client()
        ruta_remota = f"{SUPABASE_BASE_PREFIX}/{nombre_archivo_remoto}" if SUPABASE_BASE_PREFIX else nombre_archivo_remoto

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp:
                tmp.write(contenido_texto)
                temp_path = tmp.name

            ya_existia = existe_archivo_en_supabase(nombre_archivo_remoto)

            _ = client.storage.from_(SUPABASE_BUCKET_NAME).upload(
                path=ruta_remota,
                file=temp_path,
                file_options={
                    "cacheControl": "3600",
                    "upsert": "true",
                    "contentType": "text/markdown; charset=utf-8",
                },
            )

            accion = "actualizado" if ya_existia else "creado"
            print(f"\n✅ Archivo {accion} en Supabase: bucket='{SUPABASE_BUCKET_NAME}', path='{ruta_remota}'")
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

def main():
    # --- Verificación Inicial de APIs ---
    apis_listas = check_api_status('AAPL', ALPHA_VANTAGE_API_KEY, FMP_API_KEY, FINNHUB_API_KEY)
    
    if not apis_listas:
        return # Detener la ejecución si las APIs no están listas

    tickers_a_procesar = ['NVDA', 'GOOGL', 'AAPL', 'TLT', 'IEF', 'MBB'] # Ejemplo con múltiples tickers
    all_reports = []

    for ticker_actual in tickers_a_procesar:
        print(f"\nProcesando datos para {ticker_actual}...")
        global TICKER # Solo para este ejemplo simplificado
        TICKER = ticker_actual

        # 1. Obtener Datos Fundamentales (FMP)
        profile = get_fmp_company_profile(TICKER, FMP_API_KEY)
        income_statement = get_fmp_financial_statements(TICKER, FMP_API_KEY, 'income-statement')
        balance_sheet = get_fmp_financial_statements(TICKER, FMP_API_KEY, 'balance-sheet-statement')
        cash_flow = get_fmp_financial_statements(TICKER, FMP_API_KEY, 'cash-flow-statement')

        # 2. Obtener Datos de Precios (Alpha Vantage)
        daily_prices_av = get_alpha_vantage_daily_prices(TICKER, ALPHA_VANTAGE_API_KEY)
        intraday_prices_av = get_alpha_vantage_intraday_prices(TICKER, ALPHA_VANTAGE_API_KEY) # Para posible pre-mercado

        # 3. Obtener Datos de Precios (yfinance)
        daily_prices_yf = get_yfinance_historical_data(TICKER, FECHA_INICIO, FECHA_FIN)

        # 4. Obtener Noticias (Finnhub)
        finnhub_news = get_finnhub_company_news(TICKER, FINNHUB_API_KEY, FECHA_INICIO, FECHA_FIN)

        # 5. Generar el informe para el ticker actual
        report_content = generate_markdown_report(
            TICKER, profile, daily_prices_av, intraday_prices_av,
            income_statement, balance_sheet, cash_flow, daily_prices_yf, finnhub_news
        )
        all_reports.append(report_content)
        print(f"Informe para {ticker_actual} generado y añadido al consolidado.")

        # PAUSA ESTRATÉGICA
        if ticker_actual != tickers_a_procesar[-1]:
            print(f"Pausando por 15 segundos para respetar los límites de la API...")
            time.sleep(15)

    # 6. Unir y guardar el informe consolidado
    if all_reports:
        consolidated_report_title = f"# Análisis Financiero Consolidado\n## Empresas: {', '.join(tickers_a_procesar)}\n"
        final_report = consolidated_report_title + "\n\n<br><hr><br>\n\n".join(all_reports)
        
        file_name = "analisis_financiero_consolidado.md"
        # Subir a Supabase (crea/actualiza) con service role si existe
        print("\nSubiendo informe consolidado a Supabase Storage...")
        ok = subir_texto_a_supabase(final_report, file_name)
        if not ok:
            print("No se pudo subir el informe consolidado a Supabase. Verifica configuración y permisos.")

    print("\nProcesamiento completado para todas las empresas.")

if __name__ == "__main__":
    main()