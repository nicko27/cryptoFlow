import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.models import (
    BotConfiguration,
    CryptoPrice,
    MarketData,
    OpportunityScore,
    Prediction,
    PredictionType,
    TechnicalIndicators,
)
from core.services.report_service import ReportService
from core.services.summary_service import SummaryService


def _make_market(symbol: str = "BTC", change_24h: float = 1.2, change_7d: float = 5.5) -> MarketData:
    price = CryptoPrice(
        symbol=symbol,
        price_usd=50000.0,
        price_eur=45000.0,
        timestamp=datetime.now(timezone.utc),
        volume_24h=123456.0,
        change_24h=change_24h,
    )
    indicators = TechnicalIndicators(rsi=55.0, ma20=44000.0, support=43000.0, resistance=46000.0)
    return MarketData(symbol=symbol, current_price=price, technical_indicators=indicators, weekly_change=change_7d)


def _make_market_without_price(symbol: str = "BTC") -> MarketData:
    return MarketData(symbol=symbol, current_price=None, technical_indicators=None)


def _make_prediction() -> Prediction:
    return Prediction(
        prediction_type=PredictionType.BULLISH,
        confidence=85.0,
        direction="📈",
        trend_score=4,
    )


def test_summary_service_handles_empty_data():
    service = SummaryService(BotConfiguration())

    summary = service.generate_summary({}, {}, {}, simple=True)

    assert "Aucune donnée" in summary


def test_simple_summary_handles_missing_market_for_best_opportunity():
    service = SummaryService(BotConfiguration())

    opportunities = {"ETH": OpportunityScore(score=8, recommendation="Potentiel haussier")}

    summary = service.generate_summary({}, {}, opportunities, simple=True)

    assert "données de prix indisponibles" in summary


def test_simple_summary_handles_market_without_price():
    service = SummaryService(BotConfiguration())

    markets = {"BTC": _make_market_without_price("BTC")}
    opportunities = {"BTC": OpportunityScore(score=8, recommendation="Bonne opportunité")}

    summary = service.generate_summary(markets, {}, opportunities, simple=True)

    assert "prix indisponible" in summary


def test_simple_summary_reports_when_no_strong_opportunity():
    service = SummaryService(BotConfiguration())

    markets = {"BTC": _make_market()}
    opportunities = {"BTC": OpportunityScore(score=5, recommendation="Surveiller la tendance")}

    summary = service.generate_summary(markets, {}, opportunities, simple=True)

    assert "Aucune opportunité forte" in summary


def test_simple_summary_includes_trend_and_recommendation():
    config = BotConfiguration(
        trend_buy_threshold_24h=1.0,
        trend_buy_threshold_7d=4.0
    )
    service = SummaryService(config)

    markets = {"BTC": _make_market(change_24h=2.5, change_7d=6.0)}
    opportunities = {"BTC": OpportunityScore(score=8, recommendation="Configuration haussière")}

    summary = service.generate_summary(markets, {}, opportunities, simple=True)

    assert "24h: +2.5%" in summary
    assert "7j: +6.0%" in summary
    assert "opportunité d'achat" in summary


def test_simple_summary_flags_sell_signal_with_negative_trend():
    config = BotConfiguration(
        trend_sell_threshold_24h=-1.0,
        trend_sell_threshold_7d=-4.0
    )
    service = SummaryService(config)

    markets = {"BTC": _make_market(change_24h=-2.0, change_7d=-5.5)}
    opportunities = {"BTC": OpportunityScore(score=8, recommendation="Risque élevé")}

    summary = service.generate_summary(markets, {}, opportunities, simple=True)

    assert "24h: -2.0%" in summary
    assert "7j: -5.5%" in summary
    assert "Tendance baissière" in summary


def test_summary_service_next_summary_time_without_hours():
    config = BotConfiguration(summary_hours=[])
    service = SummaryService(config)

    assert service._next_summary_time() == "indisponible"


def test_detailed_summary_handles_missing_opportunities():
    service = SummaryService(BotConfiguration())

    summary = service.generate_summary({"BTC": _make_market()}, {}, {}, simple=False)

    assert "Aucune opportunité analysée" in summary


def test_detailed_summary_handles_opportunity_without_market():
    service = SummaryService(BotConfiguration())

    markets = {"BTC": _make_market()}
    opportunities = {"ETH": OpportunityScore(score=9, recommendation="Forte dynamique")}

    summary = service.generate_summary(markets, {}, opportunities, simple=False)

    assert "ETH" in summary
    assert "Prix: données indisponibles" in summary
    assert "Variation 24h: indisponible" in summary


