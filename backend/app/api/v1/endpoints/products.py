from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import category as category_crud
from app.crud import product as product_crud
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

require_writer = require_roles("admin", "manager")


@router.get("", response_model=list[ProductRead])
def list_products(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
) -> list[ProductRead]:
    return product_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        is_active=is_active,
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> ProductRead:
    if product_crud.get_by_sku(db, payload.sku):
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    if payload.barcode and product_crud.get_by_barcode(db, payload.barcode):
        raise HTTPException(status.HTTP_409_CONFLICT, "Barcode already exists")
    if payload.category_id is not None and not category_crud.get(db, payload.category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")
    return product_crud.create(db, payload)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: DbDep,
    _: CurrentUser,
) -> ProductRead:
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> ProductRead:
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if payload.sku and payload.sku != product.sku:
        existing = product_crud.get_by_sku(db, payload.sku)
        if existing and existing.id != product.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    if payload.barcode and payload.barcode != product.barcode:
        existing = product_crud.get_by_barcode(db, payload.barcode)
        if existing and existing.id != product.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Barcode already exists")
    if payload.category_id is not None and not category_crud.get(db, payload.category_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category does not exist")
    return product_crud.update(db, product, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> None:
    product = product_crud.get(db, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product_crud.delete(db, product)
