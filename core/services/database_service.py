"""
Database Service - Persistance des données
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, timezone
from typing import List, Optional, Dict
import json

from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    Session,
)

from core.models import Alert, CryptoPrice, MarketData  # noqa: F401  (si MarketData est utilisé ailleurs)


# ---------------------------------------
# Base declarative (SQLAlchemy 2.x)
# ---------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------
# Modèles
# ---------------------------------------
class AlertRecord(Base):
    """Table des alertes"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    alert_type: Mapped[Optional[str]] = mapped_column(String(50))
    alert_level: Mapped[Optional[str]] = mapped_column(String(20))
    message: Mapped[Optional[str]] = mapped_column(Text)

    # ⚠️ Nom de colonne "metadata" conservé en base,
    #    mais attribut Python renommé (réservé par SQLAlchemy).
    metadata_json: Mapped[Optional[str]] = mapped_column("metadata", Text)

    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_alerts_symbol_ts", "symbol", "timestamp"),
    )


class PriceRecord(Base):
    """Table de l'historique des prix"""
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    price_usd: Mapped[Optional[float]] = mapped_column(Float)
    price_eur: Mapped[Optional[float]] = mapped_column(Float)
    volume_24h: Mapped[Optional[float]] = mapped_column(Float)
    change_24h: Mapped[Optional[float]] = mapped_column(Float)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_prices_symbol_ts", "symbol", "timestamp"),
    )


class StatRecord(Base):
    """Table des statistiques"""
    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    checks_count: Mapped[int] = mapped_column(Integer)
    alerts_sent: Mapped[int] = mapped_column(Integer)
    errors_count: Mapped[int] = mapped_column(Integer)
    uptime_seconds: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        Index("ix_stats_ts", "timestamp"),
    )


# ---------------------------------------
# Service DB
# ---------------------------------------
class DatabaseService:
    """Service de gestion de la base de données"""

    def __init__(self, db_path: str = "data/crypto_bot.db"):
        self.db_path = db_path
        # SQLite + threads éventuels → check_same_thread=False
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )

    def get_session(self) -> Session:
        """Retourne une session"""
        return self.SessionLocal()

    # --------------------------
    # Écritures
    # --------------------------
    def save_alert(self, alert: Alert) -> None:
        """Sauvegarde une alerte"""
        session = self.get_session()
        try:
            record = AlertRecord(
                alert_id=alert.alert_id,
                symbol=alert.symbol,
                alert_type=alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
                alert_level=alert.alert_level.value if hasattr(alert.alert_level, "value") else str(alert.alert_level),
                message=alert.message,
                metadata_json=json.dumps(alert.metadata) if alert.metadata is not None else None,
                timestamp=alert.timestamp if alert.timestamp is not None else datetime.now(timezone.utc),
                acknowledged=bool(alert.acknowledged),
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    def save_price(self, price: CryptoPrice) -> None:
        """Sauvegarde un prix"""
        session = self.get_session()
        try:
            record = PriceRecord(
                symbol=price.symbol,
                price_usd=price.price_usd,
                price_eur=price.price_eur,
                volume_24h=price.volume_24h,
                change_24h=price.change_24h,
                timestamp=price.timestamp if price.timestamp is not None else datetime.now(timezone.utc),
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    def save_stats(self, checks: int, alerts: int, errors: int, uptime: int) -> None:
        """Sauvegarde des statistiques"""
        session = self.get_session()
        try:
            record = StatRecord(
                timestamp=datetime.now(timezone.utc),
                checks_count=int(checks),
                alerts_sent=int(alerts),
                errors_count=int(errors),
                uptime_seconds=int(uptime),
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    # --------------------------
    # Lectures
    # --------------------------
    def get_alerts_history(self, symbol: Optional[str] = None, days: int = 7) -> List[AlertRecord]:
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
            return (
                session.query(PriceRecord)
                .filter(PriceRecord.symbol == symbol)
                .filter(PriceRecord.timestamp >= cutoff)
                .order_by(PriceRecord.timestamp.asc())
                .all()
            )
        finally:
            session.close()

    def get_stats_summary(self, days: int = 7) -> Dict[str, float]:
        """Récupère un résumé des stats"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            records = session.query(StatRecord).filter(StatRecord.timestamp >= cutoff).all()

            if not records:
                return {
                    "total_checks": 0,
                    "total_alerts": 0,
                    "total_errors": 0,
                    "avg_checks_per_day": 0.0,
                }

            total_checks = sum(r.checks_count for r in records)
            total_alerts = sum(r.alerts_sent for r in records)
            total_errors = sum(r.errors_count for r in records)
            avg_checks_per_day = total_checks / float(days) if days > 0 else 0.0

            return {
                "total_checks": total_checks,
                "total_alerts": total_alerts,
                "total_errors": total_errors,
                "avg_checks_per_day": avg_checks_per_day,
            }
        finally:
            session.close()

    # --------------------------
    # Maintenance
    # --------------------------
    def cleanup_old_data(self, keep_days: int = 30) -> None:
        """Nettoie les anciennes données"""
        session = self.get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

            # Supprimer anciennes alertes
            session.query(AlertRecord).filter(AlertRecord.timestamp < cutoff).delete(synchronize_session=False)

            # Supprimer anciens prix
            session.query(PriceRecord).filter(PriceRecord.timestamp < cutoff).delete(synchronize_session=False)

            # Supprimer anciennes stats
            session.query(StatRecord).filter(StatRecord.timestamp < cutoff).delete(synchronize_session=False)

            session.commit()
        finally:
            session.close()
