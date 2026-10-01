"""pydantic 契约校验。

目的：验证接口响应的字段名 / 类型 / 必填项符合约定。
比"只查 HTTP 200"强  能发现字段缺失、拼写错误、类型不符等隐性 bug。
"""
import allure
import pytest

from schemas.credit_schemas import (
    EligibilityResponse,
    ErrorResponse,
    LoanCreateResponse,
    LoanDetailResponse,
    RegisterResponse,
)

pytestmark = [pytest.mark.api, pytest.mark.credit]


@allure.feature("接口响应契约校验")
class TestContract:

    # ==================== 成功响应契约 ====================

    @allure.story("注册-契约")
    @allure.title("TC_CT_001 注册成功响应符合契约（customer_id: int）")
    def test_register_response_schema(self, api_client):
        with allure.step("准备注册请求数据"):
            payload = {"name": "张三", "age": 22, "income": 8000, "credit_score": 700}

        with allure.step("发送注册请求"):
            resp = api_client.register(payload)

        with allure.step("校验 HTTP 状态码为 201"):
            assert resp.status_code == 201

        with allure.step("校验响应符合 RegisterResponse 契约"):
            RegisterResponse(**resp.json())

    @allure.story("资格检查-契约")
    @allure.title("TC_CT_002 资格检查-通过：eligible=true + max_amount")
    def test_eligibility_pass_schema(self, api_client):
        with allure.step("发送资格检查请求（预期通过）"):
            resp = api_client.check_eligibility({
                "age": 22, "income": 8000, "credit_score": 700,
            })

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200

        with allure.step("校验响应符合 EligibilityResponse 契约"):
            data = EligibilityResponse(**resp.json())

        with allure.step("校验业务字段：eligible=True 且 max_amount=100000"):
            assert data.eligible is True
            assert data.max_amount == 100000

    @allure.story("资格检查-契约")
    @allure.title("TC_CT_003 资格检查-拒绝：eligible=false + reason")
    def test_eligibility_fail_schema(self, api_client):
        with allure.step("发送资格检查请求（年龄 17，预期拒绝）"):
            resp = api_client.check_eligibility({
                "age": 17, "income": 8000, "credit_score": 700,
            })

        with allure.step("校验 HTTP 状态码为 200（业务拒绝仍是 200）"):
            assert resp.status_code == 200

        with allure.step("校验响应符合 EligibilityResponse 契约"):
            data = EligibilityResponse(**resp.json())

        with allure.step("校验业务字段：eligible=False 且 reason 非空"):
            assert data.eligible is False
            assert data.reason is not None

    @allure.story("创建贷款-契约")
    @allure.title("TC_CT_004 创建贷款成功响应符合契约（loan_id + status）")
    def test_create_loan_response_schema(self, api_client, sample_customer):
        with allure.step(f"准备请求数据（customer_id={sample_customer}）"):
            payload = {"customer_id": sample_customer, "amount": 50000}

        with allure.step("发送创建贷款请求"):
            resp = api_client.create_loan(payload)

        with allure.step("校验 HTTP 状态码为 201"):
            assert resp.status_code == 201

        with allure.step("校验响应符合 LoanCreateResponse 契约"):
            data = LoanCreateResponse(**resp.json())

        with allure.step("校验初始状态为 PENDING"):
            assert data.status == "PENDING"

    @allure.story("查询贷款-契约")
    @allure.title("TC_CT_005 查询贷款成功响应包含全部字段")
    def test_view_loan_response_schema(self, api_client, sample_loan):
        with allure.step(f"发送查询请求（loan_id={sample_loan}）"):
            resp = api_client.view_loan(sample_loan)

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200

        with allure.step("校验响应符合 LoanDetailResponse 契约"):
            LoanDetailResponse(**resp.json())

    # ==================== 错误响应契约 ====================

    @allure.story("错误响应-契约")
    @allure.title("TC_CT_006 缺必填字段时响应含 error 字段")
    def test_register_error_schema(self, api_client):
        with allure.step("发送缺少 3 个必填字段的注册请求"):
            resp = api_client.register({"name": "张三"})

        with allure.step("校验 HTTP 状态码为 400"):
            assert resp.status_code == 400

        with allure.step("校验响应符合 ErrorResponse 契约"):
            ErrorResponse(**resp.json())

    @allure.story("错误响应-契约")
    @allure.title("TC_CT_007 查询不存在的贷款时响应含 error 字段")
    def test_view_loan_not_found_schema(self, api_client):
        with allure.step("发送查询请求（loan_id=99999，不存在）"):
            resp = api_client.view_loan(99999)

        with allure.step("校验 HTTP 状态码为 404"):
            assert resp.status_code == 404

        with allure.step("校验响应符合 ErrorResponse 契约"):
            ErrorResponse(**resp.json())

    @allure.story("错误响应-契约")
    @allure.title("TC_CT_008 创建贷款缺字段时响应含 error 字段")
    def test_create_loan_error_schema(self, api_client):
        with allure.step("发送缺少 customer_id 的创建请求"):
            resp = api_client.create_loan({"amount": 50000})

        with allure.step("校验 HTTP 状态码为 400"):
            assert resp.status_code == 400

        with allure.step("校验响应符合 ErrorResponse 契约"):
            ErrorResponse(**resp.json())