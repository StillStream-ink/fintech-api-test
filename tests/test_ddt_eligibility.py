"""数据驱动的资格预审测试。

数据来源：data/*.yaml
新增边界场景只需改 YAML，不用改代码。
"""
import allure
import pytest

from tests.yaml_loader import case_id, load_yaml

pytestmark = [pytest.mark.api, pytest.mark.credit, pytest.mark.eligibility]


@allure.feature("数据驱动-资格预审")
class TestEligibilityDDT:

    @allure.story("年龄边界")
    @pytest.mark.parametrize(
        "case",
        load_yaml("eligibility_age.yaml"),
        ids=case_id,
    )
    def test_eligibility_age(self, api_client, case):
        with allure.step(f"[{case['case_id']}] {case['desc']}"):
            resp = api_client.check_eligibility(case["input"])

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200, f"实际 {resp.status_code}：{resp.text}"

        with allure.step(f"校验 eligible == {case['expected_eligible']}"):
            data = resp.json()
            assert data["eligible"] is case["expected_eligible"], (
                f"输入={case['input']}，期望 eligible={case['expected_eligible']}，"
                f"实际 {data}"
            )

    @allure.story("收入边界")
    @pytest.mark.parametrize(
        "case",
        load_yaml("eligibility_income.yaml"),
        ids=case_id,
    )
    def test_eligibility_income(self, api_client, case):
        with allure.step(f"[{case['case_id']}] {case['desc']}"):
            resp = api_client.check_eligibility(case["input"])

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200, f"实际 {resp.status_code}：{resp.text}"

        with allure.step(f"校验 eligible == {case['expected_eligible']}"):
            data = resp.json()
            assert data["eligible"] is case["expected_eligible"], (
                f"输入={case['input']}，期望 eligible={case['expected_eligible']}，"
                f"实际 {data}"
            )

    @allure.story("信用分边界")
    @pytest.mark.parametrize(
        "case",
        load_yaml("eligibility_credit_score.yaml"),
        ids=case_id,
    )
    def test_eligibility_credit_score(self, api_client, case):
        with allure.step(f"[{case['case_id']}] {case['desc']}"):
            resp = api_client.check_eligibility(case["input"])

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200, f"实际 {resp.status_code}：{resp.text}"

        with allure.step(f"校验 eligible == {case['expected_eligible']}"):
            data = resp.json()
            assert data["eligible"] is case["expected_eligible"], (
                f"输入={case['input']}，期望 eligible={case['expected_eligible']}，"
                f"实际 {data}"
            )