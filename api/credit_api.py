"""信贷业务 API 客户端。"""
from api.base_api import BaseAPI


class CreditAPI(BaseAPI):
    """Mock 信贷服务的 API 客户端。"""

    def register(self, payload):
        return self.post("/api/v1/register", json=payload)

    def check_eligibility(self, payload):
        return self.post("/api/v1/check-eligibility", json=payload)

    def create_loan(self, payload):
        return self.post("/api/v1/loan", json=payload)

    def view_loan(self, loan_id):
        return self.get(f"/api/v1/view-loan/{loan_id}")

    def approve_loan(self, loan_id):
        return self.post(f"/api/v1/loan/{loan_id}/approve")

    def reject_loan(self, loan_id):
        return self.post(f"/api/v1/loan/{loan_id}/reject")

    def disburse_loan(self, loan_id):
        return self.post(f"/api/v1/loan/{loan_id}/disburse")

    def repay_loan(self, loan_id):
        return self.post(f"/api/v1/loan/{loan_id}/repay")

    def reset_db(self):
        return self.post("/api/v1/_reset_db")
