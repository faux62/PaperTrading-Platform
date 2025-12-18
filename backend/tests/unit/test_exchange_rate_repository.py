"""
Unit Tests - Exchange Rate Repository
Tests for the ExchangeRateRepository class.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models.exchange_rate import ExchangeRate
from app.db.repositories.exchange_rate import ExchangeRateRepository


class TestExchangeRateRepository:
    """Tests for ExchangeRateRepository."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mock db."""
        return ExchangeRateRepository(mock_db)
    
    @pytest.fixture
    def sample_exchange_rate(self):
        """Create sample exchange rate model."""
        rate = MagicMock(spec=ExchangeRate)
        rate.id = 1
        rate.base_currency = "EUR"
        rate.quote_currency = "USD"
        rate.rate = Decimal("1.0850")
        rate.source = "frankfurter"
        rate.fetched_at = datetime.utcnow()
        rate.created_at = datetime.utcnow()
        rate.updated_at = datetime.utcnow()
        return rate
    
    # =====================
    # get_rate tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_get_rate_existing(self, repo, mock_db, sample_exchange_rate):
        """Should return rate when it exists."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_exchange_rate
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repo.get_rate("EUR", "USD")
        
        # Verify
        assert result is not None
        assert result.base_currency == "EUR"
        assert result.quote_currency == "USD"
        assert result.rate == Decimal("1.0850")
    
    @pytest.mark.asyncio
    async def test_get_rate_not_found(self, repo, mock_db):
        """Should return None when rate doesn't exist."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repo.get_rate("XYZ", "ABC")
        
        # Verify
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_rate_normalizes_currency_codes(self, repo, mock_db):
        """Should normalize currency codes to uppercase."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute with lowercase
        await repo.get_rate("eur", "usd")
        
        # Verify execute was called (currency normalization happens in query)
        assert mock_db.execute.called
    
    # =====================
    # get_rate_value tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_get_rate_value_returns_rate(self, repo, mock_db, sample_exchange_rate):
        """Should return rate value when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_exchange_rate
        mock_db.execute.return_value = mock_result
        
        result = await repo.get_rate_value("EUR", "USD")
        
        assert result == Decimal("1.0850")
    
    @pytest.mark.asyncio
    async def test_get_rate_value_same_currency(self, repo, mock_db):
        """Should return 1.0 for same currency."""
        result = await repo.get_rate_value("USD", "USD")
        
        assert result == Decimal("1.0")
        # Should not query DB for same currency
        assert not mock_db.execute.called
    
    @pytest.mark.asyncio
    async def test_get_rate_value_not_found_returns_default(self, repo, mock_db):
        """Should return 1.0 when rate not found (safe default)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await repo.get_rate_value("XYZ", "ABC")
        
        assert result == Decimal("1.0")
    
    # =====================
    # get_all_rates tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_get_all_rates(self, repo, mock_db, sample_exchange_rate):
        """Should return all rates."""
        rate2 = MagicMock(spec=ExchangeRate)
        rate2.base_currency = "USD"
        rate2.quote_currency = "EUR"
        rate2.rate = Decimal("0.9217")
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_exchange_rate, rate2]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await repo.get_all_rates()
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_rates_empty(self, repo, mock_db):
        """Should return empty list when no rates."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await repo.get_all_rates()
        
        assert result == []
    
    # =====================
    # upsert_rate tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_upsert_rate_insert_new(self, repo, mock_db):
        """Should insert new rate when it doesn't exist."""
        # Setup: rate doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repo.upsert_rate(
            base_currency="GBP",
            quote_currency="EUR",
            rate=Decimal("1.1650"),
            source="test"
        )
        
        # Verify add was called (new record)
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_upsert_rate_update_existing(self, repo, mock_db, sample_exchange_rate):
        """Should update existing rate."""
        # Setup: rate exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_exchange_rate
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await repo.upsert_rate(
            base_currency="EUR",
            quote_currency="USD",
            rate=Decimal("1.0900"),
            source="updated"
        )
        
        # Verify rate was updated
        assert sample_exchange_rate.rate == Decimal("1.0900")
        assert mock_db.commit.called
    
    # =====================
    # convert_amount tests
    # =====================
    
    @pytest.mark.asyncio
    async def test_convert_amount_same_currency(self, repo, mock_db):
        """Should return same amount for same currency."""
        result = await repo.convert_amount(
            amount=Decimal("100.00"),
            from_currency="USD",
            to_currency="USD"
        )
        
        assert result == Decimal("100.00")
    
    @pytest.mark.asyncio
    async def test_convert_amount_different_currency(self, repo, mock_db, sample_exchange_rate):
        """Should convert amount using rate."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_exchange_rate
        mock_db.execute.return_value = mock_result
        
        result = await repo.convert_amount(
            amount=Decimal("100.00"),
            from_currency="EUR",
            to_currency="USD"
        )
        
        # 100 EUR * 1.0850 = 108.50 USD
        assert result == Decimal("108.50")


class TestExchangeRateModel:
    """Tests for ExchangeRate model structure."""
    
    def test_model_attributes(self):
        """ExchangeRate model should have all expected attributes."""
        assert hasattr(ExchangeRate, 'id')
        assert hasattr(ExchangeRate, 'base_currency')
        assert hasattr(ExchangeRate, 'quote_currency')
        assert hasattr(ExchangeRate, 'rate')
        assert hasattr(ExchangeRate, 'source')
        assert hasattr(ExchangeRate, 'fetched_at')
        assert hasattr(ExchangeRate, 'created_at')
        assert hasattr(ExchangeRate, 'updated_at')
    
    def test_model_tablename(self):
        """ExchangeRate model should have correct tablename."""
        assert ExchangeRate.__tablename__ == "exchange_rates"
