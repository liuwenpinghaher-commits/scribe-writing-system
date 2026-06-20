"""Scribe 领域 MCP 工具(FastMCP)。薄封装 Domain;写工具登记审批表。

段4 Hermes run 挂本 server:命中 WRITE_TOOLS 内的工具 -> 暂停并 emit 审批事件。
工具函数经 @mcp.tool 装饰后仍返回原函数,可直接调用(测试无需 async)。
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:
    from mcp.types import ToolAnnotations
except Exception:
    ToolAnnotations = None  # type: ignore

from .conn import connect, domain_from
from .domain import Domain

mcp = FastMCP("scribe")

_state: dict = {"domain": None}


def set_domain(d: Domain) -> None:
    """测试/启动期注入已装配的 Domain。"""
    _state["domain"] = d


def _domain() -> Domain:
    if _state["domain"] is None:
        _state["domain"] = domain_from(connect())
    return _state["domain"]


WRITE_TOOLS: set[str] = set()


def requires_approval(tool_name: str) -> bool:
    """该工具是否为需人审批的写操作。"""
    return tool_name in WRITE_TOOLS


def _make_tool(read_only: bool):
    """构造带 readOnlyHint 注解的工具装饰器;SDK 不支持 annotations 则降级。"""
    if ToolAnnotations is not None:
        try:
            return mcp.tool(annotations=ToolAnnotations(readOnlyHint=read_only))
        except TypeError:
            pass
    return mcp.tool()


def _read_tool():
    """只读工具装饰器。"""
    return _make_tool(read_only=True)


def _write_tool(fn):
    """写工具:登记进 WRITE_TOOLS + 标 readOnlyHint=False。返回原函数(可直接调用)。"""
    WRITE_TOOLS.add(fn.__name__)
    return _make_tool(read_only=False)(fn)


@_read_tool()
def search_knowledge(work_id: str, query: str, k: int = 6) -> list[dict]:
    """对全书做 向量+全文 混合检索并沿图扩展,汇聚相关设定/正文/伏笔/记忆。只读。"""
    return _domain().search(work_id, query, k)


@_read_tool()
def get_work(work_id: str) -> dict | None:
    """读取作品元数据。"""
    return _domain().get_work(work_id)


@_read_tool()
def list_works(owner: str = "u1") -> list[dict]:
    """列出某 owner 的全部作品。"""
    return _domain().list_works(owner)


@_read_tool()
def list_chapters(work_id: str) -> list[dict]:
    """按 seq 升序列出作品的章节。"""
    return _domain().list_chapters(work_id)


@_read_tool()
def list_snapshots(chapter_id: str) -> list[dict]:
    """按 version 升序列出某章的版本快照。"""
    return _domain().list_snapshots(chapter_id)


@_read_tool()
def latest_prose(chapter_id: str) -> str:
    """取某章最新版本的正文文本。"""
    return _domain().latest_prose(chapter_id)


@_read_tool()
def list_settings(work_id: str) -> list[dict]:
    """列出作品的设定条目。"""
    return _domain().list_settings(work_id)


@_write_tool
def create_work(title: str, genre: str = "", owner: str = "u1") -> dict:
    """新建作品。写操作,需审批。"""
    return {"work_id": _domain().create_work(title, genre, owner)}


@_write_tool
def create_volume(work_id: str, seq: int, title: str = "") -> dict:
    """新建卷。写操作,需审批。"""
    return {"volume_id": _domain().create_volume(work_id, seq, title)}


@_write_tool
def create_chapter(work_id: str, seq: int, title: str = "", volume_id: str | None = None) -> dict:
    """在作品下新建章节(可选挂卷)。写操作,需审批。"""
    return {"chapter_id": _domain().add_chapter(work_id, seq, title, volume_id)}


@_write_tool
def save_prose(work_id: str, chapter_id: str, content: str, lock: bool = False) -> dict:
    """为某章存一份正文快照(自动递增版本)。写操作,需审批。"""
    return {"snapshot_id": _domain().save_prose(work_id, chapter_id, content, lock)}


@_write_tool
def add_setting(work_id: str, name: str, desc: str = "") -> dict:
    """新增设定条目(自动嵌入,立即可被 search_knowledge 召回)。写操作,需审批。"""
    return {"setting_id": _domain().add_setting(work_id, name, desc)}


def main() -> None:
    """以 stdio 传输启动 MCP server,供 Hermes run / MCP 客户端挂载(段4)。"""
    mcp.run()


if __name__ == "__main__":
    main()
