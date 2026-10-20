"""MCP tools — recall surface (split from tools.py Phase C)."""
from __future__ import annotations



"""MCP s3_* tools (FastMCP decorators preserved)."""

from scribe3.mcp._common import *  # noqa: F403
from scribe3.mcp.gating import *  # noqa: F403

def _semantic_recall_impl(query: str, k: int, reveal_secret: bool,
                          work: str | None, chapter: int | None = None) -> list[dict]:
    """chapter 非空时走 store 时间门(valid_from/valid_to),与 hybrid 一致。"""
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute,
            "value": _mask_value(f.value, bool(f.secret), reveal_secret),
            "is_secret": bool(f.secret),
            "valid_from": f.valid_from,
            "valid_to": f.valid_to}
            for f in _store_for(work).semantic_recall(query, k, chapter=chapter)]


@mcp.tool(annotations=_RO)
def s3_semantic_recall(query: str, k: int = 5, chapter: int | None = None,
                       work: str | None = None) -> list[dict]:
    """语义召回最相关的设定/命题(向量 RAG,非字面匹配;头部工具仍多用字面,这是差异化)。

    chapter: 可选故事章时间门——只返回 valid_from<=chapter 且仍有效的命题;省略=不按章过滤。
    恒掩码私密命题的 value(显示 '🔒 私密'),is_secret 标志始终保留——本工具**没有**
    reveal_secret 参数(U-003 修复:能否解锁明文从"模型的参数"降格为"工具的名字",
    工具面白名单物理隔离,不再靠模型自律)。全知明文见孪生工具 s3_semantic_recall_reveal。"""
    return _semantic_recall_impl(query, k, False, work, chapter=chapter)


@mcp.tool(annotations=_RO)
def s3_semantic_recall_reveal(query: str, k: int = 5, chapter: int | None = None,
                              work: str | None = None) -> list[dict]:
    """s3_semantic_recall 的全知孪生:返回明文(secret 命题不掩码)。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _semantic_recall_impl(query, k, True, work, chapter=chapter)


def _hybrid_recall_impl(query: str, chapter: int, k: int, reveal_secret: bool,
                        work: str | None) -> list[dict]:
    return [{"id": f.id, "entity": f.entity_id, "attribute": f.attribute,
            "value": _mask_value(f.value, bool(f.secret), reveal_secret),
            "is_secret": bool(f.secret)}
            for f in _store_for(work).hybrid_recall(query, chapter, k)]


@mcp.tool(annotations=_RO)
def s3_hybrid_recall(query: str, chapter: int, k: int = 5,
                     work: str | None = None) -> list[dict]:
    """混合召回:向量语义 + 中文关键词 → RRF 融合排名。
    比纯向量召回多关键词路(专名/法器名精确匹配),叠加限知时间门。

    恒掩码私密命题的 value(显示 '🔒 私密'),is_secret 标志始终保留——本工具**没有**
    reveal_secret 参数(U-003 修复:能否解锁明文从"模型的参数"降格为"工具的名字",
    工具面白名单物理隔离,不再靠模型自律)。全知明文见孪生工具 s3_hybrid_recall_reveal。"""
    return _hybrid_recall_impl(query, chapter, k, False, work)


@mcp.tool(annotations=_RO)
def s3_hybrid_recall_reveal(query: str, chapter: int, k: int = 5,
                            work: str | None = None) -> list[dict]:
    """s3_hybrid_recall 的全知孪生:返回明文(secret 命题不掩码)。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _hybrid_recall_impl(query, chapter, k, True, work)


@mcp.tool(annotations=_RO)
def s3_chapter_recall(query: str, k: int = 5, work: str | None = None) -> list[dict]:
    """章节语义召回:按标题+正文匹配语义最接近的章(向量 RAG)。
    用来查'与哪章描写接近'、'某主题首次出现在哪章'等。"""
    return _store_for(work).chapter_recall(query, k)


def _graph_recall_impl(query: str, chapter: int, k: int, reveal_secret: bool,
                       work: str | None) -> list[dict]:
    results = _store_for(work).graph_recall(query, chapter, k)
    for item in results:
        is_secret = bool(item.get("secret", False))
        if "is_secret" not in item:
            item["is_secret"] = is_secret
        item["value"] = _mask_value(item.get("value", ""), is_secret, reveal_secret)
    return results


@mcp.tool(annotations=_RO)
def s3_graph_recall(query: str, chapter: int, k: int = 5,
                    work: str | None = None) -> list[dict]:
    """Graph RAG 召回:语义相关命题 + 其知识子图(谁知道/来源事件/同场角色)。
    叠加章时间门(限知)。不喂限知渲染。

    恒掩码私密命题的 value(显示 '🔒 私密'),is_secret 标志始终保留——本工具**没有**
    reveal_secret 参数(U-003 修复:能否解锁明文从"模型的参数"降格为"工具的名字",
    工具面白名单物理隔离,不再靠模型自律)。全知明文见孪生工具 s3_graph_recall_reveal。"""
    return _graph_recall_impl(query, chapter, k, False, work)


@mcp.tool(annotations=_RO)
def s3_graph_recall_reveal(query: str, chapter: int, k: int = 5,
                           work: str | None = None) -> list[dict]:
    """s3_graph_recall 的全知孪生:返回明文(secret 命题不掩码)。供主编全知联查。

    **仅供主编全知联查专用**,其输出严禁进入限知章续写 prompt。U-003 真机实测推翻了
    "只挂 scribe3_chief server"的旧设想——Hermes 的 server_label 不做过滤,主编对话与
    限知续写共用同一个网关进程(:8643),挂给任一 profile 就等于挂给了写作路径。
    **当前不挂载在任何网关**:两条路径的 profile include 白名单都不含这把工具,模型
    物理调不到(见 `_summarize_hermes_runtime` 的 `gateway_exposes_reveal_tools` 自检,
    钉死"任何 profile 的 include 都不得出现 *_reveal 工具"这条不变量)。要启用须另起
    一个**绝不服务写作/续写路径**的专用网关,而不是靠 label 隔离。"""
    return _graph_recall_impl(query, chapter, k, True, work)


@mcp.tool(annotations=_RO)
def s3_material_recall(query: str, chapter: int = 9999, k: int = 5,
                       work: str | None = None) -> list[dict]:
    """素材记忆召回:三通道(语义+关键词+图)唤起与 query 相关的参考素材(借鉴非事实)。
    返回标题/正文摘要/参考维度,供主编借鉴并向作者说明为什么参考。区别于设定召回:
    素材是创作参考(风格/手法/桥段),非故事内事实,不受限知约束,可放心用于讨论与构思。"""
    return [{"id": r.get("material_id"), "title": r.get("title"),
            "excerpt": (r.get("body") or "")[:200], "ref_tags": r.get("ref_tags") or [],
            "pinned": r.get("pinned")}
            for r in _store_for(work).material_recall(query, chapter, k)]

