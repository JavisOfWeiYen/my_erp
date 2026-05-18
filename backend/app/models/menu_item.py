from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MenuItem(Base):
    """Sidebar navigation entry — either a group (no route_path) or a leaf
    (route_path set). Self-referential tree via parent_id."""

    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Built-in items reference an i18n key (e.g. "nav.products"); admin-added items
    # supply a free-text custom_label. At least one must be set (enforced at schema).
    label_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    custom_label: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # MUI icon component name without the "Icon" suffix, e.g. "Inventory2" or "Storefront".
    icon_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Frontend route, e.g. "/products". Null for group/folder nodes.
    route_path: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Comma-separated role names. Null/empty = visible to all authenticated users.
    required_roles: Mapped[str | None] = mapped_column(String(128), nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parent: Mapped["MenuItem | None"] = relationship(
        back_populates="children", remote_side="MenuItem.id"
    )
    children: Mapped[list["MenuItem"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
