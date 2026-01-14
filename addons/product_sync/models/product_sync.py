# -*- coding: utf-8 -*-
"""
Extensión del modelo product.template para sincronización
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """
    Extiende product.template para agregar funcionalidad de sincronización
    """
    _inherit = 'product.template'

    # ========== Campos de Sincronización ==========
    external_id = fields.Char(
        string='External ID',
        help='ID del producto en el sistema externo',
        index=True,
        copy=False,
        readonly=True,
    )
    
    external_sku = fields.Char(
        string='External SKU',
        help='SKU del producto en el sistema externo',
        index=True,
        copy=False,
    )
    
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        help='Última vez que se sincronizó con el sistema externo',
        readonly=True,
        copy=False,
    )
    
    sync_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('synced', 'Synced'),
            ('error', 'Error'),
            ('manual', 'Manual - No Sync'),
        ],
        string='Sync Status',
        default='manual',
        help='Estado de sincronización del producto',
        readonly=True,
        copy=False,
    )
    
    sync_error_message = fields.Text(
        string='Sync Error Message',
        help='Último mensaje de error durante la sincronización',
        readonly=True,
        copy=False,
    )
    
    is_from_external = fields.Boolean(
        string='From External System',
        help='Indica si este producto fue creado desde un sistema externo',
        default=False,
        copy=False,
    )
    
    sync_log_ids = fields.One2many(
        comodel_name='product.sync.log',
        inverse_name='product_id',
        string='Sync Logs',
        help='Historial de sincronizaciones de este producto',
    )
    
    sync_log_count = fields.Integer(
        string='Sync Log Count',
        compute='_compute_sync_log_count',
        store=False,
    )

    # ========== Campos Computados ==========
    @api.depends('sync_log_ids')
    def _compute_sync_log_count(self):
        """Calcula el número de logs de sincronización"""
        for product in self:
            product.sync_log_count = len(product.sync_log_ids)

    # ========== Constraints ==========
    _sql_constraints = [
        (
            'external_id_unique',
            'UNIQUE(external_id)',
            'El External ID debe ser único. Ya existe un producto con este ID externo.'
        ),
        (
            'external_sku_unique',
            'UNIQUE(external_sku)',
            'El External SKU debe ser único. Ya existe un producto con este SKU externo.'
        ),
    ]

    @api.constrains('external_id', 'external_sku')
    def _check_external_fields(self):
        """Valida que external_id y external_sku sean consistentes"""
        for product in self:
            if product.external_id and not product.external_sku:
                raise ValidationError(
                    'Si el producto tiene External ID, debe tener también External SKU'
                )

    # ========== Métodos de Búsqueda ==========
    def search_by_external_id(self, external_id):
        """
        Busca un producto por su external_id
        
        Args:
            external_id (str): ID del sistema externo
            
        Returns:
            product.template: Producto encontrado o recordset vacío
        """
        return self.search([('external_id', '=', external_id)], limit=1)

    def search_by_sku(self, sku):
        """
        Busca un producto por su SKU (interno o externo)
        
        Args:
            sku (str): SKU a buscar
            
        Returns:
            product.template: Producto encontrado o recordset vacío
        """
        # Buscar primero por external_sku
        product = self.search([('external_sku', '=', sku)], limit=1)
        
        # Si no se encuentra, buscar por default_code (SKU interno de Odoo)
        if not product:
            product = self.search([('default_code', '=', sku)], limit=1)
        
        return product

    # ========== Métodos de Sincronización ==========
    def mark_as_synced(self):
        """Marca el producto como sincronizado exitosamente"""
        self.write({
            'sync_status': 'synced',
            'last_sync_date': fields.Datetime.now(),
            'sync_error_message': False,
        })
        _logger.info(f"Producto {self.name} (ID: {self.id}) marcado como sincronizado")

    def mark_as_error(self, error_message):
        """
        Marca el producto con error de sincronización
        
        Args:
            error_message (str): Mensaje de error descriptivo
        """
        self.write({
            'sync_status': 'error',
            'last_sync_date': fields.Datetime.now(),
            'sync_error_message': error_message,
        })
        _logger.error(f"Error en producto {self.name} (ID: {self.id}): {error_message}")

    def update_from_external(self, external_data):
        """
        Actualiza el producto con datos del sistema externo
        
        Args:
            external_data (dict): Diccionario con datos del sistema externo
                Esperado: {
                    'id': int,
                    'name': str,
                    'sku': str,
                    'description': str,
                    'list_price': float,
                    'standard_price': float,
                    'barcode': str,
                    'category': str,
                    'active': bool,
                }
        
        Returns:
            bool: True si se actualizó, False si no hubo cambios
        """
        values = self._prepare_values_from_external(external_data)
        
        # Verificar si hay cambios reales
        has_changes = False
        for field_name, new_value in values.items():
            old_value = getattr(self, field_name)
            if old_value != new_value:
                has_changes = True
                break
        
        if has_changes:
            self.write(values)
            _logger.info(f"Producto {self.name} actualizado con datos externos")
            return True
        else:
            _logger.debug(f"Producto {self.name} sin cambios, omitiendo actualización")
            return False

    def _prepare_values_from_external(self, external_data):
        """
        Prepara los valores para crear/actualizar desde datos externos
        
        Args:
            external_data (dict): Datos del sistema externo
            
        Returns:
            dict: Valores preparados para Odoo
        """
        values = {
            'name': external_data.get('name', ''),
            'external_id': str(external_data.get('id', '')),
            'external_sku': external_data.get('sku', ''),
            'default_code': external_data.get('sku', ''),  # SKU interno de Odoo
            'description': external_data.get('description', ''),
            'list_price': float(external_data.get('list_price', 0.0)),
            'standard_price': float(external_data.get('standard_price', 0.0)),
            'barcode': external_data.get('barcode', ''),
            'active': external_data.get('active', True),
            'is_from_external': True,
            'last_sync_date': fields.Datetime.now(),
        }
        
        # Limpiar valores None o vacíos
        values = {k: v for k, v in values.items() if v not in [None, '']}
        
        return values

    @api.model
    def create_from_external(self, external_data):
        """
        Crea un nuevo producto desde datos externos
        
        Args:
            external_data (dict): Datos del sistema externo
            
        Returns:
            product.template: Producto creado
        """
        values = self._prepare_values_from_external(external_data)
        values['sync_status'] = 'synced'
        
        product = self.create(values)
        
        _logger.info(
            f"Producto creado desde sistema externo: {product.name} "
            f"(External ID: {product.external_id})"
        )
        
        return product

    # ========== Métodos de Acción (llamados desde UI) ==========
    def action_sync_from_external(self):
        """
        Acción manual: Sincronizar productos seleccionados
        
        Llamada desde: Botón en vista de lista de productos
        """
        sync_service = self.env['product.sync.service']
        
        for product in self:
            if not product.external_id:
                _logger.warning(
                    f"Producto {product.name} no tiene External ID, omitiendo"
                )
                continue
            
            try:
                sync_service.sync_single_product(product.external_id)
            except Exception as e:
                _logger.error(
                    f"Error al sincronizar producto {product.name}: {str(e)}"
                )

    def action_view_sync_logs(self):
        """
        Acción: Ver logs de sincronización de este producto
        
        Returns:
            dict: Acción de Odoo para abrir vista de logs
        """
        self.ensure_one()
        
        return {
            'name': f'Sync Logs - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.sync.log',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_mark_manual(self):
        """Marca productos como manuales (no sincronizar)"""
        self.write({'sync_status': 'manual', 'is_from_external': False})

    # ========== Métodos Auxiliares ==========
    @api.model
    def get_sync_statistics(self):
        """
        Obtiene estadísticas de sincronización
        
        Returns:
            dict: Diccionario con estadísticas
        """
        total = self.search_count([])
        synced = self.search_count([('sync_status', '=', 'synced')])
        pending = self.search_count([('sync_status', '=', 'pending')])
        errors = self.search_count([('sync_status', '=', 'error')])
        manual = self.search_count([('sync_status', '=', 'manual')])
        from_external = self.search_count([('is_from_external', '=', True)])
        
        return {
            'total_products': total,
            'synced': synced,
            'pending': pending,
            'errors': errors,
            'manual': manual,
            'from_external': from_external,
            'last_sync': self.search(
                [('last_sync_date', '!=', False)],
                order='last_sync_date desc',
                limit=1
            ).last_sync_date or False,
        }
