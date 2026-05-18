"""Seed the default menu tree on first run. Idempotent: only populates when
menu_items is empty. Re-run safe but will not overwrite admin customisations.

Run via: python -m app.scripts.seed_menu
"""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.menu_item import MenuItem

# Groups + their child leaves. (label_key, icon, route_path, required_roles)
# Tree is built top-to-bottom; display_order = index within siblings.
DEFAULT_TREE = [
    # Home — top-level leaf, not in a group.
    {
        "label_key": "nav.home",
        "icon_name": "Home",
        "route_path": "/",
        "required_roles": None,
        "children": [],
    },
    {
        "label_key": "nav.groupSales",
        "icon_name": "PointOfSale",
        "route_path": None,
        "required_roles": None,
        "children": [
            ("nav.customers", "Groups", "/customers", None),
            ("nav.sales", "PointOfSale", "/sales", None),
        ],
    },
    {
        "label_key": "nav.groupInventory",
        "icon_name": "Warehouse",
        "route_path": None,
        "required_roles": None,
        "children": [
            ("nav.products", "Inventory2", "/products", None),
            ("nav.categories", "Category", "/categories", "admin,manager"),
            ("nav.suppliers", "Storefront", "/suppliers", None),
            ("nav.purchases", "LocalShipping", "/purchases", None),
            ("nav.inventory", "Warehouse", "/inventory", None),
            ("nav.adjustments", "Tune", "/adjustments", "admin,manager,warehouse"),
        ],
    },
    {
        "label_key": "nav.groupAccounting",
        "icon_name": "AccountBalance",
        "route_path": None,
        "required_roles": None,
        "children": [
            ("nav.accountsReceivable", "RequestQuote", "/accounts-receivable", None),
            ("nav.accountsPayable", "Payments", "/accounts-payable", None),
            ("nav.aging", "Schedule", "/aging", None),
        ],
    },
    {
        "label_key": "nav.reports",
        "icon_name": "Assessment",
        "route_path": "/reports",
        "required_roles": None,
        "children": [],
    },
    {
        "label_key": "nav.groupAdmin",
        "icon_name": "Settings",
        "route_path": None,
        "required_roles": "admin",
        "children": [
            ("nav.users", "People", "/users", "admin"),
            ("nav.menuManagement", "AccountTree", "/menu-management", "admin"),
        ],
    },
]


def seed_menu() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(MenuItem).limit(1))
        if existing:
            print("menu_items already populated — skipping seed.")
            return

        for group_order, group in enumerate(DEFAULT_TREE):
            parent = MenuItem(
                parent_id=None,
                label_key=group["label_key"],
                custom_label=None,
                icon_name=group["icon_name"],
                route_path=group["route_path"],
                required_roles=group["required_roles"],
                display_order=group_order,
                is_active=True,
            )
            db.add(parent)
            db.flush()  # populate parent.id
            for child_order, (label_key, icon, route, roles) in enumerate(group["children"]):
                db.add(
                    MenuItem(
                        parent_id=parent.id,
                        label_key=label_key,
                        custom_label=None,
                        icon_name=icon,
                        route_path=route,
                        required_roles=roles,
                        display_order=child_order,
                        is_active=True,
                    )
                )
        db.commit()
        print(f"Seeded {sum(1 + len(g['children']) for g in DEFAULT_TREE)} menu items.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_menu()
