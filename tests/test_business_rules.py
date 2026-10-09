"""业务规则测试（风控 / 额度 / 利率 / 频率）。"""
import allure
import pytest

from tests.db_helper import get_loan


@allure.feature("信贷业务规则")
class TestBusinessRules:

    @allure.story("信用分规则")
    @allure.title("TC_RULE_001 信用分 < 600 拒绝借款")
    def test_low_credit_score_rejected(self, api_client):
        with allure.step("注册信用分 500 的客户"):
            cust_id = api_client.register({
                "name": "低分客户", "age": 30,
                "income": 10000, "credit_score": 500,
            }).json()["customer_id"]

        with allure.step("尝试借款"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 10000})

        with allure.step("期望 403 拒绝"):
            assert resp.status_code == 403
            assert "信用评分不足" in resp.json()["error"]

    @allure.story("收入规则")
    @allure.title("TC_RULE_002 收入 < 5000 拒绝借款")
    def test_low_income_rejected(self, api_client):
        with allure.step("注册收入 3000 的客户"):
            cust_id = api_client.register({
                "name": "低收入", "age": 30,
                "income": 3000, "credit_score": 700,
            }).json()["customer_id"]

        with allure.step("尝试借款"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 10000})

        with allure.step("期望 403 拒绝"):
            assert resp.status_code == 403
            assert "收入不足" in resp.json()["error"]

    @allure.story("边界规则")
    @allure.title("TC_RULE_003 信用分刚好 600 可以借款")
    def test_credit_score_boundary_pass(self, api_client):
        with allure.step("注册信用分 600 的客户"):
            cust_id = api_client.register({
                "name": "边界客户", "age": 30,
                "income": 10000, "credit_score": 600,
            }).json()["customer_id"]

        with allure.step("尝试借款"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 10000})

        with allure.step("期望 201 成功"):
            assert resp.status_code == 201

    @allure.story("利率规则")
    @allure.title("TC_RULE_004 不同信用分对应不同利率")
    @pytest.mark.parametrize("credit_score, expected_rate", [
        (850, 0.02),
        (750, 0.035),
        (650, 0.05),
    ])
    def test_interest_rate_by_score(self, api_client, credit_score, expected_rate):
        with allure.step(f"注册信用分 {credit_score}"):
            cust_id = api_client.register({
                "name": "利率客户", "age": 30,
                "income": 10000, "credit_score": credit_score,
            }).json()["customer_id"]

        with allure.step("借款"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 10000})
            assert resp.status_code == 201

        with allure.step(f"校验利率 = {expected_rate}"):
            loan = get_loan(resp.json()["loan_id"])
            assert loan["interest_rate"] == expected_rate

    @allure.story("频率规则")
    @allure.title("TC_RULE_005 月借款 5 次后拒绝")
    def test_monthly_loan_limit(self, api_client):
        with allure.step("注册合格客户"):
            cust_id = api_client.register({
                "name": "高频客户", "age": 30,
                "income": 10000, "credit_score": 700,
            }).json()["customer_id"]

        with allure.step("连续借款 5 次（都成功）"):
            for i in range(5):
                resp = api_client.create_loan({"customer_id": cust_id, "amount": 1000})
                assert resp.status_code == 201, f"第 {i+1} 次应成功"

        with allure.step("第 6 次应被拒绝"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 1000})
            assert resp.status_code == 429
            assert "上限" in resp.json()["error"]