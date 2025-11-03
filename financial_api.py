"""
API Financiera Multi-Cliente - Versión Escalable
================================================

Módulo principal para análisis financiero dinámico de portfolios de clientes.
Obtiene los assets de cada cliente desde Supabase y genera informes personalizados.
"""

import datetime
import logging
import re
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

try:
    from pandas_datareader import data as pdr  # type: ignore[import]
    PDR_AVAILABLE = True
    PDR_IMPORT_ERROR: Optional[Exception] = None
except Exception as err:  # noqa: BLE001 - queremos capturar cualquier problema de importación
    pdr = None  # type: ignore[assignment]
    PDR_AVAILABLE = False
    PDR_IMPORT_ERROR = err

from database import Cliente, get_cliente_por_id, get_clientes_activos
from storage_manager import crear_carpeta_cliente, subir_informe_cliente
from config import DIAS_HISTORICOS

if PDR_AVAILABLE:
    yf.pdr_override()  # type: ignore[attr-defined]

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- Configuración Global ---
print("✅ Dependencias financieras inicializadas (yfinance + pandas-datareader)")

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
        '^SPX': '^GSPC',
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


# --- Utilidades de datos (yfinance / pandas-datareader) ---

def sanitizar_nombre_archivo(nombre: str) -> str:
    """Normaliza un identificador para usarlo como nombre de archivo en Supabase."""
    seguro = re.sub(r"[^A-Za-z0-9._-]", "-", nombre)
    seguro = re.sub(r"-+", "-", seguro).strip("-")
    return seguro or "reporte"


def get_yf_ticker(ticker: str) -> Optional[yf.Ticker]:
    try:
        return yf.Ticker(ticker)
    except Exception as err:
        logger.error(f"Error al instanciar yfinance.Ticker para {ticker}: {err}")
        return None


def get_yf_profile(ticker_obj: yf.Ticker) -> Optional[Dict[str, Any]]:
    try:
        info = ticker_obj.get_info()
        if info:
            return info
    except Exception as err:
        logger.warning(f"No se pudo obtener la información general para {ticker_obj.ticker}: {err}")
    return None


def _obtener_estado_financiero(ticker_obj: yf.Ticker, attr: str, metodo: str) -> Optional[pd.DataFrame]:
    for accessor in (attr, metodo):
        try:
            valor = getattr(ticker_obj, accessor, None)
            if valor is None:
                continue
            data = valor() if callable(valor) else valor
            if isinstance(data, pd.DataFrame) and not data.empty:
                return data
        except Exception as err:
            logger.debug(f"Accessor {accessor} no disponible para {ticker_obj.ticker}: {err}")
    return None


def get_yf_financial_statements(ticker_obj: yf.Ticker) -> Dict[str, Optional[pd.DataFrame]]:
    return {
        "income": _obtener_estado_financiero(ticker_obj, "income_stmt", "get_income_stmt"),
        "balance": _obtener_estado_financiero(ticker_obj, "balance_sheet", "get_balance_sheet"),
        "cashflow": _obtener_estado_financiero(ticker_obj, "cashflow", "get_cashflow"),
    }


def get_yf_daily_prices(ticker: str, start_date: datetime.date, end_date: datetime.date) -> Optional[pd.DataFrame]:
    logger.debug(f"Descargando histórico diario (yfinance) para {ticker}")
    try:
        data = yf.download(ticker, start=start_date, end=end_date + datetime.timedelta(days=1), progress=False)
        if data is not None and not data.empty:
            return data
        logger.warning(f"No se encontraron datos diarios en yfinance para {ticker}")
    except Exception as err:
        logger.error(f"Error al obtener datos diarios en yfinance para {ticker}: {err}")
    return None


def get_yf_intraday_prices(ticker: str, period: str = "5d", interval: str = "1h") -> Optional[pd.DataFrame]:
    logger.debug(f"Descargando datos intradía (yfinance) para {ticker}")
    try:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
        if data is not None and not data.empty:
            return data
        logger.warning(f"No se encontraron datos intradía en yfinance para {ticker}")
    except Exception as err:
        logger.error(f"Error al obtener datos intradía para {ticker}: {err}")
    return None


def get_pdr_daily_prices(ticker: str, start_date: datetime.date, end_date: datetime.date) -> Optional[pd.DataFrame]:
    logger.debug(f"Descargando histórico diario (pandas-datareader) para {ticker}")
    if not PDR_AVAILABLE or pdr is None:
        if PDR_IMPORT_ERROR:
            logger.warning(
                "pandas-datareader no disponible: %s", PDR_IMPORT_ERROR
            )
        else:
            logger.warning("pandas-datareader no está instalado en el entorno actual")
        return None

    try:
        df = pdr.get_data_yahoo(ticker, start=start_date, end=end_date + datetime.timedelta(days=1))
        if df is not None:
            if isinstance(df, pd.Series):
                df = df.to_frame(name="value")
            df = pd.DataFrame(df)
            if not df.empty:
                return df
        logger.warning(f"No se encontraron datos diarios en pandas-datareader para {ticker}")
    except Exception as err:
        logger.error(f"Error al obtener datos diarios con pandas-datareader para {ticker}: {err}")
    return None


