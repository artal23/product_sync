# -*- coding: utf-8 -*-
"""
Modelo para registrar logs de sincronización
Proporciona trazabilidad completa de todas las operaciones
"""

from odoo import models, fields, api
import logging
import json

_logger = logging.getLogger(__name__)


class ProductSyncLog(models.Model):
    """
    Registro de eventos de sincronización de productos
    
    Almacena información detallada de cada operación de sincronización
    para auditoría, debugging y análisis.
    """
    _name = 'product.sync.log'
    _description = 'Product Synchronization Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    # ========== Campos Básicos ==========
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        store=True,
    )
    
    operation = fields.Selection(
        selection=[
            ('create', 'Create'),
            ('update', 'Update'),
            ('skip', 'Skip (No Changes)'),
            ('delete', 'Delete'),
            ('error', 'Error'),
        ],
        string='Operation',
        required=True,
        help='Tipo de operación realizada',
    )
    
    status = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('error', 'Error'),
            ('warning', 'Warning'),
        ],
        string='Status',
        required=True,
        default='success',
        help='Resultado de la operación',
    )
    
    # ========== Relaciones ==========
    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        ondelete='set null',
        index=True,
        help='Producto afectado por esta operación',
    )
    
    # ========== Campos de Identificación Externa ==========
    external_id = fields.Char(
        string='External ID',
        index=True,
        help='ID del producto en el sistema externo',
    )
    
    external_sku = fields.Char(
        string='External SKU',
        index=True,
        help='SKU del producto en el sistema externo',
    )
    
    # ========== Mensajes y Detalles ==========
    message = fields.Text(
        string='Message',
        help='Mensaje descriptivo de la operación',
    )
    
    error_details = fields.Text(
        string='Error Details',
        help='Detalles técnicos del error (si aplica)',
    )
    
    # ========== Datos de la Operación ==========
    request_data = fields.Text(
        string='Request Data',
        help='Datos enviados/recibidos en la operación (JSON)',
    )
    
    response_data = fields.Text(
        string='Response Data',
        help='Respuesta del sistema externo (JSON)',
    )
    
    # ========== Metadatos ==========
    sync_batch_id = fields.Char(
        string='Sync Batch ID',
        index=True,
        help='ID del lote de sincronización (agrupa operaciones de la misma ejecución)',
    )
    
    execution_time = fields.Float(
        string='Execution Time (s)',
        help='Tiempo de ejecución en segundos',
        digits=(10, 3),
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Número de reintentos realizados',
    )
    
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        default=lambda self: self.env.user,
        help='Usuario que ejecutó la operación',
    )
    
    is_automatic = fields.Boolean(
        string='Automatic',
        default=True,
        help='Indica si la sincronización fue automática (cron) o manual',
    )
    
    create_date = fields.Datetime(
        string='Date',
        readonly=True,
        help='Fecha y hora de la operación',
    )

    # ========== Campos Computados ==========
    @api.depends('operation', 'product_id', 'external_id', 'create_date')
    def _compute_display_name(self):
        """Genera un nombre descriptivo para el log"""
        for log in self:
            product_name = log.product_id.name if log.product_id else 'Unknown'
            operation = dict(log._fields['operation'].selection).get(log.operation, log.operation)
            date = log.create_date.strftime('%Y-%m-%d %H:%M') if log.create_date else ''
            
            log.display_name = f"{operation} - {product_name} ({date})"

    # ========== Métodos de Creación ==========
    @api.model
    def log_operation(self, operation, product=None, external_id=None, 
                      external_sku=None, status='success', message='', 
                      error_details=None, request_data=None, response_data=None,
                      sync_batch_id=None, execution_time=0.0, retry_count=0,
                      is_automatic=True):
        """
        Registra una operación de sincronización
        
        Args:
            operation (str): Tipo de operación ('create', 'update', 'skip', 'error')
            product (product.template, optional): Producto afectado
            external_id (str, optional): ID externo
            external_sku (str, optional): SKU externo
            status (str): Estado ('success', 'error', 'warning')
            message (str): Mensaje descriptivo
            error_details (str, optional): Detalles del error
            request_data (dict, optional): Datos de la petición
            response_data (dict, optional): Datos de la respuesta
            sync_batch_id (str, optional): ID del lote
            execution_time (float): Tiempo de ejecución
            retry_count (int): Número de reintentos
            is_automatic (bool): Si es automático o manual
            
        Returns:
            product.sync.log: Log creado
        """
        values = {
            'operation': operation,
            'status': status,
            'message': message,
            'error_details': error_details,
            'external_id': external_id,
            'external_sku': external_sku,
            'sync_batch_id': sync_batch_id,
            'execution_time': execution_time,
            'retry_count': retry_count,
            'is_automatic': is_automatic,
        }
        
        if product:
            values['product_id'] = product.id
        
        # Convertir datos a JSON si es necesario
        if request_data:
            values['request_data'] = json.dumps(request_data, indent=2)
        
        if response_data:
            values['response_data'] = json.dumps(response_data, indent=2)
        
        log = self.create(values)
        
        # Logging en consola según el status
        log_message = f"[{operation.upper()}] {message}"
        if status == 'error':
            _logger.error(log_message)
        elif status == 'warning':
            _logger.warning(log_message)
        else:
            _logger.info(log_message)
        
        return log

    @api.model
    def log_success(self, operation, product=None, message='', **kwargs):
        """Atajo para registrar operación exitosa"""
        return self.log_operation(
            operation=operation,
            product=product,
            status='success',
            message=message,
            **kwargs
        )

    @api.model
    def log_error(self, operation, message='', error_details=None, **kwargs):
        """Atajo para registrar error"""
        return self.log_operation(
            operation='error',
            status='error',
            message=message,
            error_details=error_details,
            **kwargs
        )

    @api.model
    def log_warning(self, operation, message='', **kwargs):
        """Atajo para registrar advertencia"""
        return self.log_operation(
            operation=operation,
            status='warning',
            message=message,
            **kwargs
        )

    # ========== Métodos de Análisis ==========
    @api.model
    def get_statistics(self, sync_batch_id=None, date_from=None, date_to=None):
        """
        Obtiene estadísticas de sincronización
        
        Args:
            sync_batch_id (str, optional): Filtrar por lote
            date_from (datetime, optional): Fecha desde
            date_to (datetime, optional): Fecha hasta
            
        Returns:
            dict: Estadísticas agregadas
        """
        domain = []
        
        if sync_batch_id:
            domain.append(('sync_batch_id', '=', sync_batch_id))
        
        if date_from:
            domain.append(('create_date', '>=', date_from))
        
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        logs = self.search(domain)
        
        total = len(logs)
        success = len(logs.filtered(lambda l: l.status == 'success'))
        errors = len(logs.filtered(lambda l: l.status == 'error'))
        warnings = len(logs.filtered(lambda l: l.status == 'warning'))
        
        created = len(logs.filtered(lambda l: l.operation == 'create'))
        updated = len(logs.filtered(lambda l: l.operation == 'update'))
        skipped = len(logs.filtered(lambda l: l.operation == 'skip'))
        
        avg_execution_time = sum(logs.mapped('execution_time')) / total if total > 0 else 0
        total_execution_time = sum(logs.mapped('execution_time'))
        
        return {
            'total_operations': total,
            'success_count': success,
            'error_count': errors,
            'warning_count': warnings,
            'created_count': created,
            'updated_count': updated,
            'skipped_count': skipped,
            'avg_execution_time': round(avg_execution_time, 3),
            'total_execution_time': round(total_execution_time, 2),
            'success_rate': round((success / total * 100), 2) if total > 0 else 0,
        }

    @api.model
    def get_recent_errors(self, limit=10):
        """
        Obtiene los errores más recientes
        
        Args:
            limit (int): Número máximo de errores a retornar
            
        Returns:
            product.sync.log: Recordset con errores recientes
        """
        return self.search(
            [('status', '=', 'error')],
            order='create_date desc',
            limit=limit
        )

    @api.model
    def cleanup_old_logs(self, days=30):
        """
        Limpia logs antiguos para mantener la base de datos limpia
        
        Args:
            days (int): Días de antigüedad para eliminar
            
        Returns:
            int: Número de logs eliminados
        """
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        
        old_logs = self.search([
            ('create_date', '<', cutoff_date),
            ('status', '!=', 'error'),  # Mantener errores por más tiempo
        ])
        
        count = len(old_logs)
        old_logs.unlink()
        
        _logger.info(f"Eliminados {count} logs antiguos (más de {days} días)")
        
        return count

    # ========== Acciones de Vista ==========
    def action_view_product(self):
        """Acción: Ver el producto relacionado"""
        self.ensure_one()
        
        if not self.product_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No product associated with this log',
                    'type': 'warning',
                }
            }
        
        return {
            'name': 'Product',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_retry_operation(self):
        """Acción: Reintentar operación fallida"""
        self.ensure_one()
        
        if self.status != 'error':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Only error operations can be retried',
                    'type': 'warning',
                }
            }
        
        sync_service = self.env['product.sync.service']
        
        try:
            if self.external_id:
                sync_service.sync_single_product(self.external_id)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Operation retried successfully',
                        'type': 'success',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Retry failed: {str(e)}',
                    'type': 'danger',
                }
            }
