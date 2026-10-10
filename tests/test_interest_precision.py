"""利息计算精度测试。

验证 Decimal 修复是否生效：
- 50000 * 0.035 应该是 1750（而不是 1749）
- 大额、小额、边界金额都要精确
- 使用 ROUND_HALF_UP 四舍五入
"""
from decimal import Decimal, ROUND_HALF_UP

import allure
import pytest

from tests.db_helper import get_loan


def expected_interest(principal: int, rate: float) -> int:
    """测试侧独立计算预期利息（与生产代码算法一致）。"""
    return int(
        (Decimal(str(principal)) * Decimal(str(rate))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


@allure.feature("金融计算精度")
class TestInterestPrecision:

    @allure.story("浮点误差回归")
    @allure.title("TC_PREC_001 50000 × 0.035 应得 1750（不是 1749）")
    def test_classic_float_bug(self, api_client, sample_customer):
        """经典浮点陷阱：int(50000 * 0.035) = 1749，Decimal 后 = 1750。"""
        with allure.step("创建贷款（信用分 700 → 利率 3.5%）"):
            resp = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 50000,
            })
            assert resp.status_code == 201
            loan_id = resp.json()["loan_id"]

        with allure.step("从 DB 读取贷款"):
            loan = get_loan(loan_id)

        with allure.step("校验本金和利率"):
            assert loan["principal"] == 50000
            assert loan["interest_rate"] == 0.035

        with allure.step("校验：利息 = 1750（而非浮点误差的 1749）"):
            interest = loan["amount"] - loan["principal"]
            assert interest == 1750, \
                f"利息应为 1750（Decimal 修复后），实际 {interest}（浮点误差会得到 1749）"

    @allure.story("边界金额精度")
    @allure.title("TC_PREC_002 小额贷款（1 元）精度")
    @pytest.mark.parametrize("amount, credit_score, expected_rate", [
        (1,     700, 0.035),
        (100,   700, 0.035),
        (1000,  700, 0.035),
    ])
    def test_small_amount_precision(self, api_client, amount, credit_score, expected_rate):
        with allure.step(f"注册信用分 {credit_score} 的客户"):
            cust_id = api_client.register({
                "name": "精度测试",
                "age": 25,
                "income": 8000,
                "credit_score": credit_score,
            }).json()["customer_id"]

        with allure.step(f"创建贷款 amount={amount}"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": amount})
            assert resp.status_code == 201

        with allure.step(f"校验利息 = {expected_interest(amount, expected_rate)}"):
            loan = get_loan(resp.json()["loan_id"])
            interest = loan["amount"] - loan["principal"]
            expected = expected_interest(amount, expected_rate)
            assert interest == expected, \
                f"本金 {amount} 利率 {expected_rate}，预期利息 {expected}，实际 {interest}"

    @allure.story("边界金额精度")
    @allure.title("TC_PREC_003 最大金额（1000 万）精度")
    def test_large_amount_precision(self, api_client, sample_customer):
        """接口上限 10_000_000，测试边界值。"""
        with allure.step("创建贷款 1000 万元"):
            resp = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 10_000_000,
            })
            assert resp.status_code == 201

        with allure.step("校验利息 = 350,000"):
            loan = get_loan(resp.json()["loan_id"])
            interest = loan["amount"] - loan["principal"]
            expected = expected_interest(10_000_000, 0.035)
            assert interest == expected, \
                f"1000 万 × 3.5% 应为 {expected}，实际 {interest}"

    @allure.story("所有利率档位精度")
    @allure.title("TC_PREC_004 三档利率精度")
    @pytest.mark.parametrize("credit_score, rate", [
        (850, 0.02),
        (700, 0.035),
        (600, 0.05),
    ])
    def test_all_interest_rates(self, api_client, credit_score, rate):
        with allure.step(f"信用分 {credit_score} → 利率 {rate}"):
            cust_id = api_client.register({
                "name": "利率测试",
                "age": 25,
                "income": 8000,
                "credit_score": credit_score,
            }).json()["customer_id"]

        with allure.step("创建贷款 12345 元"):
            resp = api_client.create_loan({"customer_id": cust_id, "amount": 12345})
            assert resp.status_code == 201

        with allure.step(f"校验利息 = {expected_interest(12345, rate)}"):
            loan = get_loan(resp.json()["loan_id"])
            interest = loan["amount"] - loan["principal"]
            expected = expected_interest(12345, rate)
            assert interest == expected, \
                f"12345 × {rate} 应为 {expected}，实际 {interest}"

    @allure.story("测试侧算法独立验证")
    @allure.title("TC_PREC_005 测试侧 Decimal 计算与生产一致")
    @pytest.mark.parametrize("principal, rate, expected", [
        (50000,  0.035, 1750),
        (10000,  0.035, 350),
        (12345,  0.02,  247),
        (12345,  0.05,  617),
        (1,      0.05,  0),
        (100,    0.05,  5),
        (999,    0.035, 35),
    ])
    def test_decimal_reference(self, principal, rate, expected):
        """纯单元测试：验证 Decimal 算法本身。不调接口。"""
        with allure.step(f"Decimal({principal}) × Decimal({rate}) = {expected}"):
            result = expected_interest(principal, rate)
            assert result == expected, \
                f"{principal} × {rate} 应为 {expected}，实际 {result}"