def get_yf_news(ticker_obj: yf.Ticker) -> Optional[pd.DataFrame]:
    try:
        news_items = ticker_obj.news
    except Exception as err:
        logger.warning(f"No se pudieron obtener noticias para {ticker_obj.ticker}: {err}")
        return None

    if not news_items:
        logger.info(f"Sin noticias recientes para {ticker_obj.ticker}")
        return None

    df = pd.DataFrame(news_items)
    if "providerPublishTime" in df.columns:
        df["providerPublishTime"] = pd.to_datetime(df["providerPublishTime"], unit="s", errors="coerce")
        df = df.sort_values(by="providerPublishTime", ascending=False)
    return df


# --- Verificación Previa de APIs ---

def check_api_status(test_ticker: str = "AAPL") -> bool:
    """Realiza una verificación rápida utilizando yfinance y pandas-datareader."""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN PREVIA DE FUENTES (yfinance / pandas-datareader)")
    print("=" * 60)

    servicios_ok = True

    print("\n🔍 Verificando yfinance (histórico diario)...")
    if get_yf_daily_prices(test_ticker, FECHA_INICIO, FECHA_FIN) is None:
        print("❌ ESTADO: FALLO en yfinance.")
        servicios_ok = False
    else:
        print("✅ ESTADO: ÉXITO en yfinance.")

    print("\n🔍 Verificando pandas-datareader (Yahoo Finance)...")
    if PDR_AVAILABLE and pdr is not None:
        if get_pdr_daily_prices(test_ticker, FECHA_INICIO, FECHA_FIN) is None:
            print("❌ ESTADO: FALLO en pandas-datareader.")
            servicios_ok = False
        else:
            print("✅ ESTADO: ÉXITO en pandas-datareader.")
    else:
        print("⚠️  pandas-datareader no está disponible. Se continuará solo con yfinance.")

    print("\n" + "=" * 60)
    if not servicios_ok:
        print("⚠️  ADVERTENCIA: Una o más fuentes fallaron la verificación.")
        print("=" * 60)
        return False

    print("✅ Fuentes verificadas correctamente.")
    print("=" * 60)
    return True


# --- Generación de Informes ---

def _formatear_moneda(valor: Any) -> str:
    if isinstance(valor, (int, float)):
        return f"${valor:,.2f}"
    return str(valor) if valor not in (None, "") else "N/A"


