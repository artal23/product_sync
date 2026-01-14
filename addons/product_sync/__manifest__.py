# -*- coding: utf-8 -*-
{
    'name': 'Product Synchronization',
    'version': '17.0.1.0.0',
    'category': 'Sales/Integration',
    'summary': 'Sincronización bidireccional de productos con API externa',
    'description': """
        Product Synchronization Module
        ================================
        
        Este módulo proporciona sincronización robusta entre Odoo y sistemas externos.
        
        Características principales:
        ----------------------------
        * Sincronización automática mediante cron jobs
        * Idempotencia garantizada (evita duplicados)
        * Reintentos con backoff exponencial
        * Rate limiting configurable
        * Logs estructurados y trazabilidad completa
        * Validación y normalización de datos
        * Testing automatizado
        
        Casos de uso:
        -------------
        * Sincronizar catálogos de proveedores
        * Integración con marketplaces
        * Actualización automática de precios
        * Consolidación de inventarios
        
        Documentación técnica:
        ---------------------
        Ver README.md para instrucciones detalladas de instalación,
        configuración y uso.
        
        Autor: Candidato Backend Developer
        Fecha: Enero 2026
    """,
    'author': 'Candidato Odoo',
    'website': 'https://github.com/tu-usuario/odoo-product-sync',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/sync_log_views.xml',
        'views/menu_views.xml',
        'data/ir_cron.xml',
        'data/sync_config.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}