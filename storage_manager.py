"""
Módulo de gestión de almacenamiento en Supabase Storage.
Maneja la subida, descarga y gestión de archivos por cliente.
"""

import os
import tempfile
from typing import Optional, List
from supabase import create_client, Client
from config import (
    SUPABASE_URL, 
    SUPABASE_ANON_KEY, 
    SUPABASE_SERVICE_ROLE, 
    SUPABASE_BUCKET_NAME
)
import logging

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Gestor de almacenamiento en Supabase Storage.
    
    Estructura de carpetas:
    portfolio-files/
    ├── {cliente_id_1}/
    │   ├── AAPL_analisis_financiero.md
    │   ├── MSFT_analisis_financiero.md
    │   └── informe_consolidado.md
    ├── {cliente_id_2}/
    │   └── ...
    └── shared/
        └── templates/
    """

    def __init__(self):
        """Inicializa el gestor de almacenamiento."""
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initialization del cliente Supabase."""
        if self._client is None:
            key = SUPABASE_SERVICE_ROLE or SUPABASE_ANON_KEY
            self._client = create_client(SUPABASE_URL, key)
        return self._client

    def _get_ruta_cliente(self, cliente_id: str, nombre_archivo: str) -> str:
        """
        Construye la ruta completa del archivo en el storage del cliente.
        
        Args:
            cliente_id: ID del cliente
            nombre_archivo: Nombre del archivo
            
        Returns:
            str: Ruta completa (ej: "cliente_123/AAPL_analisis_financiero.md")
        """
        return f"{cliente_id}/{nombre_archivo}"

    def existe_archivo(self, cliente_id: str, nombre_archivo: str) -> bool:
        """
        Verifica si un archivo existe en el storage del cliente.
        
        Args:
            cliente_id: ID del cliente
            nombre_archivo: Nombre del archivo
            
        Returns:
            bool: True si el archivo existe
        """
        try:
            items = self.client.storage.from_(SUPABASE_BUCKET_NAME).list(path=cliente_id)
            if not items:
                return False
            return any(
                getattr(it, "name", None) == nombre_archivo or 
                (isinstance(it, dict) and it.get("name") == nombre_archivo) 
                for it in items
            )
        except Exception as e:
            logger.error(f"Error al verificar existencia de archivo {nombre_archivo} para cliente {cliente_id}: {e}")
            return False

    def subir_texto(
        self, 
        contenido_texto: str, 
        nombre_archivo: str, 
        cliente_id: str,
        content_type: str = "text/markdown; charset=utf-8"
    ) -> bool:
        """
        Sube un archivo de texto al storage del cliente.
        
        Args:
            contenido_texto: Contenido del archivo
            nombre_archivo: Nombre del archivo
            cliente_id: ID del cliente
            content_type: Tipo de contenido MIME
            
        Returns:
            bool: True si se subió exitosamente
        """
        try:
            ruta_remota = self._get_ruta_cliente(cliente_id, nombre_archivo)
            temp_path = None
            
            try:
                # Crear archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp:
                    tmp.write(contenido_texto)
                    temp_path = tmp.name

                # Verificar si ya existe
                ya_existia = self.existe_archivo(cliente_id, nombre_archivo)

                # Subir a Supabase
                self.client.storage.from_(SUPABASE_BUCKET_NAME).upload(
                    path=ruta_remota,
                    file=temp_path,
                    file_options={
                        "cacheControl": "3600",
                        "upsert": "true",
                        "contentType": content_type,
                    },
                )

                accion = "actualizado" if ya_existia else "creado"
                logger.info(f"✅ Archivo {accion}: bucket='{SUPABASE_BUCKET_NAME}', path='{ruta_remota}'")
                print(f"✅ Archivo {accion} en Supabase: {ruta_remota}")
                return True
                
            finally:
                # Limpiar archivo temporal
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Error al subir archivo {nombre_archivo} para cliente {cliente_id}: {e}")
            print(f"❌ Error al subir archivo {nombre_archivo}: {e}")
            return False

    def descargar_archivo(self, cliente_id: str, nombre_archivo: str) -> Optional[bytes]:
        """
        Descarga un archivo del storage del cliente.
        
        Args:
            cliente_id: ID del cliente
            nombre_archivo: Nombre del archivo
            
        Returns:
            bytes: Contenido del archivo o None si falla
        """
        try:
            ruta_remota = self._get_ruta_cliente(cliente_id, nombre_archivo)
            response = self.client.storage.from_(SUPABASE_BUCKET_NAME).download(ruta_remota)
            logger.info(f"✅ Archivo descargado: {ruta_remota}")
            return response
        except Exception as e:
            logger.error(f"Error al descargar archivo {nombre_archivo} para cliente {cliente_id}: {e}")
            return None

    def listar_archivos_cliente(self, cliente_id: str) -> List[dict]:
        """
        Lista todos los archivos en el storage del cliente.
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            List[dict]: Lista de metadatos de archivos
        """
        try:
            items = self.client.storage.from_(SUPABASE_BUCKET_NAME).list(path=cliente_id)
            logger.info(f"✅ Listados {len(items)} archivos para cliente {cliente_id}")
            return items
        except Exception as e:
            logger.error(f"Error al listar archivos para cliente {cliente_id}: {e}")
            return []

    def eliminar_archivo(self, cliente_id: str, nombre_archivo: str) -> bool:
        """
        Elimina un archivo del storage del cliente.
        
        Args:
            cliente_id: ID del cliente
            nombre_archivo: Nombre del archivo
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            ruta_remota = self._get_ruta_cliente(cliente_id, nombre_archivo)
            self.client.storage.from_(SUPABASE_BUCKET_NAME).remove([ruta_remota])
            logger.info(f"✅ Archivo eliminado: {ruta_remota}")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar archivo {nombre_archivo} para cliente {cliente_id}: {e}")
            return False

    def crear_carpeta_cliente(self, cliente_id: str) -> bool:
        """
        Crea la carpeta para un nuevo cliente (si es necesario).
        En Supabase, las carpetas se crean implícitamente al subir archivos.
        Esta función crea un archivo .gitkeep para forzar la creación de la carpeta.
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            bool: True si se creó exitosamente
        """
        try:
            return self.subir_texto(
                contenido_texto="# Portfolio files directory\nThis folder contains financial reports for this client.\n",
                nombre_archivo=".gitkeep",
                cliente_id=cliente_id,
                content_type="text/plain; charset=utf-8"
            )
        except Exception as e:
            logger.error(f"Error al crear carpeta para cliente {cliente_id}: {e}")
            return False

    def limpiar_archivos_antiguos_cliente(self, cliente_id: str, max_archivos: int = 50) -> bool:
        """
        Limpia archivos antiguos de un cliente si excede el límite.
        Mantiene solo los archivos más recientes.
        
        Args:
            cliente_id: ID del cliente
            max_archivos: Número máximo de archivos a mantener
            
        Returns:
            bool: True si se limpió exitosamente
        """
        try:
            archivos = self.listar_archivos_cliente(cliente_id)
            
            if len(archivos) <= max_archivos:
                logger.info(f"Cliente {cliente_id} tiene {len(archivos)} archivos (límite: {max_archivos})")
                return True
            
            # Ordenar por fecha (más antiguos primero)
            archivos_ordenados = sorted(
                archivos, 
                key=lambda x: x.get('created_at', '') or x.get('updated_at', ''), 
                reverse=False
            )
            
            # Eliminar los más antiguos
            archivos_a_eliminar = archivos_ordenados[:len(archivos) - max_archivos]
            for archivo in archivos_a_eliminar:
                nombre = archivo.get('name') or archivo.get('filename', '')
                if nombre and nombre != '.gitkeep':
                    self.eliminar_archivo(cliente_id, nombre)
            
            logger.info(f"✅ Limpiados {len(archivos_a_eliminar)} archivos antiguos para cliente {cliente_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error al limpiar archivos antiguos para cliente {cliente_id}: {e}")
            return False

    def get_url_publica(self, cliente_id: str, nombre_archivo: str) -> Optional[str]:
        """
        Obtiene la URL pública de un archivo (si el bucket es público).
        
        Args:
            cliente_id: ID del cliente
            nombre_archivo: Nombre del archivo
            
        Returns:
            str: URL pública o None si falla
        """
        try:
            ruta_remota = self._get_ruta_cliente(cliente_id, nombre_archivo)
            url = self.client.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(ruta_remota)
            return url
        except Exception as e:
            logger.error(f"Error al obtener URL pública para {nombre_archivo} del cliente {cliente_id}: {e}")
            return None


# Instancia global del gestor de almacenamiento
storage_manager = StorageManager()


# Funciones de conveniencia para acceso rápido
def subir_informe_cliente(contenido: str, nombre_archivo: str, cliente_id: str) -> bool:
    """Sube un informe al storage del cliente."""
    return storage_manager.subir_texto(contenido, nombre_archivo, cliente_id)


def listar_informes_cliente(cliente_id: str) -> List[dict]:
    """Lista todos los informes de un cliente."""
    return storage_manager.listar_archivos_cliente(cliente_id)


def crear_carpeta_cliente(cliente_id: str) -> bool:
    """Crea la carpeta para un nuevo cliente."""
    return storage_manager.crear_carpeta_cliente(cliente_id)
