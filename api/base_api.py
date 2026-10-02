"""通用 HTTP 客户端基类。

职责：
- 管理 session / 超时 / 默认 headers
- 封装 _request，统一处理 URL 拼接、日志
- 提供 get / post 快捷方法
- 提供可覆盖的钩子（_before_request / _after_response）

子类只需要定义业务方法，不用关心 HTTP 细节。
"""
import logging

import requests

logger = logging.getLogger(__name__)


class BaseAPI:
    """所有业务 API 客户端的基类。"""

    def __init__(
        self,
        base_url,
        timeout=10,
        default_headers=None,
        enable_log=True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = default_headers or {"Content-Type": "application/json"}
        self.enable_log = enable_log

    # ==================== 扩展钩子 ====================

    def _before_request(self, method, url, kwargs):
        """请求前钩子，子类可覆盖。"""
        if self.enable_log:
            logger.debug("[REQ] %s %s payload=%s", method, url, kwargs.get("json"))

    def _after_response(self, method, url, response):
        """响应后钩子，子类可覆盖。"""
        if self.enable_log:
            logger.debug(
                "[RES] %s %s status=%s body=%s",
                method, url, response.status_code,
                response.text[:200] if response.text else "",
            )

    # ==================== 核心请求方法 ====================

    def _request(self, method, path, **kwargs):
        """统一请求入口。"""
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", None) or self.headers
        timeout = kwargs.pop("timeout", None) or self.timeout

        self._before_request(method, url, kwargs)

        response = self.session.request(
            method, url, headers=headers, timeout=timeout, **kwargs
        )

        self._after_response(method, url, response)
        return response

    # ==================== 快捷方法 ====================

    def get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)