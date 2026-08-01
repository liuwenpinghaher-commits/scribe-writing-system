"""scribe3 后端 API 入口。

物理拆分: 实现主体位于 ``scribe3/api/app_impl.py``。
本模块在导入时将自身替换为 app_impl,保证:

- ``import scribe3.app as A`` 与实现模块是同一对象
- 测试 ``monkeypatch.setattr(A, ...)`` 作用于真实 handler 闭包全局
- ``from scribe3.app import app`` 仍可用

存储层物理拆分见 ``scribe3/store/`` 包。
"""
from __future__ import annotations

import sys

from scribe3.api import app_impl as _impl

if __name__ == "__main__":
    # `python -m scribe3.app` 是公开的后端启动约定。模块别名本身不会触发
    # app_impl 的 `if __name__ == "__main__"`，因此必须显式委托入口。
    _impl.main()
else:
    # 关键模块身份 → 测试与生产共用同一 globals
    sys.modules[__name__] = _impl
