"""
Database Service - Persistance des données
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
import json

from core.models import Alert, CryptoPrice, MarketData

Base = declarative_base()


class AlertRecord(Base):
    """Table des alertes"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(100), unique=True)
    symbol = Column(String(20))
    alert_type = Column(String(50))
    alert_level = Column(String(20))
    message = Column(Text)
    metadata = Column(Text)  # JSON
    timestamp = Column(DateTime)
    acknowledged = Column(Boolean, default=False)


class PriceRecord(Base):
    """Table de l'historique des prix"""
    __tablename__ = 'prices'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    price_usd = Column(Float)
    price_eur = Column(Float)
    volume_24h = Column(Float)
    change_24h = Column(Float)
    timestamp = Column(DateTime)


class StatRecord(Base):
    """Table des statistiques"""
    __tablename__ = 'stats'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    checks_count = Column(Integer)
    alerts_sent = Column(Integer)
    errors_count = Column(Integer)
    uptime_seconds = Column(Integer)


class DatabaseService:
    """Service de gestion de la base de données"""
    
    def __init__(self, db_path: str = "data/crypto_bot.db"):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Retourne une session"""
        return self.SessionLocal()
    
    def save_alert(self, alert: Alert):
        """Sauvegarde une alerte"""
        session = self.get_session()
        try:
            record = AlertRecord(
                alert_id=alert.alert_id,
                symbol=alert.symbol,
                alert_type=alert.alert_type.value,
                alert_level=alert.alert_level.value,
                message=alert.message,
                metadata=json.dumps(alert.metadata),
                timestamp=alert.timestamp,
                acknowledged=alert.acknowledged
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
    
    def save_price(self, price: CryptoPrice):
        """Sauvegarde un prix"""
        session = self.get_session()
        try:
            record = PriceRecord(
                symbol=price.symbol,
                price_usd=price.price_usd,
                price_eur=price.price_eur,
                volume_24h=price.volume_24h,
                change_24h=price.change_24h,
                timestamp=price.timestamp
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
    
    def get_alerts_history(self, symbol: Optional[str] = None, 
                          days: int = 7) -> List[AlertRecord]:
        """Récupère l'historique des alertes"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = session.query(AlertRecord).filter(AlertRecord.timestamp >= cutoff)
            
            if symbol:
                query = query.filter(AlertRecord.symbol == symbol)
            
            return query.order_by(AlertRecord.timestamp.desc()).all()
        finally:
            session.close()
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[PriceRecord]:
        """Récupère l'historique des prix"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            return session.query(PriceRecord)\
                .filter(PriceRecord.symbol == symbol)\
                .filter(PriceRecord.timestamp >= cutoff)\
                .order_by(PriceRecord.timestamp.asc())\
                .all()
        finally:
            session.close()
    
    def save_stats(self, checks: int, alerts: int, errors: int, uptime: int):
        """Sauvegarde des statistiques"""
        session = self.get_session()
        try:
            record = StatRecord(
                timestamp=datetime.now(timezone.utc),
                checks_count=checks,
                alerts_sent=alerts,
                errors_count=errors,
                uptime_seconds=uptime
            )
            session.add(record)
            session.commit()
        finally:
            session.close()
    
    def get_stats_summary(self, days: int = 7) -> Dict:
        """Récupère un résumé des stats"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            records = session.query(StatRecord)\
                .filter(StatRecord.timestamp >= cutoff)\
                .all()
            
            if not records:
                return {
                    "total_checks": 0,
                    "total_alerts": 0,
                    "total_errors": 0,
                    "avg_checks_per_day": 0
                }
            
            return {
                "total_checks": sum(r.checks_count for r in records),
                "total_alerts": sum(r.alerts_sent for r in records),
                "total_errors": sum(r.errors_count for r in records),
                "avg_checks_per_day": sum(r.checks_count for r in records) / days
            }
        finally:
            session.close()
    
    def cleanup_old_data(self, keep_days: int = 30):
        """Nettoie les anciennes données"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
            
            # Supprimer anciennes alertes
            session.query(AlertRecord)\
                .filter(AlertRecord.timestamp < cutoff)\
                .delete()
            
            # Supprimer anciens prix
            session.query(PriceRecord)\
                .filter(PriceRecord.timestamp < cutoff)\
                .delete()
            
            # Supprimer anciennes stats
            session.query(StatRecord)\
                .filter(StatRecord.timestamp < cutoff)\
                .delete()
            
            session.commit()
        finally:
            session.close()
