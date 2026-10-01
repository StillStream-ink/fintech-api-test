"""接口 + SQLite 数据库双检。

核心思想：
    接口返回 2xx  数据真的落库
    每一条"写"接口的用例，都直连 SQLite 校验真实数据
"""
import allure
import pytest

from tests.db_helper import (
    count_customers,
    count_loans,
    get_customer,
    get_loan,
    list_loans_by_customer,
)

pytestmark = [pytest.mark.api, pytest.mark.credit]


@allure.feature("接口 + 数据库双检")
class TestDatabaseConsistency:

    # ==================== 注册 ====================

    @allure.story("注册-数据落库")
    @allure.title("TC_DB_001 注册接口成功后，DB 里应有完整记录")
    def test_register_persists_to_db(self, api_client):
        with allure.step("准备注册数据"):
            payload = {"name": "张三", "age": 22, "income": 8000, "credit_score": 700}

        with allure.step("调用注册接口"):
            resp = api_client.register(payload)
            assert resp.status_code == 201

        with allure.step("从接口响应中提取 customer_id"):
            cust_id = resp.json()["customer_id"]

        with allure.step(f"直连 DB 查询 customer_id={cust_id} 的记录"):
            row = get_customer(cust_id)

        with allure.step("校验 DB 记录存在且字段与请求一致"):
            assert row is not None, f"DB 里没有 customer_id={cust_id} 的记录"
            assert row["name"] == "张三"
            assert row["age"] == 22
            assert row["income"] == 8000
            assert row["credit_score"] == 700

    @allure.story("注册-并发安全")
    @allure.title("TC_DB_002 连续注册 3 个客户，DB 应有 3 条记录")
    def test_multiple_registers_count(self, api_client):
        with allure.step("连续调用注册接口 3 次"):
            for i in range(3):
                resp = api_client.register({
                    "name": f"用户{i}",
                    "age": 22 + i,
                    "income": 8000,
                    "credit_score": 700,
                })
                assert resp.status_code == 201

        with allure.step("校验 DB 里 customer 表应有 3 条记录"):
            assert count_customers() == 3

    @allure.story("注册-必填校验")
    @allure.title("TC_DB_003 缺必填字段时，DB 不应新增记录")
    def test_register_missing_field_no_db_write(self, api_client):
        with allure.step("记录当前 customer 表行数"):
            before = count_customers()

        with allure.step("发送缺字段的注册请求"):
            resp = api_client.register({"name": "张三"})

        with allure.step("校验 HTTP 状态码为 400"):
            assert resp.status_code == 400

        with allure.step("校验 DB 行数未变化（校验失败不落库）"):
            assert count_customers() == before, "校验失败不应写入 DB"

    # ==================== 资格检查（只读接口） ====================

    @allure.story("资格检查-只读")
    @allure.title("TC_DB_004 资格检查是只读接口，不应写 DB")
    def test_eligibility_does_not_write(self, api_client):
        with allure.step("记录调用前 customer / loan 表行数"):
            before_c = count_customers()
            before_l = count_loans()

        with allure.step("调用资格检查接口"):
            resp = api_client.check_eligibility({
                "age": 22, "income": 8000, "credit_score": 700,
            })
            assert resp.status_code == 200

        with allure.step("校验两张表行数均未变化"):
            assert count_customers() == before_c, "资格检查不应写 customer 表"
            assert count_loans() == before_l, "资格检查不应写 loan 表"

    # ==================== 创建贷款 ====================

    @allure.story("创建贷款-数据落库")
    @allure.title("TC_DB_005 创建贷款成功后，DB 应写入 PENDING 状态")
    def test_create_loan_persists(self, api_client, sample_customer):
        with allure.step(f"调用创建贷款接口（customer_id={sample_customer}）"):
            resp = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 50000,
            })
            assert resp.status_code == 201

        with allure.step("从响应中提取 loan_id"):
            loan_id = resp.json()["loan_id"]

        with allure.step(f"直连 DB 查询 loan_id={loan_id} 的记录"):
            row = get_loan(loan_id)

        with allure.step("校验 DB 记录字段与请求一致，状态为 PENDING"):
            assert row is not None
            assert row["customer_id"] == sample_customer
            assert row["amount"] == 50000
            assert row["status"] == "PENDING"

    @allure.story("创建贷款-外键一致")
    @allure.title("TC_DB_006 贷款的 customer_id 应指向真实客户")
    def test_loan_customer_foreign_key(self, api_client, sample_customer):
        with allure.step("创建一笔贷款"):
            resp = api_client.create_loan({
                "customer_id": sample_customer,
                "amount": 50000,
            })
            loan_id = resp.json()["loan_id"]

        with allure.step("从 DB 读取贷款和关联客户"):
            loan = get_loan(loan_id)
            customer = get_customer(loan["customer_id"])

        with allure.step("校验外键指向的客户记录真实存在"):
            assert customer is not None, "贷款关联的 customer_id 不存在于客户表"

    @allure.story("创建贷款-幂等缺陷")
    @allure.title("TC_DB_007 [BUG] 重复提交同一贷款，DB 里却生成 2 条记录")
    @pytest.mark.xfail(
        strict=True,
        reason="BUG-004：接口未实现幂等，重复提交生成多条记录",
    )
    
    @allure.story("创建贷款-幂等缺陷")
    @allure.title("TC_DB_007 [BUG] 重复提交同一贷款，DB 里却生成 2 条记录")
    @pytest.mark.xfail(
        strict=True,
        reason="BUG-004：接口未实现幂等，重复提交生成多条记录",
    )
    def test_create_loan_idempotent_db(self, api_client, sample_customer):
        with allure.step("连续两次提交完全相同的贷款请求"):
            payload = {"customer_id": sample_customer, "amount": 50000}
            r1 = api_client.create_loan(payload)
            r2 = api_client.create_loan(payload)

        with allure.step("期望两次返回同一个 loan_id"):
            assert r1.json()["loan_id"] == r2.json()["loan_id"]

        # xfail 在上一行断言失败，以下行永远走不到
        assert len(list_loans_by_customer(sample_customer)) == 1, "DB 应只有 1 条贷款"  # pragma: no cover
    @allure.story("创建贷款-非法客户")
    @allure.title("TC_DB_008 不存在的 customer_id 应返回 404 且不写库")
    def test_create_loan_invalid_customer_no_db_write(self, api_client):
        with allure.step("记录当前 loan 表行数"):
            before = count_loans()

        with allure.step("发送 customer_id=99999（不存在）的创建请求"):
            resp = api_client.create_loan({
                "customer_id": 99999,
                "amount": 50000,
            })

        with allure.step("校验 HTTP 状态码为 404"):
            assert resp.status_code == 404

        with allure.step("校验 DB 行数未变化（非法客户不应写库）"):
            assert count_loans() == before, "非法客户不应写入 DB"

    # ==================== 查询贷款 ====================

    @allure.story("查询贷款-DB 一致性")
    @allure.title("TC_DB_009 查询接口返回的数据应与 DB 完全一致")
    def test_view_loan_matches_db(self, api_client, sample_loan):
        with allure.step(f"调用查询接口（loan_id={sample_loan}）"):
            resp = api_client.view_loan(sample_loan)
            assert resp.status_code == 200

        with allure.step("从接口响应和 DB 分别取数据"):
            api_data = resp.json()
            db_data = get_loan(sample_loan)

        with allure.step("校验字段逐个一致"):
            assert api_data["loan_id"] == db_data["id"]
            assert api_data["customer_id"] == db_data["customer_id"]
            assert api_data["amount"] == db_data["amount"]
            assert api_data["status"] == db_data["status"]

    # ==================== 重置接口 ====================

    @allure.story("重置-清理完整")
    @allure.title("TC_DB_010 重置接口调用后，所有表应为空")
    def test_reset_db_clears_all(self, api_client, sample_customer, sample_loan):
        with allure.step("前置校验：DB 里已有数据"):
            assert count_customers() > 0
            assert count_loans() > 0

        with allure.step("调用重置接口"):
            resp = api_client.reset_db()
            assert resp.status_code == 200

        with allure.step("校验 customer 和 loan 表均被清空"):
            assert count_customers() == 0, "重置后 customer 表应为空"
            assert count_loans() == 0, "重置后 loan 表应为空"