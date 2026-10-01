"""参数化边界测试。

设计原则：先跑一遍看服务端真实行为，不预判对错。
- 缺参数 / 类型错误 / 空串 / 负数 / 超大值 / 非法 JSON
- 每个参数值代表一类独立风险
"""
import allure
import pytest

pytestmark = [pytest.mark.api, pytest.mark.credit]


@allure.feature("参数化边界校验")
class TestRegisterBoundary:
    """POST /api/v1/register 的边界测试"""

    @allure.story("注册-缺失必填字段")
    @pytest.mark.parametrize("missing_field", [
        "name", "age", "income", "credit_score",
    ])
    def test_register_missing_required_field(self, api_client, missing_field):
        """缺任一个必填字段应返回 400"""
        payload = {
            "name": "张三", "age": 22,
            "income": 8000, "credit_score": 700,
        }
        del payload[missing_field]

        resp = api_client.register(payload)
        assert resp.status_code == 400, \
            f"缺 {missing_field} 应返回 400，实际 {resp.status_code}"

    @allure.story("注册-数据类型错误")
    @pytest.mark.parametrize("bad_payload, desc", [
        ({"name": 123, "age": 22, "income": 8000, "credit_score": 700}, "name 传整数"),
        ({"name": "张三", "age": "22", "income": 8000, "credit_score": 700}, "age 传字符串"),
        ({"name": "张三", "age": 22.5, "income": 8000, "credit_score": 700}, "age 传浮点"),
        ({"name": "张三", "age": 22, "income": "8000", "credit_score": 700}, "income 传字符串"),
        ({"name": "张三", "age": 22, "income": 8000, "credit_score": "700"}, "credit_score 传字符串"),
    ])
    def test_register_invalid_type(self, api_client, bad_payload, desc):
        """类型错误应返回 400"""
        resp = api_client.register(bad_payload)
        assert resp.status_code == 400, \
            f"{desc} 应被拒绝，实际 {resp.status_code}"

    @allure.story("注册-空字符串")
    @pytest.mark.parametrize("field", ["name"])
    def test_register_empty_string(self, api_client, field):
        """name 空串应被拒绝"""
        payload = {
            "name": "", "age": 22,
            "income": 8000, "credit_score": 700,
        }
        resp = api_client.register(payload)
        assert resp.status_code == 400, \
            f"{field} 空串应被拒绝，实际 {resp.status_code}"

    @allure.story("注册-数值非法")
    @pytest.mark.parametrize("payload, desc", [
        ({"name": "张三", "age": -1, "income": 8000, "credit_score": 700}, "age 负数"),
        ({"name": "张三", "age": 22, "income": -100, "credit_score": 700}, "income 负数"),
        ({"name": "张三", "age": 22, "income": 8000, "credit_score": -1}, "credit_score 负数"),
        ({"name": "张三", "age": 999, "income": 8000, "credit_score": 700}, "age 超大值"),
        ({"name": "张三", "age": 22, "income": 999999999999, "credit_score": 700}, "income 超大值"),
        ({"name": "张三", "age": 22, "income": 8000, "credit_score": 9999}, "credit_score 超大值"),
    ])
    def test_register_invalid_number(self, api_client, payload, desc):
        """数值超出合法范围应被拒绝"""
        resp = api_client.register(payload)
        assert resp.status_code == 400, \
            f"{desc} 应被拒绝，实际 {resp.status_code}"


