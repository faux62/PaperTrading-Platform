"""
PaperTrading Platform - Currency Service (Minimal)

This module contains only the essential currency utilities.
The IBKR-style CurrencyService class has been removed.

For currency conversions, use:
    from app.utils.currency import convert

The cash_balances table has been deprecated and removed.
Use portfolio.cash_balance (Single Currency Model) instead.
"""
from typing import Optional


# Currency symbols for display
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'CHF': 'CHF',
    'JPY': '¥',
    'CAD': 'C$',
    'AUD': 'A$',
    'HKD': 'HK$',
    'SGD': 'S$',
    'CNY': '¥',
}

# Supported currencies
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SGD', 'CNY']


def get_symbol_currency(symbol: str, exchange: Optional[str] = None) -> str:
    """
    Determine the native currency of a symbol based on exchange or symbol suffix.
    
    Args:
        symbol: The stock symbol (e.g., 'AAPL', 'VOD.L', 'SAP.DE')
        exchange: Optional exchange name (e.g., 'NYSE', 'LSE', 'XETRA')
    
    Returns:
        Currency code (e.g., 'USD', 'GBP', 'EUR')
    """
    # Exchange to currency mapping
    exchange_currencies = {
        'NYSE': 'USD', 'NASDAQ': 'USD', 'AMEX': 'USD', 'ARCA': 'USD',
        'LSE': 'GBP', 'LON': 'GBP',
        'XETRA': 'EUR', 'FRA': 'EUR', 'ETR': 'EUR',
        'PAR': 'EUR', 'EPA': 'EUR',
        'AMS': 'EUR', 'AEX': 'EUR',
        'MIL': 'EUR', 'BIT': 'EUR',
        'TSE': 'JPY', 'TYO': 'JPY',
        'HKEX': 'HKD', 'HKG': 'HKD',
        'SGX': 'SGD', 'SES': 'SGD',
        'ASX': 'AUD',
        'TSX': 'CAD', 'TOR': 'CAD',
        'SIX': 'CHF', 'SWX': 'CHF', 'EBS': 'CHF',
    }
    
    # Check exchange first
    if exchange and exchange.upper() in exchange_currencies:
        return exchange_currencies[exchange.upper()]
    
    # Check symbol suffix (Yahoo Finance style: VOD.L, SAP.DE, etc.)
    if '.' in symbol:
        suffix = symbol.split('.')[-1].upper()
        suffix_currencies = {
            'L': 'GBP',      # London
            'DE': 'EUR',     # Germany (XETRA)
            'F': 'EUR',      # Frankfurt
            'PA': 'EUR',     # Paris
            'AS': 'EUR',     # Amsterdam
            'MI': 'EUR',     # Milan
            'MC': 'EUR',     # Madrid
            'BR': 'EUR',     # Brussels
            'T': 'JPY',      # Tokyo
            'HK': 'HKD',     # Hong Kong
            'SI': 'SGD',     # Singapore
            'AX': 'AUD',     # Australia
            'TO': 'CAD',     # Toronto
            'SW': 'CHF',     # Swiss
            'VX': 'CHF',     # Swiss (SIX)
        }
        if suffix in suffix_currencies:
            return suffix_currencies[suffix]
    
    # Default to USD for US markets
    return 'USD'


def get_currency_symbol(currency: str) -> str:
    """
    Get the display symbol for a currency code.
    
    Args:
        currency: Currency code (e.g., 'USD', 'EUR')
    
    Returns:
        Currency symbol (e.g., '$', '€')
    """
    return CURRENCY_SYMBOLS.get(currency.upper(), currency)
