"""信贷 API 响应契约模型（pydantic v2）。

用途：验证接口返回的字段名 / 类型 / 必填项符合约定。
"""
from typing import Optional

from pydantic import BaseModel


class RegisterResponse(BaseModel):
    """POST /api/v1/register 成功响应。"""
    customer_id: int


class EligibilityResponse(BaseModel):
    """POST /api/v1/check-eligibility 响应（成功/拒绝均适用）。"""
    eligible: bool
    max_amount: Optional[int] = None
    reason: Optional[str] = None


class LoanCreateResponse(BaseModel):
    """POST /api/v1/loan 成功响应。"""
    loan_id: int
    status: str


class LoanDetailResponse(BaseModel):
    """GET /api/v1/view-loan/{id} 成功响应。"""
    loan_id: int
    customer_id: int
    amount: int
    status: str


class ErrorResponse(BaseModel):
    """通用错误响应（4xx / 5xx）。"""
    error: str
