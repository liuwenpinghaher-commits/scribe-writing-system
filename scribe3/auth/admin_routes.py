"""Admin console HTTP API: users + cross-account works + audit."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from scribe3.auth.middleware import resolve_username
from scribe3.auth.users import (
    create_user,
    delete_user,
    force_logout,
    get_user,
    is_admin,
    list_audit,
    list_users,
    set_password,
    summary_counts,
    update_user,
    write_audit,
)

router = APIRouter(tags=["admin"])


def _require_admin(request: Request) -> str:
    user = resolve_username(request)
    if not user:
        raise HTTPException(401, "authentication required")
    if not is_admin(user):
        raise HTTPException(403, "admin role required")
    return user


class UserCreateIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=200)
    role: Literal["admin", "author"] = "author"
    display_name: str = ""
    note: str = ""
    status: Literal["active", "disabled"] = "active"


class UserPatchIn(BaseModel):
    display_name: str | None = None
    role: Literal["admin", "author"] | None = None
    status: Literal["active", "disabled"] | None = None
    note: str | None = None


class PasswordIn(BaseModel):
    password: str = Field(min_length=6, max_length=200)


class WorkCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    owner_user_id: str = Field(min_length=1, max_length=64)
    slug: str | None = None


class WorkPatchIn(BaseModel):
    title: str | None = None
    owner_user_id: str | None = None


class WorkTransferIn(BaseModel):
    new_owner: str = Field(min_length=1, max_length=64)


class WorkPurgeIn(BaseModel):
    confirm_title: str = Field(min_length=1)


@router.get("/admin/summary")
def admin_summary(request: Request):
    actor = _require_admin(request)
    users = summary_counts()
    try:
        from scribe3.store.core_preamble import list_works_admin
        works = list_works_admin(archived="all")
        active = sum(1 for w in works if not w.get("archived"))
        archived = sum(1 for w in works if w.get("archived"))
        by_owner: dict[str, int] = {}
        for w in works:
            if w.get("archived"):
                continue
            o = w.get("effective_owner") or "?"
            by_owner[o] = by_owner.get(o, 0) + 1
    except Exception as e:
        works = []
        active = archived = 0
        by_owner = {}
        users["works_error"] = str(e)[:120]
    return {
        "ok": True,
        "viewer": actor,
        "users": users,
        "works": {
            "total": len(works),
            "active": active,
            "archived": archived,
            "by_owner": by_owner,
        },
    }


@router.get("/admin/users")
def admin_list_users(
    request: Request,
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    _require_admin(request)
    data = list_users(q=q, role=role, status=status, offset=offset, limit=limit)
    # attach work counts
    try:
        from scribe3.store.core_preamble import list_works_admin
        all_w = list_works_admin(archived="all")
    except Exception:
        all_w = []
    counts: dict[str, dict[str, int]] = {}
    for w in all_w:
        o = w.get("effective_owner") or ""
        if not o:
            continue
        bucket = counts.setdefault(o, {"active": 0, "archived": 0})
        if w.get("archived"):
            bucket["archived"] += 1
        else:
            bucket["active"] += 1
    for it in data["items"]:
        c = counts.get(it["username"]) or {"active": 0, "archived": 0}
        it["works_active"] = c["active"]
        it["works_archived"] = c["archived"]
    return data


@router.post("/admin/users")
def admin_create_user(request: Request, body: UserCreateIn):
    actor = _require_admin(request)
    try:
        user = create_user(
            body.username,
            body.password,
            role=body.role,
            display_name=body.display_name,
            note=body.note,
            status=body.status,
        )
    except ValueError as e:
        raise HTTPException(409 if "exists" in str(e) else 422, str(e))
    write_audit(
        actor, "user.create",
        target_type="user", target_id=user["username"],
        detail={"role": user["role"], "status": user["status"]},
    )
    return user


@router.get("/admin/users/{username}")
def admin_get_user(request: Request, username: str):
    _require_admin(request)
    u = get_user(username)
    if not u:
        raise HTTPException(404, "user not found")
    try:
        from scribe3.store.core_preamble import list_works_admin
        works = list_works_admin(owner=username, archived="all")
    except Exception:
        works = []
    u["works"] = works
    u["works_active"] = sum(1 for w in works if not w.get("archived"))
    u["works_archived"] = sum(1 for w in works if w.get("archived"))
    return u


@router.patch("/admin/users/{username}")
def admin_patch_user(request: Request, username: str, body: UserPatchIn):
    actor = _require_admin(request)
    try:
        u = update_user(
            username,
            display_name=body.display_name,
            role=body.role,
            status=body.status,
            note=body.note,
        )
    except KeyError:
        raise HTTPException(404, "user not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    write_audit(
        actor, "user.update",
        target_type="user", target_id=username,
        detail=body.model_dump(exclude_none=True),
    )
    return u


@router.post("/admin/users/{username}/password")
def admin_set_password(request: Request, username: str, body: PasswordIn):
    actor = _require_admin(request)
    try:
        set_password(username, body.password, bump_session=True)
    except KeyError:
        raise HTTPException(404, "user not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    write_audit(
        actor, "user.password_reset",
        target_type="user", target_id=username,
        detail={"by": actor},
    )
    return {"ok": True, "username": username, "sessions_revoked": True}


@router.post("/admin/users/{username}/force-logout")
def admin_force_logout(request: Request, username: str):
    actor = _require_admin(request)
    try:
        sv = force_logout(username)
    except KeyError:
        raise HTTPException(404, "user not found")
    write_audit(
        actor, "user.force_logout",
        target_type="user", target_id=username,
        detail={"session_version": sv},
    )
    return {"ok": True, "username": username, "session_version": sv}


@router.delete("/admin/users/{username}")
def admin_delete_user(
    request: Request,
    username: str,
    confirm_username: str = Query(..., description="必须与 username 完全一致"),
):
    actor = _require_admin(request)
    if confirm_username.strip() != username.strip():
        raise HTTPException(422, "confirm_username mismatch")
    if actor == username.strip():
        raise HTTPException(422, "cannot delete yourself")
    try:
        delete_user(username)
    except KeyError:
        raise HTTPException(404, "user not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    write_audit(
        actor, "user.delete",
        target_type="user", target_id=username,
        detail={},
    )
    return {"ok": True, "deleted": username}


@router.get("/admin/works")
def admin_list_works(
    request: Request,
    owner: str | None = None,
    archived: str = Query("all", pattern="^(active|archived|all)$"),
    q: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    _require_admin(request)
    from scribe3.store.core_preamble import list_works_admin
    rows = list_works_admin(owner=owner, archived=archived, q=q)
    total = len(rows)
    page = rows[offset: offset + limit]
    # optional stats
    enriched = []
    for w in page:
        item = dict(w)
        try:
            from scribe3.api.app_impl import _store_for
            st = _store_for(w["slug"])
            stats = st.stats() or {}
            item["chapter_count"] = stats.get("chapter_count")
            item["word_count"] = stats.get("word_count")
        except Exception:
            item["stats_error"] = True
        enriched.append(item)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": enriched,
    }


@router.post("/admin/works")
def admin_create_work(request: Request, body: WorkCreateIn):
    actor = _require_admin(request)
    if not get_user(body.owner_user_id):
        raise HTTPException(422, f"owner user not found: {body.owner_user_id}")
    from scribe3.store.core_preamble import create_work
    try:
        w = create_work(
            body.title,
            slug=body.slug,
            owner_user_id=body.owner_user_id.strip(),
        )
    except ValueError as e:
        raise HTTPException(409 if "同名" in str(e) else 422, str(e))
    write_audit(
        actor, "work.create",
        target_type="work", target_id=w["slug"],
        detail={"owner": body.owner_user_id, "title": body.title},
    )
    return w


@router.patch("/admin/works/{slug}")
def admin_patch_work(request: Request, slug: str, body: WorkPatchIn):
    actor = _require_admin(request)
    from scribe3.store.core_preamble import list_works_admin, rename_work, set_work_owner
    hits = [w for w in list_works_admin(archived="all") if w["slug"] == slug]
    if not hits:
        raise HTTPException(404, "work not found")
    out = dict(hits[0])
    try:
        if body.title is not None:
            rename_work(slug, body.title)
            out["title"] = body.title
        if body.owner_user_id is not None:
            if not get_user(body.owner_user_id):
                raise HTTPException(422, f"owner user not found: {body.owner_user_id}")
            out = set_work_owner(slug, body.owner_user_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    write_audit(
        actor, "work.update",
        target_type="work", target_id=slug,
        detail=body.model_dump(exclude_none=True),
    )
    return out


@router.post("/admin/works/{slug}/transfer")
def admin_transfer_work(request: Request, slug: str, body: WorkTransferIn):
    actor = _require_admin(request)
    if not get_user(body.new_owner):
        raise HTTPException(422, f"owner user not found: {body.new_owner}")
    from scribe3.store.core_preamble import set_work_owner
    try:
        out = set_work_owner(slug, body.new_owner)
    except ValueError as e:
        raise HTTPException(404 if "不存在" in str(e) else 422, str(e))
    write_audit(
        actor, "work.transfer",
        target_type="work", target_id=slug,
        detail={"new_owner": body.new_owner},
    )
    return out


@router.post("/admin/works/{slug}/archive")
def admin_archive_work(request: Request, slug: str):
    actor = _require_admin(request)
    from scribe3.store.core_preamble import archive_work
    try:
        archive_work(slug)
    except ValueError as e:
        raise HTTPException(400, str(e))
    write_audit(actor, "work.archive", target_type="work", target_id=slug)
    return {"ok": True, "archived": True, "slug": slug}


@router.post("/admin/works/{slug}/restore")
def admin_restore_work(request: Request, slug: str):
    actor = _require_admin(request)
    from scribe3.store.core_preamble import restore_work
    try:
        restore_work(slug)
    except ValueError as e:
        raise HTTPException(409, str(e))
    write_audit(actor, "work.restore", target_type="work", target_id=slug)
    return {"ok": True, "slug": slug}


@router.delete("/admin/works/{slug}/purge")
def admin_purge_work(request: Request, slug: str, body: WorkPurgeIn):
    actor = _require_admin(request)
    from scribe3.store.core_preamble import delete_work, list_works_admin
    hits = [w for w in list_works_admin(archived="all") if w["slug"] == slug]
    if not hits:
        raise HTTPException(404, "work not found")
    title = (hits[0].get("title") or "").strip()
    if not title or body.confirm_title.strip() != title:
        raise HTTPException(422, "书名不匹配,永久删除已取消")
    try:
        delete_work(slug)
    except ValueError as e:
        raise HTTPException(409, str(e))
    try:
        from scribe3.api import app_impl as core
        getattr(core, "_stores", {}).pop(slug, None)
    except Exception:
        pass
    write_audit(
        actor, "work.purge",
        target_type="work", target_id=slug,
        detail={"title": title},
    )
    return {"ok": True, "purged": True, "slug": slug}


@router.get("/admin/audit")
def admin_audit(
    request: Request,
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    _require_admin(request)
    return list_audit(
        actor=actor, action=action, target_type=target_type,
        offset=offset, limit=limit,
    )
