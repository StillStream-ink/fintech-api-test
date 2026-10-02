"""兼容层：保留旧的导入路径。

新代码请使用：
    from api.credit_api import CreditAPI

旧代码（conftest.py、tests/*.py）继续可用：
    from credit_api import CreditAPI
"""
from api.credit_api import CreditAPI  # noqa: F401

__all__ = ["CreditAPI"]
