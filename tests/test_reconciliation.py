"""金融对账测试。

验证多表关联下的金额一致性：
- 借款金额 = 本金 + 利息
- 还款流水总额 = 已还金额
- 流水拆分（本金 + 利息）= 还款总额
"""
import allure
import pytest

from tests.db_helper import (
    count_repayment_flows,
    get_loan,
    get_repayment_flows,
)


@allure.feature("金融对账")
class TestReconciliation:

    @allure.story("借款金额拆分")
    @allure.title("TC_RECON_001 借款金额 = 本金 + 利息")
    def test_loan_amount_equals_principal_plus_interest(self, api_client, sample_customer):
        with allure.step("创建借款"):
            resp = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 10000,
            })
            assert resp.status_code == 201
            loan_id = resp.json()["loan_id"]

        with allure.step("从 DB 读取贷款"):
            loan = get_loan(loan_id)

        with allure.step("校验：金额 = 本金 + (金额 - 本金)"):
            expected_interest = loan["amount"] - loan["principal"]
            assert loan["principal"] == 10000, f"本金应为 10000，实际 {loan['principal']}"
            assert loan["amount"] == loan["principal"] + expected_interest

    @allure.story("借款金额拆分")
    @allure.title("TC_RECON_002 利率按信用分区间匹配")
    @pytest.mark.parametrize("credit_score, expected_rate", [
        (850, 0.02),
        (700, 0.035),
        (600, 0.05),
    ])
    def test_interest_rate_by_credit_score(self, api_client, credit_score, expected_rate):
        with allure.step(f"注册信用分 {credit_score} 的客户"):
            cust_id = api_client.register({
                "name": "利率测试",
                "age": 30,
                "income": 10000,
                "credit_score": credit_score,
            }).json()["customer_id"]

        with allure.step("创建借款"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 10000})
            assert resp.status_code == 201

        with allure.step(f"校验利率 == {expected_rate}"):
            loan = get_loan(resp.json()["loan_id"])
            assert loan["interest_rate"] == expected_rate, \
                f"信用分 {credit_score} 应为 {expected_rate}，实际 {loan['interest_rate']}"

    @allure.story("还款流水")
    @allure.title("TC_RECON_003 还款流水总额 = 贷款金额")
    def test_repayment_flow_total_equals_loan_amount(self, api_client, sample_loan):
        with allure.step("走完生命周期到还款"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)
            resp = api_client.repay_loan(sample_loan)
            assert resp.status_code == 200

        with allure.step("从 DB 读取流水"):
            flows = get_repayment_flows(sample_loan)
            loan = get_loan(sample_loan)

        with allure.step("校验：流水总额 = 贷款金额"):
            assert len(flows) == 1, f"应有 1 条流水，实际 {len(flows)}"
            total_flow = sum(f["amount"] for f in flows)
            assert total_flow == loan["amount"], \
                f"流水总额 {total_flow} != 贷款金额 {loan['amount']}"

    @allure.story("还款流水")
    @allure.title("TC_RECON_004 流水拆分（本金 + 利息）= 还款总额")
    def test_repayment_flow_split(self, api_client, sample_loan):
        with allure.step("走完生命周期"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)
            api_client.repay_loan(sample_loan)

        with allure.step("校验流水拆分"):
            flows = get_repayment_flows(sample_loan)
            for f in flows:
                assert f["principal_part"] + f["interest_part"] == f["amount"], \
                    f"流水 {f['id']} 拆分不一致"

    @allure.story("状态审计")
    @allure.title("TC_RECON_005 状态流转后 paid_interest 同步更新")
    def test_paid_interest_updates_after_repay(self, api_client, sample_loan):
        with allure.step("还款前 paid_interest = 0"):
            assert get_loan(sample_loan)["paid_interest"] == 0

        with allure.step("走完生命周期"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)
            api_client.repay_loan(sample_loan)

        with allure.step("还款后 paid_interest = 利息总额"):
            loan = get_loan(sample_loan)
            expected_interest = loan["amount"] - loan["principal"]
            assert loan["paid_interest"] == expected_interest

    @allure.story("孤儿记录")
    @allure.title("TC_RECON_006 每条流水都有对应的贷款")
    def test_no_orphan_flows(self, api_client, sample_loan):
        with allure.step("走完生命周期生成流水"):
            api_client.approve_loan(sample_loan)
            api_client.disburse_loan(sample_loan)
            api_client.repay_loan(sample_loan)

        with allure.step("校验流水对应的贷款存在"):
            flows = get_repayment_flows(sample_loan)
            for f in flows:
                assert get_loan(f["loan_id"]) is not None, \
                    f"流水 {f['id']} 是孤儿记录"