"""P3:跨书作者偏好——事实源 = Hermes USER.md(人级,天生跨书)。

注入路径唯一(零降级,不赌网关行为):scribe3 读文件拼进 _editor_system(主编全部面
——讨论/agentic/写作都基于它);hermes CLI/desktop 对同一文件原生可见可编辑。
2026-07-16 与 P1 同批探针实证::8643 responses 路径不注入 hermes 原生记忆,故自注入。

红线(捕获点限知红线延续):**偏好≠正典**——书内设定/人物/世界观/情节一律禁止入内;
写路径经 s3_author_pref_add(_RW,elicitation 待批)作者批准才落盘,拿不准就不写。
"""
import os
from pathlib import Path

_SECTION = "## scribe3 写作偏好(主编待批写入)"


def _user_md_path() -> Path:
    return (Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser() / "USER.md")


def author_prefs_block(cap: int = 1500) -> str:
    """注入块。文件不存在=合法初始态(返回空,非静默失败);
    文件存在但读取失败=直接抛(fail-loud:有偏好却没注入是静默失忆)。"""
    p = _user_md_path()
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    return ("\n\n## 作者跨书偏好(USER.md·人级;偏好≠正典,与本书设定冲突时以本书设定为准)\n"
            + text[:cap])


def append_pref(text: str) -> str:
    """待批批准后落盘:追加一条偏好到 USER.md 的 scribe3 小节(缺则建段)。
    只做形式校验(空/超长抛错);"是不是正典"由工具 docstring + 人批把关。"""
    t = " ".join((text or "").split())
    if not t:
        raise ValueError("偏好内容为空")
    if len(t) > 200:
        raise ValueError("单条偏好过长(≤200字)——偏好是风格倾向,不是设定文档")
    p = _user_md_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cur = p.read_text(encoding="utf-8") if p.exists() else ""
    if _SECTION not in cur:
        cur = (cur.rstrip() + f"\n\n{_SECTION}\n") if cur.strip() else f"{_SECTION}\n"
    cur = cur.rstrip() + f"\n- {t}\n"
    p.write_text(cur, encoding="utf-8")
    return t
