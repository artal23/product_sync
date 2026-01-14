# 🔄 Odoo Product Sync Integration

[![Odoo](https://img.shields.io/badge/Odoo-17.0-714B67?style=flat&logo=odoo)](https://www.odoo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)

Integración backend robusta entre Odoo 17 y sistemas externos para sincronización bidireccional de productos. Implementa buenas prácticas de backend, idempotencia, reintentos con backoff exponencial, rate limiting y testing automatizado.

---

## 📋 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Arquitectura](#-arquitectura)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Ejecución](#-ejecución)
- [Testing](#-testing)
- [API Endpoints](#-api-endpoints)
- [Casos de Uso](#-casos-de-uso)
- [Troubleshooting](#-troubleshooting)
- [Documentación Técnica](#-documentación-técnica)

---

## ✨ Características Principales

### 🎯 Funcionalidades Core

- **Sincronización Bidireccional**: Integración completa entre Odoo y API externa
- **Idempotencia Garantizada**: Evita duplicados mediante external_id y SKU único
- **Reintentos Inteligentes**: Backoff exponencial con hasta 5 reintentos automáticos
- **Rate Limiting**: Control de tasa con algoritmo Token Bucket (10 req/s configurable)
- **Logs Estructurados**: Trazabilidad completa de cada operación
- **Testing Automatizado**: Cobertura de pruebas unitarias e integración
- **Health Checks**: Monitoreo automático de servicios
- **Docker Compose**: Entorno completamente reproducible

### 🔧 Características Técnicas

| Característica | Descripción |
|----------------|-------------|
| **ORM** | Odoo ORM con modelos extendidos |
| **API Client** | Cliente HTTP robusto con session pooling |
| **Validaciones** | Constraints SQL + validaciones Python |
| **Reconciliación** | Búsqueda por external_id y SKU |
| **Normalización** | Limpieza y validación de datos externos |
| **Cron Jobs** | Sincronización automática cada 15 minutos |
| **UI/UX** | Vistas tree, form, search con filtros avanzados |

---

## 🏗️ Arquitectura

### Diagrama de Componentes
```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER NETWORK                           │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐ │
│  │              │      │              │      │          │ │
│  │   Odoo 17    │◄────►│  PostgreSQL  │      │ Mock API │ │
│  │   :8069      │      │    :5432     │      │  :8000   │ │
│  │              │      │              │      │          │ │
│  └──────┬───────┘      └──────────────┘      └────┬─────┘ │
│         │                                          │       │
│         │   ┌─────────────────────────┐           │       │
│         └──►│  product_sync module    │◄──────────┘       │
│             │                         │                   │
│             │  - Models               │                   │
│             │  - Services             │                   │
│             │  - API Client           │                   │
│             │  - Rate Limiter         │                   │
│             │  - Sync Logs            │                   │
│             └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Sincronización
```
1. CRON Job / Manual Trigger
         ↓
2. ProductSyncService.sync_products()
         ↓
3. APIClient.get('/products') → Rate Limiter
         ↓
4. Para cada producto:
   ├─ Búsqueda por external_id (idempotencia)
   ├─ Si existe: Comparar y actualizar (skip si sin cambios)
   └─ Si no existe: Crear nuevo
         ↓
5. Registrar en ProductSyncLog
         ↓
6. Commit transaccional
         ↓
7. Retornar estadísticas
```

### Entidades Sincronizadas

| Entidad | Modelo Odoo | Campos Clave | Operaciones |
|---------|-------------|--------------|-------------|
| **Productos** | `product.template` | name, sku, external_id, list_price, standard_price, barcode, category | CREATE, UPDATE, SKIP |
| **Logs** | `product.sync.log` | operation, status, external_id, execution_time | CREATE (auto) |

---

## 📦 Requisitos Previos

### Software Necesario

- **Docker** >= 20.10.0
- **Docker Compose** >= 2.0.0
- **Make** (opcional pero recomendado)
- **curl** / **jq** (para testing manual)
- **Git**

### Verificar Instalación
```bash
# Verificar Docker
docker --version
# Esperado: Docker version 20.10.0+

# Verificar Docker Compose
docker-compose --version
# Esperado: Docker Compose version 2.0.0+

# Verificar Make (opcional)
make --version
# Esperado: GNU Make 4.x
```

### Recursos del Sistema

| Componente | CPU | RAM | Disco |
|------------|-----|-----|-------|
| **Odoo** | 2 cores | 2GB | 2GB |
| **PostgreSQL** | 1 core | 512MB | 5GB |
| **Mock API** | 1 core | 256MB | 100MB |
| **Total Recomendado** | 4 cores | 3GB | 10GB |

---

## 🚀 Instalación

### Opción 1: Instalación Rápida con Make (Recomendada)
```bash
# 1. Clonar el repositorio
git clone git@github.com:artal23/product_sync.git
cd odoo-product-sync

# 2. Setup completo automatizado
make setup

# Esto ejecutará:
# - docker-compose build (construir imágenes)
# - docker-compose up -d (levantar servicios)
# - health checks automáticos
```

### Opción 2: Instalación Manual
```bash
# 1. Clonar el repositorio
git clone git@github.com:artal23/product_sync.git
cd odoo-product-sync

# 2. Construir imágenes Docker
docker-compose build

# 3. Levantar servicios
docker-compose up -d

# 4. Verificar que todo esté corriendo
docker-compose ps
```

### Verificar Instalación
```bash
# Con Make
make health

# Sin Make
curl http://localhost:8069/web/health  # Odoo
curl http://localhost:8000/health       # Mock API
docker exec odoo17_postgres pg_isready -U odoo  # PostgreSQL
```

**Salida esperada:**
```
✅ PostgreSQL: OK
✅ Mock API: OK
✅ Odoo: OK
```

---

## ⚙️ Configuración

### 1. Crear Base de Datos en Odoo
```bash
# Acceder a Odoo
http://localhost:8069

# En la interfaz web:
# 1. Click en "Create Database"
# 2. Master Password: admin
# 3. Database Name: odoo_sync_test
# 4. Email: admin@example.com
# 5. Password: admin
# 6. Language: Spanish(PE)
# 7. Country: Perú (o tu país)
# 8. Click "Create Database"
```

### 2. Instalar el Módulo product_sync

#### Opción A: Con Make
```bash
make install-module
```

#### Opción B: Desde UI de Odoo
```bash
# 1. Activar Modo Desarrollador
Settings > Developer Tools > Activate Developer Mode

# 2. Actualizar Lista de Apps
Apps > Update Apps List

# 3. Buscar e Instalar
Apps > Search "Product Synchronization" > Install
```

#### Opción C: Desde línea de comandos
```bash
docker exec odoo17_app odoo -d odoo_sync_test -i product_sync --stop-after-init
docker-compose restart odoo
```

### 3. Verificar Parámetros de Configuración
```bash
# En Odoo UI:
Settings > Technical > System Parameters

# Verificar que existan:
product_sync.api_base_url = http://mock-api:8000
product_sync.api_timeout = 30
product_sync.api_max_retries = 5
product_sync.rate_limit = 10
```

### 4. (Opcional) Activar Cron Job
```bash
# En Odoo UI:
Settings > Technical > Automation > Scheduled Actions

# Buscar: "Product Sync: Automatic Synchronization"
# Click en el registro
# Marcar "Active"
# Guardar
```

---

## 🎮 Ejecución

### Comandos Principales

#### Ver Todos los Comandos Disponibles
```bash
make help
```

#### Gestión de Servicios
```bash
# Levantar servicios
make up

# Detener servicios
make down

# Reiniciar servicios
make restart

# Ver estado
make status

# Ver logs en tiempo real
make logs

# Ver logs específicos
make logs-odoo    # Solo Odoo
make logs-api     # Solo Mock API
```

#### Sincronización de Productos
```bash
# Ver productos disponibles en API externa
make demo

# Sincronización completa
make sync

# Simulación (dry run - no escribe en BD)
make sync-dry-run

# Probar sincronización con límite
make test-sync
```

#### Desarrollo y Debug
```bash
# Entrar al shell de Odoo (Python)
make shell-odoo

# Dentro del shell:
>>> sync_service = env['product.sync.service']
>>> result = sync_service.test_connection()
>>> print(result)

# Entrar al shell de PostgreSQL
make shell-postgres

# Ver productos sincronizados
SELECT id, name, external_id, external_sku, sync_status 
FROM product_template 
WHERE is_from_external = true;
```

### Workflows Comunes

#### Workflow 1: Primera Sincronización
```bash
# 1. Verificar que todo esté funcionando
make health

# 2. Ver productos disponibles en API
make demo

# 3. Ejecutar sincronización de prueba (dry run)
make sync-dry-run

# 4. Sincronización real
make sync

# 5. Verificar en Odoo UI
# Ir a: Product Sync > Products > Synchronized Products
```

#### Workflow 2: Desarrollo y Testing
```bash
# 1. Hacer cambios en el código
vim addons/product_sync/services/sync_service.py

# 2. Actualizar el módulo
make update-module

# 3. Ejecutar pruebas
make test

# 4. Ver logs
make logs-odoo

# 5. Probar sincronización
make test-sync
```

#### Workflow 3: Troubleshooting
```bash
# 1. Ver estado de servicios
make status

# 2. Verificar salud
make health

# 3. Ver logs de errores
make logs | grep ERROR

# 4. Entrar al shell para debug
make shell-odoo

# 5. Limpiar y reiniciar
make clean
make setup
```

---

## 🧪 Testing

### Ejecutar Todas las Pruebas
```bash
# Con Make
make test

# Sin Make
docker exec odoo17_app pytest /mnt/extra-addons/product_sync/tests/ -v
```

### Pruebas Unitarias
```bash
# Con Make
make test-unit

# Sin Make
docker exec odoo17_app pytest /mnt/extra-addons/product_sync/tests/test_unit.py -v
```

**Cobertura:**
- ✅ Validaciones de modelos
- ✅ Constraints SQL
- ✅ Métodos de búsqueda
- ✅ Rate Limiter
- ✅ API Client (reintentos, backoff)

### Pruebas de Integración
```bash
# Con Make
make test-integration

# Sin Make
docker exec odoo17_app pytest /mnt/extra-addons/product_sync/tests/test_integration.py -v
```

**Cobertura:**
- ✅ Sincronización end-to-end
- ✅ Idempotencia (sin duplicados)
- ✅ Manejo de errores de API
- ✅ Reconciliación de datos
- ✅ Logging estructurado

### Test de API Externa
```bash
# Con Make
make api-test

# Sin Make
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/products | jq '.items[0:3]'
```

### Pruebas Manuales desde Odoo Shell
```bash
make shell-odoo
```
```python
# Dentro del shell de Odoo:

# 1. Test de conexión
sync_service = env['product.sync.service']
result = sync_service.test_connection()
print(result)

# 2. Sincronización con límite
result = sync_service.sync_products(limit=3)
print(result)

# 3. Verificar logs
logs = env['product.sync.log'].search([], limit=5, order='create_date desc')
for log in logs:
    print(f"{log.operation} - {log.status} - {log.message}")

# 4. Estadísticas
stats = env['product.template'].get_sync_statistics()
print(stats)
```

---

## 🌐 API Endpoints

### Mock API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check de la API |
| GET | `/products` | Listar productos (con paginación) |
| GET | `/products/{id}` | Obtener producto específico |
| POST | `/products` | Crear nuevo producto |
| PATCH | `/products/{id}` | Actualizar producto |
| DELETE | `/products/{id}` | Eliminar producto (soft delete) |
| GET | `/categories` | Listar categorías |
| GET | `/docs` | Documentación Swagger |

### Ejemplos de Uso
```bash
# Health Check
curl http://localhost:8000/health

# Listar productos
curl http://localhost:8000/products | jq

# Obtener producto específico
curl http://localhost:8000/products/1 | jq

# Listar con filtros
curl "http://localhost:8000/products?category=Electronics&limit=5" | jq

# Simular actualización de precios (testing)
curl http://localhost:8000/simulate/price-update | jq
```

### Documentación Interactiva

Acceder a la documentación Swagger:
```
http://localhost:8000/docs
```

---

## 💼 Casos de Uso

### Caso 1: Sincronización Inicial de Catálogo

**Escenario:** Primera carga de 100+ productos desde proveedor externo
```bash
# 1. Verificar productos disponibles
make demo

# 2. Ejecutar sincronización completa
make sync

# 3. Verificar resultados en UI
# Ir a: Product Sync > Synchronization > Sync Logs
```

**Resultado esperado:**
```json
{
  "total": 10,
  "created": 10,
  "updated": 0,
  "skipped": 0,
  "errors": 0,
  "execution_time": 12.45
}
```

### Caso 2: Actualización de Precios

**Escenario:** El proveedor cambia precios de productos
```bash
# 1. Simular cambio de precios en API externa
curl http://localhost:8000/simulate/price-update

# 2. Ejecutar sincronización
make sync

# 3. Verificar productos actualizados
# Los productos con cambios mostrarán operation='update'
# Los productos sin cambios mostrarán operation='skip'
```

### Caso 3: Recuperación de Errores

**Escenario:** La API externa estuvo caída y hay productos pendientes
```bash
# 1. Ver errores recientes
make shell-odoo

>>> logs = env['product.sync.log'].search([('status', '=', 'error')], limit=10)
>>> for log in logs:
...     print(f"{log.external_id}: {log.error_details}")

# 2. Reintentar sincronización
>>> sync_service = env['product.sync.service']
>>> result = sync_service.sync_products()
```

### Caso 4: Sincronización Automática (Cron)

**Escenario:** Mantener catálogo actualizado cada 15 minutos
```bash
# 1. Activar Cron Job en Odoo UI
Settings > Technical > Scheduled Actions
Buscar: "Product Sync: Automatic Synchronization"
Activar: ✅

# 2. Verificar logs automáticos
# Los logs tendrán is_automatic=True
```

---

## 🔍 Troubleshooting

### Problema 1: Servicios no levantan

**Síntomas:**
```bash
make up
# Error: port 8069 is already in use
```

**Solución:**
```bash
# Ver qué está usando el puerto
lsof -i :8069

# Detener servicio conflictivo o cambiar puerto en docker-compose.yml
ports:
  - "8070:8069"  # Cambiar puerto externo
```

### Problema 2: Error "No module named 'requests'"

**Síntomas:**
```bash
ModuleNotFoundError: No module named 'requests'
```

**Solución:**
```bash
# Reconstruir imagen con Dockerfile.odoo
make down
make build --no-cache
make up
```

### Problema 3: Productos duplicados

**Síntomas:**
```bash
ERROR: duplicate key value violates unique constraint "external_id_unique"
```

**Solución:**
```bash
# Limpiar datos y resincronizar
make reset-data
make sync
```

### Problema 4: API externa no responde

**Síntomas:**
```bash
APIClientError: Request failed after 5 attempts
```

**Solución:**
```bash
# 1. Verificar que Mock API esté corriendo
make health

# 2. Ver logs de Mock API
make logs-api

# 3. Reiniciar Mock API
docker-compose restart mock-api
```

### Problema 5: Base de datos corrupta

**Síntomas:**
```bash
psycopg2.OperationalError: could not connect to server
```

**Solución:**
```bash
# Opción 1: Reiniciar PostgreSQL
docker-compose restart postgres

# Opción 2: Recrear desde cero
make clean
make setup
```

---

## 📚 Documentación Técnica

### Estructura del Proyecto
```
odoo-product-sync/
├── addons/
│   └── product_sync/              # Módulo principal
│       ├── __init__.py
│       ├── __manifest__.py        # Manifest del módulo
│       ├── models/
│       │   ├── __init__.py
│       │   ├── product_sync.py    # Extensión de product.template
│       │   └── sync_log.py        # Modelo de logs
│       ├── services/
│       │   ├── __init__.py
│       │   ├── api_client.py      # Cliente HTTP con reintentos
│       │   ├── rate_limiter.py    # Rate limiting (Token Bucket)
│       │   └── sync_service.py    # Lógica de sincronización
│       ├── views/
│       │   ├── product_views.xml  # Vistas de productos
│       │   ├── sync_log_views.xml # Vistas de logs
│       │   └── menu_views.xml     # Menús
│       ├── data/
│       │   ├── ir_cron.xml        # Cron jobs
│       │   └── sync_config.xml    # Parámetros
│       ├── security/
│       │   └── ir.model.access.csv # Permisos
│       └── tests/
│           ├── __init__.py
│           ├── test_unit.py       # Pruebas unitarias
│           └── test_integration.py # Pruebas de integración
├── mock_api/
│   ├── Dockerfile
│   ├── main.py                    # FastAPI mock server
│   └── requirements.txt
├── config/
│   ├── odoo.conf                  # Configuración de Odoo
│   └── requirements.txt           # Dependencias Python
├── Dockerfile.odoo                # Imagen personalizada
├── docker-compose.yml             # Orquestación
├── Makefile                       # Comandos automatizados
└── README.md                      # Este archivo
```

### Modelos de Datos

#### product.template (extendido)
```python
# Campos agregados:
external_id: Char             # ID en sistema externo (unique)
external_sku: Char            # SKU externo (unique)
last_sync_date: Datetime      # Última sincronización
sync_status: Selection        # pending|synced|error|manual
sync_error_message: Text      # Último error
is_from_external: Boolean     # Origen externo
sync_log_ids: One2many        # Relación con logs
```

#### product.sync.log
```python
operation: Selection          # create|update|skip|delete|error
status: Selection             # success|error|warning
product_id: Many2one          # Producto relacionado
external_id: Char             # ID externo
external_sku: Char            # SKU externo
message: Text                 # Mensaje descriptivo
error_details: Text           # Detalles técnicos
request_data: Text            # JSON request
response_data: Text           # JSON response
sync_batch_id: Char           # ID del lote
execution_time: Float         # Tiempo de ejecución (s)
retry_count: Integer          # Número de reintentos
is_automatic: Boolean         # Automático vs manual
```

### Parámetros de Configuración

| Parámetro | Valor Default | Descripción |
|-----------|---------------|-------------|
| `product_sync.api_base_url` | `http://mock-api:8000` | URL de la API externa |
| `product_sync.api_timeout` | `30` | Timeout en segundos |
| `product_sync.api_max_retries` | `5` | Reintentos máximos |
| `product_sync.rate_limit` | `10` | Peticiones por segundo |
| `product_sync.auto_sync_enabled` | `True` | Sincronización automática |
| `product_sync.sync_interval` | `15` | Intervalo en minutos |

### Algoritmos Implementados

#### 1. Backoff Exponencial
```python
# Tiempo de espera = 2^(intento-1) segundos
# Intento 1: 1s
# Intento 2: 2s
# Intento 3: 4s
# Intento 4: 8s
# Intento 5: 16s
# Máximo: 60s
```

#### 2. Token Bucket (Rate Limiting)
```python
# Capacidad: rate peticiones
# Refill: rate tokens por segundo
# Consumo: 1 token por petición
# Espera si no hay tokens disponibles
```

#### 3. Idempotencia
```python
# 1. Buscar por external_id
# 2. Si no existe, buscar por SKU
# 3. Si existe: comparar valores → UPDATE o SKIP
# 4. Si no existe: CREATE
```

---

## 👥 Equipo y Soporte

### Autor
**Arturo Jara**  
Especialista en Odoo, Python, Integraciones

### Contacto
- GitHub: [@tu-usuario](https://github.com/artal23)
- Email: artal23jara@gmail.com

---

## 📄 Licencia

Este proyecto está bajo la Licencia LGPL-3. Ver archivo `LICENSE` para más detalles.

---
<div align="center">
  <sub>Built with ❤️ using Odoo 17, Python, FastAPI and Docker</sub>
</div>
