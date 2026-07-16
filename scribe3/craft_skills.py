"""P1:通用写作技法库(引擎层,题材无关)——渐进披露。

定案 B(2026-07-16 实测):Hermes :8643 responses 路径不注入原生 skills(探针问"可用
skills",回复不含任何已装 skill 名)→ 索引进 instructions(每条一行)+ s3_skill_read
按需取全文。**定案后唯一路径,无运行时 A/B 降级**(作者零降级纪律)。

分层边界(craft 资产复核决策):这里只放**题材无关**的通用技法;本书专属规则走
craft_rule(DB + assembler),两层不混。技法文件 = scribe3/craft_skills/*.md,
首行 `# 名称`,次段 `> 一句话描述`(索引用),其余正文。
"""
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "craft_skills"


def list_skills() -> list[dict]:
    """索引:[{slug, name, desc}](按文件名序,稳定)。目录缺失=部署损坏,直接抛。"""
    out = []
    for f in sorted(_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        name = lines[0].lstrip("#").strip() if lines else f.stem
        desc = ""
        for ln in lines[1:5]:
            if ln.strip().startswith(">"):
                desc = ln.strip().lstrip(">").strip()
                break
        out.append({"slug": f.stem, "name": name, "desc": desc})
    return out


def read_skill(slug: str) -> str:
    """按 slug 取技法全文。未知/非法 slug 直接抛 ValueError(带可用清单,fail-loud)。"""
    s = (slug or "").strip()
    if not s or "/" in s or "\\" in s or ".." in s:
        raise ValueError(f"非法技法名 {slug!r}")
    p = _DIR / f"{s}.md"
    if not p.exists():
        known = "、".join(x["slug"] for x in list_skills())
        raise ValueError(f"未知技法 {slug!r}(可用:{known})")
    return p.read_text(encoding="utf-8")


def skills_index_block() -> str:
    """注入 instructions 的索引块(渐进披露:常驻只有这几行,全文靠工具取)。
    只应注入**带 s3_ 工具面的路径**——纯讨论无工具,写了调不到=对模型说谎(仓库纪律)。"""
    rows = list_skills()
    if not rows:
        return ""
    lines = ["\n\n## 写作技法库(渐进披露)",
             "讨论或写作触及下列技法时,先调 s3_skill_read(slug) 取全文再引用,不要凭印象复述:"]
    for s in rows:
        lines.append(f"- {s['slug']}:{s['desc']}")
    return "\n".join(lines)
