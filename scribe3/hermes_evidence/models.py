from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

SourceKind = Literal["website", "release", "main", "runtime"]
FILTER_POLICY_VERSION = "1"

_SENSITIVE_LABELS = frozenset(
    {
        "access token",
        "api key",
        "authorization",
        "client secret",
        "cookie",
        "credential",
        "password",
        "proxy authorization",
        "secret",
        "set cookie",
        "token",
        "x api key",
        "x auth token",
    }
)
_AUTHORIZATION_LABELS = frozenset({"authorization", "proxy authorization"})
_COOKIE_LABELS = frozenset({"cookie", "set cookie"})
_SECRET_SHAPED_VALUE_PATTERN = re.compile(r"(?i)\bsk-[a-z0-9_-]{8,}")
_SENSITIVE_LABEL_OCCURRENCE_PATTERN = re.compile(
    r'''(?ix)
    (?<![a-z0-9_-])
    (?P<quote>["']?)
    (?P<label>
        proxy[\s_-]+authorization
        | access[\s_-]+token
        | client[\s_-]+secret
        | set[\s_-]+cookie
        | x[\s_-]+api[\s_-]+key
        | x[\s_-]+auth[\s_-]+token
        | api[\s_-]+key
        | authorization
        | credential
        | password
        | secret
        | token
        | cookie
    )
    (?P=quote)
    (?![a-z0-9_-])
    \s*[:=]\s*
    (?P<value>[^\r\n;]+)
    '''
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _normalize_label(value: str) -> str:
    label = value.strip().lstrip("{[(").strip().strip("\"'")
    return re.sub(r"[\s_-]+", " ", label.lower()).strip()


def _is_sensitive_label(value: str) -> bool:
    return _normalize_label(value) in _SENSITIVE_LABELS


def _is_placeholder(value: str) -> bool:
    candidate = value.strip().rstrip(".,;").strip("\"'").rstrip(".,;")
    return bool(
        re.fullmatch(r"\$\{[A-Z_][A-Z0-9_]*\}", candidate)
        or re.fullmatch(r"\$[A-Z_][A-Z0-9_]*", candidate)
        or re.fullmatch(r"YOUR_[A-Z0-9_]+", candidate)
        or candidate.lower() in {"[redacted]", "<redacted>"}
    )


def _has_actual_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not _is_placeholder(value)
    return True


def _authorization_has_actual_credential(value: str) -> bool:
    parts = value.strip().split(maxsplit=1)
    return len(parts) == 2 and _has_actual_value(parts[1])


def _cookie_has_actual_value(label: str, value: str) -> bool:
    pairs = value.split(";")
    if label == "set cookie":
        pairs = pairs[:1]
    for pair in pairs:
        candidate = pair.split("=", maxsplit=1)[-1].strip()
        if _has_actual_value(candidate):
            return True
    return False


def _line_contains_sensitive_value(line: str) -> bool:
    for match in _SENSITIVE_LABEL_OCCURRENCE_PATTERN.finditer(line):
        label = _normalize_label(match["label"])
        value = match["value"].strip()
        if label in _AUTHORIZATION_LABELS:
            if _authorization_has_actual_credential(value):
                return True
            continue
        if label in _COOKIE_LABELS:
            if _cookie_has_actual_value(label, value):
                return True
            continue
        if label in _SENSITIVE_LABELS and _has_actual_value(value):
            return True
    return False


def contains_sensitive_data(value: object) -> bool:
    """Return whether a manifest value appears to contain credentials or secrets."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_label(key) and _has_actual_value(item):
                return True
            if contains_sensitive_data(item):
                return True
        return False
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(contains_sensitive_data(item) for item in value)
    if not isinstance(value, str):
        return False

    try:
        parsed = urlsplit(value)
    except (UnicodeError, ValueError):
        parsed = None
    if parsed is not None and parsed.query and any(
        _is_sensitive_label(key) for key, _ in parse_qsl(parsed.query)
    ):
        return True
    return bool(
        _SECRET_SHAPED_VALUE_PATTERN.search(value)
        or any(_line_contains_sensitive_value(line) for line in value.splitlines())
    )


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    source_kind: SourceKind
    output_path: str
    content_sha256: str
    byte_length: int
    text_length: int
    semantic_status: str
    requested_url: str | None = None
    final_url: str | None = None
    repo_path: str | None = None
    language: str = "en"
    category: str = "core"
    mime_type: str = "text/markdown"
    http_status: int | None = None
    title: str | None = None
    h1: str | None = None
    source_commit: str | None = None
    website_snapshot_id: str | None = None
    is_skill: bool = False
    is_runtime_contract: bool = False
    excluded_reason: str | None = None
    error: str | None = None
    supersedes_document_id: str | None = None
    logical_key: str = ""
    source_blob_sha: str | None = None
    extracted_text_path: str | None = None
    extracted_text_sha256: str | None = None


@dataclass
class SnapshotManifest:
    snapshot_id: str
    source_kind: SourceKind
    source_origin: str
    requested_ref: str
    resolved_sha: str | None
    release_tag: str | None
    fetched_at: str
    crawler_version: str
    documents: list[DocumentRecord] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)
    previous_snapshot_id: str | None = None
    notes: list[str] = field(default_factory=list)
    discovery_sha256: str | None = None
    expected_document_count: int | None = None
    tree_truncated: bool | None = None
    filter_policy_version: str = FILTER_POLICY_VERSION
    retry_events: list[dict] = field(default_factory=list)

    def payload(self) -> dict:
        data = asdict(self)
        data["document_count"] = len(self.documents)
        data["total_bytes"] = sum(document.byte_length for document in self.documents)
        data["success_count"] = len(
            [document for document in self.documents if not document.error]
        )
        data["failed_count"] = len(self.failures)
        data["excluded_count"] = len(self.exclusions)
        data["completeness_status"] = "pass" if not self.failures else "fail"
        return data


@dataclass(frozen=True)
class IntegrityReport:
    snapshot_id: str
    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    duplicate_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    name: str
    category: str
    official_evidence_refs: tuple[str, ...]
    documented_in_release: bool
    documented_in_main: bool
    runtime_advertised: bool | None
    runtime_probed: bool | None
    current_scribe_config_refs: tuple[str, ...]
    current_scribe_consumer_refs: tuple[str, ...]
    current_state: str
    first_principle_contribution: str
    authority_risk: str
    quality_hypothesis: str
    decision: str
    verification_plan: str
    rollback_boundary: str
    evidence_confidence: str


def write_manifest(path: Path, manifest: SnapshotManifest) -> str:
    payload = manifest.payload()
    if contains_sensitive_data(payload):
        raise ValueError("Manifest contains sensitive data and cannot be persisted")

    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(stable_json_bytes(payload))
    payload["manifest_sha256"] = digest
    path.write_bytes(stable_json_bytes(payload))
    return digest


def document_id_for(source_kind: str, logical_key: str, content_sha256: str) -> str:
    identity = sha256_bytes(logical_key.encode("utf-8"))[:16]
    return f"{source_kind}:{identity}:{content_sha256[:16]}"
