from __future__ import annotations

from .models import SnapshotManifest
from .integrity import _manifest_layer_errors


def _content_by_logical_key(manifest: SnapshotManifest) -> dict[str, str]:
    content: dict[str, str] = {}
    for document in manifest.documents:
        if document.source_kind != manifest.source_kind:
            raise ValueError("document source kind conflicts with manifest")
        logical_key = document.logical_key or document.document_id
        if logical_key in content:
            raise ValueError("duplicate logical key")
        content[logical_key] = document.content_sha256
    return content


def diff_manifests(
    old: SnapshotManifest, new: SnapshotManifest
) -> dict[str, list[str]]:
    if old.source_kind != new.source_kind:
        raise ValueError("cannot diff manifests from different source kinds")
    if _manifest_layer_errors(old) or _manifest_layer_errors(new):
        raise ValueError("manifest source identity is invalid")
    before = _content_by_logical_key(old)
    after = _content_by_logical_key(new)
    return {
        "added": sorted(set(after) - set(before)),
        "changed": sorted(
            key
            for key in set(before) & set(after)
            if before[key] != after[key]
        ),
        "removed": sorted(set(before) - set(after)),
    }
