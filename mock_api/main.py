
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uvicorn
import random

app = FastAPI(
    title="Mock Product API",
    description="API externa simulada para sincronización con Odoo",
    version="1.0.0"
)

class Product(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., description="Código único del producto")
    description: Optional[str] = None
    list_price: float = Field(..., gt=0, description="Precio de venta")
    standard_price: Optional[float] = Field(None, description="Costo del producto")
    barcode: Optional[str] = None
    category: str = "General"
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Laptop Dell XPS 13",
                "sku": "DELL-XPS13-001",
                "description": "Laptop ultraportátil de alto rendimiento",
                "list_price": 1299.99,
                "standard_price": 950.00,
                "barcode": "7501234567890",
                "category": "Electronics",
                "active": True
            }
        }

# Base de datos en memoria (simulada)
PRODUCTS_DB = [
    {
        "id": 1,
        "name": "Laptop Dell XPS 13",
        "sku": "DELL-XPS13-001",
        "description": "Laptop ultraportátil 13\" con procesador Intel Core i7",
        "list_price": 1299.99,
        "standard_price": 950.00,
        "barcode": "7501234567890",
        "category": "Electronics",
        "active": True,
        "created_at": "2026-01-01T10:00:00",
        "updated_at": "2026-01-01T10:00:00"
    },
    {
        "id": 2,
        "name": "Mouse Logitech MX Master 3",
        "sku": "LOG-MX3-002",
        "description": "Mouse inalámbrico ergonómico de precisión",
        "list_price": 99.99,
        "standard_price": 65.00,
        "barcode": "7501234567891",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-02T11:00:00",
        "updated_at": "2026-01-02T11:00:00"
    },
    {
        "id": 3,
        "name": "Teclado Mecánico Keychron K2",
        "sku": "KEY-K2-003",
        "description": "Teclado mecánico 75% con switches Gateron",
        "list_price": 89.99,
        "standard_price": 55.00,
        "barcode": "7501234567892",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-03T12:00:00",
        "updated_at": "2026-01-03T12:00:00"
    },
    {
        "id": 4,
        "name": "Monitor LG UltraWide 34\"",
        "sku": "LG-UW34-004",
        "description": "Monitor UltraWide QHD 34 pulgadas",
        "list_price": 549.99,
        "standard_price": 380.00,
        "barcode": "7501234567893",
        "category": "Electronics",
        "active": True,
        "created_at": "2026-01-04T13:00:00",
        "updated_at": "2026-01-04T13:00:00"
    },
    {
        "id": 5,
        "name": "Auriculares Sony WH-1000XM5",
        "sku": "SONY-WH5-005",
        "description": "Auriculares con cancelación de ruido activa",
        "list_price": 399.99,
        "standard_price": 280.00,
        "barcode": "7501234567894",
        "category": "Audio",
        "active": True,
        "created_at": "2026-01-05T14:00:00",
        "updated_at": "2026-01-05T14:00:00"
    },
    {
        "id": 6,
        "name": "Webcam Logitech C920",
        "sku": "LOG-C920-006",
        "description": "Webcam Full HD 1080p para streaming",
        "list_price": 79.99,
        "standard_price": 50.00,
        "barcode": "7501234567895",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-06T15:00:00",
        "updated_at": "2026-01-06T15:00:00"
    },
    {
        "id": 7,
        "name": "SSD Samsung 970 EVO 1TB",
        "sku": "SAM-970-007",
        "description": "SSD NVMe M.2 1TB de alta velocidad",
        "list_price": 149.99,
        "standard_price": 95.00,
        "barcode": "7501234567896",
        "category": "Storage",
        "active": True,
        "created_at": "2026-01-07T16:00:00",
        "updated_at": "2026-01-07T16:00:00"
    },
    {
        "id": 8,
        "name": "Hub USB-C Anker 7-en-1",
        "sku": "ANK-HUB-008",
        "description": "Hub multiconector USB-C con HDMI y SD",
        "list_price": 49.99,
        "standard_price": 28.00,
        "barcode": "7501234567897",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-08T17:00:00",
        "updated_at": "2026-01-08T17:00:00"
    },
    {
        "id": 9,
        "name": "Cable HDMI 2.1 Premium 2m",
        "sku": "CBL-HDMI-009",
        "description": "Cable HDMI 2.1 de alta velocidad 4K/120Hz",
        "list_price": 19.99,
        "standard_price": 8.00,
        "barcode": "7501234567898",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-09T18:00:00",
        "updated_at": "2026-01-09T18:00:00"
    },
    {
        "id": 10,
        "name": "Soporte Laptop Ergonómico",
        "sku": "SUP-LAP-010",
        "description": "Soporte ajustable de aluminio para laptop",
        "list_price": 34.99,
        "standard_price": 18.00,
        "barcode": "7501234567899",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-10T19:00:00",
        "updated_at": "2026-01-10T19:00:00"
    },
    {
        "id": 999,
        "name": "Producto Error",
        # ❌ sku ausente → provocará ValueError en Odoo
        "description": "Producto sin SKU",
        "list_price": 1500,
        "standard_price": 1200,
        "barcode": "7501234567890",
        "category": "Electronics",
        "active": True,
        "created_at": "2026-01-03T12:00:00",
        "updated_at": "2026-01-03T12:00:00"
    },
    {
        "id": 888,
        "name": "Producto Error 2",
        # ❌ sku ausente → provocará ValueError en Odoo
        "description": "Producto sin SKU 2",
        "list_price": 1600,
        "standard_price": 1300,
        "barcode": "8881234567890",
        "category": "Accessories",
        "active": True,
        "created_at": "2026-01-03T12:00:00",
        "updated_at": "2026-01-03T12:00:00"
    }
]

