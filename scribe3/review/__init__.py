"""校验统一层：severity normalize、blocking 真源、review runner、L1、台账 D/L。"""
from scribe3.review.blocking import is_blocking_issue
from scribe3.review.fp import prose_fp
from scribe3.review.normalize import map_legacy_severity, normalize_issues
from scribe3.review.schema import CANONICAL_SEVERITIES, S1_BLOCKING_TYPES

__all__ = [
    "CANONICAL_SEVERITIES",
    "S1_BLOCKING_TYPES",
    "is_blocking_issue",
    "map_legacy_severity",
    "normalize_issues",
    "prose_fp",
]
