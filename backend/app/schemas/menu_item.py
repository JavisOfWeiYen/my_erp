from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MenuItemBase(BaseModel):
    """Either label_key or custom_label must be supplied. label_key is used by
    built-in items (mapped to i18n); custom_label overrides for admin entries."""
    parent_id: int | None = None
    label_key: str | None = Field(default=None, max_length=64)
    custom_label: str | None = Field(default=None, max_length=64)
    icon_name: str | None = Field(default=None, max_length=64)
    route_path: str | None = Field(default=None, max_length=128)
    required_roles: str | None = Field(default=None, max_length=128)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def _at_least_one_label(self):
        if not self.label_key and not self.custom_label:
            raise ValueError("label_key or custom_label must be provided")
        return self


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    parent_id: int | None = None
    label_key: str | None = Field(default=None, max_length=64)
    custom_label: str | None = Field(default=None, max_length=64)
    icon_name: str | None = Field(default=None, max_length=64)
    route_path: str | None = Field(default=None, max_length=128)
    required_roles: str | None = Field(default=None, max_length=128)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parent_id: int | None
    label_key: str | None
    custom_label: str | None
    icon_name: str | None
    route_path: str | None
    required_roles: str | None
    display_order: int
    is_active: bool
    children: list["MenuItemRead"] = Field(default_factory=list)


class ReorderEntry(BaseModel):
    id: int
    parent_id: int | None = None
    display_order: int = Field(ge=0)