# Contador para nuevos IDs
next_id = len(PRODUCTS_DB) + 1

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "Mock Product API - Odoo Integration",
        "version": "1.0.0",
        "endpoints": {
            "products": "/products",
            "product_detail": "/products/{id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check para verificar que la API está funcionando"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "products_count": len(PRODUCTS_DB)
    }

@app.get("/products", response_model=List[Product])
async def list_products(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=100, description="Límite de registros"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    active: Optional[bool] = Query(None, description="Filtrar por estado activo")
):
    """
    Obtiene lista de productos con paginación y filtros
    
    Simula:
    - Paginación real
    - Filtros por categoría y estado
    - Respuesta similar a APIs de proveedores
    """
    products = PRODUCTS_DB.copy()
    
    # Aplicar filtros
    if category:
        products = [p for p in products if p.get("category") == category]
    
    if active is not None:
        products = [p for p in products if p.get("active") == active]
    
    # Aplicar paginación
    total = len(products)
    products = products[skip:skip + limit]
    
    return JSONResponse(
        content={
            "items": products,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )

@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """
    Obtiene un producto específico por ID
    
    Retorna 404 si no existe (simula comportamiento real)
    """
    product = next((p for p in PRODUCTS_DB if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    return product

@app.post("/products", response_model=Product, status_code=201)
async def create_product(product: Product):
    """
    Crea un nuevo producto
    
    Valida:
    - SKU único
    - Campos requeridos
    """
    global next_id
    
    # Validar SKU único
    if any(p["sku"] == product.sku for p in PRODUCTS_DB):
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un producto con SKU {product.sku}"
        )
    
    new_product = product.dict()
    new_product["id"] = next_id
    new_product["created_at"] = datetime.now().isoformat()
    new_product["updated_at"] = datetime.now().isoformat()
    
    PRODUCTS_DB.append(new_product)
    next_id += 1
    
    return new_product

@app.patch("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, updates: dict):
    """
    Actualiza un producto existente parcialmente
    
    Solo actualiza los campos enviados
    """
    product = next((p for p in PRODUCTS_DB if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    # Actualizar campos permitidos
    allowed_fields = ["name", "description", "list_price", "standard_price", 
                     "barcode", "category", "active"]
    
    for key, value in updates.items():
        if key in allowed_fields:
            product[key] = value
    
    product["updated_at"] = datetime.now().isoformat()
    
    return product

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int):
    """
    Elimina un producto (soft delete - marca como inactivo)
    """
    product = next((p for p in PRODUCTS_DB if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {product_id} no encontrado"
        )
    
    product["active"] = False
    product["updated_at"] = datetime.now().isoformat()
    
    return None

@app.get("/categories")
async def list_categories():
    """Retorna lista de categorías disponibles"""
    categories = list(set(p.get("category", "General") for p in PRODUCTS_DB))
    return {"categories": sorted(categories)}

@app.get("/simulate/price-update")
async def simulate_price_update():
    """
    Endpoint de prueba: simula actualización aleatoria de precios
    
    Útil para testing de sincronización
    """
    updated = []
    
    for product in random.sample(PRODUCTS_DB, min(3, len(PRODUCTS_DB))):
        old_price = product["list_price"]
        # Variación de +/- 10%
        variation = random.uniform(0.9, 1.1)
        product["list_price"] = round(old_price * variation, 2)
        product["updated_at"] = datetime.now().isoformat()
        
        updated.append({
            "id": product["id"],
            "sku": product["sku"],
            "old_price": old_price,
            "new_price": product["list_price"]
        })
    
    return {
        "message": "Precios actualizados aleatoriamente",
        "updated": updated
    }

@app.get("/simulate/rate-limit-test")
async def simulate_rate_limit():
    """
    Endpoint para testing de rate limiting
    
    Retorna timestamp para medir frecuencia de requests
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "message": "Use este endpoint para probar rate limiting"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
