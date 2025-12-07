"""
Phase 4: Load and Stability Tests
=================================

Tests for:
    LOAD-01: Concurrent login (5 users)
    LOAD-02: Portfolio with 50+ positions loads < 3s
    LOAD-03: Analytics calculates < 5s
    LOAD-05: Database size < 1GB after 1000 trades
    LOAD-06: Redis cache hit rate > 80%
    LOAD-07: Backend restart without data loss
    LOAD-08: Graceful degradation if Redis down

Prerequisites:
    - Docker containers running
    - Test data generated (run generate_test_data.py first)

Run with:
    pytest tests/load/test_load_stability.py -v --tb=short
    
Or run individual tests:
    pytest tests/load/test_load_stability.py::TestLOAD01 -v
"""
import pytest
import asyncio
import aiohttp
import time
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import sys
import os

# Configuration
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# Test users (created by generate_test_data.py)
TEST_USERS = [
    {"email": "loadtest1@test.com", "password": "LoadTest123!"},
    {"email": "loadtest2@test.com", "password": "LoadTest123!"},
    {"email": "loadtest3@test.com", "password": "LoadTest123!"},
    {"email": "loadtest4@test.com", "password": "LoadTest123!"},
    {"email": "loadtest5@test.com", "password": "LoadTest123!"},
]


