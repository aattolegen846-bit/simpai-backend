from locust import HttpUser, between, task


class SimpaiPerfUser(HttpUser):
    wait_time = between(0.1, 0.8)

    @task(2)
    def health(self):
        self.client.get("/api/v1/health")

    @task(3)
    def synonyms(self):
        self.client.get("/api/v1/synonyms/good")

    @task(1)
    def leaderboard(self):
        self.client.get("/api/v1/social/leaderboard?limit=10")
