"""信贷 Mock 服务性能压测。

用法：
    1. 先启动 Mock 服务：py app.py
    2. 再启动 Locust：  locust -f locustfile.py
    3. 浏览器打开 http://localhost:8089
       - Number of users: 100
       - Spawn rate: 10
       - Host: http://127.0.0.1:5000
"""
import random

from locust import HttpUser, task, between


class CreditUser(HttpUser):
    """模拟一个信贷 App 用户的行为。"""

    wait_time = between(0.5, 2)  # 每个请求间隔 0.5~2 秒

    def on_start(self):
        """虚拟用户启动时先注册，拿到 customer_id。"""
        payload = {
            "name": f"压测用户_{random.randint(10000, 99999)}",
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
                resp.failure(f"注册失败: {resp.status_code} {resp.text}")

    @task(5)
    def check_eligibility(self):
        """高频：资格预审（只读，不落库）。"""
        self.client.post(
            "/api/v1/check-eligibility",
            json={"age": 22, "income": 8000, "credit_score": 700},
            name="[资格预审] POST /check-eligibility",
        )

    @task(3)
    def create_and_view_loan(self):
        """中频：创建贷款 + 查询详情。"""
        if not self.customer_id:
            return
        with self.client.post(
            "/api/v1/loan",
            json={"customer_id": self.customer_id, "amount": 50000},
            catch_response=True,
            name="[创建贷款] POST /api/v1/loan",
        ) as resp:
            if resp.status_code == 201:
                loan_id = resp.json()["loan_id"]
                self.client.get(
                    f"/api/v1/view-loan/{loan_id}",
                    name="[查询贷款] GET /view-loan/{id}",
                )
            else:
                resp.failure(f"创建贷款失败: {resp.status_code} {resp.text}")

    @task(2)
    def full_lifecycle(self):
        """低频：完整生命周期（申请-审批-放款-还款）。"""
        if not self.customer_id:
            return
        with self.client.post(
            "/api/v1/loan",
            json={"customer_id": self.customer_id, "amount": 10000},
            catch_response=True,
            name="[生命周期] POST /api/v1/loan",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"创建失败: {resp.status_code}")
                return
            loan_id = resp.json()["loan_id"]

        self.client.post(
            f"/api/v1/loan/{loan_id}/approve",
            name="[生命周期] POST /approve",
        )
        self.client.post(
            f"/api/v1/loan/{loan_id}/disburse",
            name="[生命周期] POST /disburse",
        )
        self.client.post(
            f"/api/v1/loan/{loan_id}/repay",
            name="[生命周期] POST /repay",
        )