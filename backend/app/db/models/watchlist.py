"""
PaperTrading Platform - Watchlist Model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.db.database import Base


# Association table for watchlist symbols
watchlist_symbols = Table(
    "watchlist_symbols",
    Base.metadata,
    Column("watchlist_id", Integer, ForeignKey("watchlists.id", ondelete="CASCADE")),
    Column("symbol", String(20)),
    Column("added_at", DateTime, default=datetime.utcnow),
)


class Watchlist(Base):
    """Watchlist model."""
    
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Watchlist info
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    
    def __repr__(self):
        return f"<Watchlist {self.name}>"
