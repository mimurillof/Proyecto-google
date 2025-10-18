"""
Módulo de gestión de base de datos para clientes y portfolios.
Gestiona la conexión con Supabase y operaciones CRUD para clientes y sus assets.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE
import logging

logger = logging.getLogger(__name__)


@dataclass
class Asset:
    """Representa un activo financiero en el portfolio de un cliente."""
    asset_id: int
    portfolio_id: int
    ticker: str  # asset_symbol en la BD
    cantidad: Optional[float] = None  # quantity
    precio_compra: Optional[float] = None  # acquisition_price
    fecha_adquisicion: Optional[str] = None  # acquisition_date


@dataclass
class Portfolio:
    """Representa un portfolio de un usuario."""
    portfolio_id: int
    user_id: str
    nombre: Optional[str] = None  # portfolio_name
    descripcion: Optional[str] = None  # description
    assets: List[Asset] = None

    def __post_init__(self):
        if self.assets is None:
            self.assets = []


@dataclass
class Cliente:
    """Representa un cliente/usuario con sus portfolios."""
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    portfolios: List[Portfolio] = None

    def __post_init__(self):
        if self.portfolios is None:
            self.portfolios = []
    
    @property
    def nombre_completo(self) -> str:
        """Retorna el nombre completo del cliente."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else f"Usuario {self.user_id}"
    
    def get_todos_los_assets(self) -> List[Asset]:
        """Retorna todos los assets de todos los portfolios del cliente."""
        all_assets = []
        for portfolio in self.portfolios:
            all_assets.extend(portfolio.assets)
        return all_assets
    
    def get_todos_los_tickers(self) -> List[str]:
        """Retorna una lista única de todos los tickers en todos los portfolios."""
        tickers = set()
        for portfolio in self.portfolios:
            for asset in portfolio.assets:
                tickers.add(asset.ticker)
        return list(tickers)


