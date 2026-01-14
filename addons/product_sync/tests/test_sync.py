# -*- coding: utf-8 -*-
"""
Tests de Integración para Product Sync
Requiere entorno de Odoo activo
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from unittest.mock import patch, Mock
import json


class TestProductSync(TransactionCase):
    """Tests de sincronización de productos"""
    
    def setUp(self):
        super(TestProductSync, self).setUp()
        
        # Limpiar datos de prueba
        self.env['product.template'].search([
            ('is_from_external', '=', True)
        ]).unlink()
        
        self.env['product.sync.log'].search([]).unlink()
    
    def test_product_creation_from_external(self):
        """Test: Crear producto desde datos externos"""
        external_data = {
            'id': 999,
            'name': 'Test Product',
            'sku': 'TEST-SKU-001',
            'description': 'Test description',
            'list_price': 99.99,
            'standard_price': 50.00,
            'barcode': '1234567890',
            'category': 'Test',
            'active': True,
        }
        
        product = self.env['product.template'].create_from_external(external_data)
        
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.external_id, '999')
        self.assertEqual(product.external_sku, 'TEST-SKU-001')
        self.assertEqual(product.list_price, 99.99)
        self.assertTrue(product.is_from_external)
        self.assertEqual(product.sync_status, 'synced')
    
    def test_product_update_from_external(self):
        """Test: Actualizar producto existente"""
        # Crear producto inicial
        product = self.env['product.template'].create({
            'name': 'Old Name',
            'external_id': '999',
            'external_sku': 'TEST-SKU-001',
            'list_price': 50.00,
            'is_from_external': True,
        })
        
        # Actualizar con nuevos datos
        new_data = {
            'id': 999,
            'name': 'New Name',
            'sku': 'TEST-SKU-001',
            'list_price': 99.99,
        }
        
        has_changes = product.update_from_external(new_data)
        
        self.assertTrue(has_changes)
        self.assertEqual(product.name, 'New Name')
        self.assertEqual(product.list_price, 99.99)
    
    def test_product_update_no_changes(self):
        """Test: Actualizar producto sin cambios retorna False"""
        product = self.env['product.template'].create({
            'name': 'Same Name',
            'external_id': '999',
            'external_sku': 'TEST-SKU-001',
            'list_price': 50.00,
            'is_from_external': True,
        })
        
        # Mismos datos
        same_data = {
            'id': 999,
            'name': 'Same Name',
            'sku': 'TEST-SKU-001',
            'list_price': 50.00,
        }
        
        has_changes = product.update_from_external(same_data)
        
        self.assertFalse(has_changes)
    
    def test_search_by_external_id(self):
        """Test: Búsqueda por external_id"""
        product = self.env['product.template'].create({
            'name': 'Test',
            'external_id': '123',
            'external_sku': 'SKU-123',
        })
        
        found = self.env['product.template'].search_by_external_id('123')
        
        self.assertEqual(found.id, product.id)
    
    def test_search_by_sku(self):
        """Test: Búsqueda por SKU"""
        product = self.env['product.template'].create({
            'name': 'Test',
            'external_sku': 'TEST-SKU',
            'default_code': 'TEST-SKU',
        })
        
        found = self.env['product.template'].search_by_sku('TEST-SKU')
        
        self.assertEqual(found.id, product.id)
    
    def test_external_id_uniqueness(self):
        """Test: external_id debe ser único"""
        self.env['product.template'].create({
            'name': 'First',
            'external_id': 'UNIQUE-ID',
            'external_sku': 'SKU-1',
        })
        
        # Intentar crear otro con mismo external_id debe fallar
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Second',
                'external_id': 'UNIQUE-ID',
                'external_sku': 'SKU-2',
            })
    
    def test_external_sku_uniqueness(self):
        """Test: external_sku debe ser único"""
        self.env['product.template'].create({
            'name': 'First',
            'external_id': 'ID-1',
            'external_sku': 'UNIQUE-SKU',
        })
        
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Second',
                'external_id': 'ID-2',
                'external_sku': 'UNIQUE-SKU',
            })
    
    def test_mark_as_synced(self):
        """Test: Marcar producto como sincronizado"""
        product = self.env['product.template'].create({
            'name': 'Test',
            'sync_status': 'pending',
        })
        
        product.mark_as_synced()
        
        self.assertEqual(product.sync_status, 'synced')
        self.assertIsNotNone(product.last_sync_date)
        self.assertFalse(product.sync_error_message)
    
    def test_mark_as_error(self):
        """Test: Marcar producto con error"""
        product = self.env['product.template'].create({
            'name': 'Test',
            'sync_status': 'synced',
        })
        
        product.mark_as_error('Test error message')
        
        self.assertEqual(product.sync_status, 'error')
        self.assertEqual(product.sync_error_message, 'Test error message')
        self.assertIsNotNone(product.last_sync_date)


class TestSyncLog(TransactionCase):
    """Tests para modelo de logs"""
    
    def setUp(self):
        super(TestSyncLog, self).setUp()
        self.SyncLog = self.env['product.sync.log']
        
        # Limpiar logs
        self.SyncLog.search([]).unlink()
    
    def test_log_creation(self):
        """Test: Crear log de sincronización"""
        log = self.SyncLog.log_operation(
            operation='create',
            external_id='123',
            external_sku='TEST-SKU',
            status='success',
            message='Product created successfully'
        )
        
        self.assertEqual(log.operation, 'create')
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.external_id, '123')
        self.assertIsNotNone(log.create_date)
    
    def test_log_success_shortcut(self):
        """Test: Atajo log_success"""
        log = self.SyncLog.log_success(
            operation='create',
            message='Success'
        )
        
        self.assertEqual(log.status, 'success')
    
    def test_log_error_shortcut(self):
        """Test: Atajo log_error"""
        log = self.SyncLog.log_error(
            operation='sync',
            message='Error occurred',
            error_details='Stack trace here'
        )
        
        self.assertEqual(log.status, 'error')
        self.assertEqual(log.operation, 'error')
        self.assertIsNotNone(log.error_details)
    
    def test_get_statistics(self):
        """Test: Obtener estadísticas de logs"""
        # Crear varios logs
        self.SyncLog.log_success(operation='create', message='1')
        self.SyncLog.log_success(operation='create', message='2')
        self.SyncLog.log_success(operation='update', message='3')
        self.SyncLog.log_error(operation='sync', message='4')
        
        stats = self.SyncLog.get_statistics()
        
        self.assertEqual(stats['total_operations'], 4)
        self.assertEqual(stats['success_count'], 3)
        self.assertEqual(stats['error_count'], 1)
        self.assertEqual(stats['created_count'], 2)
        self.assertEqual(stats['updated_count'], 1)
    
    def test_get_recent_errors(self):
        """Test: Obtener errores recientes"""
        # Crear logs
        self.SyncLog.log_success(operation='create', message='OK')
        self.SyncLog.log_error(operation='sync', message='Error 1')
        self.SyncLog.log_error(operation='sync', message='Error 2')
        
        errors = self.SyncLog.get_recent_errors(limit=2)
        
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].status, 'error')


class TestSyncIntegration(TransactionCase):
    """Tests de integración completa"""
    
    def setUp(self):
        super(TestSyncIntegration, self).setUp()
        
        # Limpiar datos
        self.env['product.template'].search([
            ('is_from_external', '=', True)
        ]).unlink()
        self.env['product.sync.log'].search([]).unlink()
        
        self.sync_service = self.env['product.sync.service']
    
    @patch('addons.product_sync.services.api_client.APIClient.get')
    def test_sync_products_success(self, mock_get):
        """Test: Sincronización exitosa de productos"""
        # Mock de respuesta de API
        mock_get.return_value = {
            'items': [
                {
                    'id': 1,
                    'name': 'Product 1',
                    'sku': 'SKU-001',
                    'list_price': 10.0,
                    'active': True,
                },
                {
                    'id': 2,
                    'name': 'Product 2',
                    'sku': 'SKU-002',
                    'list_price': 20.0,
                    'active': True,
                }
            ],
            'total': 2
        }
        
        result = self.sync_service.sync_products()
        
        # Verificar resultado
        self.assertEqual(result['total'], 2)
        self.assertGreater(result.get('create', 0) + result.get('created', 0), 0)
        self.assertEqual(result['errors'], 0)
        
        # Verificar productos creados
        products = self.env['product.template'].search([
            ('is_from_external', '=', True)
        ])
        self.assertEqual(len(products), 2)
    
    @patch('addons.product_sync.services.api_client.APIClient.get')
    def test_sync_idempotency(self, mock_get):
        """Test: Idempotencia - ejecutar 2 veces no duplica"""
        mock_get.return_value = {
            'items': [
                {
                    'id': 1,
                    'name': 'Product 1',
                    'sku': 'SKU-001',
                    'list_price': 10.0,
                    'active': True,
                }
            ],
            'total': 1
        }
        
        # Primera sincronización
        result1 = self.sync_service.sync_products()
        
        # Segunda sincronización (mismos datos)
        result2 = self.sync_service.sync_products()
        
        # Segunda vez debe ser skip, no create
        self.assertGreater(result2.get('skip', 0) + result2.get('skipped', 0), 0)
        
        # Solo debe haber 1 producto
        products = self.env['product.template'].search([
            ('is_from_external', '=', True)
        ])
        self.assertEqual(len(products), 1)


if __name__ == '__main__':
    import unittest
    unittest.main()