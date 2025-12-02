"""
PaperTrading Platform - Trading Engine Module

Core trading functionality including:
- Order management
- Execution simulation
- Position tracking
- P&L calculation
"""
from app.core.trading.order_manager import (
    OrderManager,
    OrderRequest,
    OrderResult,
    OrderValidationError,
    InsufficientFundsError,
    InsufficientSharesError
)
from app.core.trading.execution import (
    ExecutionEngine,
    OrderExecutor,
    ExecutionResult,
    SlippageConfig,
    MarketCondition
)
from app.core.trading.position_tracker import (
    PositionTracker,
    PositionSummary,
    PortfolioPositions
)
from app.core.trading.pnl_calculator import (
    PnLCalculator,
    RealizedPnL,
    UnrealizedPnL,
    PortfolioPnL,
    TimeFrame
)

__all__ = [
    # Order Management
    "OrderManager",
    "OrderRequest",
    "OrderResult",
    "OrderValidationError",
    "InsufficientFundsError",
    "InsufficientSharesError",
    
    # Execution
    "ExecutionEngine",
    "OrderExecutor",
    "ExecutionResult",
    "SlippageConfig",
    "MarketCondition",
    
    # Position Tracking
    "PositionTracker",
    "PositionSummary",
    "PortfolioPositions",
    
    # P&L
    "PnLCalculator",
    "RealizedPnL",
    "UnrealizedPnL",
    "PortfolioPnL",
    "TimeFrame"
]
