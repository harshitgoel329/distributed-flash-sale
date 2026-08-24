import uuid
from locust import HttpUser, task, between

class FlashSaleLoadTest(HttpUser):
    wait_time = between(0.01, 0.05)  # Aggressive concurrency spike

    @task
    def attempt_reservation(self):
        headers = {
            "X-Idempotency-Key": str(uuid.uuid4())
        }
        payload = {
            "product_id": "prod_phone_123",
            "user_id": f"usr_{uuid.uuid4().hex[:8]}",
            "quantity": 1
        }
        self.client.post("/api/v1/orders/reserve", json=payload, headers=headers)