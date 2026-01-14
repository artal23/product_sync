# -*- coding: utf-8 -*-
"""
Servicio de Sincronización de Productos
Lógica principal de integración con sistema externo
"""

from odoo import models, api
from odoo.exceptions import UserError
import logging
import time
import uuid

_logger = logging.getLogger(__name__)


class ProductSyncService(models.AbstractModel):
    """
    Servicio transaccional para sincronización de productos
    
    Responsabilidades:
    - Orquestar el flujo de sincronización
    - Garantizar idempotencia
    - Manejar errores y reintentos
    - Registrar logs estructurados
    """
    _name = 'product.sync.service'
    _description = 'Product Synchronization Service'

    def _get_api_client(self):
        """
        Obtiene o crea una instancia del cliente API
        
        Returns:
            APIClient: Cliente HTTP configurado
        """
        # Lazy import para evitar problemas de inicialización
        from .api_client import APIClient
        
        # Obtener configuración desde parámetros del sistema
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'product_sync.api_base_url',
            'http://mock-api:8000'
        )
        
        timeout = int(self.env['ir.config_parameter'].sudo().get_param(
            'product_sync.api_timeout',
            '30'
        ))
        
        max_retries = int(self.env['ir.config_parameter'].sudo().get_param(
            'product_sync.api_max_retries',
            '5'
        ))
        
        return APIClient(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )

    def _get_rate_limiter(self):
        """
        Obtiene o crea una instancia del rate limiter
        
        Returns:
            RateLimiter: Controlador de tasa de peticiones
        """
        # Lazy import para evitar problemas de inicialización
        from .rate_limiter import RateLimiter
        
        rate_limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'product_sync.rate_limit',
            '10'  # 10 peticiones por segundo
        ))
        
        return RateLimiter(rate=rate_limit)

    @api.model
    def sync_products(self, dry_run=False, limit=None):
        """
        Sincroniza productos desde el sistema externo
        
        Flujo principal:
        1. Obtener productos de API externa
        2. Para cada producto:
           a. Validar datos
           b. Buscar si existe (por SKU)
           c. Crear o actualizar
           d. Registrar log
        
        Args:
            dry_run (bool): Si es True, no escribe en BD (solo simula)
            limit (int, optional): Limitar número de productos a procesar
            
        Returns:
            dict: Resumen de la sincronización
        """
        _logger.info("=" * 80)
        _logger.info("INICIANDO SINCRONIZACIÓN DE PRODUCTOS")
        _logger.info("=" * 80)
        
        start_time = time.time()
        sync_batch_id = str(uuid.uuid4())
        
        api_client = self._get_api_client()
        rate_limiter = self._get_rate_limiter()
        
        ProductTemplate = self.env['product.template']
        SyncLog = self.env['product.sync.log']
        
        summary = {
            'total': 0,
            'create': 0,    # Operación desde API
            'created': 0,   # Contador legacy
            'update': 0,    # Operación desde API
            'updated': 0,   # Contador legacy
            'skip': 0,      # Operación desde API
            'skipped': 0,   # Contador legacy
            'errors': 0,
            'sync_batch_id': sync_batch_id,
        }
        
        try:
            # 1. Obtener productos de API externa
            _logger.info("Fetching products from external API...")
            rate_limiter.wait_if_needed()
            
            response = api_client.get('/products')
            
            if not response or 'items' not in response:
                raise UserError("Invalid response from external API")
            
            external_products = response['items']
            total_available = response.get('total', len(external_products))
            
            _logger.info(f"Found {total_available} products in external API")
            
            # Aplicar límite si se especificó
            if limit:
                external_products = external_products[:limit]
                _logger.info(f"Limited to {limit} products for processing")
            
            summary['total'] = len(external_products)
            
            # 2. Procesar cada producto
            for index, ext_product in enumerate(external_products, start=1):
                _logger.info(f"\nProcessing product {index}/{len(external_products)}: {ext_product.get('name')}")
                
                operation_start = time.time()
                
                try:
                    result = self._sync_single_product(
                        ext_product,
                        sync_batch_id=sync_batch_id,
                        dry_run=dry_run
                    )
                    
                    summary[result['operation']] += 1
                    
                except Exception as e:
                    _logger.error(f"Error processing product: {str(e)}", exc_info=True)
                    summary['errors'] += 1
                    
                    if not dry_run:
                        SyncLog.log_error(
                            operation='error',
                            external_id=str(ext_product.get('id', '')),
                            external_sku=ext_product.get('sku', ''),
                            message=f"Error processing product: {str(e)}",
                            error_details=str(e),
                            request_data=ext_product,
                            sync_batch_id=sync_batch_id,
                            execution_time=time.time() - operation_start,
                        )
                
                # Respetar rate limit entre productos
                rate_limiter.wait_if_needed()
            
            # 3. Commit final si no es dry run
            if not dry_run:
                self.env.cr.commit()
        
        except Exception as e:
            _logger.error(f"Critical error during synchronization: {str(e)}", exc_info=True)
            if not dry_run:
                self.env.cr.rollback()
            raise
        
        finally:
            execution_time = time.time() - start_time
            
            _logger.info("\n" + "=" * 80)
            _logger.info("SINCRONIZACIÓN COMPLETADA")
            _logger.info("=" * 80)
            _logger.info(f"Total:    {summary['total']}")
            _logger.info(f"Created:  {summary['created']}")
            _logger.info(f"Updated:  {summary['updated']}")
            _logger.info(f"Skipped:  {summary['skipped']}")
            _logger.info(f"Errors:   {summary['errors']}")
            _logger.info(f"Time:     {execution_time:.2f}s")
            _logger.info(f"Batch ID: {sync_batch_id}")
            _logger.info("=" * 80)
            
            summary['execution_time'] = round(execution_time, 2)
        
        return summary

    def _sync_single_product(self, ext_product, sync_batch_id=None, dry_run=False):
        """
        Sincroniza un solo producto
        
        Garantiza idempotencia mediante:
        - Búsqueda por external_id
        - Búsqueda por SKU si no tiene external_id
        - Comparación de valores antes de actualizar
        
        Args:
            ext_product (dict): Datos del producto externo
            sync_batch_id (str): ID del lote de sincronización
            dry_run (bool): Modo simulación
            
        Returns:
            dict: Resultado de la operación
        """
        operation_start = time.time()
        
        ProductTemplate = self.env['product.template']
        SyncLog = self.env['product.sync.log']
        
        external_id = str(ext_product.get('id', ''))
        external_sku = ext_product.get('sku', '')
        
        # 1. Validar datos mínimos
        if not external_id or not external_sku:
            raise ValueError(f"Missing required fields: id={external_id}, sku={external_sku}")
        
        # 2. Buscar producto existente (IDEMPOTENCIA)
        existing_product = ProductTemplate.search_by_external_id(external_id)
        
        if not existing_product:
            # Buscar por SKU como fallback
            existing_product = ProductTemplate.search_by_sku(external_sku)
        
        # 3. Decidir operación: CREATE o UPDATE o SKIP
        if existing_product:
            # Producto existe: verificar si hay cambios
            if dry_run:
                operation = 'update'
                message = f"[DRY RUN] Would update product: {ext_product.get('name')}"
            else:
                has_changes = existing_product.update_from_external(ext_product)
                
                if has_changes:
                    operation = 'update'
                    message = f"Product updated: {existing_product.name}"
                    existing_product.mark_as_synced()
                else:
                    operation = 'skip'
                    message = f"Product unchanged, skipping: {existing_product.name}"
            
            product = existing_product
        
        else:
            # Producto no existe: crear
            if dry_run:
                operation = 'create'
                message = f"[DRY RUN] Would create product: {ext_product.get('name')}"
                product = ProductTemplate  # Mock para dry_run
            else:
                product = ProductTemplate.create_from_external(ext_product)
                operation = 'create'
                message = f"Product created: {product.name}"
        
        # 4. Registrar log
        execution_time = time.time() - operation_start
        
        if not dry_run:
            SyncLog.log_success(
                operation=operation,
                product=product if not dry_run else None,
                external_id=external_id,
                external_sku=external_sku,
                message=message,
                request_data=ext_product,
                sync_batch_id=sync_batch_id,
                execution_time=execution_time,
            )
        
        _logger.info(f"  → {operation.upper()}: {message} ({execution_time:.3f}s)")
        
        return {
            'operation': operation,
            'product': product,
            'execution_time': execution_time,
        }

    @api.model
    def sync_single_product(self, external_id):
        """
        Sincroniza un solo producto por su external_id
        
        Útil para:
        - Sincronización manual desde UI
        - Webhooks de cambios en tiempo real
        - Recuperación de errores específicos
        
        Args:
            external_id (str): ID del producto en sistema externo
            
        Returns:
            dict: Resultado de la sincronización
        """
        _logger.info(f"Syncing single product: {external_id}")
        
        api_client = self._get_api_client()
        rate_limiter = self._get_rate_limiter()
        
        # Obtener producto de API
        rate_limiter.wait_if_needed()
        ext_product = api_client.get(f'/products/{external_id}')
        
        if not ext_product:
            raise UserError(f"Product {external_id} not found in external API")
        
        # Sincronizar
        sync_batch_id = str(uuid.uuid4())
        result = self._sync_single_product(ext_product, sync_batch_id=sync_batch_id)
        
        self.env.cr.commit()
        
        return result

    @api.model
    def run_scheduled_sync(self):
        """
        Método llamado por el cron job
        
        Ejecuta sincronización completa automáticamente
        """
        _logger.info("Running scheduled product synchronization (CRON)")
        
        try:
            result = self.sync_products()
            
            # Enviar notificación si hay errores
            if result['errors'] > 0:
                self._send_error_notification(result)
            
            return result
        
        except Exception as e:
            _logger.error(f"Scheduled sync failed: {str(e)}", exc_info=True)
            self._send_error_notification({'error': str(e)})
            raise

    def _send_error_notification(self, result):
        """
        Envía notificación de errores al administrador
        
        Args:
            result (dict): Resultado de la sincronización
        """
        # Implementar según necesidades:
        # - Email al administrador
        # - Notification en Odoo
        # - Log en Sentry/otro sistema
        
        _logger.warning(f"Sync errors detected: {result}")
        
        # TODO: Implementar notificación real
        pass

    @api.model
    def test_connection(self):
        """
        Prueba la conexión con la API externa
        
        Returns:
            dict: Estado de la conexión
        """
        _logger.info("Testing external API connection...")
        
        try:
            api_client = self._get_api_client()
            response = api_client.get('/health')
            
            if response and response.get('status') == 'healthy':
                _logger.info("✓ API connection successful")
                return {
                    'status': 'success',
                    'message': 'Connection successful',
                    'details': response,
                }
            else:
                _logger.error("✗ API connection failed")
                return {
                    'status': 'error',
                    'message': 'API returned unexpected response',
                    'details': response,
                }
        
        except Exception as e:
            _logger.error(f"✗ Connection test failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
            }