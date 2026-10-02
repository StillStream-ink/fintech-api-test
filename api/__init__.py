"""API 客户端分层包。

- base_api.py    通用 HTTP 客户端（session、超时、请求封装、日志）
- credit_api.py  信贷业务 API（继承 BaseAPI，只写业务方法）
"""
