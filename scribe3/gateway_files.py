# scribe3/gateway_files.py
"""Hermes profile 文件的白名单读写(设置中心网关区)。

安全边界:
- 白名单硬编码:profiles/{scribe3,scribe3_write}/{config.yaml,SOUL.md,.env},
  id 必须精确命中,resolve 后必须仍在 HERMES_HOME 下(双保险防穿越)。
- .env 读取时掩码含 KEY/TOKEN/PASS/SECRET 的行(value → ••••);保存时凡值为
  «••••» 的行按原文件还原(密钥永不经网络明文往返)。
- 写前自动备份 <file>.bak.<ts>;base_sha256 失配抛 StaleFileError(→409)。
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
_SECRET_LINE = re.compile(r"^(\s*[A-Za-z0-9_]*(?:KEY|TOKEN|PASS|SECRET)[A-Za-z0-9_]*\s*=).*$")


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


def _mask_env(text: str) -> str:
    return "\n".join(_SECRET_LINE.sub(rf"\g<1>{_MASK}", ln) for ln in text.split("\n"))


def list_files() -> list[dict]:
    out = []
    for prof in _PROFILES:
        for name in _NAMES:
            fid = f"{prof}/{name}"
            p = _resolve(fid)
            if p.exists():
                raw = p.read_text(encoding="utf-8")
                shown = _mask_env(raw) if name == ".env" else raw
                out.append({"id": fid, "path": str(p), "exists": True,
                            "content": shown, "sha256": _sha(raw)})
            else:
                out.append({"id": fid, "path": str(p), "exists": False,
                            "content": "", "sha256": _sha("")})
    return out


def write_file(file_id: str, content: str, *, base_sha256: str) -> dict:
    p = _resolve(file_id)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    if _sha(old) != base_sha256:
        raise StaleFileError("文件已被外部修改,请重新加载后再编辑")
    if file_id.endswith("/.env"):
        # 掩码行还原:值为 •••• 的行,用原文件同名行替换(密钥不经网络往返)
        orig = {}
        for ln in old.split("\n"):
            m = _SECRET_LINE.match(ln)
            if m:
                orig[m.group(1)] = ln
        restored = []
        for ln in content.split("\n"):
            m = _SECRET_LINE.match(ln)
            if m and ln.strip().endswith(_MASK) and m.group(1) in orig:
                restored.append(orig[m.group(1)])
            else:
                restored.append(ln)
        content = "\n".join(restored)
    if p.exists():
        bak = p.with_name(f"{p.name}.bak.{time.strftime('%Y%m%d%H%M%S')}")
        bak.write_text(old, encoding="utf-8")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"id": file_id, "sha256": _sha(content)}
