"""信贷 API 响应契约模型（pydantic v2）。

用途：验证接口返回的字段名 / 类型 / 必填项符合约定。
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator


class _BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterResponse(_BaseSchema):
    """POST /api/v1/register 成功响应。"""
    customer_id: int


class EligibilityResponse(_BaseSchema):
    """POST /api/v1/check-eligibility 响应（成功/拒绝均适用）。"""
    eligible: bool
    max_amount: Optional[int] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def check_consistency(self):
        if self.eligible and self.max_amount is None:
            raise ValueError("eligible=True 时必须返回 max_amount")
        if not self.eligible and self.reason is None:
            raise ValueError("eligible=False 时必须返回 reason")
        return self


class LoanCreateResponse(_BaseSchema):
    """POST /api/v1/loan 成功响应。"""
    loan_id: int
    status: str
    principal: int
    interest_rate: float
    total_amount: int


class LoanDetailResponse(_BaseSchema):
    """GET /api/v1/view-loan/{id} 成功响应。"""
    loan_id: int
    customer_id: int
    amount: int
    principal: int
    interest_rate: float
    paid_interest: int
    status: str


class LoanTransitionResponse(_BaseSchema):
    """POST /api/v1/loan/{id}/{action} 成功响应。"""
    loan_id: int
    from_status: str
    status: str


class ResetDbResponse(_BaseSchema):
    """POST /api/v1/_reset_db 成功响应。"""
    msg: str


class ErrorResponse(_BaseSchema):
    """通用错误响应（4xx / 5xx）。"""
    error: str
    missing: Optional[list] = None
    detail: Optional[str] = None


class StateTransitionErrorResponse(_BaseSchema):
    """409 非法状态流转响应。"""
    error: str
    current_status: str
    target_status: str