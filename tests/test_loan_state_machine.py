"""贷款状态机全流程测试。"""
import allure
import pytest

from tests.db_helper import get_loan

pytestmark = [pytest.mark.api, pytest.mark.credit, pytest.mark.loan]


@allure.feature("贷款状态机")
class TestLoanStateMachine:

    # ==================== 正常流程 ====================

    @allure.story("正常流程")
    @allure.title("TC_STM_001 贷款申请后应处于 PENDING 状态")
    def test_initial_state_is_pending(self, api_client, sample_loan):
        with allure.step(f"查询贷款 loan_id={sample_loan}"):
            resp = api_client.view_loan(sample_loan)

        with allure.step("校验状态为 PENDING"):
            assert resp.status_code == 200
            assert resp.json()["status"] == "PENDING"

    @allure.story("正常流程")
    @allure.title("TC_STM_002 审批通过后状态变为 APPROVED")
    def test_approve_transitions_to_approved(self, api_client, sample_loan):
        with allure.step("调用审批通过接口"):
            resp = api_client.approve_loan(sample_loan)

        with allure.step("校验接口返回的状态流转信息"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["from_status"] == "PENDING"
            assert data["status"] == "APPROVED"

        with allure.step("校验数据库中状态已同步为 APPROVED"):
            assert get_loan(sample_loan)["status"] == "APPROVED"

    @allure.story("正常流程")
    @allure.title("TC_STM_003 放款后状态变为 DISBURSED")
    def test_disburse_transitions_to_disbursed(self, api_client, sample_loan):
        with allure.step("前置：审批通过"):
            api_client.approve_loan(sample_loan)

        with allure.step("调用放款接口"):
            resp = api_client.disburse_loan(sample_loan)

        with allure.step("校验接口返回的状态流转"):
            assert resp.status_code == 200
            assert resp.json()["from_status"] == "APPROVED"
            assert resp.json()["status"] == "DISBURSED"

        with allure.step("校验数据库中状态为 DISBURSED"):
            assert get_loan(sample_loan)["status"] == "DISBURSED"

    @allure.story("正常流程")
    @allure.title("TC_STM_004 还款后状态变为 SETTLED")
    def test_repay_transitions_to_settled(self, api_client, sample_loan):
        with allure.step("前置：审批 + 放款"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)

        with allure.step("调用还款接口"):
            resp = api_client.repay_loan(sample_loan)

        with allure.step("校验状态流转为 SETTLED"):
            assert resp.status_code == 200
            assert resp.json()["from_status"] == "DISBURSED"
            assert resp.json()["status"] == "SETTLED"

    @allure.story("正常流程")
    @allure.title("TC_STM_005 完整生命周期")
    def test_full_lifecycle(self, api_client, sample_loan):
        with allure.step("初始状态应为 PENDING"):
            assert api_client.view_loan(sample_loan).json()["status"] == "PENDING"

        with allure.step("审批通过 → APPROVED"):
            api_client.approve_loan(sample_loan)
            assert api_client.view_loan(sample_loan).json()["status"] == "APPROVED"

        with allure.step("放款 → DISBURSED"):
            api_client.disburse_loan(sample_loan)
            assert api_client.view_loan(sample_loan).json()["status"] == "DISBURSED"

        with allure.step("还款 → SETTLED"):
            api_client.repay_loan(sample_loan)
            assert api_client.view_loan(sample_loan).json()["status"] == "SETTLED"

    @allure.story("正常流程")
    @allure.title("TC_STM_006 拒绝后状态变为 REJECTED")
    def test_reject_transitions_to_rejected(self, api_client, sample_loan):
        with allure.step("调用拒绝接口"):
            resp = api_client.reject_loan(sample_loan)

        with allure.step("校验状态流转为 REJECTED"):
            assert resp.status_code == 200
            assert resp.json()["from_status"] == "PENDING"
            assert resp.json()["status"] == "REJECTED"

    # ==================== 非法流转 ====================

    @allure.story("非法流转")
    @allure.title("TC_STM_101 PENDING 不能直接 DISBURSED")
    def test_pending_cannot_disburse(self, api_client, sample_loan):
        with allure.step("PENDING 状态直接调用放款"):
            resp = api_client.disburse_loan(sample_loan)

        with allure.step("期望返回 409 且提示非法状态流转"):
            assert resp.status_code == 409
            assert "非法状态流转" in resp.json()["error"]

    @allure.story("非法流转")
    @allure.title("TC_STM_102 PENDING 不能直接 SETTLED")
    def test_pending_cannot_settle(self, api_client, sample_loan):
        with allure.step("PENDING 状态直接调用还款"):
            resp = api_client.repay_loan(sample_loan)

        with allure.step("期望返回 409"):
            assert resp.status_code == 409

    @allure.story("非法流转")
    @allure.title("TC_STM_103 APPROVED 不能回退 REJECTED")
    def test_approved_cannot_reject(self, api_client, sample_loan):
        with allure.step("前置：审批通过"):
            api_client.approve_loan(sample_loan)

        with allure.step("尝试回退为 REJECTED"):
            resp = api_client.reject_loan(sample_loan)

        with allure.step("期望返回 409"):
            assert resp.status_code == 409

    @allure.story("非法流转")
    @allure.title("TC_STM_104 APPROVED 不能重复 APPROVED")
    def test_approved_cannot_reapprove(self, api_client, sample_loan):
        with allure.step("第一次审批通过"):
            api_client.approve_loan(sample_loan)

        with allure.step("第二次重复审批"):
            resp = api_client.approve_loan(sample_loan)

        with allure.step("期望返回 409（幂等拒绝）"):
            assert resp.status_code == 409

    @allure.story("非法流转")
    @allure.title("TC_STM_105 REJECTED 是终态")
    def test_rejected_is_terminal(self, api_client, sample_loan):
        with allure.step("前置：拒绝该贷款"):
            api_client.reject_loan(sample_loan)

        with allure.step("尝试所有后续流转操作，全部应被拒绝"):
            assert api_client.approve_loan(sample_loan).status_code == 409
            assert api_client.disburse_loan(sample_loan).status_code == 409
            assert api_client.repay_loan(sample_loan).status_code == 409

    @allure.story("非法流转")
    @allure.title("TC_STM_106 SETTLED 是终态")
    def test_settled_is_terminal(self, api_client, sample_loan):
        with allure.step("前置：走完完整生命周期到 SETTLED"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)
            api_client.repay_loan(sample_loan)

        with allure.step("尝试所有后续流转操作，全部应被拒绝"):
            assert api_client.approve_loan(sample_loan).status_code == 409
            assert api_client.disburse_loan(sample_loan).status_code == 409
            assert api_client.repay_loan(sample_loan).status_code == 409

    @allure.story("非法流转")
    @allure.title("TC_STM_107 DISBURSED 不能回退 APPROVED")
    def test_disbursed_cannot_go_back(self, api_client, sample_loan):
        with allure.step("前置：审批 + 放款"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)

        with allure.step("尝试回退到 APPROVED"):
            resp = api_client.approve_loan(sample_loan)

        with allure.step("期望返回 409"):
            assert resp.status_code == 409

    # ==================== 异常场景 ====================

    @allure.story("异常场景")
    @allure.title("TC_STM_201 不存在的贷款应 404")
    def test_nonexistent_loan(self, api_client):
        with allure.step("对不存在的 loan_id=99999 执行所有流转操作"):
            resp_approve = api_client.approve_loan(99999)
            resp_reject = api_client.reject_loan(99999)
            resp_disburse = api_client.disburse_loan(99999)
            resp_repay = api_client.repay_loan(99999)

        with allure.step("全部应返回 404"):
            assert resp_approve.status_code == 404
            assert resp_reject.status_code == 404
            assert resp_disburse.status_code == 404
            assert resp_repay.status_code == 404

    # ==================== DB 一致性 ====================

    @allure.story("DB 一致性")
    @allure.title("TC_STM_202 状态流转后 DB 应同步")
    def test_state_syncs_to_db(self, api_client, sample_loan):
        with allure.step("审批 → 校验 DB 为 APPROVED"):
            api_client.approve_loan(sample_loan)
            assert get_loan(sample_loan)["status"] == "APPROVED"

        with allure.step("放款 → 校验 DB 为 DISBURSED"):
            api_client.disburse_loan(sample_loan)
            assert get_loan(sample_loan)["status"] == "DISBURSED"

        with allure.step("还款 → 校验 DB 为 SETTLED"):
            api_client.repay_loan(sample_loan)
            assert get_loan(sample_loan)["status"] == "SETTLED"

    # ==================== 隔离性 ====================

    @allure.story("隔离性")
    @allure.title("TC_STM_203 状态流转不影响其他贷款")
    def test_state_isolation(self, api_client, sample_customer):
        with allure.step("为同一客户创建两笔贷款"):
            r1 = api_client.create_loan({"customer_id": sample_customer, "amount": 10000})
            r2 = api_client.create_loan({"customer_id": sample_customer, "amount": 20000})
            loan1 = r1.json()["loan_id"]
            loan2 = r2.json()["loan_id"]

        with allure.step("只审批 loan1"):
            api_client.approve_loan(loan1)

        with allure.step("校验 loan1 为 APPROVED，loan2 保持 PENDING"):
            assert api_client.view_loan(loan1).json()["status"] == "APPROVED"
            assert api_client.view_loan(loan2).json()["status"] == "PENDING"