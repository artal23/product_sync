# ============================================================================
# Makefile para Odoo Product Sync Integration
# ============================================================================
# Proporciona comandos simples para gestionar el entorno de desarrollo
# y ejecutar pruebas automatizadas
# ============================================================================

.PHONY: help build up down restart logs clean test test-integration test-unit install-module demo health check setup

# Variables de configuración
DOCKER_COMPOSE = docker-compose
ODOO_CONTAINER = odoo17_app
POSTGRES_CONTAINER = odoo17_postgres
API_CONTAINER = mock_api
DB_NAME = odoo_sync_test
ODOO_PORT = 8069
API_PORT = 8000

GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

# ============================================================================
# COMANDOS PRINCIPALES
# ============================================================================

help:
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Odoo Product Sync - Makefile Commands$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Comandos de Infraestructura:$(NC)"
	@echo "  make setup              - Configuración inicial completa"
	@echo "  make build              - Construir las imágenes Docker"
	@echo "  make up                 - Levantar todos los servicios"
	@echo "  make down               - Detener todos los servicios"
	@echo "  make restart            - Reiniciar todos los servicios"
	@echo "  make clean              - Limpiar contenedores y volúmenes"
	@echo ""
	@echo "$(YELLOW)Comandos de Monitoreo:$(NC)"
	@echo "  make logs               - Ver logs de todos los servicios"
	@echo "  make logs-odoo          - Ver logs solo de Odoo"
	@echo "  make logs-api           - Ver logs solo de Mock API"
	@echo "  make health             - Verificar salud de los servicios"
	@echo "  make status             - Ver estado de los contenedores"
	@echo ""
	@echo "$(YELLOW)Comandos de Desarrollo:$(NC)"
	@echo "  make shell-odoo         - Entrar al shell de Odoo"
	@echo "  make shell-postgres     - Entrar al shell de PostgreSQL"
	@echo "  make shell-api          - Entrar al shell de Mock API"
	@echo "  make install-module     - Instalar módulo product_sync"
	@echo "  make update-module      - Actualizar módulo product_sync"
	@echo ""
	@echo "$(YELLOW)Comandos de Testing:$(NC)"
	@echo "  make test               - Ejecutar todas las pruebas"
	@echo "  make test-unit          - Ejecutar pruebas unitarias"
	@echo "  make test-integration   - Ejecutar pruebas de integración"
	@echo "  make test-sync          - Probar sincronización manual"
	@echo ""
	@echo "$(YELLOW)Comandos de Datos:$(NC)"
	@echo "  make demo               - Cargar datos de demostración"
	@echo "  make sync               - Ejecutar sincronización completa"
	@echo "  make sync-dry-run       - Simular sincronización (dry run)"
	@echo "  make reset-data         - Limpiar datos de sincronización"
	@echo ""
	@echo "$(YELLOW)URLs de Acceso:$(NC)"
	@echo "  Odoo:         http://localhost:$(ODOO_PORT)"
	@echo "  Mock API:     http://localhost:$(API_PORT)"
	@echo "  API Docs:     http://localhost:$(API_PORT)/docs"
	@echo ""

# ============================================================================
# SETUP E INSTALACIÓN INICIAL
# ============================================================================

setup:
	@echo "$(GREEN)🚀 Configurando entorno inicial...$(NC)"
	@make build
	@make up
	@echo "$(YELLOW)⏳ Esperando que los servicios estén listos...$(NC)"
	@sleep 10
	@make health
	@echo "$(GREEN)✅ Setup completado!$(NC)"
	@echo ""
	@echo "$(YELLOW)📋 Próximos pasos:$(NC)"
	@echo "1. Crear base de datos en: http://localhost:$(ODOO_PORT)"
	@echo "2. Instalar módulo: make install-module"
	@echo "3. Ejecutar sincronización: make sync"

