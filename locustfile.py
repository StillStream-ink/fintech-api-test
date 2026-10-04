"""信贷 Mock 服务性能压测。

适配业务规则：
- 每个虚拟用户最多创建 1 笔贷款（避免触发"月借款 ≤5 次"限制）
- 主要压力集中在查询和资格预审（只读接口）
- 少量完整生命周期测试（低频）

用法：
    1. 终端 A：py app.py
    2. 终端 B：py scripts\run_load_test.py
"""
import random

from locust import HttpUser, task, between


class CreditUser(HttpUser):
    """模拟一个信贷 App 用户。"""

    wait_time = between(0.5, 2)

    def on_start(self):
        """启动时注册一次，拿到 customer_id。"""
        payload = {
            "name": f"压测用户_{random.randint(10000, 999999)}",
            "age": 25,
            "income": 8000,
            "credit_score": 700,
        }
        with self.client.post(
            "/api/v1/register",
            json=payload,
            catch_response=True,
            name="[注册] POST /api/v1/register",
        ) as resp:
            if resp.status_code == 201:
                self.customer_id = resp.json()["customer_id"]
            else:
                self.customer_id = None
                resp.failure(f"注册失败: {resp.status_code}")

        # 每个用户只创建 1 笔贷款
        self.loan_created = False
        self.loan_id = None

    @task(10)
    def check_eligibility(self):
        """高频：资格预审（只读）。"""
        self.client.post(
            "/api/v1/check-eligibility",
            json={"age": 22, "income": 8000, "credit_score": 700},
            name="[资格预审] POST /check-eligibility",
        )

    @task(5)
    def create_loan_once(self):
        """中频：每个用户最多创建 1 笔贷款。"""
        if not self.customer_id or self.loan_created:
            return

        with self.client.post(
            "/api/v1/loan",
            json={"customer_id": self.customer_id, "amount": 5000},
            catch_response=True,
            name="[创建贷款] POST /api/v1/loan",
        ) as resp:
            if resp.status_code == 201:
                self.loan_id = resp.json()["loan_id"]
                self.loan_created = True
            else:
                resp.failure(f"创建失败: {resp.status_code} {resp.text[:100]}")

    @task(8)
    def view_loan(self):
        """高频：查询贷款详情（只读）。"""
        if not self.loan_id:
            return
        self.client.get(
            f"/api/v1/view-loan/{self.loan_id}",
            name="[查询贷款] GET /view-loan/{id}",
        )

    @task(2)
    def full_lifecycle_once(self):
        """低频：完整生命周期（仅当还没走过）。"""
        if not self.loan_id or getattr(self, "_lifecycle_done", False):
            return

        self.client.post(
            f"/api/v1/loan/{self.loan_id}/approve",
            name="[生命周期] POST /approve",
        )
        self.client.post(
            f"/api/v1/loan/{self.loan_id}/disburse",
            name="[生命周期] POST /disburse",
        )
        self.client.post(
            f"/api/v1/loan/{self.loan_id}/repay",
            name="[生命周期] POST /repay",
        )
        self._lifecycle_done = True