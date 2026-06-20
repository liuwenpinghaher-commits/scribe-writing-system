from __future__ import annotations
import os
from surrealdb import Surreal
from .store import Store
from .domain import Domain

SURREAL_URL = os.environ.get("SURREAL_URL", "ws://127.0.0.1:8000/rpc")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")
SURREAL_NS = os.environ.get("SURREAL_NS", "scribe")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")

def connect() -> Surreal:
    d = Surreal(SURREAL_URL)
    d.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    d.use(SURREAL_NS, SURREAL_DB)
    return d

def domain_from(db) -> Domain:
    return Domain(Store(db))
