import requests


class CreditAPI:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        return self.session.request(method, url, headers=self.headers, timeout=self.timeout, **kwargs)

    def register(self, payload: dict):
        return self._request("POST", "/api/v1/register", json=payload)

    def check_eligibility(self, payload: dict):
        return self._request("POST", "/api/v1/check-eligibility", json=payload)

    def create_loan(self, payload: dict):
        return self._request("POST", "/api/v1/loan", json=payload)

    def view_loan(self, loan_id: int):
        return self._request("GET", f"/api/v1/view-loan/{loan_id}")

    def approve_loan(self, loan_id: int):
        return self._request("POST", f"/api/v1/loan/{loan_id}/approve")

    def reject_loan(self, loan_id: int):
        return self._request("POST", f"/api/v1/loan/{loan_id}/reject")

    def disburse_loan(self, loan_id: int):
        return self._request("POST", f"/api/v1/loan/{loan_id}/disburse")

    def repay_loan(self, loan_id: int):
        return self._request("POST", f"/api/v1/loan/{loan_id}/repay")

    def reset_db(self):
        return self._request("POST", "/api/v1/_reset_db")
