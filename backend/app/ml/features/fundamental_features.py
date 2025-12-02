"""
Fundamental Features Calculator

Calculates fundamental analysis features:
- Valuation: P/E, P/B, P/S, EV/EBITDA
- Profitability: ROE, ROA, ROI, Profit Margin
- Growth: Revenue Growth, EPS Growth
- Financial Health: Debt/Equity, Current Ratio, Quick Ratio
- Dividends: Yield, Payout Ratio
"""
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class FundamentalFeatures:
    """Container for fundamental analysis features."""
    symbol: str
    timestamp: str
    
    # Valuation Ratios
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ev_revenue: Optional[float] = None
    
    # Profitability Ratios
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    roi: Optional[float] = None  # Return on Investment
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    profit_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    
    # Growth Metrics
    revenue_growth_yoy: Optional[float] = None
    revenue_growth_qoq: Optional[float] = None
    eps_growth_yoy: Optional[float] = None
    earnings_growth: Optional[float] = None
    book_value_growth: Optional[float] = None
    
    # Financial Health
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    cash_ratio: Optional[float] = None
    
    # Efficiency
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    
    # Dividend Metrics
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    dividend_growth_5y: Optional[float] = None
    
    # Per Share Metrics
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None
    book_value_per_share: Optional[float] = None
    revenue_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None
    
    # Market Data
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    beta: Optional[float] = None
    shares_outstanding: Optional[float] = None
    float_shares: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def to_feature_vector(self) -> list[float]:
        """Convert to numerical feature vector for ML."""
        features = []
        for key, value in self.__dict__.items():
            if key in ('symbol', 'timestamp'):
                continue
            if isinstance(value, (int, float)):
                # Handle potential NaN/Inf values
                if value is None or value != value:  # NaN check
                    features.append(0.0)
                elif abs(value) == float('inf'):
                    features.append(0.0)
                else:
                    features.append(float(value))
            elif value is None:
                features.append(0.0)
        return features


@dataclass
class FinancialStatements:
    """Container for financial statement data."""
    # Income Statement
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    short_term_debt: Optional[float] = None
    inventory: Optional[float] = None
    accounts_receivable: Optional[float] = None
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None
    dividends_paid: Optional[float] = None
    
    # Shares
    shares_outstanding: Optional[float] = None
    shares_diluted: Optional[float] = None


