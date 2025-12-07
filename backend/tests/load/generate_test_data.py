#!/usr/bin/env python3
"""
Generate Test Data for Load Testing
====================================

Creates:
- 5 test users
- 3 portfolios per user
- 20-50 positions per portfolio
- 100+ trades per portfolio

Usage:
    python tests/load/generate_test_data.py
    
Or with custom base URL:
    TEST_BASE_URL=http://192.168.1.100:8000 python tests/load/generate_test_data.py
"""
import asyncio
import aiohttp
import random
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional

# Configuration
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# Test data configuration
NUM_USERS = 5
PORTFOLIOS_PER_USER = 3
POSITIONS_PER_PORTFOLIO = (20, 50)  # Min, max
TRADES_PER_PORTFOLIO = 100

# Stock symbols for testing
SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC", "NFLX",
    "DIS", "PYPL", "ADBE", "CRM", "ORCL", "IBM", "CSCO", "QCOM", "TXN", "AVGO",
    "V", "MA", "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK",
    "JNJ", "PFE", "UNH", "MRK", "ABBV", "LLY", "TMO", "ABT", "BMY", "AMGN",
    "XOM", "CVX", "COP", "EOG", "SLB", "KO", "PEP", "MCD", "SBUX", "NKE"
]


class TestDataGenerator:
    """Generates test data via API calls."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.users_created = []
        self.portfolios_created = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        token: str = None,
        **kwargs
    ) -> tuple[int, dict]:
        """Make API request."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{self.base_url}{API_PREFIX}{endpoint}"
        
        async with self.session.request(method, url, headers=headers, **kwargs) as resp:
            try:
                data = await resp.json()
            except:
                data = {}
            return resp.status, data
    
    async def create_user(self, email: str, password: str) -> Optional[Dict]:
        """Create a test user."""
        username = email.split('@')[0]  # Use email prefix as username
        status, data = await self._request(
            "POST", "/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "full_name": f"Load Test User {username}"
            }
        )
        
        if status in (200, 201):
            print(f"  ✓ Created user: {email}")
            return data
        elif status == 400 and "already" in str(data).lower():
            print(f"  → User exists: {email}")
            return {"email": email}  # User already exists
        else:
            print(f"  ✗ Failed to create user {email}: {data}")
            return None
    
    async def login(self, email: str, password: str) -> Optional[str]:
        """Login and get token (OAuth2 form-data format)."""
        # OAuth2PasswordRequestForm expects form-data, not JSON
        async with self.session.post(
            f"{self.base_url}{API_PREFIX}/auth/login",
            data={"username": email, "password": password}  # form-data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
        return None
    
    async def create_portfolio(
        self, 
        token: str, 
        name: str,
        initial_capital: float = 100000.0
    ) -> Optional[Dict]:
        """Create a portfolio."""
        status, data = await self._request(
            "POST", "/portfolios/",
            token=token,
            json={
                "name": name,
                "description": f"Load test portfolio - {name}",
                "initial_capital": initial_capital,
                "currency": "USD",
                "risk_profile": random.choice(["prudent", "balanced", "aggressive"])
            }
        )
        
        if status in (200, 201):
            print(f"    ✓ Created portfolio: {name} (ID: {data.get('id')})")
            return data
        else:
            print(f"    ✗ Failed to create portfolio {name}: {data}")
            return None
    
    async def create_position(
        self,
        token: str,
        portfolio_id: int,
        symbol: str,
        quantity: int,
        avg_cost: float
    ) -> Optional[Dict]:
        """Create a position by executing a buy trade."""
        status, data = await self._request(
            "POST", "/trades/orders",  # Correct endpoint
            token=token,
            json={
                "portfolio_id": portfolio_id,
                "symbol": symbol,
                "trade_type": "buy",
                "order_type": "market",
                "quantity": quantity
                # price is simulated for market orders
            }
        )
        
        if status in (200, 201):
            return data
        return None
    
    async def create_trade(
        self,
        token: str,
        portfolio_id: int,
        symbol: str,
        trade_type: str,
        quantity: int,
        price: float
    ) -> Optional[Dict]:
        """Create a trade."""
        status, data = await self._request(
            "POST", "/trades/orders",  # Correct endpoint
            token=token,
            json={
                "portfolio_id": portfolio_id,
                "symbol": symbol,
                "trade_type": trade_type,
                "order_type": "market",
                "quantity": quantity
            }
        )
        return data if status in (200, 201) else None
    
    async def get_portfolios(self, token: str) -> List[Dict]:
        """Get user's portfolios."""
        status, data = await self._request("GET", "/portfolios/", token=token)
        return data if status == 200 and isinstance(data, list) else []
    
    async def generate_all(self):
        """Generate all test data."""
        print("\n" + "="*60)
        print("Generating Load Test Data")
        print("="*60)
        
        # Step 1: Create users
        print("\n📝 Creating test users...")
        for i in range(1, NUM_USERS + 1):
            email = f"loadtest{i}@test.com"
            password = "LoadTest123!"
            
            user = await self.create_user(email, password)
            if user:
                self.users_created.append({
                    "email": email,
                    "password": password
                })
        
        print(f"\n   Total users: {len(self.users_created)}")
        
        # Step 2: Create portfolios and positions for each user
        print("\n📊 Creating portfolios and positions...")
        
        for user in self.users_created:
            token = await self.login(user["email"], user["password"])
            if not token:
                print(f"  ✗ Could not login as {user['email']}")
                continue
            
            print(f"\n  User: {user['email']}")
            
            # Check existing portfolios
            existing = await self.get_portfolios(token)
            portfolios_to_create = PORTFOLIOS_PER_USER - len(existing)
            
            if portfolios_to_create <= 0:
                print(f"    → Already has {len(existing)} portfolios")
                continue
            
            # Create portfolios
            for j in range(1, portfolios_to_create + 1):
                portfolio_name = f"LoadTest Portfolio {j}"
                initial_capital = random.uniform(50000, 200000)
                
                portfolio = await self.create_portfolio(
                    token, portfolio_name, initial_capital
                )
                
                if not portfolio:
                    continue
                
                portfolio_id = portfolio["id"]
                self.portfolios_created.append(portfolio)
                
                # Create positions
                num_positions = random.randint(*POSITIONS_PER_PORTFOLIO)
                symbols_used = random.sample(SYMBOLS, min(num_positions, len(SYMBOLS)))
                
                positions_created = 0
                for symbol in symbols_used:
                    quantity = random.randint(10, 500)
                    price = random.uniform(20, 500)
                    
                    result = await self.create_position(
                        token, portfolio_id, symbol, quantity, price
                    )
                    if result:
                        positions_created += 1
                
                print(f"      Created {positions_created} positions")
                
                # Create additional trades
                trades_created = 0
                for _ in range(TRADES_PER_PORTFOLIO - num_positions):
                    symbol = random.choice(symbols_used)
                    trade_type = random.choice(["buy", "sell"])
                    quantity = random.randint(1, 50)
                    price = random.uniform(20, 500)
                    
                    result = await self.create_trade(
                        token, portfolio_id, symbol, trade_type, quantity, price
                    )
                    if result:
                        trades_created += 1
                
                print(f"      Created {trades_created} additional trades")
        
        # Summary
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        print(f"  Users created: {len(self.users_created)}")
        print(f"  Portfolios created: {len(self.portfolios_created)}")
        print("\n  Test credentials:")
        for user in self.users_created[:3]:
            print(f"    - {user['email']} / {user['password']}")
        
        print("\n✅ Test data generation complete!")
        print("   You can now run: pytest tests/load/test_load_stability.py -v")


async def main():
    """Main entry point."""
    async with TestDataGenerator() as generator:
        await generator.generate_all()


if __name__ == "__main__":
    print(f"Using base URL: {BASE_URL}")
    asyncio.run(main())
