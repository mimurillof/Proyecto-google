"""
API Financiera Multi-Cliente - Versión Escalable
================================================

Módulo principal para análisis financiero dinámico de portfolios de clientes.
Obtiene los assets de cada cliente desde Supabase y genera informes personalizados.
"""

import requests
import pandas as pd
import json
import yfinance as yf
import datetime
import time
import logging
from typing import Optional, List, Dict, Any

from database import get_clientes_activos, get_cliente_por_id, Cliente
from storage_manager import subir_informe_cliente, crear_carpeta_cliente
from config import (
    ALPHA_VANTAGE_API_KEY, 
    FMP_API_KEY, 
    FINNHUB_API_KEY, 
    DIAS_HISTORICOS
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Configuración Global ---
print("✅ Claves API financieras cargadas desde .env")

# Rango de fechas para datos históricos
FECHA_FIN = datetime.date.today()
FECHA_INICIO = FECHA_FIN - datetime.timedelta(days=DIAS_HISTORICOS)


# --- Normalización de Tickers ---

def normalizar_ticker(ticker: str) -> str:
    """
    Normaliza el formato de los tickers para asegurar compatibilidad con las APIs.
    
    Reglas de normalización:
    1. Criptomonedas: BTCUSD -> BTC-USD, ETHUSD -> ETH-USD, etc.
    2. Metales preciosos: PAXGUSD -> PAXG-USD, GOLDUSD -> GOLD-USD, etc.
    3. Sufijos de mercado: NVD.F -> NVDA, AAPL.DE -> AAPL, etc.
    4. Espacios y caracteres especiales se limpian
    
    Args:
        ticker: Ticker original desde la base de datos
        
    Returns:
        str: Ticker normalizado para las APIs
    """
    if not ticker:
        return ticker
    
    ticker_original = ticker
    ticker = ticker.strip().upper()
    
    # 1. Mapeo de criptomonedas comunes (formato XXX-USD)
    crypto_map = {
        'BTCUSD': 'BTC-USD',
        'ETHUSD': 'ETH-USD',
        'ADAUSD': 'ADA-USD',
        'SOLUSD': 'SOL-USD',
        'DOTUSD': 'DOT-USD',
        'DOGEUSD': 'DOGE-USD',
        'MATICUSD': 'MATIC-USD',
        'XRPUSD': 'XRP-USD',
        'LINKUSD': 'LINK-USD',
        'LTCUSD': 'LTC-USD',
        'UNIUSD': 'UNI-USD',
        'XLMUSD': 'XLM-USD',
    }
    
    # 2. Mapeo de metales preciosos y commodities
    commodity_map = {
        'PAXGUSD': 'PAXG-USD',  # Paxos Gold
        'GOLDUSD': 'GOLD-USD',
        'SILVERUSD': 'SILVER-USD',
        'XAUUSD': 'GLD',  # Gold ETF
        'XAGUSD': 'SLV',  # Silver ETF
    }
    
    # 3. Mapeo de sufijos de mercados internacionales
    market_suffixes = {
        '.F': '',      # Frankfurt (ej: NVD.F -> NVDA)
        '.DE': '',     # Deutsche Börse
        '.L': '',      # London Stock Exchange
        '.PA': '',     # Euronext Paris
        '.AS': '',     # Amsterdam
        '.MI': '',     # Milan
        '.MC': '',     # Madrid
        '.SW': '',     # Swiss Exchange
        '.TO': '',     # Toronto
        '.AX': '',     # Australian Stock Exchange
        '.HK': '',     # Hong Kong
        '.T': '',      # Tokyo
    }
    
    # 4. Mapeo específico de tickers conocidos que requieren corrección
    specific_map = {
        'NVD.F': 'NVDA',
        'NVDA.F': 'NVDA',
        'GOOGL.F': 'GOOGL',
        'GOOG.F': 'GOOGL',
        'AAPL.F': 'AAPL',
        'MSFT.F': 'MSFT',
        'AMZN.F': 'AMZN',
        'TSLA.F': 'TSLA',
        'META.F': 'META',
        'NFLX.F': 'NFLX',
    }
    
    # Aplicar normalización en orden de prioridad
    
    # 1º - Mapeo específico (máxima prioridad)
    if ticker in specific_map:
        ticker_normalizado = specific_map[ticker]
        logger.info(f"🔄 Ticker normalizado (específico): {ticker_original} -> {ticker_normalizado}")
        return ticker_normalizado
    
    # 2º - Mapeo de criptomonedas
    if ticker in crypto_map:
        ticker_normalizado = crypto_map[ticker]
        logger.info(f"🔄 Ticker normalizado (crypto): {ticker_original} -> {ticker_normalizado}")
        return ticker_normalizado
    
    # 3º - Mapeo de commodities
    if ticker in commodity_map:
        ticker_normalizado = commodity_map[ticker]
        logger.info(f"🔄 Ticker normalizado (commodity): {ticker_original} -> {ticker_normalizado}")
        return ticker_normalizado
    
    # 4º - Remover sufijos de mercados internacionales
    for suffix, replacement in market_suffixes.items():
        if ticker.endswith(suffix):
            ticker_normalizado = ticker.replace(suffix, replacement)
            logger.info(f"🔄 Ticker normalizado (sufijo): {ticker_original} -> {ticker_normalizado}")
            return ticker_normalizado
    
    # 5º - Si no hay cambios, retornar el ticker limpio
    logger.debug(f"✓ Ticker sin cambios: {ticker_original}")
    return ticker


# --- Funciones de Acceso a APIs ---

def get_alpha_vantage_daily_prices(ticker, api_key, output_size='compact'):
    """Obtiene datos de precios diarios de Alpha Vantage."""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize={output_size}&apikey={api_key}"
    logger.debug(f"Llamando a Alpha Vantage (Daily): {ticker}")
    try:
        response = requests.get(url)
        response.raise_for_status()
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
            logger.warning(f"Error o límite alcanzado en Alpha Vantage (Daily) para {ticker}: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Alpha Vantage (Daily) para {ticker}: {e}")
        return None


def get_alpha_vantage_intraday_prices(ticker, api_key, interval='5min', output_size='compact'):
    """Obtiene datos de precios intradía de Alpha Vantage."""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={interval}&outputsize={output_size}&apikey={api_key}"
    logger.debug(f"Llamando a Alpha Vantage (Intraday): {ticker}")
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
            logger.warning(f"Error o límite alcanzado en Alpha Vantage (Intraday) para {ticker}: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Alpha Vantage (Intraday) para {ticker}: {e}")
        return None


def get_fmp_company_profile(ticker, api_key):
    """Obtiene el perfil general de la empresa de FMP."""
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
    logger.debug(f"Llamando a FMP (Profile): {ticker}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and data[0]:
            return data[0]
        else:
            logger.warning(f"Error o datos no encontrados en FMP (Profile) para {ticker}: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con FMP (Profile) para {ticker}: {e}")
        return None


def get_fmp_financial_statements(ticker, api_key, statement_type, limit=1):
    """Obtiene estados financieros de FMP."""
    url = f"https://financialmodelingprep.com/api/v3/{statement_type}/{ticker}?limit={limit}&apikey={api_key}"
    logger.debug(f"Llamando a FMP ({statement_type}): {ticker}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            df = pd.DataFrame(data).set_index('date')
            df = df.sort_index(ascending=True)
            return df
        else:
            logger.warning(f"Error o datos no encontrados en FMP ({statement_type}) para {ticker}: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con FMP ({statement_type}) para {ticker}: {e}")
        return None


def get_yfinance_historical_data(ticker, start_date, end_date):
    """Obtiene datos históricos de precios de Yahoo Finance."""
    logger.debug(f"Llamando a yfinance para {ticker}")
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if not data.empty:
            return data
        else:
            logger.warning(f"No se encontraron datos históricos de yfinance para {ticker}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener datos de yfinance para {ticker}: {e}")
        return None


def get_finnhub_quote(ticker, api_key):
    """Obtiene una cotización simple de Finnhub."""
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"
    logger.debug(f"Verificando Finnhub (Quote): {ticker}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and 'error' not in data and 'c' in data:
            return True
        else:
            logger.warning(f"Error en la verificación de Finnhub para {ticker}: {data}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Finnhub (Quote) para {ticker}: {e}")
        return False
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar la respuesta JSON de Finnhub (Quote) para {ticker}")
        return False


def get_finnhub_company_news(ticker, api_key, start_date, end_date):
    """Obtiene noticias de la empresa de Finnhub."""
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&token={api_key}"
    logger.debug(f"Llamando a Finnhub (Company News): {ticker}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
            df = df.sort_values(by='datetime', ascending=False)
            return df
        else:
            logger.warning(f"No se encontraron noticias de Finnhub para {ticker}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con Finnhub (Company News) para {ticker}: {e}")
        return None


# --- Verificación Previa de APIs ---

def check_api_status(test_ticker: str = 'AAPL') -> bool:
    """Realiza una verificación rápida en todas las APIs."""
    print("\n" + "="*60)
    print("VERIFICACIÓN PREVIA DE APIs")
    print("="*60)
    apis_ok = True

    print("\n🔍 Verificando Alpha Vantage...")
    av_check = get_alpha_vantage_daily_prices(test_ticker, ALPHA_VANTAGE_API_KEY, output_size='compact')
    if av_check is None:
        print("❌ ESTADO: FALLO en Alpha Vantage.")
        apis_ok = False
    else:
        print("✅ ESTADO: ÉXITO en Alpha Vantage.")

    print("\n🔍 Verificando Financial Modeling Prep...")
    fmp_check = get_fmp_company_profile(test_ticker, FMP_API_KEY)
    if fmp_check is None:
        print("❌ ESTADO: FALLO en Financial Modeling Prep.")
        apis_ok = False
    else:
        print("✅ ESTADO: ÉXITO en Financial Modeling Prep.")

    print("\n🔍 Verificando Finnhub...")
    finnhub_check = get_finnhub_quote(test_ticker, FINNHUB_API_KEY)
    if not finnhub_check:
        print("❌ ESTADO: FALLO en Finnhub.")
        apis_ok = False
    else:
        print("✅ ESTADO: ÉXITO en Finnhub.")

    print("\n" + "="*60)
    if not apis_ok:
        print("⚠️  ADVERTENCIA: Una o más APIs fallaron la verificación.")
        print("="*60)
        return False
    
    print("✅ Todas las APIs están funcionando correctamente.")
    print("="*60)
    return True


# --- Generación de Informes ---

def generate_markdown_report(ticker, profile, daily_prices_av, intraday_prices_av,
                             income_statement_fmp, balance_sheet_fmp, cash_flow_fmp,
                             daily_prices_yf, finnhub_news):
    """Genera un informe en formato Markdown con los datos recopilados."""
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
        report += f"* **Descripción:** {profile.get('description', 'N/A')[:500]}...\n"
    else:
        report += "No se pudo obtener el perfil de la empresa.\n"
    report += "\n"

    # 2. Datos Fundamentales Clave (FMP)
    report += "## 2. Datos Fundamentales Clave (FMP - Último Reporte Anual)\n"

    # Estado de Resultados
    if income_statement_fmp is not None and not income_statement_fmp.empty:
        report += "### 2.1. Estado de Resultados (Income Statement)\n"
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

    # 3. Datos Históricos de Precios
    report += "## 3. Datos Históricos de Precios e Indicadores\n"

    if daily_prices_av is not None and not daily_prices_av.empty:
        report += f"### 3.1. Precios Diarios (Alpha Vantage - Últimos {min(len(daily_prices_av), DIAS_HISTORICOS)} Días)\n"
        report += daily_prices_av.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios de Alpha Vantage.\n"

    if intraday_prices_av is not None and not intraday_prices_av.empty:
        report += "### 3.2. Precios Intradía (Alpha Vantage - Intervalo de 5min - Últimas 100 barras)\n"
        report += "_Nota: La disponibilidad de datos de pre-mercado específicos depende del plan y configuración de la API._\n"
        report += intraday_prices_av.tail(100).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios intradía de Alpha Vantage.\n"

    if daily_prices_yf is not None and not daily_prices_yf.empty:
        report += f"### 3.3. Precios Diarios (yfinance - Últimos {min(len(daily_prices_yf), DIAS_HISTORICOS)} Días)\n"
        report += daily_prices_yf.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios de yfinance.\n"

    # 4. Noticias Recientes
    report += "## 4. Noticias Recientes y Eventos (Finnhub)\n"
    if finnhub_news is not None and not finnhub_news.empty:
        report += "### 4.1. Últimas Noticias de la Empresa\n"
        cols_news = ['datetime', 'headline', 'source', 'url']
        report += finnhub_news[cols_news].head(10).to_markdown(index=False) + "\n\n"
    else:
        report += f"No se pudieron obtener noticias recientes de Finnhub para {ticker}.\n"

    report += "---\n\n"
    report += "_Análisis generado automáticamente. Los datos pueden variar según la disponibilidad de la API y los límites del plan._\n"
    return report


# --- Procesamiento por Ticker ---

def procesar_ticker(ticker: str, cliente_id: str) -> Optional[str]:
    """
    Procesa un ticker individual y genera su informe.
    
    Args:
        ticker: Símbolo del activo (será normalizado automáticamente)
        cliente_id: ID del cliente para logging
        
    Returns:
        str: Contenido del informe o None si falla
    """
    # Normalizar el ticker antes de procesarlo
    ticker_original = ticker
    ticker = normalizar_ticker(ticker)
    
    logger.info(f"📊 Procesando {ticker} para cliente {cliente_id}...")
    if ticker != ticker_original:
        logger.info(f"   Ticker original: {ticker_original} -> Normalizado: {ticker}")
    
    try:
        # 1. Obtener Datos Fundamentales (FMP)
        profile = get_fmp_company_profile(ticker, FMP_API_KEY)
        income_statement = get_fmp_financial_statements(ticker, FMP_API_KEY, 'income-statement')
        balance_sheet = get_fmp_financial_statements(ticker, FMP_API_KEY, 'balance-sheet-statement')
        cash_flow = get_fmp_financial_statements(ticker, FMP_API_KEY, 'cash-flow-statement')

        # 2. Obtener Datos de Precios (Alpha Vantage)
        daily_prices_av = get_alpha_vantage_daily_prices(ticker, ALPHA_VANTAGE_API_KEY)
        intraday_prices_av = get_alpha_vantage_intraday_prices(ticker, ALPHA_VANTAGE_API_KEY)

        # 3. Obtener Datos de Precios (yfinance)
        daily_prices_yf = get_yfinance_historical_data(ticker, FECHA_INICIO, FECHA_FIN)

        # 4. Obtener Noticias (Finnhub)
        finnhub_news = get_finnhub_company_news(ticker, FINNHUB_API_KEY, FECHA_INICIO, FECHA_FIN)

        # 5. Generar el informe
        report_content = generate_markdown_report(
            ticker, profile, daily_prices_av, intraday_prices_av,
            income_statement, balance_sheet, cash_flow, daily_prices_yf, finnhub_news
        )
        
        logger.info(f"✅ Informe generado para {ticker}")
        return report_content
        
    except Exception as e:
        logger.error(f"❌ Error al procesar {ticker}: {e}")
        return None


# --- Procesamiento por Cliente ---

def procesar_cliente(cliente: Cliente, generar_consolidado: bool = True) -> Dict[str, Any]:
    """
    Procesa todos los assets de un cliente y genera sus informes.
    
    Args:
        cliente: Objeto Cliente con sus portfolios
        generar_consolidado: Si True, genera un informe consolidado
        
    Returns:
        Dict con estadísticas del procesamiento
    """
    # Obtener todos los assets de todos los portfolios
    todos_los_assets = cliente.get_todos_los_assets()
    todos_los_tickers = cliente.get_todos_los_tickers()
    
    print("\n" + "="*80)
    print(f"🎯 PROCESANDO CLIENTE: {cliente.nombre_completo}")
    print(f"📧 Email: {cliente.email or 'N/A'}")
    print(f"📂 Total de Portfolios: {len(cliente.portfolios)}")
    print(f"📊 Total de Assets: {len(todos_los_assets)}")
    print(f"🎯 Tickers únicos: {len(todos_los_tickers)}")
    print("="*80 + "\n")
    
    # Asegurar que existe la carpeta del cliente
    crear_carpeta_cliente(cliente.user_id)
    
    tickers = todos_los_tickers
    logger.info(f"Assets del cliente {cliente.user_id}: {', '.join(tickers)}")
    
    informes_generados = []
    errores = []
    
    for idx, ticker in enumerate(tickers, 1):
        print(f"\n[{idx}/{len(tickers)}] Procesando {ticker}...")
        
        # Procesar ticker
        report_content = procesar_ticker(ticker, cliente.user_id)
        
        if report_content:
            # Guardar informe individual
            nombre_archivo = f"{ticker}_analisis_financiero.md"
            success = subir_informe_cliente(report_content, nombre_archivo, cliente.user_id)
            
            if success:
                informes_generados.append({
                    'ticker': ticker,
                    'archivo': nombre_archivo,
                    'contenido': report_content
                })
                print(f"✅ Informe de {ticker} guardado exitosamente")
            else:
                errores.append(ticker)
                print(f"❌ Error al guardar informe de {ticker}")
        else:
            errores.append(ticker)
            print(f"❌ Error al procesar {ticker}")
        
        # Pausa estratégica entre tickers (excepto el último)
        if idx < len(tickers):
            print(f"⏸️  Pausando 15 segundos para respetar límites de API...")
            time.sleep(15)
    
    # Generar informe consolidado si se solicita
    if generar_consolidado and informes_generados:
        print("\n📑 Generando informe consolidado...")
        consolidated_title = f"# Análisis Financiero Consolidado - Cliente: {cliente.nombre_completo}\n"
        consolidated_title += f"## User ID: {cliente.user_id}\n"
        consolidated_title += f"## Portfolio: {', '.join([info['ticker'] for info in informes_generados])}\n"
        consolidated_title += f"## Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        final_report = consolidated_title + "\n\n<br><hr><br>\n\n".join([info['contenido'] for info in informes_generados])
        
        nombre_consolidado = "informe_consolidado.md"
        success = subir_informe_cliente(final_report, nombre_consolidado, cliente.user_id)
        
        if success:
            print(f"✅ Informe consolidado guardado exitosamente")
        else:
            print(f"❌ Error al guardar informe consolidado")
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DEL PROCESAMIENTO")
    print("="*80)
    print(f"✅ Informes generados exitosamente: {len(informes_generados)}")
    print(f"❌ Errores encontrados: {len(errores)}")
    if errores:
        print(f"   Tickers con error: {', '.join(errores)}")
    print("="*80 + "\n")
    
    return {
        'cliente_id': cliente.user_id,
        'cliente_nombre': cliente.nombre_completo,
        'total_portfolios': len(cliente.portfolios),
        'total_assets': len(todos_los_assets),
        'tickers_unicos': len(tickers),
        'informes_generados': len(informes_generados),
        'errores': len(errores),
        'tickers_error': errores
    }


# --- Función Principal ---

def main(cliente_id: Optional[str] = None, modo_demo: bool = False):
    """
    Función principal para ejecutar el análisis financiero.
    
    Args:
        cliente_id: Si se especifica, procesa solo ese cliente. Si es None, procesa todos los clientes activos.
        modo_demo: Si True, usa una lista hardcodeada de tickers para pruebas sin base de datos.
    """
    print("\n" + "🚀"*40)
    print("API FINANCIERA MULTI-CLIENTE - SISTEMA ESCALABLE")
    print("🚀"*40 + "\n")
    
    # Verificación inicial de APIs
    if not check_api_status():
        print("\n❌ No se puede continuar sin APIs funcionales. Abortando...")
        return
    
    # Modo Demo (sin base de datos)
    if modo_demo:
        print("\n⚠️  MODO DEMO ACTIVADO - Usando portfolio hardcodeado")
        from database import Cliente, Portfolio, Asset
        
        # Crear portfolio demo
        portfolio_demo = Portfolio(
            portfolio_id=1,
            user_id="demo_user_001",
            nombre="Portfolio Demo",
            descripcion="Portfolio de prueba para demo"
        )
        
        # Agregar assets al portfolio
        portfolio_demo.assets = [
            Asset(asset_id=1, portfolio_id=1, ticker='NVDA'),
            Asset(asset_id=2, portfolio_id=1, ticker='GOOGL'),
            Asset(asset_id=3, portfolio_id=1, ticker='AAPL'),
        ]
        
        # Crear cliente demo
        cliente_demo = Cliente(
            user_id="demo_user_001",
            first_name="Cliente",
            last_name="Demo",
            email="demo@example.com"
        )
        
        # Asignar portfolio al cliente
        cliente_demo.portfolios = [portfolio_demo]
        
        stats = procesar_cliente(cliente_demo, generar_consolidado=True)
        print(f"\n✅ Procesamiento completado para cliente demo")
        return
    
    # Modo Producción (con base de datos)
    try:
        if cliente_id:
            # Procesar un cliente específico
            print(f"\n🎯 Modo: Cliente Individual ({cliente_id})")
            cliente = get_cliente_por_id(cliente_id)
            
            if not cliente:
                print(f"\n❌ No se encontró el cliente con ID: {cliente_id}")
                return
            
            if not cliente.portfolios:
                print(f"\n⚠️  El cliente {cliente_id} no tiene portfolios configurados.")
                return
            
            todos_los_assets = cliente.get_todos_los_assets()
            if not todos_los_assets:
                print(f"\n⚠️  El cliente {cliente_id} no tiene assets en ningún portfolio.")
                return
            
            stats = procesar_cliente(cliente, generar_consolidado=True)
            
        else:
            # Procesar todos los clientes activos
            print("\n🌐 Modo: Todos los Clientes Activos")
            clientes = get_clientes_activos()
            
            if not clientes:
                print("\n⚠️  No se encontraron clientes activos en la base de datos.")
                return
            
            print(f"\n📊 Total de clientes activos a procesar: {len(clientes)}")
            
            all_stats = []
            for idx, cliente in enumerate(clientes, 1):
                print(f"\n{'='*80}")
                print(f"CLIENTE {idx}/{len(clientes)}")
                print(f"{'='*80}")
                
                # Verificar si tiene assets
                todos_los_assets = cliente.get_todos_los_assets()
                if not todos_los_assets:
                    print(f"⚠️  Cliente {cliente.user_id} no tiene assets en ningún portfolio. Saltando...")
                    continue
                
                stats = procesar_cliente(cliente, generar_consolidado=True)
                all_stats.append(stats)
                
                # Pausa entre clientes (excepto el último)
                if idx < len(clientes):
                    print(f"\n⏸️  Pausando 30 segundos antes del siguiente cliente...")
                    time.sleep(30)
            
            # Resumen global
            print("\n" + "🎉"*40)
            print("RESUMEN GLOBAL DE PROCESAMIENTO")
            print("🎉"*40)
            for stat in all_stats:
                print(f"\n📌 Cliente: {stat['cliente_nombre'] or stat['cliente_id']}")
                print(f"   Total assets: {stat['total_assets']}")
                print(f"   ✅ Éxitos: {stat['informes_generados']}")
                print(f"   ❌ Errores: {stat['errores']}")
            print("\n" + "="*80)
        
        print("\n✅ Procesamiento completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error fatal en la ejecución: {e}", exc_info=True)
        print(f"\n❌ Error fatal: {e}")


if __name__ == "__main__":
    import sys
    
    # Permitir pasar argumentos por línea de comandos
    # Uso: python financial_api.py [cliente_id] [--demo]
    
    args = sys.argv[1:]
    cliente_id_arg = None
    modo_demo_arg = False
    
    for arg in args:
        if arg == '--demo':
            modo_demo_arg = True
        elif not arg.startswith('--'):
            cliente_id_arg = arg
    
    main(cliente_id=cliente_id_arg, modo_demo=modo_demo_arg)
