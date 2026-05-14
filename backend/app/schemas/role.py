from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
