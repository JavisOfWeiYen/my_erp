from fastapi import APIRouter

from app.core.deps import CurrentUser, DbDep
from app.crud import role as role_crud
from app.schemas.role import RoleRead

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
def list_roles(db: DbDep, _: CurrentUser) -> list[RoleRead]:
    return role_crud.list_all(db)
