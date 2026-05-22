"""Catalog generator: suppliers + categories + products + customers.

Idempotent: each create POST is preceded by a list-and-lookup against the
natural key (supplier name, category name, product sku, customer name). Re-
running this step adopts the existing rows and skips POSTs.
"""
from __future__ import annotations

from typing import Any

from seed.config import customers as customers_cfg
from seed.config import products as products_cfg
from seed.config import suppliers as suppliers_cfg

from ._payload import build_payload
from .api_client import SeedAPIClient
from .seed_setup import SeedState


def _index_existing(client: SeedAPIClient, path: str, key: str) -> dict[str, int]:
    """List all rows from ``path`` and return ``{row[key]: row['id']}``."""
    rows = client.get(path, params={"limit": 200}).json()
    return {row[key]: row["id"] for row in rows}


def seed_suppliers(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[catalog] suppliers ({len(suppliers_cfg.SUPPLIERS)} total) ...")
    existing = _index_existing(client, "/suppliers", "name")
    created = adopted = 0
    for sup in suppliers_cfg.SUPPLIERS:
        if sup["name"] in existing:
            state.supplier_ids[sup["code"]] = existing[sup["name"]]
            adopted += 1
            continue
        payload = build_payload(sup, drop={"code"})
        resp = client.post("/suppliers", json=payload)
        state.supplier_ids[sup["code"]] = resp.json()["id"]
        created += 1
    print(f"[catalog]   suppliers: {created} created, {adopted} adopted")


def seed_categories(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[catalog] categories ({len(products_cfg.CATEGORIES)} total) ...")
    existing = _index_existing(client, "/categories", "name")
    created = adopted = 0
    for cat in products_cfg.CATEGORIES:
        if cat["name"] in existing:
            state.category_ids[cat["code"]] = existing[cat["name"]]
            adopted += 1
            continue
        payload = build_payload(cat, drop={"code"})
        resp = client.post("/categories", json=payload)
        state.category_ids[cat["code"]] = resp.json()["id"]
        created += 1
    print(f"[catalog]   categories: {created} created, {adopted} adopted")


def seed_products(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[catalog] products ({len(products_cfg.PRODUCTS)} total) ...")
    existing = _index_existing(client, "/products", "sku")
    created = adopted = 0
    for prod in products_cfg.PRODUCTS:
        if prod["sku"] in existing:
            state.product_ids[prod["sku"]] = existing[prod["sku"]]
            adopted += 1
            continue
        category_id = state.category_ids[prod["category_code"]]
        payload = build_payload(
            prod,
            drop={"category_code", "launch_month", "supplier_codes"},
        )
        payload["category_id"] = category_id
        resp = client.post("/products", json=payload)
        state.product_ids[prod["sku"]] = resp.json()["id"]
        created += 1
    print(f"[catalog]   products: {created} created, {adopted} adopted")


def seed_customers(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[catalog] customers ({len(customers_cfg.CUSTOMERS)} total) ...")
    existing = _index_existing(client, "/customers", "name")
    created = adopted = 0
    for cust in customers_cfg.CUSTOMERS:
        if cust["name"] in existing:
            state.customer_ids[cust["code"]] = existing[cust["name"]]
            adopted += 1
            continue
        payload = build_payload(cust, drop={"code", "role"})
        resp = client.post("/customers", json=payload)
        state.customer_ids[cust["code"]] = resp.json()["id"]
        created += 1
    print(f"[catalog]   customers: {created} created, {adopted} adopted")


def run_catalog(client: SeedAPIClient, state: SeedState) -> None:
    """Build the static catalogue: suppliers → categories → products → customers."""
    seed_suppliers(client, state)
    seed_categories(client, state)
    seed_products(client, state)
    seed_customers(client, state)