class FundamentalFeaturesCalculator:
    """
    Calculates fundamental analysis features from financial data.
    
    Usage:
        calc = FundamentalFeaturesCalculator()
        features = calc.calculate_all(
            symbol="AAPL",
            current_price=185.50,
            statements=financial_statements,
            prev_year_statements=last_year_statements,
        )
    """
    
    def __init__(self):
        pass
    
    def calculate_all(
        self,
        symbol: str,
        current_price: float,
        statements: FinancialStatements,
        prev_year_statements: Optional[FinancialStatements] = None,
        prev_quarter_statements: Optional[FinancialStatements] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> FundamentalFeatures:
        """
        Calculate all fundamental features.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            statements: Current period financial statements
            prev_year_statements: Previous year statements for growth calc
            prev_quarter_statements: Previous quarter for QoQ growth
            market_data: Additional market data (beta, market cap, etc.)
        
        Returns:
            FundamentalFeatures with all calculated metrics
        """
        timestamp = datetime.utcnow().isoformat()
        features = FundamentalFeatures(symbol=symbol, timestamp=timestamp)
        
        try:
            # Calculate market cap and enterprise value first
            features.shares_outstanding = statements.shares_outstanding
            if statements.shares_outstanding and current_price:
                features.market_cap = current_price * statements.shares_outstanding
                
                # Enterprise Value = Market Cap + Total Debt - Cash
                total_debt = statements.total_debt or 0
                cash = statements.cash_and_equivalents or 0
                features.enterprise_value = features.market_cap + total_debt - cash
            
            # Valuation Ratios
            features.pe_ratio = self._calculate_pe(current_price, statements.eps)
            features.pb_ratio = self._calculate_pb(current_price, statements)
            features.ps_ratio = self._calculate_ps(features.market_cap, statements.revenue)
            features.ev_ebitda = self._calculate_ev_ebitda(features.enterprise_value, statements.ebitda)
            features.ev_revenue = self._calculate_ev_revenue(features.enterprise_value, statements.revenue)
            
            # Profitability Ratios
            features.roe = self._calculate_roe(statements)
            features.roa = self._calculate_roa(statements)
            features.gross_margin = self._calculate_margin(statements.gross_profit, statements.revenue)
            features.operating_margin = self._calculate_margin(statements.operating_income, statements.revenue)
            features.profit_margin = self._calculate_margin(statements.net_income, statements.revenue)
            features.ebitda_margin = self._calculate_margin(statements.ebitda, statements.revenue)
            
            # Growth Metrics
            if prev_year_statements:
                features.revenue_growth_yoy = self._calculate_growth(
                    statements.revenue, prev_year_statements.revenue
                )
                features.eps_growth_yoy = self._calculate_growth(
                    statements.eps, prev_year_statements.eps
                )
                features.earnings_growth = self._calculate_growth(
                    statements.net_income, prev_year_statements.net_income
                )
            
            if prev_quarter_statements:
                features.revenue_growth_qoq = self._calculate_growth(
                    statements.revenue, prev_quarter_statements.revenue
                )
            
            # Financial Health
            features.debt_to_equity = self._calculate_debt_to_equity(statements)
            features.debt_to_assets = self._calculate_debt_to_assets(statements)
            features.current_ratio = self._calculate_current_ratio(statements)
            features.quick_ratio = self._calculate_quick_ratio(statements)
            features.interest_coverage = self._calculate_interest_coverage(statements)
            features.cash_ratio = self._calculate_cash_ratio(statements)
            
            # Efficiency
            features.asset_turnover = self._calculate_asset_turnover(statements)
            features.inventory_turnover = self._calculate_inventory_turnover(statements)
            features.receivables_turnover = self._calculate_receivables_turnover(statements)
            
            # Dividend Metrics
            features.dividend_yield = self._calculate_dividend_yield(statements, current_price)
            features.payout_ratio = self._calculate_payout_ratio(statements)
            
            # Per Share Metrics
            features.eps = statements.eps
            features.eps_diluted = statements.eps_diluted
            features.book_value_per_share = self._calculate_book_value_per_share(statements)
            features.revenue_per_share = self._calculate_per_share(
                statements.revenue, statements.shares_outstanding
            )
            features.free_cash_flow_per_share = self._calculate_per_share(
                statements.free_cash_flow, statements.shares_outstanding
            )
            
            # Market Data
            if market_data:
                features.beta = market_data.get('beta')
                features.forward_pe = market_data.get('forward_pe')
                features.peg_ratio = market_data.get('peg_ratio')
                features.float_shares = market_data.get('float_shares')
                features.dividend_growth_5y = market_data.get('dividend_growth_5y')
            
        except Exception as e:
            logger.warning(f"Error calculating fundamental features for {symbol}: {e}")
        
        return features
    
    def _calculate_pe(self, price: float, eps: Optional[float]) -> Optional[float]:
        """Calculate Price-to-Earnings ratio."""
        if eps is None or eps <= 0:
            return None
        return price / eps
    
    def _calculate_pb(self, price: float, statements: FinancialStatements) -> Optional[float]:
        """Calculate Price-to-Book ratio."""
        if not statements.total_equity or not statements.shares_outstanding:
            return None
        if statements.shares_outstanding <= 0:
            return None
        
        book_value_per_share = statements.total_equity / statements.shares_outstanding
        if book_value_per_share <= 0:
            return None
        
        return price / book_value_per_share
    
    def _calculate_ps(self, market_cap: Optional[float], revenue: Optional[float]) -> Optional[float]:
        """Calculate Price-to-Sales ratio."""
        if not market_cap or not revenue or revenue <= 0:
            return None
        return market_cap / revenue
    
    def _calculate_ev_ebitda(self, ev: Optional[float], ebitda: Optional[float]) -> Optional[float]:
        """Calculate EV/EBITDA ratio."""
        if not ev or not ebitda or ebitda <= 0:
            return None
        return ev / ebitda
    
    def _calculate_ev_revenue(self, ev: Optional[float], revenue: Optional[float]) -> Optional[float]:
        """Calculate EV/Revenue ratio."""
        if not ev or not revenue or revenue <= 0:
            return None
        return ev / revenue
    
    def _calculate_roe(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Return on Equity."""
        if not statements.net_income or not statements.total_equity:
            return None
        if statements.total_equity <= 0:
            return None
        return (statements.net_income / statements.total_equity) * 100
    
    def _calculate_roa(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Return on Assets."""
        if not statements.net_income or not statements.total_assets:
            return None
        if statements.total_assets <= 0:
            return None
        return (statements.net_income / statements.total_assets) * 100
    
    def _calculate_margin(self, numerator: Optional[float], revenue: Optional[float]) -> Optional[float]:
        """Calculate margin percentage."""
        if not numerator or not revenue or revenue <= 0:
            return None
        return (numerator / revenue) * 100
    
    def _calculate_growth(self, current: Optional[float], previous: Optional[float]) -> Optional[float]:
        """Calculate growth rate."""
        if not current or not previous or previous == 0:
            return None
        return ((current - previous) / abs(previous)) * 100
    
    def _calculate_debt_to_equity(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Debt-to-Equity ratio."""
        total_debt = statements.total_debt or 0
        if not statements.total_equity or statements.total_equity <= 0:
            return None
        return total_debt / statements.total_equity
    
    def _calculate_debt_to_assets(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Debt-to-Assets ratio."""
        total_debt = statements.total_debt or 0
        if not statements.total_assets or statements.total_assets <= 0:
            return None
        return total_debt / statements.total_assets
    
    def _calculate_current_ratio(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Current Ratio."""
        if not statements.current_assets or not statements.current_liabilities:
            return None
        if statements.current_liabilities <= 0:
            return None
        return statements.current_assets / statements.current_liabilities
    
    def _calculate_quick_ratio(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Quick Ratio (Acid Test)."""
        if not statements.current_assets or not statements.current_liabilities:
            return None
        if statements.current_liabilities <= 0:
            return None
        
        inventory = statements.inventory or 0
        quick_assets = statements.current_assets - inventory
        return quick_assets / statements.current_liabilities
    
    def _calculate_interest_coverage(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Interest Coverage Ratio."""
        if not statements.ebitda:
            return None
        
        # Approximate interest expense from operating income vs net income
        # In real implementation, would use actual interest expense
        operating_income = statements.operating_income or 0
        net_income = statements.net_income or 0
        interest_expense = operating_income - net_income
        
        if interest_expense <= 0:
            return None
        
        return statements.ebitda / interest_expense
    
    def _calculate_cash_ratio(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Cash Ratio."""
        if not statements.cash_and_equivalents or not statements.current_liabilities:
            return None
        if statements.current_liabilities <= 0:
            return None
        return statements.cash_and_equivalents / statements.current_liabilities
    
    def _calculate_asset_turnover(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Asset Turnover."""
        if not statements.revenue or not statements.total_assets:
            return None
        if statements.total_assets <= 0:
            return None
        return statements.revenue / statements.total_assets
    
    def _calculate_inventory_turnover(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Inventory Turnover."""
        if not statements.cost_of_revenue or not statements.inventory:
            return None
        if statements.inventory <= 0:
            return None
        return statements.cost_of_revenue / statements.inventory
    
    def _calculate_receivables_turnover(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Receivables Turnover."""
        if not statements.revenue or not statements.accounts_receivable:
            return None
        if statements.accounts_receivable <= 0:
            return None
        return statements.revenue / statements.accounts_receivable
    
    def _calculate_dividend_yield(
        self, 
        statements: FinancialStatements, 
        price: float
    ) -> Optional[float]:
        """Calculate Dividend Yield."""
        if not statements.dividends_paid or not statements.shares_outstanding or price <= 0:
            return None
        
        dividends_per_share = abs(statements.dividends_paid) / statements.shares_outstanding
        return (dividends_per_share / price) * 100
    
    def _calculate_payout_ratio(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Dividend Payout Ratio."""
        if not statements.dividends_paid or not statements.net_income:
            return None
        if statements.net_income <= 0:
            return None
        return (abs(statements.dividends_paid) / statements.net_income) * 100
    
    def _calculate_book_value_per_share(self, statements: FinancialStatements) -> Optional[float]:
        """Calculate Book Value per Share."""
        if not statements.total_equity or not statements.shares_outstanding:
            return None
        if statements.shares_outstanding <= 0:
            return None
        return statements.total_equity / statements.shares_outstanding
    
    def _calculate_per_share(
        self, 
        total_value: Optional[float], 
        shares: Optional[float]
    ) -> Optional[float]:
        """Calculate per-share value."""
        if not total_value or not shares or shares <= 0:
            return None
        return total_value / shares
    
    @staticmethod
    def get_feature_names() -> list[str]:
        """Get list of all feature names."""
        return [
            # Valuation
            'pe_ratio', 'forward_pe', 'peg_ratio', 'pb_ratio', 'ps_ratio',
            'ev_ebitda', 'ev_revenue',
            # Profitability
            'roe', 'roa', 'roi', 'gross_margin', 'operating_margin',
            'profit_margin', 'ebitda_margin',
            # Growth
            'revenue_growth_yoy', 'revenue_growth_qoq', 'eps_growth_yoy',
            'earnings_growth', 'book_value_growth',
            # Financial Health
            'debt_to_equity', 'debt_to_assets', 'current_ratio', 'quick_ratio',
            'interest_coverage', 'cash_ratio',
            # Efficiency
            'asset_turnover', 'inventory_turnover', 'receivables_turnover',
            # Dividend
            'dividend_yield', 'payout_ratio', 'dividend_growth_5y',
            # Per Share
            'eps', 'eps_diluted', 'book_value_per_share', 'revenue_per_share',
            'free_cash_flow_per_share',
            # Market
            'market_cap', 'enterprise_value', 'beta', 'shares_outstanding', 'float_shares',
        ]


# Module-level instance
calculator = FundamentalFeaturesCalculator()


def calculate_fundamental_features(
    symbol: str,
    current_price: float,
    statements: FinancialStatements,
    prev_year_statements: Optional[FinancialStatements] = None,
    prev_quarter_statements: Optional[FinancialStatements] = None,
    market_data: Optional[Dict[str, Any]] = None,
) -> FundamentalFeatures:
    """
    Convenience function to calculate all fundamental features.
    
    Example:
        statements = FinancialStatements(
            revenue=394_328_000_000,
            net_income=99_803_000_000,
            total_assets=352_755_000_000,
            total_equity=50_672_000_000,
            eps=6.14,
            shares_outstanding=15_550_000_000,
        )
        
        features = calculate_fundamental_features(
            symbol="AAPL",
            current_price=185.50,
            statements=statements,
        )
    """
    return calculator.calculate_all(
        symbol=symbol,
        current_price=current_price,
        statements=statements,
        prev_year_statements=prev_year_statements,
        prev_quarter_statements=prev_quarter_statements,
        market_data=market_data,
    )