def test_detailed_summary_surfaces_opportunities_without_market_data():
    service = SummaryService(BotConfiguration())

    opportunities = {"ETH": OpportunityScore(score=9, recommendation="Forte dynamique")}
    predictions = {"ETH": _make_prediction()}

    summary = service.generate_summary({}, predictions, opportunities, simple=False)

    assert "Données de marché indisponibles" in summary
    assert "TOP OPPORTUNITÉS" in summary
    assert "ETH" in summary
    assert "Prix: données indisponibles" in summary


def test_report_service_handles_empty_inputs():
    service = ReportService()

    report = service.generate_complete_report({}, {}, {})

    assert "Données insuffisantes" in report


def test_report_service_recommendations_handle_missing_market_data():
    service = ReportService()

    opportunities = {"ETH": OpportunityScore(score=9, recommendation="Forte dynamique")}

    report = service.generate_complete_report({}, {}, opportunities)

    assert "ETH" in report
    assert "prix indisponible" in report


def test_report_service_handles_market_without_price_or_indicators():
    service = ReportService()

    markets = {"BTC": _make_market_without_price("BTC")}

    report = service.generate_complete_report(markets, {}, {})

    assert "Prix actuel : prix indisponible" in report
    assert "Indicateurs techniques indisponibles" in report


def test_report_service_executive_summary_handles_missing_changes():
    service = ReportService()

    market = _make_market()
    market.current_price.change_24h = None

    report = service.generate_complete_report({"BTC": market}, {}, {})

    assert "Tendance générale 24h : données indisponibles" in report


def test_report_service_executive_summary_without_market_data():
    service = ReportService()

    opportunities = {"ETH": OpportunityScore(score=8, recommendation="Bonne dynamique")}

    report = service.generate_complete_report({}, {}, opportunities)

    assert "Meilleure opportunité" in report
    assert "Données de marché indisponibles" in report


def test_report_service_executive_summary_without_opportunities():
    service = ReportService()

    report = service.generate_complete_report({"BTC": _make_market()}, {}, {})

    assert "Aucune opportunité analysée" in report


def test_services_generate_content_with_valid_data():
    config = BotConfiguration()
    summary_service = SummaryService(config)
    report_service = ReportService()

    markets = {"BTC": _make_market()}
    opportunities = {"BTC": OpportunityScore(score=8, recommendation="Bonne opportunité")}
    predictions = {"BTC": _make_prediction()}

    summary = summary_service.generate_summary(markets, predictions, opportunities, simple=False)
    report = report_service.generate_complete_report(markets, predictions, opportunities)

    assert "BTC" in summary
    assert "BTC" in report


def test_morning_summary_handles_missing_market_for_opportunity():
    service = SummaryService(BotConfiguration())

    markets = {"BTC": _make_market()}
    opportunities = {"ETH": OpportunityScore(score=8, recommendation="Bonne dynamique")}

    summary = service.generate_morning_summary(markets, opportunities)

    assert "Prix: données indisponibles" in summary
    assert "Bonne dynamique" in summary


def test_morning_summary_reports_opportunities_without_market_data():
    service = SummaryService(BotConfiguration())

    opportunities = {
        "BTC": OpportunityScore(score=9, recommendation="Setup haussier à surveiller")
    }

    summary = service.generate_morning_summary({}, opportunities)

    assert "OPPORTUNITÉS DU JOUR" in summary
    assert "Prix: données indisponibles" in summary
    assert "Données de marché indisponibles" in summary


def test_evening_summary_reports_missing_variations_and_weak_opportunity():
    service = SummaryService(BotConfiguration())

    market = _make_market("BTC", change_24h=None)
    opportunities = {"BTC": OpportunityScore(score=5, recommendation="À surveiller")}

    summary = service.generate_evening_summary({"BTC": market}, opportunities)

    assert "Aucune variation disponible" in summary
    assert "Aucune opportunité forte" in summary


def test_evening_summary_highlights_opportunity_without_market_data():
    service = SummaryService(BotConfiguration())

    opportunities = {"ETH": OpportunityScore(score=7, recommendation="Potentiel intéressant")}

    summary = service.generate_evening_summary({}, opportunities)

    assert "Données de marché indisponibles" in summary
    assert "OPPORTUNITÉ POUR DEMAIN" in summary
    assert "Potentiel intéressant" in summary
