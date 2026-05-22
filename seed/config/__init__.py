"""Static seed data (Step 2): 5 namespaced configuration modules.

These are pure-Python TypedDict catalogues. Step 3+ generators import them
to drive API writes; no backend / DB connection is required to import this
package.
"""
from __future__ import annotations

from . import customers, people, products, stories, suppliers

__all__ = ["customers", "people", "products", "stories", "suppliers"]