build:
	@echo "$(GREEN)🔨 Construyendo imágenes Docker...$(NC)"
	$(DOCKER_COMPOSE) build

up:
	@echo "$(GREEN)🚀 Levantando servicios...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Servicios levantados$(NC)"
	@make status

down:
	@echo "$(YELLOW)⏹️  Deteniendo servicios...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Servicios detenidos$(NC)"

restart:
	@echo "$(YELLOW)🔄 Reiniciando servicios...$(NC)"
	@make down
	@make up

clean:
	@echo "$(RED)🧹 Limpiando contenedores y volúmenes...$(NC)"
	@echo "$(RED)⚠️  ADVERTENCIA: Esto eliminará todos los datos!$(NC)"
	@read -p "¿Estás seguro? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) down -v; \
		docker system prune -f; \
		echo "$(GREEN)✅ Limpieza completada$(NC)"; \
	else \
		echo "$(YELLOW)❌ Operación cancelada$(NC)"; \
	fi

# ============================================================================
# MONITOREO Y LOGS
# ============================================================================

logs:
	$(DOCKER_COMPOSE) logs -f

logs-odoo:
	$(DOCKER_COMPOSE) logs -f $(ODOO_CONTAINER)

logs-api:
	$(DOCKER_COMPOSE) logs -f $(API_CONTAINER)

status:
	@echo "$(GREEN)📊 Estado de los servicios:$(NC)"
	@$(DOCKER_COMPOSE) ps

health:
	@echo "$(GREEN)🏥 Verificando salud de los servicios...$(NC)"
	@echo ""
	@echo "$(YELLOW)PostgreSQL:$(NC)"
	@docker exec $(POSTGRES_CONTAINER) pg_isready -U odoo && \
		echo "  $(GREEN)✅ PostgreSQL: OK$(NC)" || \
		echo "  $(RED)❌ PostgreSQL: FAIL$(NC)"
	@echo ""
	@echo "$(YELLOW)Mock API:$(NC)"
	@curl -s http://localhost:$(API_PORT)/health | grep -q "healthy" && \
		echo "  $(GREEN)✅ Mock API: OK$(NC)" || \
		echo "  $(RED)❌ Mock API: FAIL$(NC)"
	@echo ""
	@echo "$(YELLOW)Odoo:$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:$(ODOO_PORT)/web/database/selector | grep -q "200\|303" && \
		echo "  $(GREEN)✅ Odoo: OK$(NC)" || \
		echo "  $(RED)❌ Odoo: FAIL$(NC)"
	@echo ""

check: health

# ============================================================================
# DESARROLLO
# ============================================================================

shell-odoo:
	@echo "$(GREEN)🐚 Entrando al shell de Odoo...$(NC)"
	docker exec -it $(ODOO_CONTAINER) odoo shell -d $(DB_NAME)

shell-postgres:
	@echo "$(GREEN)🐚 Entrando al shell de PostgreSQL...$(NC)"
	docker exec -it $(POSTGRES_CONTAINER) psql -U odoo -d $(DB_NAME)

shell-api:
	@echo "$(GREEN)🐚 Entrando al shell de Mock API...$(NC)"
	docker exec -it $(API_CONTAINER) /bin/bash

install-module:
	@echo "$(GREEN)📦 Instalando módulo product_sync...$(NC)"
	docker exec $(ODOO_CONTAINER) odoo -d $(DB_NAME) -i product_sync --stop-after-init
	@echo "$(GREEN)✅ Módulo instalado$(NC)"
	@make restart

update-module:
	@echo "$(GREEN)🔄 Actualizando módulo product_sync...$(NC)"
	docker exec $(ODOO_CONTAINER) odoo -d $(DB_NAME) -u product_sync --stop-after-init
	@echo "$(GREEN)✅ Módulo actualizado$(NC)"
	@make restart

# ============================================================================
# TESTING
# ============================================================================

test:
	@echo "$(GREEN)🧪 Ejecutando todas las pruebas...$(NC)"
	@make test-unit
	@make test-integration

