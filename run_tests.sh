#!/bin/bash

echo "🧪 ===== PRODUCT SYNC - TEST SUITE ====="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
DB_NAME="sync"
ODOO_CONTAINER="odoo17_app"

echo "${YELLOW}📋 Preparando entorno de tests...${NC}"

# 1. Tests unitarios (API Client y Rate Limiter)
echo ""
echo "${YELLOW}===============================================${NC}"
echo "${YELLOW}  1️⃣  TESTS UNITARIOS (sin Odoo)${NC}"
echo "${YELLOW}===============================================${NC}"

# Test de API Client
echo ""
echo "${GREEN}▶ Testing API Client...${NC}"
docker exec $ODOO_CONTAINER python3 -m pytest \
    /mnt/extra-addons/product_sync/tests/test_api_client.py \
    -v --tb=short

API_CLIENT_EXIT=$?

# Test de Rate Limiter
echo ""
echo "${GREEN}▶ Testing Rate Limiter...${NC}"
docker exec $ODOO_CONTAINER python3 -m pytest \
    /mnt/extra-addons/product_sync/tests/test_rate_limiter.py \
    -v --tb=short

RATE_LIMITER_EXIT=$?

# 2. Tests de integración (con Odoo)
echo ""
echo "${YELLOW}===============================================${NC}"
echo "${YELLOW}  2️⃣  TESTS DE INTEGRACIÓN (con Odoo)${NC}"
echo "${YELLOW}===============================================${NC}"

echo ""
echo "${GREEN}▶ Testing Product Sync Models & Services...${NC}"
docker exec $ODOO_CONTAINER odoo -d $DB_NAME \
    --test-enable \
    --test-tags=product_sync \
    --stop-after-init \
    --log-level=test

INTEGRATION_EXIT=$?

# 3. Test de sincronización real (end-to-end)
echo ""
echo "${YELLOW}===============================================${NC}"
echo "${YELLOW}  3️⃣  TEST END-TO-END (API Mock)${NC}"
echo "${YELLOW}===============================================${NC}"

echo ""
echo "${GREEN}▶ Testing full synchronization flow...${NC}"

# Verificar que Mock API está corriendo
echo "  Checking Mock API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ${GREEN}✓${NC} Mock API is running"
else
    echo "  ${RED}✗${NC} Mock API is NOT running"
    echo "  Starting Mock API..."
    docker-compose up -d mock-api
    sleep 3
fi

# Ejecutar sincronización de prueba
echo ""
echo "  Running sync test..."
docker exec $ODOO_CONTAINER odoo shell -d $DB_NAME <<EOF
try:
    # Limpiar datos de prueba
    env['product.template'].search([('is_from_external', '=', True)]).unlink()
    env['product.sync.log'].search([]).unlink()
    env.cr.commit()
    
    # Ejecutar sincronización
    result = env['product.sync.service'].sync_products()
    
    # Verificar resultados
    assert result['total'] > 0, "No products fetched"
    assert result['errors'] == 0, f"Errors found: {result['errors']}"
    
    # Verificar productos creados
    products = env['product.template'].search([('is_from_external', '=', True)])
    assert len(products) > 0, "No products created"
    
    print("\\n${GREEN}✓ End-to-end test PASSED${NC}")
    print(f"  Products synced: {len(products)}")
    print(f"  Created: {result.get('create', 0)}")
    print(f"  Updated: {result.get('update', 0)}")
    print(f"  Skipped: {result.get('skip', 0)}")
    print(f"  Errors: {result['errors']}")
    
except Exception as e:
    print(f"\\n${RED}✗ End-to-end test FAILED${NC}")
    print(f"  Error: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

exit(0)
EOF

E2E_EXIT=$?

# 4. Test de idempotencia
echo ""
echo "${YELLOW}===============================================${NC}"
echo "${YELLOW}  4️⃣  TEST DE IDEMPOTENCIA${NC}"
echo "${YELLOW}===============================================${NC}"

echo ""
echo "${GREEN}▶ Testing idempotency (run sync twice)...${NC}"

docker exec $ODOO_CONTAINER odoo shell -d $DB_NAME <<EOF
try:
    # Primera sincronización
    result1 = env['product.sync.service'].sync_products()
    
    # Segunda sincronización (debe ser idempotente)
    result2 = env['product.sync.service'].sync_products()
    
    # Verificar idempotencia
    created_second = result2.get('create', 0) + result2.get('created', 0)
    skipped_second = result2.get('skip', 0) + result2.get('skipped', 0)
    
    assert created_second == 0, f"Created products in 2nd run: {created_second}"
    assert skipped_second > 0, "No products skipped in 2nd run"
    
    # Verificar que no hay duplicados
    products = env['product.template'].search([('is_from_external', '=', True)])
    skus = products.mapped('external_sku')
    unique_skus = set(skus)
    
    assert len(skus) == len(unique_skus), "Duplicate products found!"
    
    print("\\n${GREEN}✓ Idempotency test PASSED${NC}")
    print(f"  1st run - Created: {result1.get('create', 0)}")
    print(f"  2nd run - Created: {created_second}")
    print(f"  2nd run - Skipped: {skipped_second}")
    print(f"  Total unique products: {len(products)}")
    
except Exception as e:
    print(f"\\n${RED}✗ Idempotency test FAILED${NC}")
    print(f"  Error: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

exit(0)
EOF

IDEMPOTENCY_EXIT=$?

# =============================================================================
# RESUMEN DE RESULTADOS
# =============================================================================

echo ""
echo "${YELLOW}===============================================${NC}"
echo "${YELLOW}  📊 RESUMEN DE TESTS${NC}"
echo "${YELLOW}===============================================${NC}"
echo ""

TOTAL_TESTS=5
PASSED=0
FAILED=0

# Función para mostrar resultado
print_result() {
    TEST_NAME=$1
    EXIT_CODE=$2
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "  ${GREEN}✓${NC} $TEST_NAME"
        ((PASSED++))
    else
        echo "  ${RED}✗${NC} $TEST_NAME"
        ((FAILED++))
    fi
}

print_result "API Client Tests" $API_CLIENT_EXIT
print_result "Rate Limiter Tests" $RATE_LIMITER_EXIT
print_result "Integration Tests" $INTEGRATION_EXIT
print_result "End-to-End Test" $E2E_EXIT
print_result "Idempotency Test" $IDEMPOTENCY_EXIT

echo ""
echo "${YELLOW}-----------------------------------------------${NC}"
echo "  Total: $TOTAL_TESTS tests"
echo "  ${GREEN}Passed: $PASSED${NC}"
echo "  ${RED}Failed: $FAILED${NC}"
echo "${YELLOW}-----------------------------------------------${NC}"

# Código de salida
if [ $FAILED -eq 0 ]; then
    echo ""
    echo "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo ""
    exit 0
else
    echo ""
    echo "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