class DatabaseManager:
    """
    Gestor de base de datos para operaciones con clientes y portfolios.
    
    Estructura real en Supabase:
    
    Tabla: users
    - user_id (uuid, PK)
    - first_name (varchar)
    - last_name (varchar)
    - email (varchar)
    - password_hash (varchar)
    - birth_date (date)
    - gender (enum)
    - created_at (timestamptz)
    
    Tabla: portfolios
    - portfolio_id (int4, PK)
    - user_id (uuid, FK -> users.user_id)
    - portfolio_name (varchar)
    - description (text)
    - created_at (timestamptz)
    
    Tabla: assets
    - asset_id (int4, PK)
    - portfolio_id (int4, FK -> portfolios.portfolio_id)
    - asset_symbol (varchar) -> ticker
    - quantity (numeric)
    - acquisition_price (numeric)
    - acquisition_date (date)
    - added_at (timestamptz)
    """

    def __init__(self):
        """Inicializa el gestor de base de datos con conexión a Supabase."""
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initialization del cliente Supabase."""
        if self._client is None:
            key = SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY
            self._client = create_client(SUPABASE_URL, key)
        return self._client

    def get_clientes_activos(self) -> List[Cliente]:
        """
        Obtiene todos los clientes/usuarios de la base de datos con sus portfolios.
        
        Returns:
            List[Cliente]: Lista de clientes con sus portfolios y assets cargados
        """
        try:
            # Obtener todos los usuarios
            response = self.client.table('users').select('*').execute()
            
            if not response.data:
                logger.warning("No se encontraron usuarios en la base de datos")
                return []
            
            clientes = []
            for row in response.data:
                cliente = Cliente(
                    user_id=row['user_id'],
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    email=row.get('email')
                )
                
                # Cargar portfolios del cliente
                cliente.portfolios = self.get_portfolios_cliente(cliente.user_id)
                clientes.append(cliente)
            
            logger.info(f"✅ Se cargaron {len(clientes)} clientes")
            return clientes
            
        except Exception as e:
            logger.error(f"Error al obtener clientes: {e}")
            raise

    def get_cliente_por_id(self, user_id: str) -> Optional[Cliente]:
        """
        Obtiene un cliente específico por su user_id.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Cliente o None si no se encuentra
        """
        try:
            response = self.client.table('users').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                logger.warning(f"No se encontró el usuario con ID: {user_id}")
                return None
            
            row = response.data[0]
            cliente = Cliente(
                user_id=row['user_id'],
                first_name=row.get('first_name'),
                last_name=row.get('last_name'),
                email=row.get('email')
            )
            
            # Cargar portfolios del cliente
            cliente.portfolios = self.get_portfolios_cliente(cliente.user_id)
            
            total_assets = sum(len(p.assets) for p in cliente.portfolios)
            logger.info(f"✅ Cliente {user_id} cargado con {len(cliente.portfolios)} portfolios y {total_assets} assets")
            return cliente
            
        except Exception as e:
            logger.error(f"Error al obtener cliente {user_id}: {e}")
            raise

    def get_portfolios_cliente(self, user_id: str) -> List[Portfolio]:
        """
        Obtiene todos los portfolios de un cliente.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            List[Portfolio]: Lista de portfolios del cliente con sus assets
        """
        try:
            response = self.client.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            if not response.data:
                logger.warning(f"No se encontraron portfolios para el usuario: {user_id}")
                return []
            
            portfolios = []
            for row in response.data:
                portfolio = Portfolio(
                    portfolio_id=row['portfolio_id'],
                    user_id=row['user_id'],
                    nombre=row.get('portfolio_name'),
                    descripcion=row.get('description')
                )
                
                # Cargar assets del portfolio
                portfolio.assets = self.get_assets_portfolio(portfolio.portfolio_id)
                portfolios.append(portfolio)
            
            logger.info(f"✅ Se cargaron {len(portfolios)} portfolios para usuario {user_id}")
            return portfolios
            
        except Exception as e:
            logger.error(f"Error al obtener portfolios del usuario {user_id}: {e}")
            raise

    def get_assets_portfolio(self, portfolio_id: int) -> List[Asset]:
        """
        Obtiene todos los assets de un portfolio específico.
        
        Args:
            portfolio_id: ID del portfolio
            
        Returns:
            List[Asset]: Lista de assets del portfolio
        """
        try:
            response = self.client.table('assets').select('*').eq('portfolio_id', portfolio_id).execute()
            
            if not response.data:
                logger.debug(f"No se encontraron assets para el portfolio: {portfolio_id}")
                return []
            
            assets = []
            for row in response.data:
                asset = Asset(
                    asset_id=row['asset_id'],
                    portfolio_id=row['portfolio_id'],
                    ticker=row['asset_symbol'],  # Mapear asset_symbol a ticker
                    cantidad=row.get('quantity'),
                    precio_compra=row.get('acquisition_price'),
                    fecha_adquisicion=row.get('acquisition_date')
                )
                assets.append(asset)
            
            logger.debug(f"✅ Se cargaron {len(assets)} assets para portfolio {portfolio_id}")
            return assets
            
        except Exception as e:
            logger.error(f"Error al obtener assets del portfolio {portfolio_id}: {e}")
            raise

    def get_tickers_cliente(self, user_id: str) -> List[str]:
        """
        Obtiene solo los tickers únicos de todos los portfolios de un cliente.
        Útil para procesamiento rápido sin cargar toda la información.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            List[str]: Lista de tickers únicos
        """
        try:
            portfolios = self.get_portfolios_cliente(user_id)
            tickers = set()
            for portfolio in portfolios:
                for asset in portfolio.assets:
                    tickers.add(asset.ticker)
            return list(tickers)
        except Exception as e:
            logger.error(f"Error al obtener tickers del cliente {user_id}: {e}")
            raise

    def agregar_asset_portfolio(self, portfolio_id: int, ticker: str, cantidad: float = None, 
                                precio_compra: float = None, fecha_adquisicion: str = None) -> bool:
        """
        Agrega un asset a un portfolio específico.
        
        Args:
            portfolio_id: ID del portfolio
            ticker: Símbolo del asset
            cantidad: Cantidad de unidades
            precio_compra: Precio de adquisición
            fecha_adquisicion: Fecha de adquisición (YYYY-MM-DD)
            
        Returns:
            bool: True si se agregó exitosamente
        """
        try:
            data = {
                'portfolio_id': portfolio_id,
                'asset_symbol': ticker,
                'quantity': cantidad,
                'acquisition_price': precio_compra,
                'acquisition_date': fecha_adquisicion
            }
            
            self.client.table('assets').insert(data).execute()
            logger.info(f"✅ Asset {ticker} agregado al portfolio {portfolio_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error al agregar asset {ticker} al portfolio {portfolio_id}: {e}")
            raise

    def eliminar_asset(self, asset_id: int) -> bool:
        """
        Elimina un asset específico por su ID.
        
        Args:
            asset_id: ID del asset
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            self.client.table('assets').delete().eq('asset_id', asset_id).execute()
            logger.info(f"✅ Asset {asset_id} eliminado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar asset {asset_id}: {e}")
            raise

    def crear_portfolio(self, user_id: str, nombre: str, descripcion: str = None) -> Optional[int]:
        """
        Crea un nuevo portfolio para un usuario.
        
        Args:
            user_id: ID del usuario
            nombre: Nombre del portfolio
            descripcion: Descripción opcional
            
        Returns:
            int: ID del portfolio creado o None si falla
        """
        try:
            data = {
                'user_id': user_id,
                'portfolio_name': nombre,
                'description': descripcion
            }
            
            response = self.client.table('portfolios').insert(data).execute()
            portfolio_id = response.data[0]['portfolio_id'] if response.data else None
            logger.info(f"✅ Portfolio '{nombre}' creado para usuario {user_id} con ID {portfolio_id}")
            return portfolio_id
            
        except Exception as e:
            logger.error(f"Error al crear portfolio para usuario {user_id}: {e}")
            raise


# Instancia global del gestor de base de datos
db_manager = DatabaseManager()


# Funciones de conveniencia para acceso rápido
def get_clientes_activos() -> List[Cliente]:
    """Obtiene todos los clientes/usuarios con sus portfolios."""
    return db_manager.get_clientes_activos()


def get_cliente_por_id(user_id: str) -> Optional[Cliente]:
    """Obtiene un cliente específico por user_id."""
    return db_manager.get_cliente_por_id(user_id)


def get_tickers_cliente(user_id: str) -> List[str]:
    """Obtiene los tickers únicos de todos los portfolios de un cliente."""
    return db_manager.get_tickers_cliente(user_id)


def get_portfolios_cliente(user_id: str) -> List[Portfolio]:
    """Obtiene todos los portfolios de un cliente."""
    return db_manager.get_portfolios_cliente(user_id)
