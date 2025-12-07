"""
PaperTrading Platform - Trade Endpoints

API endpoints for order management, trade execution, and trade history.
"""
import csv
import io
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.trade import TradeType, OrderType, TradeStatus
from app.db.repositories.trade import TradeRepository
from app.core.trading.order_manager import OrderManager, OrderRequest
from app.core.trading.execution import OrderExecutor, MarketCondition
from app.core.trading.pnl_calculator import PnLCalculator, TimeFrame

router = APIRouter()


# ==================== SCHEMAS ====================

class OrderCreateRequest(BaseModel):
    """Request to create a new order."""
    portfolio_id: int = Field(..., description="Portfolio ID")
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    trade_type: TradeType = Field(..., description="BUY or SELL")
    quantity: Decimal = Field(..., gt=0, description="Number of shares")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    limit_price: Optional[Decimal] = Field(None, gt=0, description="Limit price for limit orders")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="Stop price for stop orders")
    notes: Optional[str] = Field(None, max_length=500, description="Order notes")

    class Config:
        use_enum_values = True


class OrderExecuteRequest(BaseModel):
    """Request to execute a pending order."""
    current_price: Decimal = Field(..., gt=0, description="Current market price")
    market_condition: Optional[str] = Field(
        default="normal",
        description="Market condition: normal, volatile, low_liquidity, high_volume"
    )


class TradeResponse(BaseModel):
    """Trade/Order response."""
    id: int
    portfolio_id: int
    symbol: str
    exchange: Optional[str]
    trade_type: str
    order_type: str
    status: str
    quantity: Decimal
    price: Optional[Decimal]
    executed_price: Optional[Decimal]
    executed_quantity: Optional[Decimal]
    total_value: Optional[Decimal]
    commission: Optional[Decimal]
    realized_pnl: Optional[Decimal]
    created_at: datetime
    executed_at: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True


class OrderResultResponse(BaseModel):
    """Order operation result."""
    success: bool
    order_id: Optional[int]
    message: str
    errors: List[str] = []


class TradeSummaryResponse(BaseModel):
    """Trade summary statistics."""
    total_trades: int
    buy_trades: int
    sell_trades: int
    total_volume: Decimal
    realized_pnl: Decimal
    avg_trade_size: Decimal
    most_traded_symbols: List[dict]
    period_days: int