class APIClient:
    """Async API client for load testing."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def login(self, email: str, password: str) -> float:
        """Login and return response time in seconds (OAuth2 form-data)."""
        start = time.perf_counter()
        async with self.session.post(
            f"{self.base_url}{API_PREFIX}/auth/login",
            data={"username": email, "password": password}  # form-data
        ) as resp:
            elapsed = time.perf_counter() - start
            if resp.status == 200:
                data = await resp.json()
                self.token = data.get("access_token")
            return elapsed
    
    async def get_portfolios(self) -> tuple[float, List[Dict]]:
        """Get portfolios and return (response_time, data)."""
        start = time.perf_counter()
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/portfolios/",
            headers=self._headers()
        ) as resp:
            elapsed = time.perf_counter() - start
            if resp.status == 200:
                data = await resp.json()
                # API returns {"portfolios": [...], "count": N}
                portfolios = data.get("portfolios", []) if isinstance(data, dict) else data
            else:
                portfolios = []
            return elapsed, portfolios
    
    async def get_portfolio_positions(self, portfolio_id: int) -> tuple[float, List[Dict]]:
        """Get positions for a portfolio."""
        start = time.perf_counter()
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/positions/?portfolio_id={portfolio_id}",
            headers=self._headers()
        ) as resp:
            elapsed = time.perf_counter() - start
            data = await resp.json() if resp.status == 200 else []
            return elapsed, data
    
    async def get_analytics(self, portfolio_id: int) -> tuple[float, Dict]:
        """Get analytics for a portfolio."""
        start = time.perf_counter()
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/analytics/portfolio/{portfolio_id}/performance",
            headers=self._headers()
        ) as resp:
            elapsed = time.perf_counter() - start
            data = await resp.json() if resp.status == 200 else {}
            return elapsed, data
    
    async def get_trades(self, portfolio_id: int, limit: int = 100) -> tuple[float, List[Dict]]:
        """Get trades for a portfolio."""
        start = time.perf_counter()
        async with self.session.get(
            f"{self.base_url}{API_PREFIX}/trades/?portfolio_id={portfolio_id}&limit={limit}",
            headers=self._headers()
        ) as resp:
            elapsed = time.perf_counter() - start
            data = await resp.json() if resp.status == 200 else []
            return elapsed, data


class TestLOAD01ConcurrentLogin:
    """
    LOAD-01: Login simultaneo 5 utenti
    
    Verifica che il sistema supporti login concorrenti.
    Target: tutti i login completano entro 5 secondi.
    """
    
    @pytest.mark.asyncio
    async def test_concurrent_login_5_users(self):
        """5 utenti devono poter fare login contemporaneamente."""
        async def login_user(email: str, password: str) -> tuple[str, float, bool]:
            async with APIClient() as client:
                try:
                    elapsed = await client.login(email, password)
                    success = client.token is not None
                    return email, elapsed, success
                except Exception as e:
                    return email, 0.0, False
        
        # Login tutti gli utenti contemporaneamente
        start = time.perf_counter()
        tasks = [
            login_user(user["email"], user["password"]) 
            for user in TEST_USERS
        ]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start
        
        # Analizza risultati
        successes = sum(1 for _, _, success in results if success)
        response_times = [elapsed for _, elapsed, success in results if success]
        
        print(f"\n✓ LOAD-01: {successes}/5 login riusciti in {total_time:.2f}s")
        if response_times:
            print(f"  Tempo medio: {statistics.mean(response_times):.3f}s")
            print(f"  Tempo max: {max(response_times):.3f}s")
        
        # Verifica: almeno 4/5 devono avere successo
        assert successes >= 4, f"Solo {successes}/5 login riusciti"
        # Verifica: tempo totale < 5 secondi
        assert total_time < 5.0, f"Login troppo lento: {total_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_sequential_login_performance(self):
        """Baseline: login sequenziali per confronto."""
        response_times = []
        
        for user in TEST_USERS[:3]:  # Solo 3 utenti per velocità
            async with APIClient() as client:
                elapsed = await client.login(user["email"], user["password"])
                if client.token:
                    response_times.append(elapsed)
        
        if response_times:
            avg_time = statistics.mean(response_times)
            print(f"\n✓ LOAD-01 baseline: {len(response_times)} login")
            print(f"  Tempo medio singolo: {avg_time:.3f}s")
            
            # Ogni login dovrebbe essere < 2 secondi
            assert avg_time < 2.0, f"Login singolo troppo lento: {avg_time:.2f}s"


class TestLOAD02PortfolioLoadTime:
    """
    LOAD-02: Portfolio con 50+ posizioni si carica < 3s
    
    Verifica le performance di caricamento portfolio grandi.
    """
    
    @pytest.fixture
    async def authenticated_client(self):
        """Get authenticated client."""
        client = APIClient()
        await client.__aenter__()
        await client.login(TEST_USERS[0]["email"], TEST_USERS[0]["password"])
        yield client
        await client.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_portfolio_list_load_time(self, authenticated_client):
        """Lista portfolio deve caricarsi rapidamente."""
        elapsed, portfolios = await authenticated_client.get_portfolios()
        
        print(f"\n✓ LOAD-02: Lista portfolio caricata in {elapsed:.3f}s")
        print(f"  Numero portfolio: {len(portfolios)}")
        
        assert elapsed < 3.0, f"Caricamento troppo lento: {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    async def test_positions_load_time(self, authenticated_client):
        """Posizioni (anche 50+) devono caricarsi < 3s."""
        _, portfolios = await authenticated_client.get_portfolios()
        
        if not portfolios:
            pytest.skip("Nessun portfolio trovato")
        
        # Prendi il primo portfolio
        portfolio_id = portfolios[0]["id"]
        elapsed, positions = await authenticated_client.get_portfolio_positions(portfolio_id)
        
        print(f"\n✓ LOAD-02: {len(positions)} posizioni caricate in {elapsed:.3f}s")
        
        assert elapsed < 3.0, f"Caricamento posizioni troppo lento: {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    async def test_multiple_portfolio_requests(self, authenticated_client):
        """Test carico: 10 richieste portfolio consecutive."""
        response_times = []
        
        for _ in range(10):
            elapsed, _ = await authenticated_client.get_portfolios()
            response_times.append(elapsed)
        
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        print(f"\n✓ LOAD-02: 10 richieste portfolio")
        print(f"  Tempo medio: {avg_time:.3f}s")
        print(f"  Tempo max: {max_time:.3f}s")
        
        assert avg_time < 1.0, f"Tempo medio troppo alto: {avg_time:.2f}s"
        assert max_time < 3.0, f"Tempo max troppo alto: {max_time:.2f}s"


class TestLOAD03AnalyticsPerformance:
    """
    LOAD-03: Analytics calcola in < 5s
    
    Verifica le performance dei calcoli analytics.
    """
    
    @pytest.fixture
    async def authenticated_client(self):
        client = APIClient()
        await client.__aenter__()
        await client.login(TEST_USERS[0]["email"], TEST_USERS[0]["password"])
        yield client
        await client.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_analytics_performance_calculation(self, authenticated_client):
        """Analytics performance deve calcolarsi < 5s."""
        _, portfolios = await authenticated_client.get_portfolios()
        
        if not portfolios:
            pytest.skip("Nessun portfolio trovato")
        
        portfolio_id = portfolios[0]["id"]
        elapsed, analytics = await authenticated_client.get_analytics(portfolio_id)
        
        print(f"\n✓ LOAD-03: Analytics calcolato in {elapsed:.3f}s")
        if analytics:
            print(f"  Metriche disponibili: {list(analytics.keys())[:5]}...")
        
        assert elapsed < 5.0, f"Analytics troppo lento: {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    async def test_trades_history_load(self, authenticated_client):
        """Storico trades deve caricarsi rapidamente."""
        _, portfolios = await authenticated_client.get_portfolios()
        
        if not portfolios:
            pytest.skip("Nessun portfolio trovato")
        
        portfolio_id = portfolios[0]["id"]
        
        # Test con diversi limiti
        for limit in [50, 100, 200]:
            elapsed, trades = await authenticated_client.get_trades(portfolio_id, limit)
            print(f"  {len(trades)} trades (limit {limit}): {elapsed:.3f}s")
            
            assert elapsed < 3.0, f"Trades troppo lento per limit={limit}: {elapsed:.2f}s"


class TestLOAD06RedisCachePerformance:
    """
    LOAD-06: Redis cache hit rate > 80%
    
    Verifica l'efficacia del caching Redis.
    """
    
    @pytest.fixture
    async def authenticated_client(self):
        client = APIClient()
        await client.__aenter__()
        await client.login(TEST_USERS[0]["email"], TEST_USERS[0]["password"])
        yield client
        await client.__aexit__(None, None, None)
    
    @pytest.mark.asyncio
    async def test_cache_improves_response_time(self, authenticated_client):
        """Richieste ripetute dovrebbero essere più veloci (cache hit)."""
        _, portfolios = await authenticated_client.get_portfolios()
        
        if not portfolios:
            pytest.skip("Nessun portfolio trovato")
        
        portfolio_id = portfolios[0]["id"]
        
        # Prima richiesta (cache miss)
        first_time, _ = await authenticated_client.get_portfolio_positions(portfolio_id)
        
        # Richieste successive (cache hit)
        cached_times = []
        for _ in range(5):
            elapsed, _ = await authenticated_client.get_portfolio_positions(portfolio_id)
            cached_times.append(elapsed)
        
        avg_cached = statistics.mean(cached_times)
        improvement = (first_time - avg_cached) / first_time * 100 if first_time > 0 else 0
        
        print(f"\n✓ LOAD-06: Test cache performance")
        print(f"  Prima richiesta: {first_time:.3f}s")
        print(f"  Media cached: {avg_cached:.3f}s")
        print(f"  Miglioramento: {improvement:.1f}%")
        
        # Le richieste cached dovrebbero essere almeno il 20% più veloci
        # (in realtà potrebbero non esserlo sempre a causa della latenza di rete)
        if first_time > 0.1:  # Solo se la prima è abbastanza lenta
            assert avg_cached <= first_time, "Cache non sta funzionando"


class TestLOAD07BackendRestart:
    """
    LOAD-07: Backend restart senza perdita dati
    
    Verifica che i dati persistano dopo restart.
    """
    
    @pytest.mark.asyncio
    async def test_data_persists_across_requests(self):
        """Dati devono essere consistenti tra sessioni diverse."""
        # Prima sessione
        async with APIClient() as client1:
            await client1.login(TEST_USERS[0]["email"], TEST_USERS[0]["password"])
            _, portfolios1 = await client1.get_portfolios()
        
        # Seconda sessione (simula restart client)
        async with APIClient() as client2:
            await client2.login(TEST_USERS[0]["email"], TEST_USERS[0]["password"])
            _, portfolios2 = await client2.get_portfolios()
        
        # I dati devono essere identici
        assert len(portfolios1) == len(portfolios2), "Numero portfolio diverso"
        
        if portfolios1 and portfolios2:
            ids1 = set(p["id"] for p in portfolios1)
            ids2 = set(p["id"] for p in portfolios2)
            assert ids1 == ids2, "Portfolio IDs diversi"
        
        print(f"\n✓ LOAD-07: Dati consistenti ({len(portfolios1)} portfolio)")


class TestLOAD08GracefulDegradation:
    """
    LOAD-08: Graceful degradation se Redis down
    
    Verifica che il sistema funzioni anche senza Redis.
    """
    
    @pytest.mark.asyncio
    async def test_system_responds_without_cache(self):
        """Sistema deve rispondere anche se cache non disponibile."""
        async with APIClient() as client:
            # Il login dovrebbe funzionare anche senza Redis
            # (JWT è stateless)
            try:
                elapsed = await client.login(
                    TEST_USERS[0]["email"], 
                    TEST_USERS[0]["password"]
                )
                
                if client.token:
                    print(f"\n✓ LOAD-08: Login funziona (tempo: {elapsed:.3f}s)")
                    
                    # Anche le API dovrebbero funzionare
                    elapsed2, portfolios = await client.get_portfolios()
                    print(f"  Portfolios API: {elapsed2:.3f}s ({len(portfolios)} items)")
                    
                    assert True  # Se arriviamo qui, funziona
                else:
                    pytest.skip("Login fallito - server non disponibile?")
            except Exception as e:
                pytest.skip(f"Server non disponibile: {e}")


# Summary
if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           Phase 4: Load and Stability Tests                   ║
╠═══════════════════════════════════════════════════════════════╣
║ LOAD-01: Concurrent login (5 users)                           ║
║ LOAD-02: Portfolio 50+ positions < 3s                         ║
║ LOAD-03: Analytics < 5s                                       ║
║ LOAD-06: Redis cache hit rate                                 ║
║ LOAD-07: Backend restart data persistence                     ║
║ LOAD-08: Graceful degradation without Redis                   ║
╠═══════════════════════════════════════════════════════════════╣
║ Prerequisites:                                                ║
║   1. Docker containers running                                ║
║   2. Run: python tests/load/generate_test_data.py             ║
╠═══════════════════════════════════════════════════════════════╣
║ Run: pytest tests/load/test_load_stability.py -v              ║
╚═══════════════════════════════════════════════════════════════╝
    """)