def _preparar_estado(df: Optional[pd.DataFrame], columnas: List[str]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    preparado = df.transpose()
    disponibles = [col for col in columnas if col in preparado.columns]
    if disponibles:
        return preparado[disponibles]
    return preparado.iloc[:, : min(6, preparado.shape[1])]


def generate_markdown_report(
    ticker: str,
    profile: Optional[Dict[str, Any]],
    income_statement: Optional[pd.DataFrame],
    balance_sheet: Optional[pd.DataFrame],
    cash_flow: Optional[pd.DataFrame],
    daily_prices_yf: Optional[pd.DataFrame],
    daily_prices_pdr: Optional[pd.DataFrame],
    intraday_prices_yf: Optional[pd.DataFrame],
    news_df: Optional[pd.DataFrame],
) -> str:
    """Genera un informe en formato Markdown con los datos recopilados."""
    report = f"# Análisis Financiero de {ticker}\n\n"
    report += f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "---\n\n"

    # 1. Perfil y Datos Generales
    report += "## 1. Perfil y Datos Generales (yfinance)\n"
    if profile:
        report += f"* **Nombre de la Empresa:** {profile.get('longName') or profile.get('shortName') or 'N/A'}\n"
        report += f"* **Símbolo:** {profile.get('symbol') or ticker}\n"
        report += f"* **Sector:** {profile.get('sector', 'N/A')}\n"
        report += f"* **Industria:** {profile.get('industry', 'N/A')}\n"
        report += f"* **Capitalización de Mercado:** {_formatear_moneda(profile.get('marketCap'))}\n"
        report += f"* **Moneda:** {profile.get('currency', 'N/A')}\n"
        precio_cierre = profile.get('currentPrice') or profile.get('previousClose')
        report += f"* **Último Precio de Cierre (yfinance):** {_formatear_moneda(precio_cierre)}\n"
        descripcion = profile.get('longBusinessSummary')
        if descripcion:
            report += f"* **Descripción:** {descripcion[:500]}...\n"
    else:
        report += "No se pudo obtener el perfil de la empresa desde yfinance.\n"
    report += "\n"

    # 2. Datos Fundamentales Clave
    report += "## 2. Datos Fundamentales Clave (yfinance)\n"

    estado_resultados = _preparar_estado(income_statement, [
        "Total Revenue",
        "Cost Of Revenue",
        "Gross Profit",
        "Operating Income",
        "Net Income",
        "Diluted EPS",
    ])
    if estado_resultados is not None:
        report += "### 2.1. Estado de Resultados (Income Statement)\n"
        report += estado_resultados.to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Estado de Resultados.\n"

    balance_general = _preparar_estado(balance_sheet, [
        "Cash And Cash Equivalents",
        "Total Current Assets",
        "Total Assets",
        "Total Current Liabilities",
        "Total Liab",
        "Total Stockholder Equity",
    ])
    if balance_general is not None:
        report += "### 2.2. Balance General (Balance Sheet)\n"
        report += balance_general.to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Balance General.\n"

    flujo_caja = _preparar_estado(cash_flow, [
        "Net Income",
        "Depreciation",
        "Change In Working Capital",
        "Total Cash From Operating Activities",
        "Capital Expenditures",
        "Total Cash From Financing Activities",
    ])
    if flujo_caja is not None:
        report += "### 2.3. Flujo de Caja (Cash Flow Statement)\n"
        report += flujo_caja.to_markdown() + "\n\n"
    else:
        report += "No se pudo obtener el Flujo de Caja.\n"

    # 3. Datos Históricos de Precios
    report += "## 3. Datos Históricos de Precios e Indicadores\n"

    if daily_prices_yf is not None:
        report += f"### 3.1. Precios Diarios (yfinance - Últimos {min(len(daily_prices_yf), DIAS_HISTORICOS)} datos)\n"
        report += daily_prices_yf.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios de yfinance.\n"

    if daily_prices_pdr is not None:
        report += f"### 3.2. Precios Diarios (pandas-datareader - Últimos {min(len(daily_prices_pdr), DIAS_HISTORICOS)} datos)\n"
        report += daily_prices_pdr.tail(DIAS_HISTORICOS).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios diarios desde pandas-datareader.\n"

    if intraday_prices_yf is not None:
        report += "### 3.3. Precios Intradía (yfinance)\n"
        report += "_Intervalo 1h durante los últimos 5 días._\n"
        report += intraday_prices_yf.tail(100).to_markdown() + "\n\n"
    else:
        report += "No se pudieron obtener los precios intradía de yfinance.\n"

    # 4. Noticias Recientes
    report += "## 4. Noticias Recientes y Eventos (yfinance)\n"
    if news_df is not None and not news_df.empty:
        columnas = [col for col in ["providerPublishTime", "title", "publisher", "link"] if col in news_df.columns]
        if columnas:
            report += news_df[columnas].head(10).to_markdown(index=False) + "\n\n"
        else:
            report += news_df.head(10).to_markdown(index=False) + "\n\n"
    else:
        report += f"No se encontraron noticias recientes para {ticker}.\n"

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
        ticker_obj = get_yf_ticker(ticker)
        if ticker_obj is None:
            logger.error(f"No se pudo inicializar yfinance para {ticker}")
            return None

        profile = get_yf_profile(ticker_obj)
        estados_financieros = get_yf_financial_statements(ticker_obj)
        daily_prices_yf = get_yf_daily_prices(ticker, FECHA_INICIO, FECHA_FIN)
        daily_prices_pdr = get_pdr_daily_prices(ticker, FECHA_INICIO, FECHA_FIN)
        intraday_prices_yf = get_yf_intraday_prices(ticker)
        news_df = get_yf_news(ticker_obj)

        report_content = generate_markdown_report(
            ticker,
            profile,
            estados_financieros.get("income"),
            estados_financieros.get("balance"),
            estados_financieros.get("cashflow"),
            daily_prices_yf,
            daily_prices_pdr,
            intraday_prices_yf,
            news_df,
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
            nombre_archivo = f"{sanitizar_nombre_archivo(ticker)}_analisis_financiero.md"
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
        tickers_lista = ', '.join([info['ticker'] for info in informes_generados])
        consolidated_title += f"## Portfolio: {tickers_lista}\n"
        consolidated_title += f"## Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        bloques = "\n\n<br><hr><br>\n\n".join([info['contenido'] for info in informes_generados])
        final_report = consolidated_title + bloques

        nombre_consolidado = "informe_consolidado.md"
        success = subir_informe_cliente(final_report, nombre_consolidado, cliente.user_id)

        if success:
            print("✅ Informe consolidado guardado exitosamente")
        else:
            print("❌ Error al guardar informe consolidado")
    
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
