from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

engine = create_engine(
    "sqlite:///db/bot.db",
    connect_args={"check_same_thread": False},
    poolclass=None
)
Base = declarative_base()
Session = sessionmaker(bind=engine)



class TradeBlueprint(Base):
    __tablename__ = "trade_blueprints"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    direction = Column(String)
    entry = Column(Float)
    stop = Column(Float)
    tp = Column(Float)
    rr = Column(Float)
    confidence = Column(Float)
    status = Column(String, default="open")  # open / closed
    outcome = Column(String)  # win / loss
    exit_price = Column(Float)
    pnl_pct = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)