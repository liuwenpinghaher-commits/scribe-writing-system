"""Playbook errors. No I/O."""


class FrozenAssetError(Exception):
    """Attempted in-place mutation of a frozen Play/Contract/Deduction/Draft."""


class StructFail(Exception):
    """Pure-function structural gate rejected the artifact."""

    def __init__(self, code: str, message: str, *, field: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field

    def as_dict(self) -> dict:
        out = {"ok": False, "code": self.code, "message": self.message}
        if self.field:
            out["field"] = self.field
        return out


class StageGone(Exception):
    """Old stage name retired (HTTP 410)."""

    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message

    def as_dict(self) -> dict:
        return {
            "ok": False,
            "http": 410,
            "code": "stage_gone",
            "stage": self.stage,
            "message": self.message,
        }
