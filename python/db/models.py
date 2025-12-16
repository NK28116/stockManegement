from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Portfolio(Base):
    """
    保有銘柄（ポートフォリオ）管理テーブル
    """

    __tablename__ = "portfolio"

    # サロゲートキー（ID）を導入し、同日同銘柄の複数取引に対応
    id = Column(Integer, primary_key=True, autoincrement=True)

    code = Column(String, nullable=False, index=True)
    name = Column(String)
    quantity = Column(Integer)

    # 金額は NUMERIC 型を使用 (全体桁数, 小数点以下桁数)
    purchase_price = Column(Numeric(10, 2))
    purchase_date = Column(Date, nullable=False)

    status = Column(String)  # 'HOLD', 'SOLD' など

    current_price = Column(Numeric(10, 2))
    profit_loss = Column(Numeric(15, 2))
    profit_loss_percent = Column(Numeric(10, 4))  # パーセントは数値で管理

    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    purpose = Column(Text)

    # 既存のCSVインポートロジック（code + purchase_dateでユニーク）を維持したい場合のみ有効化
    # ただし、デイトレード等に対応するならこの制約は外すべき
    __table_args__ = (
        UniqueConstraint("code", "purchase_date", name="uix_portfolio_code_date"),
    )


class Stock(Base):
    __tablename__ = "stocks"

    code = Column(String, primary_key=True)
    name = Column(String)
    market = Column(String)


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2))
    volume = Column(Integer)
    rsi = Column(Numeric(10, 2))
    bb_upper = Column(Numeric(10, 2))
    bb_lower = Column(Numeric(10, 2))

    __table_args__ = (
        UniqueConstraint("stock_code", "date", name="uix_daily_price_code_date"),
    )
