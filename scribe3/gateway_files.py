# scribe3/gateway_files.py
"""Hermes profile 文件的白名单读写(设置中心网关区)。

安全边界:
- 白名单硬编码:profiles/{scribe3,scribe3_write}/{config.yaml,SOUL.md,.env},
  id 必须精确命中,resolve 后必须仍在 HERMES_HOME 下(双保险防穿越)。
- .env 与 config.yaml 读取时掩码含 KEY/TOKEN/PASS/SECRET 的行(忽略大小写,
  含 export 前缀;value → ••••);保存时凡值为 «••••»(允许尾引号)的行按
  原文件还原(密钥永不经网络明文往返)。
- 写前自动备份 <file>.bak.<ts+毫秒>;base_sha256 失配抛 StaleFileError(→409)。
- list_files 单文件读取失败(symlink 越界/IO错)只降级该条目,不拖垮列表。
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path

_PROFILES = ("scribe3", "scribe3_write")
_NAMES = ("config.yaml", "SOUL.md", ".env")
_MASK = "••••"
_SECRET_LINE = re.compile(
    r"^(\s*(?:export\s+)?[A-Za-z0-9_]*(?:KEY|TOKEN|PASS|SECRET)[A-Za-z0-9_]*\s*=).*$",
    re.IGNORECASE,
)
_SECRET_YAML_LINE = re.compile(
    r"^(\s*[A-Za-z0-9_]*(?:key|token|pass|secret)[A-Za-z0-9_]*\s*:\s*).+$",
    re.IGNORECASE,
)


class NotAllowedError(Exception): ...
class StaleFileError(Exception): ...


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()


def _resolve(file_id: str) -> Path:
    parts = file_id.split("/")
    if len(parts) != 2 or parts[0] not in _PROFILES or parts[1] not in _NAMES:
        raise NotAllowedError(f"白名单外文件: {file_id}")
    p = (_home() / "profiles" / parts[0] / parts[1]).resolve()
    if not str(p).startswith(str(_home().resolve()) + os.sep):
        raise NotAllowedError(f"路径越界: {file_id}")
    return p


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mask_pattern(name: str) -> re.Pattern | None:
    if name == ".env":
        return _SECRET_LINE
    if name == "config.yaml":
        return _SECRET_YAML_LINE
    return None


def _mask(text: str, pattern: re.Pattern) -> str:
    return "\n".join(pattern.sub(rf"\g<1>{_MASK}", ln) for ln in text.split("\n"))


def _is_masked_value(ln: str) -> bool:
    # 编辑器往返后掩码值可能带尾引号(api_key: '••••')——三种形态都算掩码
    s = ln.strip()
    if s.endswith(("'", '"')):
        s = s[:-1]
    return s.endswith(_MASK)


def _restore_masked(old: str, content: str, pattern: re.Pattern) -> str:
    # 掩码行还原:值为 •••• 的行,用原文件同键行替换(密钥不经网络往返);
    # 键 = m.group(1)(行首缩进[+export]+键名+分隔符),精确匹配。
    orig = {}
    for ln in old.split("\n"):
        m = pattern.match(ln)
        if m:
            orig[m.group(1)] = ln
    restored = []
    for ln in content.split("\n"):
        m = pattern.match(ln)
        if m and _is_masked_value(ln):
            if m.group(1) not in orig:
                # 键名在原文件里不存在(改了键名/新增了一行掩码占位)——
                # 绝不能把字面 •••• 静默写进文件,fail-closed 拒绝整次保存。
                raise NotAllowedError(f"掩码行找不到原键,无法还原: {m.group(1).strip()}")
            restored.append(orig[m.group(1)])
        else:
            restored.append(ln)
    return "\n".join(restored)


_MODEL_SECTION_KEY = re.compile(r"^model:\s*$")
_TOP_LEVEL_KEY = re.compile(r"^\S")   # 无缩进的行 = 下一个顶级键,model 节到此结束
_MODEL_FIELD = re.compile(r"^\s+(provider|default)\s*:\s*(.+?)\s*$")


def _parse_model_section(text: str) -> tuple[str | None, str | None]:
    """逐行正则提取顶级 model: 节内的 provider/default 标量。
    绝不解析/返回 api_key 或 base_url。遇到下一个顶级键(无缩进行)即停止。"""
    provider = default_model = None
    in_model = False
    for ln in text.split("\n"):
        if not in_model:
            if _MODEL_SECTION_KEY.match(ln):
                in_model = True
            continue
        if _TOP_LEVEL_KEY.match(ln):
            break   # 下一个顶级键,model 节结束
        m = _MODEL_FIELD.match(ln)
        if m:
            key, val = m.group(1), m.group(2).strip().strip("'\"")
            if key == "provider":
                provider = val
            elif key == "default":
                default_model = val
    return provider, default_model


def model_summary() -> list[dict]:
    """三网关主模型只读摘要。独立只读路径,不经写白名单(root config.yaml 仍不可写)。

    fail-soft:文件不存在/无 model 节/读失败 → provider/default_model 为 None,不抛。
    绝不解析/返回 api_key 或 base_url。
    """
    targets = [
        ("default", _home() / "config.yaml"),
        ("scribe3", _home() / "profiles" / "scribe3" / "config.yaml"),
        ("scribe3_write", _home() / "profiles" / "scribe3_write" / "config.yaml"),
    ]
    out = []
    for gateway, path in targets:
        provider = default_model = None
        try:
            if path.exists():
                provider, default_model = _parse_model_section(path.read_text(encoding="utf-8"))
        except OSError:
            pass
        out.append({"gateway": gateway, "provider": provider, "default_model": default_model})
    return out


def list_files() -> list[dict]:
    out = []
    for prof in _PROFILES:
        for name in _NAMES:
            fid = f"{prof}/{name}"
            try:
                p = _resolve(fid)
                if p.exists():
                    raw = p.read_text(encoding="utf-8")
                    pat = _mask_pattern(name)
                    shown = _mask(raw, pat) if pat else raw
                    out.append({"id": fid, "path": str(p), "exists": True,
                                "content": shown, "sha256": _sha(raw)})
                else:
                    out.append({"id": fid, "path": str(p), "exists": False,
                                "content": "", "sha256": _sha("")})
            except (NotAllowedError, OSError) as e:
                # 单文件容错:symlink 越界/权限/IO 错只降级该条目,不 500 整个列表
                out.append({"id": fid, "path": str(_home() / "profiles" / prof / name),
                            "exists": False, "content": "", "sha256": _sha(""),
                            "error": str(e)})
    return out


def write_file(file_id: str, content: str, *, base_sha256: str) -> dict:
    p = _resolve(file_id)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    if _sha(old) != base_sha256:
        raise StaleFileError("文件已被外部修改,请重新加载后再编辑")
    pat = _mask_pattern(file_id.split("/")[1])
    if pat:
        content = _restore_masked(old, content, pat)
    if p.exists():
        ts = time.strftime("%Y%m%d%H%M%S") + f"{int(time.time() * 1000) % 1000:03d}"
        bak = p.with_name(f"{p.name}.bak.{ts}")
        bak.write_text(old, encoding="utf-8")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"id": file_id, "sha256": _sha(content)}
