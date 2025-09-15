"""
Módulo de configuración centralizado para cargar variables de entorno.
Este módulo debe ser importado al inicio de todos los scripts del proyecto.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def get_env_var(var_name: str, default_value: Optional[str] = None, required: bool = True) -> Optional[str]:
    """
    Obtiene una variable de entorno con manejo de errores.
    
    Args:
        var_name (str): Nombre de la variable de entorno
        default_value (str): Valor por defecto si no se encuentra la variable
        required (bool): Si es True, lanza una excepción si no se encuentra
        
    Returns:
        str: Valor de la variable de entorno
        
    Raises:
        ValueError: Si la variable es requerida y no se encuentra
    """
    value = os.getenv(var_name, default_value)
    
    if required and not value:
        raise ValueError(f"Variable de entorno requerida '{var_name}' no encontrada en .env")
    
    return value

# Variables de configuración principales
GOOGLE_API_KEY = get_env_var('GOOGLE_API_KEY')

# APIs específicas (con fallback a GOOGLE_API_KEY si no están definidas)  
YOUTUBE_API_KEY = get_env_var('YOUTUBE_API_KEY', required=False) or GOOGLE_API_KEY
GEMINI_API_KEY = get_env_var('GEMINI_API_KEY', required=False) or GOOGLE_API_KEY

# Supabase Configuration
SUPABASE_URL = get_env_var('SUPABASE_URL')
SUPABASE_ANON_KEY = get_env_var('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE = get_env_var('SUPABASE_SERVICE_ROLE', required=False)
SUPABASE_BUCKET_NAME = get_env_var('SUPABASE_BUCKET_NAME', 'portfolio-files')
SUPABASE_BASE_PREFIX = get_env_var('SUPABASE_BASE_PREFIX', 'Informes')
ENABLE_SUPABASE_UPLOAD = (get_env_var('ENABLE_SUPABASE_UPLOAD', 'true') or 'true').lower() == 'true'
SUPABASE_CLEANUP_AFTER_TESTS = (get_env_var('SUPABASE_CLEANUP_AFTER_TESTS', 'false') or 'false').lower() == 'true'

# API Keys para financial_api.py (si están en .env, sino usar valores por defecto)
ALPHA_VANTAGE_API_KEY = get_env_var('ALPHA_VANTAGE_API_KEY', '9DY7SR44AGOL9QB4', required=False)
FMP_API_KEY = get_env_var('FMP_API_KEY', '9gdeFvLVrQqKUZj5NGWxL0sRJxpzo2ex', required=False)
FINNHUB_API_KEY = get_env_var('FINNHUB_API_KEY', 'd1d9st1r01qr1jau5vc0d1d9st1r01qr1jau5vcg', required=False)

# Configuración específica del proyecto
DEFAULT_TICKER = get_env_var('DEFAULT_TICKER', 'AAPL', required=False)
DIAS_HISTORICOS = int(get_env_var('DIAS_HISTORICOS', '1', required=False) or '1')
CHANNEL_ID_XTB = get_env_var('CHANNEL_ID_XTB', 'UC-mfgGnt3tXtkDnFpl02f2Q', required=False)  
CONSULTA_BUSQUEDA = get_env_var('CONSULTA_BUSQUEDA', 'PRE MERCADO |', required=False)

def validate_configuration():
    """
    Valida que todas las configuraciones críticas estén disponibles.
    """
    critical_vars = [
        ('GOOGLE_API_KEY', GOOGLE_API_KEY),
        ('YOUTUBE_API_KEY', YOUTUBE_API_KEY),
        ('GEMINI_API_KEY', GEMINI_API_KEY),
        ('SUPABASE_URL', SUPABASE_URL),
        ('SUPABASE_ANON_KEY', SUPABASE_ANON_KEY),
    ]
    
    missing_vars = []
    for var_name, var_value in critical_vars:
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        print("❌ CONFIGURACIÓN INCOMPLETA:")
        for var in missing_vars:
            print(f"   - {var} no está configurada")
        print("\nVerifica tu archivo .env y asegúrate de que contenga todas las variables necesarias.")
        return False
    
    print("✅ Configuración validada correctamente")
    print(f"   - YouTube API Key: {(YOUTUBE_API_KEY or '')[:10]}...")
    print(f"   - Gemini API Key: {(GEMINI_API_KEY or '')[:10]}...")
    print(f"   - Supabase URL: {SUPABASE_URL}")
    print(f"   - Canal XTB: {CHANNEL_ID_XTB}")
    return True

if __name__ == "__main__":
    # Validar configuración al ejecutar directamente
    validate_configuration()