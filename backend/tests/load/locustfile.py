"""
Locust Load Testing Configuration
For PaperTrading Platform API

Run with:
    locust -f backend/tests/load/locustfile.py --host=http://localhost:8000

Web UI will be available at http://localhost:8089
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import json
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data
TEST_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "JNJ"]
TEST_USER_EMAIL = "loadtest@example.com"
TEST_USER_PASSWORD = "LoadTest123!"


class PaperTradingUser(HttpUser):
    """
    Simulates a typical user of the PaperTrading platform.
    
    User behavior:
    - Logs in at the start
    - Checks quotes frequently
    - Views portfolio occasionally
    - Places trades rarely
    """
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    # Store auth token
    access_token = None
    portfolio_id = None
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.login()
        self.get_portfolio()
    
    def login(self):
        """Authenticate and get access token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            },
            name="/api/v1/auth/login"
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            logger.info("User logged in successfully")
        else:
            logger.warning(f"Login failed: {response.status_code}")
    
    def get_headers(self):
        """Get authenticated headers."""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
    
    def get_portfolio(self):
        """Get user's portfolio ID."""
        if not self.access_token:
            return
            
        response = self.client.get(
            "/api/v1/portfolios",
            headers=self.get_headers(),
            name="/api/v1/portfolios"
        )
        
        if response.status_code == 200:
            data = response.json()
            portfolios = data.get("portfolios", [])
            if portfolios:
                self.portfolio_id = portfolios[0].get("id")
    
    @task(10)  # Weight 10 - most frequent
    def get_quote(self):
        """Get a stock quote - most common operation."""
        symbol = random.choice(TEST_SYMBOLS)
        
        self.client.get(
            f"/api/v1/market/quote/{symbol}",
            headers=self.get_headers(),
            name="/api/v1/market/quote/[symbol]"
        )
    
    @task(5)  # Weight 5
    def get_batch_quotes(self):
        """Get multiple quotes at once."""
        symbols = random.sample(TEST_SYMBOLS, 5)
        
        self.client.get(
            f"/api/v1/market/quotes?symbols={','.join(symbols)}",
            headers=self.get_headers(),
            name="/api/v1/market/quotes"
        )
    
    @task(3)  # Weight 3
    def view_portfolio(self):
        """View portfolio details."""
        if not self.portfolio_id:
            return
            
        self.client.get(
            f"/api/v1/portfolios/{self.portfolio_id}",
            headers=self.get_headers(),
            name="/api/v1/portfolios/[id]"
        )
    
    @task(2)  # Weight 2
    def view_positions(self):
        """View current positions."""
        if not self.portfolio_id:
            return
            
        self.client.get(
            f"/api/v1/portfolios/{self.portfolio_id}/positions",
            headers=self.get_headers(),
            name="/api/v1/portfolios/[id]/positions"
        )
    
    @task(2)  # Weight 2
    def view_watchlist(self):
        """View watchlist."""
        self.client.get(
            "/api/v1/watchlists",
            headers=self.get_headers(),
            name="/api/v1/watchlists"
        )
    
    @task(1)  # Weight 1 - least frequent
    def place_order(self):
        """Place a paper trade order."""
        if not self.portfolio_id:
            return
        
        symbol = random.choice(TEST_SYMBOLS)
        quantity = random.randint(1, 10)
        side = random.choice(["buy", "sell"])
        
        self.client.post(
            f"/api/v1/portfolios/{self.portfolio_id}/orders",
            headers=self.get_headers(),
            json={
                "symbol": symbol,
                "quantity": quantity,
                "side": side,
                "order_type": "market"
            },
            name="/api/v1/portfolios/[id]/orders"
        )
    
    @task(1)
    def view_trade_history(self):
        """View trade history."""
        if not self.portfolio_id:
            return
            
        self.client.get(
            f"/api/v1/portfolios/{self.portfolio_id}/trades",
            headers=self.get_headers(),
            name="/api/v1/portfolios/[id]/trades"
        )
    
    @task(1)
    def view_analytics(self):
        """View portfolio analytics."""
        if not self.portfolio_id:
            return
            
        self.client.get(
            f"/api/v1/analytics/portfolio/{self.portfolio_id}",
            headers=self.get_headers(),
            name="/api/v1/analytics/portfolio/[id]"
        )


class APIOnlyUser(HttpUser):
    """
    Simulates an API-only user (no auth required endpoints).
    Used for testing public endpoints under load.
    """
    
    wait_time = between(0.5, 2)
    
    @task(5)
    def health_check(self):
        """Check API health."""
        self.client.get("/health", name="/health")
    
    @task(3)
    def ready_check(self):
        """Check API readiness."""
        self.client.get("/ready", name="/ready")
    
    @task(2)
    def get_market_status(self):
        """Get market status."""
        self.client.get("/api/v1/market/status", name="/api/v1/market/status")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    logger.info("Load test starting...")
    if isinstance(environment.runner, MasterRunner):
        logger.info("Running in distributed mode (master)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    logger.info("Load test completed")
    
    # Log summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    if stats.total.num_requests > 0:
        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        logger.info(f"Failure rate: {failure_rate:.2f}%")
