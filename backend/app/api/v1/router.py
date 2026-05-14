from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    customers,
    dashboard,
    health,
    inventory,
    products,
    purchase_orders,
    roles,
    sales_orders,
    stock_adjustments,
    suppliers,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(suppliers.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(customers.router)
api_router.include_router(sales_orders.router)
api_router.include_router(inventory.router)
api_router.include_router(stock_adjustments.router)
api_router.include_router(dashboard.router)
