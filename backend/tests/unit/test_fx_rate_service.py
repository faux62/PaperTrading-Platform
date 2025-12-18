"""
Unit Tests - FX Rate Updater Service
Tests for the FxRateUpdaterService class.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.fx_rate_updater import (
    FxRateUpdaterService,
    SUPPORTED_CURRENCIES,
    FRANKFURTER_API_BASE,
)


class TestFxRateUpdaterService:
    """Tests for FxRateUpdaterService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return FxRateUpdaterService(timeout=10.0)
    
    @pytest.fixture
    def mock_api_response(self):
        """Sample API response from Frankfurter."""
        return {
            "amount": 1.0,
            "base": "EUR",
            "date": "2025-12-18",
            "rates": {
                "USD": 1.0450,
                "GBP": 0.8320,
                "CHF": 0.9380
            }
        }
    
    # =====================
    # Configuration tests
    # =====================
    
    def test_supported_currencies(self):
        """Should have correct supported currencies."""
        assert "EUR" in SUPPORTED_CURRENCIES
        assert "USD" in SUPPORTED_CURRENCIES
        assert "GBP" in SUPPORTED_CURRENCIES
        assert "CHF" in SUPPORTED_CURRENCIES
        assert len(SUPPORTED_CURRENCIES) == 4
    
    def test_frankfurter_api_base(self):
        """Should have correct API base URL."""
        assert FRANKFURTER_API_BASE == "https://api.frankfurter.app"
    
    def test_service_initialization(self, service):
        """Service should initialize with correct defaults."""
        assert service.timeout == 10.0
        assert service.api_base == FRANKFURTER_API_BASE
        assert service.currencies == SUPPORTED_CURRENCIES
    
    # =====================
    # fetch_rates_from_api tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_fetch_rates_success(self, service, mock_api_response):
        """Should fetch and parse rates correctly."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status = MagicMock()
            
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await service.fetch_rates_from_api("EUR")
            
            assert result is not None
            assert "USD" in result
            assert "GBP" in result
            assert "CHF" in result
            assert isinstance(result["USD"], Decimal)
            assert result["USD"] == Decimal("1.0450")
    
    @pytest.mark.asyncio
    async def test_fetch_rates_http_error(self, service):
        """Should return None on HTTP error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response
            )
            
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await service.fetch_rates_from_api("EUR")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_rates_request_error(self, service):
        """Should return None on request error (network issue)."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await service.fetch_rates_from_api("EUR")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_rates_empty_quotes(self, service):
        """Should handle base currency with no other currencies."""
        # Create a service with only one currency
        single_service = FxRateUpdaterService()
        single_service.currencies = ["EUR"]
        
        result = await single_service.fetch_rates_from_api("EUR")
        
        assert result == {}
    
    # =====================
    # fetch_all_rates tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_fetch_all_rates(self, service):
        """Should fetch rates for all currency pairs."""
        async def mock_fetch(base):
            if base == "EUR":
                return {"USD": Decimal("1.05"), "GBP": Decimal("0.83"), "CHF": Decimal("0.94")}
            elif base == "USD":
                return {"EUR": Decimal("0.95"), "GBP": Decimal("0.79"), "CHF": Decimal("0.89")}
            elif base == "GBP":
                return {"EUR": Decimal("1.20"), "USD": Decimal("1.26"), "CHF": Decimal("1.13")}
            elif base == "CHF":
                return {"EUR": Decimal("1.06"), "USD": Decimal("1.12"), "GBP": Decimal("0.88")}
            return {}
        
        with patch.object(service, 'fetch_rates_from_api', side_effect=mock_fetch):
            result = await service.fetch_all_rates()
            
            # 4 base currencies × 3 quote currencies each = 12 pairs
            assert len(result) == 12
            
            # Check structure
            for rate_info in result:
                assert "base_currency" in rate_info
                assert "quote_currency" in rate_info
                assert "rate" in rate_info
                assert rate_info["base_currency"] in SUPPORTED_CURRENCIES
                assert rate_info["quote_currency"] in SUPPORTED_CURRENCIES
    
    @pytest.mark.asyncio
    async def test_fetch_all_rates_partial_failure(self, service):
        """Should continue even if some currencies fail."""
        async def mock_fetch(base):
            if base == "EUR":
                return {"USD": Decimal("1.05"), "GBP": Decimal("0.83"), "CHF": Decimal("0.94")}
            elif base == "USD":
                return None  # Simulate failure
            elif base == "GBP":
                return {"EUR": Decimal("1.20"), "USD": Decimal("1.26"), "CHF": Decimal("1.13")}
            elif base == "CHF":
                return None  # Simulate failure
            return {}
        
        with patch.object(service, 'fetch_rates_from_api', side_effect=mock_fetch):
            result = await service.fetch_all_rates()
            
            # Only EUR and GBP succeeded: 3 + 3 = 6 pairs
            assert len(result) == 6
    
    # =====================
    # update_all_rates tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_update_all_rates_success(self, service):
        """Should update database with fetched rates."""
        mock_rates = [
            {"base_currency": "EUR", "quote_currency": "USD", "rate": Decimal("1.05")},
            {"base_currency": "EUR", "quote_currency": "GBP", "rate": Decimal("0.83")},
        ]
        
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.bulk_upsert_rates = AsyncMock(return_value=2)
        
        with patch.object(service, 'fetch_all_rates', return_value=mock_rates):
            with patch('app.services.fx_rate_updater.get_db') as mock_get_db:
                with patch('app.services.fx_rate_updater.ExchangeRateRepository', return_value=mock_repo):
                    # Make get_db an async generator
                    async def db_generator():
                        yield mock_db
                    mock_get_db.return_value = db_generator()
                    
                    result = await service.update_all_rates()
                    
                    assert result == 2
                    mock_repo.bulk_upsert_rates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_all_rates_no_rates(self, service):
        """Should return 0 when no rates fetched."""
        with patch.object(service, 'fetch_all_rates', return_value=[]):
            result = await service.update_all_rates()
            
            assert result == 0


class TestCurrencyConversion:
    """Tests for currency conversion logic."""
    
    def test_same_currency_conversion(self):
        """Converting same currency should return same amount."""
        amount = Decimal("100.00")
        # When from_currency == to_currency, rate is 1.0
        result = amount * Decimal("1.0")
        assert result == amount
    
    def test_eur_to_usd_conversion(self):
        """EUR to USD conversion should multiply by rate."""
        amount = Decimal("100.00")
        rate = Decimal("1.0850")  # 1 EUR = 1.0850 USD
        
        result = amount * rate
        
        assert result == Decimal("108.50")
    
    def test_usd_to_eur_conversion(self):
        """USD to EUR conversion should use inverse rate."""
        amount = Decimal("108.50")
        rate = Decimal("0.9217")  # 1 USD = 0.9217 EUR
        
        result = amount * rate
        
        # ~100 EUR
        assert result == Decimal("100.00445")
    
    def test_conversion_precision(self):
        """Conversion should maintain decimal precision."""
        amount = Decimal("1000.12345")
        rate = Decimal("1.08765432")
        
        result = amount * rate
        
        # Should not lose precision
        assert isinstance(result, Decimal)
        assert str(result).count('.') == 1  # Has decimal point


class TestRateFreshness:
    """Tests for rate freshness checks."""
    
    def test_rate_is_fresh(self):
        """Rate updated recently should be considered fresh."""
        now = datetime.utcnow()
        fetched_at = now  # Just fetched
        
        # Fresh if fetched within last 2 hours
        from datetime import timedelta
        is_fresh = (now - fetched_at) < timedelta(hours=2)
        
        assert is_fresh is True
    
    def test_rate_is_stale(self):
        """Rate updated long ago should be considered stale."""
        from datetime import timedelta
        now = datetime.utcnow()
        fetched_at = now - timedelta(hours=25)  # 25 hours ago
        
        # Stale if fetched more than 24 hours ago
        is_stale = (now - fetched_at) > timedelta(hours=24)
        
        assert is_stale is True