test-unit:
	@echo "$(GREEN)🧪 Ejecutando pruebas unitarias...$(NC)"
	docker exec $(ODOO_CONTAINER) pytest /mnt/extra-addons/product_sync/tests/test_unit.py -v

test-integration:
	@echo "$(GREEN)🧪 Ejecutando pruebas de integración...$(NC)"
	docker exec $(ODOO_CONTAINER) pytest /mnt/extra-addons/product_sync/tests/test_integration.py -v

test-sync:
	@echo "$(GREEN)🔄 Probando sincronización...$(NC)"
	@echo "env['product.sync.service'].sync_products(limit=5)" | \
		docker exec -i $(ODOO_CONTAINER) odoo shell -d $(DB_NAME)

# ============================================================================
# DATOS Y SINCRONIZACIÓN
# ============================================================================

demo:
	@echo "$(GREEN)📊 Cargando datos de demostración...$(NC)"
	@curl -s http://localhost:$(API_PORT)/products | jq '.items[] | {id, name, sku, list_price}'
	@echo ""
	@echo "$(GREEN)✅ Datos disponibles en Mock API$(NC)"

sync:
	@echo "$(GREEN)🔄 Ejecutando sincronización completa...$(NC)"
	@echo "result = env['product.sync.service'].sync_products(); print(result)" | \
		docker exec -i $(ODOO_CONTAINER) odoo shell -d $(DB_NAME)

sync-dry-run:
	@echo "$(YELLOW)🔄 Simulando sincronización (dry run)...$(NC)"
	@echo "result = env['product.sync.service'].sync_products(dry_run=True, limit=5); print(result)" | \
		docker exec -i $(ODOO_CONTAINER) odoo shell -d $(DB_NAME)

reset-data:
	@echo "$(RED)🧹 Limpiando datos de sincronización...$(NC)"
	@echo "$(RED)⚠️  Esto eliminará productos sincronizados y logs$(NC)"
	@read -p "¿Continuar? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "env['product.template'].search([('is_from_external', '=', True)]).unlink(); env['product.sync.log'].search([]).unlink(); env.cr.commit()" | \
		docker exec -i $(ODOO_CONTAINER) odoo shell -d $(DB_NAME); \
		echo "$(GREEN)✅ Datos limpiados$(NC)"; \
	fi

# ============================================================================
# UTILIDADES
# ============================================================================

api-test:
	@echo "$(GREEN)🧪 Probando Mock API...$(NC)"
	@echo ""
	@echo "$(YELLOW)GET /health:$(NC)"
	@curl -s http://localhost:$(API_PORT)/health | jq
	@echo ""
	@echo "$(YELLOW)GET /products (primeros 3):$(NC)"
	@curl -s "http://localhost:$(API_PORT)/products?limit=3" | jq '.items[0:3] | .[] | {id, name, sku, list_price}'
	@echo ""

backup-db:
	@echo "$(GREEN)💾 Creando backup de base de datos...$(NC)"
	@mkdir -p ./backups
	docker exec $(POSTGRES_CONTAINER) pg_dump -U odoo $(DB_NAME) > ./backups/$(DB_NAME)_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup creado en ./backups/$(NC)"

restore-db:
	@echo "$(YELLOW)📥 Restaurar base de datos...$(NC)"
	@ls -1 ./backups/*.sql 2>/dev/null || (echo "$(RED)No hay backups disponibles$(NC)" && exit 1)
	@echo "Backups disponibles:"
	@ls -1 ./backups/*.sql
	@read -p "Ingrese nombre del archivo: " file; \
	docker exec -i $(POSTGRES_CONTAINER) psql -U odoo -d $(DB_NAME) < ./backups/$$file
	@echo "$(GREEN)✅ Base de datos restaurada$(NC)"

ps: status

stop: down

start: up

.DEFAULT_GOAL := help