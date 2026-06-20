from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from .conn import connect, domain_from
from .domain import Domain

app = FastAPI(title="Scribe (SurrealDB)")
_singleton: dict = {"d": None}

def get_domain() -> Domain:
    if _singleton["d"] is None:
        _singleton["d"] = domain_from(connect())
    return _singleton["d"]

def owner(x: str | None) -> str:
    if not x:
        raise HTTPException(401, "缺少 X-Owner-Id")
    return x

class WorkIn(BaseModel):
    title: str; genre: str = ""
class ChapterIn(BaseModel):
    seq: int; title: str = ""
class ProseIn(BaseModel):
    content: str; lock: bool = False
class SettingIn(BaseModel):
    name: str; desc: str = ""
class SearchIn(BaseModel):
    query: str; k: int = 6

@app.post("/works")
def create_work(b: WorkIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return {"work_id": d.create_work(b.title, b.genre, owner(x_owner_id))}

@app.get("/works")
def list_works(x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    return d.list_works(owner(x_owner_id))

@app.put("/works/{w}/chapters")
def add_chapter(w: str, b: ChapterIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"chapter_id": d.add_chapter(w, b.seq, b.title)}

@app.get("/works/{w}/chapters")
def list_chapters(w: str, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.list_chapters(w)

@app.post("/works/{w}/chapters/{c}/prose")
def save_prose(w: str, c: str, b: ProseIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"snapshot_id": d.save_prose(w, c, b.content, b.lock)}

@app.post("/works/{w}/settings")
def add_setting(w: str, b: SettingIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return {"setting_id": d.add_setting(w, b.name, b.desc)}

@app.post("/works/{w}/search")
def search(w: str, b: SearchIn, x_owner_id: str | None = Header(None), d: Domain = Depends(get_domain)):
    owner(x_owner_id); return d.search(w, b.query, b.k)

@app.get("/health")
def health():
    return {"ok": True}