class PnLResponse(BaseModel):
    """P&L response."""
    portfolio_id: int
    realized_total: Decimal
    realized_gross_profit: Decimal
    realized_gross_loss: Decimal
    realized_win_rate: Decimal
    unrealized_total: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    current_value: Decimal
    time_frame: str


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[TradeResponse])
async def list_trades(
    portfolio_id: int = Query(..., description="Portfolio ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    trade_type: Optional[str] = Query(None, description="Filter by trade type (buy/sell)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[datetime] = Query(None, description="Filter trades from this date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter trades until this date (inclusive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List trades/orders for a portfolio.
    
    Supports filtering by status, trade type, symbol, and date range.
    """
    repo = TradeRepository(db)
    
    # Convert string filters to enums
    status_enum = None
    if status:
        try:
            status_enum = TradeStatus(status.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    
    trade_type_enum = None
    if trade_type:
        try:
            trade_type_enum = TradeType(trade_type.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid trade type: {trade_type}")
    
    trades = await repo.get_by_portfolio(
        portfolio_id=portfolio_id,
        status=status_enum,
        trade_type=trade_type_enum,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return [
        TradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            symbol=t.symbol,
            exchange=t.exchange,
            trade_type=t.trade_type.value,
            order_type=t.order_type.value,
            status=t.status.value,
            quantity=t.quantity,
            price=t.price,
            executed_price=t.executed_price,
            executed_quantity=t.executed_quantity,
            total_value=t.total_value,
            commission=t.commission,
            realized_pnl=t.realized_pnl,
            created_at=t.created_at,
            executed_at=t.executed_at,
            notes=t.notes
        )
        for t in trades
    ]


@router.post("/orders", response_model=OrderResultResponse)
async def create_order(
    request: OrderCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order.
    
    The order will be validated against portfolio constraints.
    Market orders are executed immediately with a simulated price.
    Limit/Stop orders are placed in PENDING status.
    """
    order_manager = OrderManager(db)
    executor = OrderExecutor(db)
    repo = TradeRepository(db)
    
    try:
        order_request = OrderRequest(
            portfolio_id=request.portfolio_id,
            symbol=request.symbol.upper(),
            trade_type=request.trade_type if isinstance(request.trade_type, TradeType) else TradeType(request.trade_type),
            quantity=request.quantity,
            order_type=request.order_type if isinstance(request.order_type, OrderType) else OrderType(request.order_type),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            notes=request.notes
        )
        
        result = await order_manager.create_order(order_request)
        
        if not result.success:
            return OrderResultResponse(
                success=result.success,
                order_id=result.order_id,
                message=result.message,
                errors=result.errors
            )
        
        # For MARKET orders, execute immediately with simulated price
        order_type = request.order_type if isinstance(request.order_type, OrderType) else OrderType(request.order_type)
        if order_type == OrderType.MARKET and result.order_id:
            # Get the created trade
            trade = await repo.get_by_id(result.order_id)
            if trade:
                # Use user-provided price (limit_price) or default mock price
                # In production, this would fetch from market data
                if request.limit_price and request.limit_price > 0:
                    execution_price = request.limit_price
                else:
                    execution_price = Decimal("150.00")  # Default mock price
                
                # Execute the order
                exec_result = await executor.execute_order(
                    trade,
                    execution_price,
                    MarketCondition.NORMAL
                )
                
                if exec_result.success:
                    result.message = f"Market order executed at ${execution_price}"
                else:
                    result.message = f"Order created but execution failed: {exec_result.message}"
                    result.errors = [exec_result.message]
        
        await db.commit()
        
        return OrderResultResponse(
            success=result.success,
            order_id=result.order_id,
            message=result.message,
            errors=result.errors
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(400, str(e))


@router.post("/orders/{order_id}/execute", response_model=TradeResponse)
async def execute_order(
    order_id: int,
    request: OrderExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a pending order at given price.
    
    Simulates market execution with slippage based on market conditions.
    """
    repo = TradeRepository(db)
    executor = OrderExecutor(db)
    
    # Get the order
    trade = await repo.get_by_id(order_id)
    if not trade:
        raise HTTPException(404, f"Order {order_id} not found")
    
    if trade.status != TradeStatus.PENDING:
        raise HTTPException(400, f"Order is not pending (status: {trade.status.value})")
    
    # Parse market condition
    try:
        market_condition = MarketCondition(request.market_condition or "normal")
    except ValueError:
        market_condition = MarketCondition.NORMAL
    
    # Execute
    result = await executor.execute_order(
        trade,
        request.current_price,
        market_condition
    )
    
    if not result.success:
        raise HTTPException(400, result.message)
    
    await db.commit()
    
    # Refresh trade
    await db.refresh(trade)
    
    return TradeResponse(
        id=trade.id,
        portfolio_id=trade.portfolio_id,
        symbol=trade.symbol,
        exchange=trade.exchange,
        trade_type=trade.trade_type.value,
        order_type=trade.order_type.value,
        status=trade.status.value,
        quantity=trade.quantity,
        price=trade.price,
        executed_price=trade.executed_price,
        executed_quantity=trade.executed_quantity,
        total_value=trade.total_value,
        commission=trade.commission,
        realized_pnl=trade.realized_pnl,
        created_at=trade.created_at,
        executed_at=trade.executed_at,
        notes=trade.notes
    )


@router.get("/orders/{order_id}", response_model=TradeResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get order/trade by ID."""
    repo = TradeRepository(db)
    trade = await repo.get_by_id(order_id)
    
    if not trade:
        raise HTTPException(404, f"Order {order_id} not found")
    
    return TradeResponse(
        id=trade.id,
        portfolio_id=trade.portfolio_id,
        symbol=trade.symbol,
        exchange=trade.exchange,
        trade_type=trade.trade_type.value,
        order_type=trade.order_type.value,
        status=trade.status.value,
        quantity=trade.quantity,
        price=trade.price,
        executed_price=trade.executed_price,
        executed_quantity=trade.executed_quantity,
        total_value=trade.total_value,
        commission=trade.commission,
        realized_pnl=trade.realized_pnl,
        created_at=trade.created_at,
        executed_at=trade.executed_at,
        notes=trade.notes
    )


@router.delete("/orders/{order_id}", response_model=OrderResultResponse)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a pending order.
    
    Only orders with PENDING status can be cancelled.
    """
    repo = TradeRepository(db)
    
    trade = await repo.get_by_id(order_id)
    if not trade:
        raise HTTPException(404, f"Order {order_id} not found")
    
    if trade.status != TradeStatus.PENDING:
        raise HTTPException(
            400, 
            f"Cannot cancel order with status {trade.status.value}"
        )
    
    await repo.cancel_order(order_id)
    await db.commit()
    
    return OrderResultResponse(
        success=True,
        order_id=order_id,
        message="Order cancelled successfully"
    )


@router.get("/pending", response_model=List[TradeResponse])
async def list_pending_orders(
    portfolio_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending orders, optionally filtered by portfolio."""
    repo = TradeRepository(db)
    trades = await repo.get_pending_orders(portfolio_id)
    
    return [
        TradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            symbol=t.symbol,
            exchange=t.exchange,
            trade_type=t.trade_type.value,
            order_type=t.order_type.value,
            status=t.status.value,
            quantity=t.quantity,
            price=t.price,
            executed_price=t.executed_price,
            executed_quantity=t.executed_quantity,
            total_value=t.total_value,
            commission=t.commission,
            realized_pnl=t.realized_pnl,
            created_at=t.created_at,
            executed_at=t.executed_at,
            notes=t.notes
        )
        for t in trades
    ]


@router.get("/history/{portfolio_id}", response_model=List[TradeResponse])
async def get_trade_history(
    portfolio_id: int,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    include_pending: bool = Query(True, description="Include pending orders in history"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[datetime] = Query(None, description="Filter trades from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter trades until this date"),
    db: AsyncSession = Depends(get_db)
):
    """Get trade history for a portfolio with optional filters."""
    repo = TradeRepository(db)
    
    # Use date filters if provided, otherwise use days parameter
    if start_date or end_date:
        trades = await repo.get_by_portfolio(
            portfolio_id=portfolio_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    else:
        trades = await repo.get_recent_trades(
            portfolio_id=portfolio_id,
            days=days,
            limit=limit
        )
        # Apply symbol filter for get_recent_trades
        if symbol:
            trades = [t for t in trades if t.symbol.upper() == symbol.upper()]
    
    # Filter based on include_pending parameter
    if not include_pending:
        trades = [t for t in trades if t.status == TradeStatus.EXECUTED]
    
    return [
        TradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            symbol=t.symbol,
            exchange=t.exchange,
            trade_type=t.trade_type.value,
            order_type=t.order_type.value,
            status=t.status.value,
            quantity=t.quantity,
            price=t.price,
            executed_price=t.executed_price,
            executed_quantity=t.executed_quantity,
            total_value=t.total_value,
            commission=t.commission,
            realized_pnl=t.realized_pnl,
            created_at=t.created_at,
            executed_at=t.executed_at,
            notes=t.notes
        )
        for t in trades
    ]


@router.get("/summary/{portfolio_id}", response_model=TradeSummaryResponse)
async def get_trade_summary(
    portfolio_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get trading summary statistics for a portfolio."""
    repo = TradeRepository(db)
    summary = await repo.get_trade_summary(portfolio_id, days)
    
    return TradeSummaryResponse(**summary)


@router.get("/pnl/{portfolio_id}", response_model=PnLResponse)
async def get_portfolio_pnl(
    portfolio_id: int,
    time_frame: str = Query("all_time", description="day, week, month, quarter, year, ytd, all_time"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get P&L summary for a portfolio.
    
    Note: For accurate unrealized P&L, current prices should be provided.
    This endpoint returns realized P&L and placeholder for unrealized.
    """
    calculator = PnLCalculator(db)
    
    # Parse time frame
    try:
        tf = TimeFrame(time_frame)
    except ValueError:
        tf = TimeFrame.ALL_TIME
    
    # For now, calculate with empty prices (unrealized will be 0)
    # In production, this would fetch current prices from market data
    prices = {}  # TODO: Integrate with market data
    
    try:
        pnl = await calculator.calculate_portfolio_pnl(portfolio_id, prices, tf)
        
        return PnLResponse(
            portfolio_id=portfolio_id,
            realized_total=pnl.realized.total,
            realized_gross_profit=pnl.realized.gross_profit,
            realized_gross_loss=pnl.realized.gross_loss,
            realized_win_rate=pnl.realized.win_rate,
            unrealized_total=pnl.unrealized.total,
            total_pnl=pnl.total_pnl,
            total_pnl_pct=pnl.total_pnl_pct,
            current_value=pnl.current_value,
            time_frame=tf.value
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/by-symbol/{portfolio_id}/{symbol}", response_model=List[TradeResponse])
async def get_trades_by_symbol(
    portfolio_id: int,
    symbol: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get trade history for a specific symbol in a portfolio."""
    repo = TradeRepository(db)
    trades = await repo.get_trades_by_symbol(portfolio_id, symbol, limit)
    
    return [
        TradeResponse(
            id=t.id,
            portfolio_id=t.portfolio_id,
            symbol=t.symbol,
            exchange=t.exchange,
            trade_type=t.trade_type.value,
            order_type=t.order_type.value,
            status=t.status.value,
            quantity=t.quantity,
            price=t.price,
            executed_price=t.executed_price,
            executed_quantity=t.executed_quantity,
            total_value=t.total_value,
            commission=t.commission,
            realized_pnl=t.realized_pnl,
            created_at=t.created_at,
            executed_at=t.executed_at,
            notes=t.notes
        )
        for t in trades
    ]


# ==================== BATCH ORDERS ====================

class BatchOrderItem(BaseModel):
    """Single order in a batch."""
    symbol: str = Field(..., min_length=1, max_length=20)
    trade_type: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^(market|limit)$")
    quantity: int = Field(..., gt=0)
    limit_price: Optional[float] = Field(None, gt=0)


class BatchOrderRequest(BaseModel):
    """Request for batch order execution."""
    portfolio_id: int
    orders: List[BatchOrderItem] = Field(..., min_length=1, max_length=50)


class BatchOrderResultItem(BaseModel):
    """Result of single order in batch."""
    symbol: str
    success: bool
    order_id: Optional[int] = None
    executed_price: Optional[float] = None
    executed_quantity: Optional[int] = None
    error: Optional[str] = None


class BatchOrderResponse(BaseModel):
    """Response for batch order execution."""
    total_orders: int
    successful: int
    failed: int
    results: List[BatchOrderResultItem]


@router.post("/batch", response_model=BatchOrderResponse)
async def execute_batch_orders(
    request: BatchOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute multiple orders in a batch.
    
    Orders are processed sequentially. Failed orders don't block others.
    Sell orders are prioritized to free up cash for buy orders.
    """
    order_manager = OrderManager(db)
    executor = OrderExecutor(db)
    
    results = []
    successful = 0
    failed = 0
    
    # Sort: sells first, then buys
    sorted_orders = sorted(
        request.orders,
        key=lambda o: 0 if o.trade_type == "sell" else 1
    )
    
    for order_item in sorted_orders:
        try:
            # Create order
            order_request = OrderRequest(
                portfolio_id=request.portfolio_id,
                symbol=order_item.symbol.upper(),
                trade_type=TradeType(order_item.trade_type),
                quantity=Decimal(str(order_item.quantity)),
                order_type=OrderType(order_item.order_type),
                limit_price=Decimal(str(order_item.limit_price)) if order_item.limit_price else None,
            )
            
            order_result = await order_manager.create_order(order_request)
            
            if not order_result.success:
                results.append(BatchOrderResultItem(
                    symbol=order_item.symbol,
                    success=False,
                    error=order_result.message
                ))
                failed += 1
                continue
            
            # Execute order immediately (paper trading)
            exec_result = await executor.execute_order(
                trade_id=order_result.trade_id,
                market_condition=MarketCondition.NORMAL
            )
            
            if exec_result.success:
                results.append(BatchOrderResultItem(
                    symbol=order_item.symbol,
                    success=True,
                    order_id=order_result.trade_id,
                    executed_price=float(exec_result.executed_price) if exec_result.executed_price else None,
                    executed_quantity=int(exec_result.executed_quantity) if exec_result.executed_quantity else None
                ))
                successful += 1
            else:
                results.append(BatchOrderResultItem(
                    symbol=order_item.symbol,
                    success=False,
                    order_id=order_result.trade_id,
                    error=exec_result.message
                ))
                failed += 1
                
        except Exception as e:
            results.append(BatchOrderResultItem(
                symbol=order_item.symbol,
                success=False,
                error=str(e)
            ))
            failed += 1
    
    await db.commit()
    
    return BatchOrderResponse(
        total_orders=len(request.orders),
        successful=successful,
        failed=failed,
        results=results
    )


# ==================== EXPORT ====================

from fastapi.responses import StreamingResponse
import csv
import io


@router.get("/export/{portfolio_id}")
async def export_trades_csv(
    portfolio_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Export trades to CSV file.
    
    Supports filtering by date range and status.
    """
    repo = TradeRepository(db)
    
    status_enum = None
    if status:
        try:
            status_enum = TradeStatus(status.lower())
        except ValueError:
            pass
    
    trades = await repo.get_by_portfolio(
        portfolio_id=portfolio_id,
        status=status_enum,
        limit=10000  # Max export
    )
    
    # Filter by date if provided
    if start_date:
        trades = [t for t in trades if t.created_at >= start_date]
    if end_date:
        trades = [t for t in trades if t.created_at <= end_date]
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Date", "Symbol", "Type", "Order Type", "Status",
        "Quantity", "Price", "Executed Price", "Total Value",
        "Commission", "Realized P&L", "Notes"
    ])
    
    # Data rows
    for t in trades:
        writer.writerow([
            t.id,
            t.created_at.isoformat() if t.created_at else "",
            t.symbol,
            t.trade_type.value,
            t.order_type.value,
            t.status.value,
            float(t.quantity) if t.quantity else "",
            float(t.price) if t.price else "",
            float(t.executed_price) if t.executed_price else "",
            float(t.total_value) if t.total_value else "",
            float(t.commission) if t.commission else "",
            float(t.realized_pnl) if t.realized_pnl else "",
            t.notes or ""
        ])
    
    output.seek(0)
    
    filename = f"trades_portfolio_{portfolio_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

