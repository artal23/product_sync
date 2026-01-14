# -*- coding: utf-8 -*-
from . import models
from . import services

def post_init_hook(cr, registry):
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("Product Sync module installed successfully!")

def uninstall_hook(cr, registry):
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("Product Sync module uninstalled")
