import pytest

from app.models.menu_item import MenuItem


def _seed_basic(db_session):
    """Two top-level items: a leaf 'home' visible to all, and a group 'admin' with one child."""
    home = MenuItem(label_key="nav.home", icon_name="Home", route_path="/", display_order=0)
    admin_grp = MenuItem(label_key="nav.groupAdmin", icon_name="Settings",
                          required_roles="admin", display_order=1)
    db_session.add_all([home, admin_grp])
    db_session.flush()
    users = MenuItem(
        parent_id=admin_grp.id, label_key="nav.users", icon_name="People",
        route_path="/users", required_roles="admin", display_order=0,
    )
    db_session.add(users)
    db_session.commit()
    return {"home": home, "admin_grp": admin_grp, "users": users}


def test_get_menu_filters_by_role_admin(db_session, auth):
    _seed_basic(db_session)
    admin = auth("admin")
    r = admin.get("/api/v1/menu")
    assert r.status_code == 200
    tree = r.json()
    assert len(tree) == 2
    labels = {n["label_key"] for n in tree}
    assert labels == {"nav.home", "nav.groupAdmin"}
    admin_group = next(n for n in tree if n["label_key"] == "nav.groupAdmin")
    assert len(admin_group["children"]) == 1
    assert admin_group["children"][0]["label_key"] == "nav.users"


def test_get_menu_filters_by_role_non_admin(db_session, auth):
    _seed_basic(db_session)
    sales = auth("sales")
    tree = sales.get("/api/v1/menu").json()
    assert {n["label_key"] for n in tree} == {"nav.home"}


def test_get_menu_orphaned_child_is_promoted_to_top(db_session, auth):
    """If a parent group is hidden (e.g. role mismatch), the visible child should
    still appear, not vanish."""
    grp = MenuItem(label_key="hidden.group", required_roles="admin", display_order=0)
    db_session.add(grp)
    db_session.flush()
    child = MenuItem(
        parent_id=grp.id, label_key="visible.child", route_path="/child",
        required_roles=None, display_order=0,
    )
    db_session.add(child)
    db_session.commit()

    tree = auth("sales").get("/api/v1/menu").json()
    # Sales user does not see the admin-restricted group, but the child has no
    # role restriction, so it must still surface — at the top level.
    assert any(n["label_key"] == "visible.child" for n in tree)


def test_get_menu_excludes_inactive(db_session, auth):
    home = MenuItem(label_key="nav.home", route_path="/", display_order=0, is_active=False)
    db_session.add(home)
    db_session.commit()
    tree = auth("admin").get("/api/v1/menu").json()
    assert tree == []


def test_admin_create_menu_item(db_session, auth):
    admin = auth("admin")
    r = admin.post(
        "/api/v1/admin/menu",
        json={
            "label_key": "nav.products",
            "icon_name": "Inventory2",
            "route_path": "/products",
            "display_order": 5,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["label_key"] == "nav.products"
    assert body["is_active"] is True


def test_admin_create_requires_label(db_session, auth):
    r = auth("admin").post("/api/v1/admin/menu", json={"icon_name": "Home"})
    assert r.status_code == 422


def test_admin_create_rejects_bad_parent(db_session, auth):
    r = auth("admin").post(
        "/api/v1/admin/menu",
        json={"parent_id": 99999, "label_key": "x.y"},
    )
    assert r.status_code == 400


def test_admin_update_menu_item(db_session, auth):
    items = _seed_basic(db_session)
    admin = auth("admin")
    r = admin.patch(
        f"/api/v1/admin/menu/{items['home'].id}",
        json={"custom_label": "Dashboard", "display_order": 10},
    )
    assert r.status_code == 200
    assert r.json()["custom_label"] == "Dashboard"
    assert r.json()["display_order"] == 10


def test_admin_update_rejects_self_parent(db_session, auth):
    items = _seed_basic(db_session)
    r = auth("admin").patch(
        f"/api/v1/admin/menu/{items['home'].id}",
        json={"parent_id": items["home"].id},
    )
    assert r.status_code == 400


def test_admin_update_rejects_cycle(db_session, auth):
    """Setting an item's parent to one of its own descendants must be rejected."""
    items = _seed_basic(db_session)
    # Make 'users' the parent of 'admin_grp' — that would put admin_grp under users
    # while users is already under admin_grp. Cycle.
    r = auth("admin").patch(
        f"/api/v1/admin/menu/{items['admin_grp'].id}",
        json={"parent_id": items["users"].id},
    )
    assert r.status_code == 400


def test_admin_delete_cascades(db_session, auth):
    items = _seed_basic(db_session)
    admin_grp_id = items["admin_grp"].id
    users_id = items["users"].id
    r = auth("admin").delete(f"/api/v1/admin/menu/{admin_grp_id}")
    assert r.status_code == 204
    db_session.expire_all()
    # Both the group and its child should be gone.
    assert db_session.get(MenuItem, admin_grp_id) is None
    assert db_session.get(MenuItem, users_id) is None


def test_admin_reorder(db_session, auth):
    items = _seed_basic(db_session)
    admin = auth("admin")
    r = admin.post(
        "/api/v1/admin/menu/reorder",
        json=[
            {"id": items["home"].id, "parent_id": None, "display_order": 99},
            {"id": items["admin_grp"].id, "parent_id": None, "display_order": 1},
        ],
    )
    assert r.status_code == 204
    db_session.expire_all()
    assert db_session.get(MenuItem, items["home"].id).display_order == 99
    assert db_session.get(MenuItem, items["admin_grp"].id).display_order == 1


def test_admin_reorder_rejects_cycle(db_session, auth):
    items = _seed_basic(db_session)
    r = auth("admin").post(
        "/api/v1/admin/menu/reorder",
        json=[
            {"id": items["admin_grp"].id, "parent_id": items["users"].id, "display_order": 0},
        ],
    )
    assert r.status_code == 400


def test_non_admin_cannot_manage_menu(db_session, auth):
    items = _seed_basic(db_session)
    sales = auth("sales")
    assert sales.get("/api/v1/admin/menu").status_code == 403
    assert sales.post("/api/v1/admin/menu", json={"label_key": "x"}).status_code == 403
    assert sales.patch(f"/api/v1/admin/menu/{items['home'].id}", json={}).status_code == 403
    assert sales.delete(f"/api/v1/admin/menu/{items['home'].id}").status_code == 403
