from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate, ReorderEntry


def get(db: Session, item_id: int) -> MenuItem | None:
    return db.scalar(select(MenuItem).where(MenuItem.id == item_id))


def list_all(db: Session) -> list[MenuItem]:
    return list(
        db.scalars(
            select(MenuItem).order_by(MenuItem.parent_id.nulls_first(), MenuItem.display_order, MenuItem.id)
        )
    )


def _role_allows(required_csv: str | None, role_name: str) -> bool:
    if not required_csv:
        return True
    allowed = {r.strip() for r in required_csv.split(",") if r.strip()}
    return role_name in allowed


def _to_tree_dict(items: list[MenuItem]) -> list[dict]:
    """Build a nested-dict tree from a flat list. Caller passes the already-filtered
    list (e.g. only items visible to a specific role); we link parent/child here.

    Items whose parent was filtered out are promoted to top-level so a child page
    never becomes unreachable just because its parent is hidden."""
    by_id = {it.id: it for it in items}
    children_map: dict[int | None, list[MenuItem]] = {}
    for it in items:
        # If parent is missing from the filtered set, treat as top-level.
        effective_parent = it.parent_id if it.parent_id in by_id else None
        children_map.setdefault(effective_parent, []).append(it)

    def build(it: MenuItem) -> dict:
        return {
            "id": it.id,
            "parent_id": it.parent_id,
            "label_key": it.label_key,
            "custom_label": it.custom_label,
            "icon_name": it.icon_name,
            "route_path": it.route_path,
            "required_roles": it.required_roles,
            "display_order": it.display_order,
            "is_active": it.is_active,
            "children": [
                build(child)
                for child in sorted(
                    children_map.get(it.id, []),
                    key=lambda x: (x.display_order, x.id),
                )
            ],
        }

    roots = sorted(children_map.get(None, []), key=lambda x: (x.display_order, x.id))
    return [build(r) for r in roots]


def tree_for_role(db: Session, role_name: str) -> list[dict]:
    """Return the visible menu tree for the given role: active items the role can see.

    Groups whose children are all hidden are kept as long as they themselves match
    the role filter (so an empty group is allowed and the admin sees it shows up)."""
    items = list_all(db)
    visible = [it for it in items if it.is_active and _role_allows(it.required_roles, role_name)]
    return _to_tree_dict(visible)


def admin_tree(db: Session) -> list[dict]:
    """Full tree including inactive items, for admin management UI."""
    return _to_tree_dict(list_all(db))


def create(db: Session, data: MenuItemCreate) -> MenuItem:
    if data.parent_id is not None and get(db, data.parent_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id does not exist")
    item = MenuItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update(db: Session, item: MenuItem, data: MenuItemUpdate) -> MenuItem:
    payload = data.model_dump(exclude_unset=True)
    if "parent_id" in payload and payload["parent_id"] is not None:
        if payload["parent_id"] == item.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Item cannot be its own parent")
        if get(db, payload["parent_id"]) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id does not exist")
        if _is_descendant(db, item.id, payload["parent_id"]):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "parent_id is a descendant of this item (would create a cycle)",
            )
    for field, value in payload.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def _is_descendant(db: Session, ancestor_id: int, candidate_id: int) -> bool:
    """Walk up from candidate; if we hit ancestor_id, candidate is a descendant."""
    current = get(db, candidate_id)
    while current is not None and current.parent_id is not None:
        if current.parent_id == ancestor_id:
            return True
        current = get(db, current.parent_id)
    return False


def delete(db: Session, item: MenuItem) -> None:
    """Cascade deletes children via ORM relationship."""
    db.delete(item)
    db.commit()


def reorder(db: Session, entries: list[ReorderEntry]) -> None:
    """Bulk-update parent_id + display_order for one transaction.

    Validates: every id exists; no cycles introduced; parent_ids that the batch
    references must also exist after the update."""
    by_id = {it.id: it for it in list_all(db)}
    missing = [e.id for e in entries if e.id not in by_id]
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown menu item ids: {missing}")

    # Build proposed parent map (post-update) to check for cycles.
    proposed_parent: dict[int, int | None] = {e.id: e.parent_id for e in entries}
    for it in by_id.values():
        proposed_parent.setdefault(it.id, it.parent_id)
    for start_id in proposed_parent:
        seen = set()
        cur = start_id
        while proposed_parent.get(cur) is not None:
            if cur in seen:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reorder would create a cycle")
            seen.add(cur)
            cur = proposed_parent[cur]

    for e in entries:
        it = by_id[e.id]
        it.parent_id = e.parent_id
        it.display_order = e.display_order
    db.commit()
