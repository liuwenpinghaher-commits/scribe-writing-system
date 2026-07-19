from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from .models import contains_sensitive_data

OFFICIAL_WEBSITE_HOST = "hermes-agent.nousresearch.com"
OFFICIAL_GITHUB_ORGANIZATION = "NousResearch"
OFFICIAL_GITHUB_REPOSITORY = "hermes-agent"
DOC_EXTENSIONS = frozenset({".md", ".mdx", ".rst", ".adoc", ".pdf"})
_BLOCKED_REPOSITORY_PARTS = frozenset({"node_modules", "venv", ".git", "dist", "build"})
_MAX_PATH_DECODE_PASSES = 8


def _has_path_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _is_github_repository_path(path: str, prefix: str) -> bool:
    repository_path = f"{prefix}/{OFFICIAL_GITHUB_ORGANIZATION}/{OFFICIAL_GITHUB_REPOSITORY}"
    return _has_path_prefix(path, repository_path)


def _decoded_path_is_safe(path: str) -> bool:
    decoded = path
    for _ in range(_MAX_PATH_DECODE_PASSES):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    else:
        return False

    if (
        decoded.count("/") != path.count("/")
        or "\\" in decoded
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded)
    ):
        return False
    return all(segment not in {".", ".."} for segment in decoded.split("/"))


def is_official_url(url: str) -> bool:
    """Return whether *url* is a permitted official Hermes evidence location."""
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        return False
    try:
        parsed = urlparse(url)
        has_explicit_port = parsed.port is not None
    except ValueError:
        return False
    if (
        parsed.scheme != "https"
        or has_explicit_port
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or contains_sensitive_data(url)
        or not _decoded_path_is_safe(parsed.path)
    ):
        return False

    if parsed.hostname == OFFICIAL_WEBSITE_HOST:
        return _has_path_prefix(parsed.path, "/docs")
    if parsed.hostname == "github.com":
        return _is_github_repository_path(parsed.path, "")
    if parsed.hostname == "api.github.com":
        return _is_github_repository_path(parsed.path, "/repos")
    if parsed.hostname == "raw.githubusercontent.com":
        return _is_github_repository_path(parsed.path, "")
    return False


def contains_secret(text: str) -> bool:
    """Use the manifest's fail-closed sensitive-data policy for source text."""
    return contains_sensitive_data(text)


def select_repo_document(path: str) -> bool:
    """Select readable documentation while excluding generated/dependency trees."""
    candidate = PurePosixPath(path)
    if not path or candidate.is_absolute() or ".." in candidate.parts:
        return False
    if candidate.suffix.lower() not in DOC_EXTENSIONS:
        return False
    return not any(part in _BLOCKED_REPOSITORY_PARTS for part in candidate.parts)


def classify_repo_path(path: str) -> tuple[str, str, bool, bool]:
    """Return language, category, skill flag, and runtime-contract flag for a path."""
    language = "zh-Hans" if "/i18n/zh-Hans/" in f"/{path}" or path.endswith(".zh-CN.md") else "en"
    if path.startswith("optional-skills/"):
        return language, "optional-skill", True, False
    if path.startswith("skills/"):
        return language, "bundled-skill", True, False
    if path.startswith(("website/docs/", "docs/")):
        return language, "core-doc", False, True
    if path.startswith("plugins/"):
        return language, "plugin-doc", False, True
    return language, "project-doc", False, False