@allure.feature("参数化边界校验")
class TestEligibilityBoundary:
    """POST /api/v1/check-eligibility 的边界测试"""

    @allure.story("资格检查-缺失字段")
    @pytest.mark.parametrize("missing_field", [
        "age", "income", "credit_score",
    ])
    def test_eligibility_missing_field(self, api_client, missing_field):
        payload = {"age": 22, "income": 8000, "credit_score": 700}
        del payload[missing_field]

        resp = api_client.check_eligibility(payload)
        assert resp.status_code == 400, \
            f"缺 {missing_field} 应返回 400，实际 {resp.status_code}"

    @allure.story("资格检查-类型错误")
    @pytest.mark.parametrize("bad_payload, desc", [
        ({"age": "abc", "income": 8000, "credit_score": 700}, "age 传字符串"),
        ({"age": 22, "income": None, "credit_score": 700}, "income 传 null"),
        ({"age": 22, "income": 8000, "credit_score": 700.5}, "credit_score 传浮点"),
    ])
    def test_eligibility_invalid_type(self, api_client, bad_payload, desc):
        resp = api_client.check_eligibility(bad_payload)
        assert resp.status_code == 400, \
            f"{desc} 应被拒绝，实际 {resp.status_code}"

    @allure.story("资格检查-年龄业务边界")
    @pytest.mark.parametrize("age, expected_eligible", [
        (0, False),     # 合法整数但业务拒绝
        (17, False),
        (18, True),
        (59, True),
        (60, True),
        (61, False),
        (100, False),
    ])
    def test_eligibility_age_boundary(self, api_client, age, expected_eligible):
        """合法范围内的年龄，走业务逻辑判断（返回 200）"""
        resp = api_client.check_eligibility({
            "age": age, "income": 8000, "credit_score": 700,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is expected_eligible, \
            f"age={age} 期望 eligible={expected_eligible}，实际 {data}"

    @allure.story("资格检查-年龄非法参数")
    @pytest.mark.parametrize("age", [-1, 151, 999])
    def test_eligibility_age_invalid(self, api_client, age):
        """负数 / 超大值应在参数层被拒绝（返回 400）"""
        resp = api_client.check_eligibility({
            "age": age, "income": 8000, "credit_score": 700,
        })
        assert resp.status_code == 400, \
            f"age={age} 应被参数校验拒绝，实际 {resp.status_code}"

    @allure.story("资格检查-收入业务边界")
    @pytest.mark.parametrize("income, expected_eligible", [
        (0, False),
        (2999, False),
        (3000, True),
        (10000, True),
        (99999999, True),   # 接近上限
    ])
    def test_eligibility_income_boundary(self, api_client, income, expected_eligible):
        resp = api_client.check_eligibility({
            "age": 22, "income": income, "credit_score": 700,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is expected_eligible, \
            f"income={income} 期望 eligible={expected_eligible}，实际 {data}"

    @allure.story("资格检查-收入非法参数")
    @pytest.mark.parametrize("income", [-1, 100_000_001, 999999999])
    def test_eligibility_income_invalid(self, api_client, income):
        """负数 / 超出上限应在参数层被拒绝"""
        resp = api_client.check_eligibility({
            "age": 22, "income": income, "credit_score": 700,
        })
        assert resp.status_code == 400, \
            f"income={income} 应被参数校验拒绝，实际 {resp.status_code}"

    @allure.story("资格检查-信用分业务边界")
    @pytest.mark.parametrize("credit_score, expected_eligible", [
        (0, False),
        (599, False),
        (600, True),
        (850, True),
        (1000, True),   # 上限
    ])
    def test_eligibility_credit_score_boundary(self, api_client, credit_score, expected_eligible):
        resp = api_client.check_eligibility({
            "age": 22, "income": 8000, "credit_score": credit_score,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["eligible"] is expected_eligible, \
            f"credit_score={credit_score} 期望 eligible={expected_eligible}，实际 {data}"

    @allure.story("资格检查-信用分非法参数")
    @pytest.mark.parametrize("credit_score", [-1, 1001, 9999])
    def test_eligibility_credit_score_invalid(self, api_client, credit_score):
        """负数 / 超出上限应在参数层被拒绝"""
        resp = api_client.check_eligibility({
            "age": 22, "income": 8000, "credit_score": credit_score,
        })
        assert resp.status_code == 400, \
            f"credit_score={credit_score} 应被参数校验拒绝，实际 {resp.status_code}"


@allure.feature("参数化边界校验")
class TestLoanBoundary:
    """POST /api/v1/loan 的边界测试"""

    @allure.story("创建贷款-缺失字段")
    @pytest.mark.parametrize("missing_field", [
        "customer_id", "amount",
    ])
    def test_create_loan_missing_field(self, api_client, sample_customer, missing_field):
        payload = {"customer_id": sample_customer, "amount": 50000}
        del payload[missing_field]

        resp = api_client.create_loan(payload)
        assert resp.status_code == 400, \
            f"缺 {missing_field} 应返回 400，实际 {resp.status_code}"

    @allure.story("创建贷款-类型错误")
    @pytest.mark.parametrize("bad_payload_func, desc", [
        (lambda cid: {"customer_id": str(cid), "amount": 50000}, "customer_id 传字符串"),
        (lambda cid: {"customer_id": cid, "amount": "50000"}, "amount 传字符串"),
        (lambda cid: {"customer_id": cid, "amount": None}, "amount 传 null"),
    ])
    def test_create_loan_invalid_type(self, api_client, sample_customer, bad_payload_func, desc):
        payload = bad_payload_func(sample_customer)
        resp = api_client.create_loan(payload)
        assert resp.status_code == 400, \
            f"{desc} 应被拒绝，实际 {resp.status_code}"

    @allure.story("创建贷款-金额边界")
    @pytest.mark.parametrize("amount, desc, should_reject", [
        (-1, "负数", True),
        (0, "零值", True),
        (1, "最小值", False),
        (999, "小额", False),
        (100000, "标准额度", False),
        (99999999, "超大额", True),
    ])
    def test_create_loan_amount_boundary(self, api_client, sample_customer, amount, desc, should_reject):
        resp = api_client.create_loan({
            "customer_id": sample_customer,
            "amount": amount,
        })
        if should_reject:
            assert resp.status_code == 400, \
                f"amount={amount} ({desc}) 应被拒绝，实际 {resp.status_code}"
        else:
            assert resp.status_code == 201, \
                f"amount={amount} ({desc}) 应被接受，实际 {resp.status_code}"

    @allure.story("创建贷款-客户不存在")
    @pytest.mark.parametrize("bad_customer_id", [99999, -1, 0])
    def test_create_loan_invalid_customer(self, api_client, bad_customer_id):
        resp = api_client.create_loan({
            "customer_id": bad_customer_id,
            "amount": 50000,
        })
        assert resp.status_code in (400, 404), \
            f"不存在的 customer_id={bad_customer_id} 应被拒绝，实际 {resp.status_code}"


@allure.feature("参数化边界校验")
class TestJsonBoundary:
    """请求体非法 JSON 等协议层边界"""

    @allure.story("协议层-非法 JSON")
    def test_register_invalid_json(self, api_client):
        """发送非法 JSON 应返回 400"""
        resp = api_client.session.post(
            f"{api_client.base_url}/api/v1/register",
            data="{not valid json",
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        assert resp.status_code == 400

    @allure.story("协议层-空 body")
    def test_register_empty_body(self, api_client):
        resp = api_client.register({})
        assert resp.status_code == 400