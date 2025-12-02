"""
PaperTrading Platform - Rebalancing Schemas
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class AllocationTargetResponse(BaseModel):
    """Response for allocation target."""
    name: str
    target_weight: float
    current_weight: float
    drift: float
    drift_percent: float
    status: str  # overweight, underweight, on_target


class RebalanceRecommendationResponse(BaseModel):
    """Response for rebalance recommendation."""
    symbol: str
    action: str  # buy, sell, hold
    current_value: float
    target_value: float
    trade_value: float
    current_weight: float
    target_weight: float
    reason: str
    priority: int


class AllocationAnalysisResponse(BaseModel):
    """Response for allocation analysis."""
    total_value: float
    cash_balance: float
    asset_class_allocations: list[AllocationTargetResponse]
    sector_allocations: list[AllocationTargetResponse]
    needs_rebalancing: bool
    max_drift: float
    rebalance_recommendations: list[RebalanceRecommendationResponse]
    analysis_date: datetime


class OrderPreviewResponse(BaseModel):
    """Preview of an order to create."""
    symbol: str
    trade_type: str
    order_type: str
    quantity: int
    estimated_value: float
    reason: str
    priority: int


class RebalancePreviewResponse(BaseModel):
    """Response for rebalance preview."""
    analysis: AllocationAnalysisResponse
    orders_to_create: list[OrderPreviewResponse]
    estimated_commissions: float
    total_buy_value: float
    total_sell_value: float
    net_cash_change: float
    warnings: list[str]


class RebalanceExecuteRequest(BaseModel):
    """Request to execute rebalancing."""
    risk_profile: str = Field(default="balanced", description="Target risk profile")
    min_trade_value: float = Field(default=100.0, ge=0, description="Minimum trade value")
    execute_sells_first: bool = Field(default=True, description="Execute sells before buys")


class OrderExecutionResult(BaseModel):
    """Result of single order execution."""
    order_id: Optional[int] = None
    symbol: str
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    error: Optional[str] = None


class RebalanceResultResponse(BaseModel):
    """Response for rebalance execution result."""
    success: bool
    orders_created: list[dict]
    orders_executed: list[dict]
    orders_failed: list[dict]
    total_trades: int
    execution_time: float
    errors: list[str]


# Batch Order Schemas
class BatchOrderItem(BaseModel):
    """Single order in a batch."""
    symbol: str = Field(..., min_length=1, max_length=20)
    trade_type: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^(market|limit|stop|stop_limit)$")
    quantity: int = Field(..., gt=0)
    limit_price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)


class BatchOrderRequest(BaseModel):
    """Request for batch order execution."""
    orders: list[BatchOrderItem] = Field(..., min_length=1, max_length=50)
    execute_sequentially: bool = Field(default=True, description="Execute orders one by one")


class BatchOrderResultItem(BaseModel):
    """Result of single order in batch."""
    symbol: str
    success: bool
    order_id: Optional[int] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    error: Optional[str] = None


class BatchOrderResponse(BaseModel):
    """Response for batch order execution."""
    total_orders: int
    successful: int
    failed: int
    results: list[BatchOrderResultItem]
