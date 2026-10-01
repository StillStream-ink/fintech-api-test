"""基础冒烟 + 安全已知缺陷测试。

职责边界：
- 边界参数化  → test_boundary.py
- 响应契约    → test_contract.py
- DB 双检     → test_db_consistency.py
- 状态机      → test_loan_state_machine.py
"""
import allure
import pytest

pytestmark = [pytest.mark.api, pytest.mark.credit]


@allure.feature("信贷API基础冒烟")
class TestCreditSmoke:
    """每个接口一次正常调用，确保主流程可跑通。"""

    @allure.story("用户注册")
    @allure.title("TC_SMOKE_001 注册成功返回 customer_id")
    def test_register(self, api_client):
        with allure.step("准备注册请求数据"):
            payload = {"name": "张三", "age": 22, "income": 8000, "credit_score": 700}

        with allure.step("发送注册请求"):
            res = api_client.register(payload)

        with allure.step("校验 HTTP 状态码为 201"):
            assert res.status_code == 201, f"实际 {res.status_code}：{res.text}"

        with allure.step("校验响应体包含合法 customer_id"):
            data = res.json()
            assert isinstance(data["customer_id"], int), f"实际 {data}"

    @allure.story("创建贷款-正常")
    @allure.title("TC_SMOKE_002 创建贷款成功返回 PENDING")
    def test_create_loan_normal(self, api_client, sample_customer):
        with allure.step(f"准备请求数据（customer_id={sample_customer}）"):
            payload = {"customer_id": sample_customer, "amount": 50000}

        with allure.step("发送创建贷款请求"):
            res = api_client.create_loan(payload)

        with allure.step("校验 HTTP 状态码为 201"):
            assert res.status_code == 201, f"实际 {res.status_code}：{res.text}"

        with allure.step("校验响应 loan_id 为整数且状态为 PENDING"):
            data = res.json()
            assert isinstance(data["loan_id"], int)
            assert data["status"] == "PENDING"

    @allure.story("查询贷款-存在")
    @allure.title("TC_SMOKE_003 查询存在的贷款返回完整信息")
    def test_view_loan_exist(self, api_client, sample_loan):
        with allure.step(f"发送查询请求（loan_id={sample_loan}）"):
            res = api_client.view_loan(sample_loan)

        with allure.step("校验 HTTP 状态码为 200"):
            assert res.status_code == 200, f"实际 {res.status_code}"

        with allure.step("校验返回的 loan_id 与请求一致"):
            assert res.json()["loan_id"] == sample_loan

    @allure.story("查询贷款-不存在")
    @allure.title("TC_SMOKE_004 查询不存在的贷款返回 404")
    def test_view_loan_not_exist(self, api_client):
        with allure.step("发送查询请求（loan_id=99999）"):
            res = api_client.view_loan(99999)

        with allure.step("校验 HTTP 状态码为 404"):
            assert res.status_code == 404

        with allure.step("校验错误信息为「贷款不存在」"):
            assert res.json()["error"] == "贷款不存在"


@allure.feature("安全-已知缺陷（xfail strict）")
class TestSecurityKnownBugs:
    """已知安全 BUG 的回归测试。

    设计要点：
    1. 用真实存在的 loan_id，确保失败原因是"缺少鉴权"而非"资源不存在"
    2. xfail(strict=True)：BUG 修复后测试会变成 FAILED，
       强制开发者移除 xfail 标记，而不是让修复被静默吞掉
    """

    @pytest.mark.xfail(
        strict=True,
        reason="BUG-005：缺少权限控制，存在水平越权漏洞，待迭代修复",
    )
    @allure.story("安全-水平越权访问")
    @allure.title("TC_SEC_001 客户不应能查看其他客户的贷款")
    def test_loan_horizontal_privilege(self, api_client, sample_customer):
        with allure.step("准备阶段：造一笔真实存在的贷款"):
            loan_id = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 50000,
            }).json()["loan_id"]

        with allure.step(f"以「另一个客户」身份访问 loan_id={loan_id}"):
            res = api_client.view_loan(loan_id)

        with allure.step("期望被拒绝（401 或 403）"):
            assert res.status_code in (401, 403), (
                f"跨客户访问应被拒绝，实际 {res.status_code}：{res.json()}"
            )

    @pytest.mark.xfail(
        strict=True,
        reason="BUG-006：无 token 鉴权，未授权可以直接访问接口，待迭代修复",
    )
    @allure.story("安全-未授权访问")
    @allure.title("TC_SEC_002 无身份凭证不应能访问贷款接口")
    def test_loan_unauthorized(self, api_client, sample_loan):
        with allure.step(f"不携带任何凭证，直接访问 loan_id={sample_loan}"):
            res = api_client.view_loan(sample_loan)

        with allure.step("期望返回 401"):
            assert res.status_code == 401, (
                f"未授权访问应返回 401，实际 {res.status_code}：{res.json()}"
            )