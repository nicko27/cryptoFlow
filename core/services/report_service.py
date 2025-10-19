"""
Report Service - Génération de rapports complets
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta, timezone
from statistics import stdev
from itertools import combinations
from core.models import (
    MarketData,
    Prediction,
    OpportunityScore,
    BotConfiguration,
    BrokerQuote,
    PredictionType,
)
from core.services.summary_service import SummaryService
from core.services.dca_service import DCAService
from core.services.broker_service import BrokerService
from io import StringIO


class ReportService:
    """Service de génération de rapports"""

    def __init__(
        self,
        config: Optional[BotConfiguration] = None,
        broker_service: Optional[BrokerService] = None,
    ):
        self.config = config
        self.broker_service = broker_service or BrokerService(config)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def configure(self, config: BotConfiguration) -> None:
        """Permet de réinjecter une configuration à chaud."""
        self.config = config
        if hasattr(self, "broker_service") and self.broker_service:
            self.broker_service.configure(config)

    def generate_complete_report(
        self,
        markets_data: Dict[str, MarketData],
        predictions: Dict[str, Prediction],
        opportunities: Dict[str, OpportunityScore],
        stats: Dict = None,
    ) -> str:
        """Génère un rapport complet en fonction de la configuration active."""

        report = StringIO()
        filtered_markets = {
            symbol: market
            for symbol, market in markets_data.items()
            if self._include_symbol_report(symbol)
        }
        filtered_predictions = {
            symbol: pred
            for symbol, pred in predictions.items()
            if self._include_symbol_report(symbol)
        }
        filtered_opportunities = {
            symbol: opp
            for symbol, opp in opportunities.items()
            if self._include_symbol_report(symbol)
        }

        # En-tête
        report.write("RAPPORT COMPLET - CRYPTO BOT v3.0\n")
        report.write(f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}\n\n")

        if self._section_enabled("executive_summary"):
            report.write(self._generate_executive_summary(markets_data, opportunities))
            report.write("\n")

        if self.config and self.config.report_include_summary:
            report.write("📢 RÉSUMÉ EN VERSION TÉLÉGRAM\n")
            telegram_summary = SummaryService(self.config).generate_summary(
                filtered_markets,
                filtered_predictions,
                filtered_opportunities,
                simple=self.config.use_simple_language,
            )
            report.write(telegram_summary.strip())
            report.write("\n\n")

        if self._section_enabled("per_crypto"):
            for symbol in sorted(markets_data.keys()):
                if not self._include_symbol_report(symbol):
                    continue
                market = markets_data[symbol]
                prediction = predictions.get(symbol)
                opportunity = opportunities.get(symbol)
                report.write(self._generate_crypto_section(symbol, market, prediction, opportunity))
                report.write("\n")

        if self._section_enabled("comparison"):
            report.write(self._generate_comparison_section(markets_data, opportunities))
            report.write("\n")

        if self._section_enabled("recommendations"):
            report.write(self._generate_recommendations(filtered_markets, filtered_opportunities))
            report.write("\n")

        if self._section_enabled("advanced_analysis"):
            report.write(self._generate_advanced_analysis(filtered_markets, filtered_opportunities))
            report.write("\n")

        chart_text = self._generate_inline_chart_text(filtered_markets)
        if chart_text:
            report.write(chart_text)
            report.write("\n")

        dca_text = self._generate_inline_dca_text(
            filtered_markets,
            filtered_predictions,
            filtered_opportunities,
        )
        if dca_text:
            report.write(dca_text)
            report.write("\n")

        if self.config and self.config.report_include_telegram_report:
            report.write("📨 RAPPORT TÉLÉGRAM (COPIE)\n")
            telegram_report = self._generate_telegram_style_report(
                markets_data,
                predictions,
                opportunities,
                stats,
            )
            report.write(telegram_report.strip())
            report.write("\n\n")

        if stats and self._section_enabled("statistics"):
            report.write(self._generate_stats_section(stats))
            report.write("\n")

        glossary = self._generate_glossary_section()
        if glossary:
            report.write(glossary)

        return report.getvalue()
    
    def _section_enabled(self, name: str) -> bool:
        if not self.config or not getattr(self.config, "report_enabled_sections", None):
            return True
        return self.config.report_enabled_sections.get(name, True)

    def _metric_enabled(self, name: str) -> bool:
        if not self.config or not getattr(self.config, "report_advanced_metrics", None):
            return True
        return self.config.report_advanced_metrics.get(name, True)

    def _detail_level(self) -> str:
        if not self.config:
            return "detailed"
        return getattr(self.config, "report_detail_level", "detailed")

    def _is_simple_report(self) -> bool:
        return self._detail_level() == "simple"

    def _coin_option(self, symbol: str, key: str, default):
        if not self.config or not getattr(self.config, "coin_settings", None):
            return default
        symbol_key = symbol.upper()
        return self.config.coin_settings.get(symbol_key, {}).get(key, default)

    def _include_symbol_report(self, symbol: str) -> bool:
        if not self._coin_option(symbol, "include_report", True):
            return False
        return self._coin_hours_allowed(symbol, "report_hours")

    def _coin_investment_amount(self, symbol: str) -> float:
        if not self.config:
            return 0.0
        return float(self._coin_option(symbol, "investment_amount", self.config.investment_amount))

    def _coin_settings_dict(self, symbol: str) -> Dict[str, Any]:
        if not self.config or not getattr(self.config, "coin_settings", None):
            return {}
        symbol_key = symbol.upper()
        return self.config.coin_settings.get(symbol_key, {}) or {}

    def _notification_content_config(self, symbol: str) -> Dict[str, Any]:
        if not self.config or not getattr(self.config, "notification_content_by_coin", None):
            return {}

        content_map = self.config.notification_content_by_coin or {}
        merged: Dict[str, Any] = {}
        default_content = content_map.get("default")
        if isinstance(default_content, dict):
            merged.update(default_content)

        symbol_content = content_map.get(symbol.upper())
        if isinstance(symbol_content, dict):
            for key, value in symbol_content.items():
                if key == "glossary" and isinstance(value, dict):
                    base_glossary = merged.get("glossary") if isinstance(merged.get("glossary"), dict) else {}
                    merged["glossary"] = self._merge_glossary_content(base_glossary, value)
                else:
                    merged[key] = value

        return merged

    @staticmethod
    def _merge_glossary_content(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if isinstance(base, dict):
            result.update(base)
        if not isinstance(override, dict):
            return result
        for key in ("enabled", "title", "intro"):
            if key in override:
                result[key] = override[key]
        if "entries" in override and isinstance(override["entries"], list):
            result["entries"] = [
                entry for entry in override["entries"] if isinstance(entry, dict)
            ]
        return result

    @staticmethod
    def _format_template(template: str, context: Dict[str, Any]) -> str:
        if not template:
            return ""

        class _SafeDict(dict):
            def __missing__(self, key):
                return ""

        try:
            safe_context = _SafeDict({k: ("" if v is None else v) for k, v in context.items()})
            return template.format_map(safe_context).strip()
        except Exception:
            return template.strip()

    def _build_notification_context(
        self,
        symbol: str,
        market: Optional[MarketData],
        prediction: Optional[Prediction],
        opportunity: Optional[OpportunityScore],
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "symbol": symbol,
            "name": symbol,
            "prediction": "",
            "opportunity": "",
            "opportunity_score": "",
            "fear_greed": "",
            "gain": "",
        }
        if market:
            context.update({
                "price": self._format_price(market),
                "change_24h": self._format_change(market),
                "volume_24h": self._format_volume(market),
                "fear_greed": market.fear_greed_index if market.fear_greed_index is not None else "",
                "gain": self._format_gain_loss_text(market),
            })
        if prediction:
            context["prediction"] = self._explain_prediction(prediction)
        if opportunity:
            context["opportunity"] = opportunity.recommendation
            context["opportunity_score"] = opportunity.score
        return context

    def _append_glossary_section(
        self,
        lines: List[str],
        glossary_cfg: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        if not glossary_cfg or not glossary_cfg.get("enabled", True):
            return

        intro = glossary_cfg.get("intro") if isinstance(glossary_cfg.get("intro"), str) else ""
        entries = glossary_cfg.get("entries") if isinstance(glossary_cfg.get("entries"), list) else []

        cleaned_entries: List[Dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            term = str(entry.get("term", "")).strip()
            definition = str(entry.get("definition", "")).strip()
            if term and definition:
                cleaned_entries.append({"term": term, "definition": definition})

        if not intro and not cleaned_entries:
            return

        title = glossary_cfg.get("title") if isinstance(glossary_cfg.get("title"), str) else ""
        rendered_title = self._format_template(title, context) if title else f"📘 Glossaire {context.get('symbol', '')}".strip()

        lines.append("")
        lines.append(rendered_title)
        if intro:
            lines.append(self._format_template(intro, context))
        for entry in cleaned_entries:
            lines.append(f"- {entry['term']} : {entry['definition']}")

    @staticmethod
    def _normalize_hours_list(value: Any) -> List[int]:
        result: List[int] = []
        if value is None:
            return result
        if isinstance(value, (int, float)):
            return [int(value)]
        if isinstance(value, str):
            value = value.replace(";", ",")
            for part in value.split(","):
                part = part.strip()
                if part.isdigit():
                    result.append(int(part))
            return result
        if isinstance(value, list):
            for item in value:
                if isinstance(item, (int, float)):
                    result.append(int(item))
                elif isinstance(item, str) and item.strip().isdigit():
                    result.append(int(item.strip()))
        return sorted(set(result))

    @staticmethod
    def _normalize_timeframes_list(value: Any) -> List[int]:
        result: List[int] = []
        if value is None:
            return result
        if isinstance(value, (int, float)):
            val = int(value)
            if val > 0:
                return [val]
            return result
        if isinstance(value, str):
            value = value.replace(";", ",")
            for part in value.split(","):
                part = part.strip()
                if part.isdigit():
                    val = int(part)
                    if val > 0:
                        result.append(val)
            return result
        if isinstance(value, list):
            for item in value:
                if isinstance(item, (int, float)):
                    val = int(item)
                    if val > 0:
                        result.append(val)
                elif isinstance(item, str) and item.strip().isdigit():
                    val = int(item.strip())
                    if val > 0:
                        result.append(val)
        return sorted(set(result))

    def _current_hour(self) -> int:
        return datetime.now(timezone.utc).hour

    def _coin_hours_allowed(self, symbol: str, key: str) -> bool:
        hours_value = self._coin_option(symbol, key, None)
        if not hours_value:
            return True
        hours = self._normalize_hours_list(hours_value)
        if not hours:
            return True
        return self._current_hour() in hours

    def _resolve_coin_options(self, symbol: str, key: str) -> Dict[str, Any]:
        options = self._coin_option(symbol, key, {})
        if not isinstance(options, dict):
            return {}

        resolved: Dict[str, Any] = {}
        base_options = {}
        if "profiles" in options:
            base_options = options.get("default", {}) or {}
        else:
            base_options = {k: v for k, v in options.items() if k != "profiles"}

        if isinstance(base_options, dict):
            resolved.update(base_options)

        profiles = options.get("profiles", [])
        if isinstance(profiles, list):
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                hours = self._normalize_hours_list(profile.get("hours"))
                if hours and self._current_hour() not in hours:
                    continue
                profile_opts = profile.get("options", {})
                if isinstance(profile_opts, dict):
                    resolved.update(profile_opts)

        return resolved

    def get_report_options(self, symbol: str) -> Dict[str, Any]:
        return self._resolve_coin_options(symbol, "report_options")

    def get_notification_options(self, symbol: str) -> Dict[str, Any]:
        return self._resolve_coin_options(symbol, "notification_options")

    def get_report_timeframes(self, symbol: str) -> List[int]:
        options = self.get_report_options(symbol)
        timeframes = options.get("chart_timeframes") if isinstance(options, dict) else None
        timeframes_list = self._normalize_timeframes_list(timeframes)
        if timeframes_list:
            return timeframes_list
        return [24, 168]

    def get_notification_timeframes(self, symbol: str) -> List[int]:
        options = self.get_notification_options(symbol)
        timeframes = options.get("chart_timeframes") if isinstance(options, dict) else None
        timeframes_list = self._normalize_timeframes_list(timeframes)
        if timeframes_list:
            return timeframes_list
        if self.config and self.config.notification_chart_timeframes:
            return self._normalize_timeframes_list(self.config.notification_chart_timeframes)
        return [24, 168]

    def _generate_executive_summary(self, markets_data: Dict[str, MarketData],
                                   opportunities: Dict[str, OpportunityScore]) -> str:
        """Résumé exécutif"""
        
        summary = "📊 RÉSUMÉ EXÉCUTIF\n"

        has_market_data = bool(markets_data)
        has_opportunities = bool(opportunities)

        if not has_market_data and not has_opportunities:
            summary += "Données insuffisantes pour générer un résumé exécutif.\n\n"
            return summary

        simple = self._is_simple_report()

        if has_opportunities:
            best_opp = max(opportunities.items(), key=lambda x: x[1].score)
            worst_opp = min(opportunities.items(), key=lambda x: x[1].score)
            if simple:
                summary += (
                    f"👉 La meilleure piste du moment est {best_opp[0]} (score {best_opp[1].score}/10).\n"
                    "Si tu débutes, retiens simplement que plus le score est élevé, plus l'opportunité semble intéressante.\n"
                )
                summary += (
                    f"🚫 À éviter pour l'instant : {worst_opp[0]} (score {worst_opp[1].score}/10).\n\n"
                )
            else:
                summary += (
                    f"🎯 Meilleure opportunité : {best_opp[0]} "
                    f"(Score: {best_opp[1].score}/10)\n"
                )
                summary += (
                    f"⚠️ À éviter : {worst_opp[0]} "
                    f"(Score: {worst_opp[1].score}/10)\n\n"
                )
        else:
            summary += "Aucune opportunité analysée pour le moment.\n\n"

        if has_market_data:
            changes = self._collect_valid_changes(markets_data)
            if changes:
                avg_change = sum(changes) / len(changes)
                trend = "en hausse" if avg_change > 0 else "en baisse"
                if simple:
                    summary += (
                        f"📈 Globalement, le marché est {trend} d'environ {avg_change:+.2f}% sur 24h.\n"
                        "Cela veut dire que la plupart des prix suivent cette direction générale.\n\n"
                    )
                else:
                    emoji = "📈" if avg_change > 0 else "📉"
                    summary += (
                        f"Tendance générale 24h : {emoji} "
                        f"({avg_change:+.2f}%)\n\n"
                    )
            else:
                summary += "Tendance générale 24h : données indisponibles\n\n"
        else:
            summary += "Données de marché indisponibles pour le moment.\n\n"

        return summary
    
    def _generate_crypto_section(self, symbol: str, market: MarketData,
                                prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Section pour une crypto"""

        section = f"\n💎 {symbol}\n\n"
        report_opts = self.get_report_options(symbol)
        show_price = report_opts.get("show_price", True)
        show_volume = report_opts.get("show_volume", True)
        show_curves = report_opts.get("show_curves", True)
        show_technicals = report_opts.get("show_technicals", True)
        show_prediction = report_opts.get("show_prediction", True)
        show_opportunity = report_opts.get("show_opportunity", True)
        show_brokers = report_opts.get(
            "show_brokers",
            self.config.report_include_broker_prices if self.config else True,
        )
        show_fear_greed = report_opts.get("show_fear_greed", True)
        show_gain = report_opts.get("show_gain", True)
        show_notification_hint = report_opts.get("show_notification_hint", True)
        report_timeframes = self.get_report_timeframes(symbol)

        detail_level = self._detail_level()

        price_comment = change_comment = volume_comment = None
        if show_price:
            price_value = self._format_price(market)
            section += f"Prix actuel : {price_value}\n"

            change_value = self._format_change(market)
            section += f"Changement 24h : {change_value}\n"

            if show_volume:
                volume_value = self._format_volume(market)
                section += f"Volume 24h : {volume_value}\n"

            price_comment = self._generate_price_comment(market)
            change_comment = self._generate_change_comment(market)
            if show_volume:
                volume_comment = self._generate_volume_comment(market)

        if detail_level == "simple":
            section += "\n"
            if show_opportunity and opportunity:
                section += f"⭐ Score : {opportunity.score}/10 — {opportunity.recommendation}\n"
                section += "(Un score supérieur à 7 signifie généralement une bonne occasion.)\n"

            if show_price:
                change = market.current_price.change_24h if market.current_price else None
                if change is not None:
                    section += f"👉 Translation : {symbol} est {self._describe_price_move(change)} sur la dernière journée.\n"
                else:
                    section += f"👉 Translation : nous n'avons pas assez d'informations sur l'évolution récente.\n"
            if show_prediction and prediction:
                section += f"🔮 Résumé prédiction : {self._explain_prediction(prediction)}\n"

            if show_gain:
                gain_text = self._format_gain_loss_text(market)
                if gain_text:
                    section += f"💰 {gain_text}\n"

            if show_curves:
                section += "📈 Graphiques détaillés envoyés avec le rapport (24h, 7j).\n"

            return section + "\n"

        if show_curves:
            section += "📈 Graphiques détaillés envoyés avec le rapport (24h, 7j).\n\n"

        if show_price:
            for comment in (price_comment, change_comment, volume_comment):
                if comment:
                    section += f"→ {comment}\n"
            section += "\n"

        if show_technicals:
            ti = market.technical_indicators
            if ti:
                section += "Indicateurs techniques :\n"
                rsi_display = "indisponible" if ti.rsi is None else f"{ti.rsi:.0f}"
                section += f"  • RSI : {rsi_display}"
                if ti.rsi is not None:
                    if ti.rsi < 30:
                        section += " (survendu 🟢)\n"
                    elif ti.rsi > 70:
                        section += " (suracheté 🔴)\n"
                    else:
                        section += "\n"
                else:
                    section += "\n"

                ma20_display = "indisponible" if ti.ma20 is None else f"{ti.ma20:.2f}€"
                support_display = "indisponible" if ti.support is None else f"{ti.support:.2f}€"
                resistance_display = "indisponible" if ti.resistance is None else f"{ti.resistance:.2f}€"

                section += f"  • MA20 : {ma20_display}\n"
                section += f"  • Support : {support_display}\n"
                section += f"  • Résistance : {resistance_display}\n\n"
                rsi_comment = self._generate_rsi_comment(ti.rsi)
                if rsi_comment:
                    section += f"     ➜ {rsi_comment}\n"
                ma_comment = self._generate_ma_comment(market)
                if ma_comment:
                    section += f"     ➜ {ma_comment}\n"
                sr_comment = self._generate_support_resistance_comment(market)
                if sr_comment:
                    section += f"     ➜ {sr_comment}\n"
            else:
                section += "Indicateurs techniques indisponibles.\n\n"

        if show_prediction and prediction:
            section += f"🔮 Prédiction : {prediction.direction} {prediction.prediction_type.value}\n"
            section += f"   Confiance : {prediction.confidence}%\n"
            section += f"   Cible haute : {prediction.target_high:.2f}€\n"
            section += f"   Cible basse : {prediction.target_low:.2f}€\n\n"
            explanation = self._explain_prediction(prediction)
            section += f"   Explication simple : {explanation}\n"
            prediction_comment = self._generate_prediction_comment(prediction)
            if prediction_comment:
                section += f"   ➜ {prediction_comment}\n\n"
            else:
                section += "\n"

        if show_opportunity and opportunity:
            section += f"⭐ Score opportunité : {opportunity.score}/10\n"
            section += f"   {opportunity.recommendation}\n\n"
            if opportunity.reasons:
                section += "   Raisons :\n"
                for reason in opportunity.reasons:
                    section += f"   • {reason}\n"
                section += "\n"

        if show_fear_greed and market.fear_greed_index is not None:
            section += f"😱 Fear & Greed Index : {market.fear_greed_index}/100\n"
            fg_comment = self._generate_fear_greed_comment(market.fear_greed_index)
            if fg_comment:
                section += f"   → {fg_comment}\n"
            section += "\n"

        if show_gain:
            gain_text = self._format_gain_loss_text(market)
            if gain_text:
                section += f"💰 {gain_text}\n\n"

        if show_brokers:
            broker_quotes = self._get_broker_quotes(symbol, market)
            if broker_quotes:
                section += "Courtiers :\n"
                for quote in broker_quotes:
                    section += self._format_broker_quote(quote)
                section += "\n"

        if show_notification_hint:
            notification = self._generate_notification_text(symbol, opportunity, prediction)
            if notification:
                section += f"🔔 Notification suggérée : {notification}\n\n"

        return section
    
    def _generate_comparison_section(self, markets_data: Dict[str, MarketData],
                                    opportunities: Dict[str, OpportunityScore]) -> str:
        """Section comparative"""
        
        section = "📊 COMPARAISON\n"

        if not markets_data:
            section += "Aucune donnée de marché disponible.\n\n"
            return section

        # Tableau comparatif
        section += f"{'Symbole':<10} {'Prix':<16} {'24h':<12} {'RSI':<10} {'Score':<8}\n"

        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            opp = opportunities.get(symbol)

            price_text = self._format_price(market)
            change_text = self._format_change(market)
            rsi_value = self._format_rsi(market)
            score_text = f"{opp.score}/10" if opp else "N/A"

            section += f"{symbol:<10} {price_text:<16} {change_text:<12} {rsi_value:<10} {score_text:<8}\n"
        
        section += "\n"
        return section
    
    def _generate_recommendations(self, markets_data: Dict[str, MarketData],
                                 opportunities: Dict[str, OpportunityScore]) -> str:
        """Recommandations"""

        section = "💡 RECOMMANDATIONS\n"
        if self._is_simple_report():
            section += "Nous traduisons les signaux en instructions faciles à suivre :\n\n"

        if not opportunities:
            section += "Aucune opportunité analysée pour le moment.\n\n"
            return section

        # Trier par score d'opportunité
        sorted_opps = sorted(opportunities.items(), key=lambda x: x[1].score, reverse=True)

        # Achats recommandés
        section += "À acheter maintenant :\n"
        buy_recommendations = [item for item in sorted_opps if item[1].score >= 7]

        if buy_recommendations:
            for symbol, opp in buy_recommendations:
                market = markets_data.get(symbol)
                section += f"  ✅ {symbol} à {self._format_price(market)} "
                section += f"(Score: {opp.score}/10)\n"
                if self._is_simple_report():
                    section += "     → Action simple : envisage un achat partiel si ton budget le permet.\n"
        else:
            section += "  Aucune opportunité excellente actuellement\n"

        section += "\n"

        # À surveiller
        section += "À surveiller :\n"
        watch_recommendations = [item for item in sorted_opps if 5 <= item[1].score < 7]

        if watch_recommendations:
            for symbol, opp in watch_recommendations[:3]:
                market = markets_data.get(symbol)
                section += f"  👀 {symbol} à {self._format_price(market)} "
                section += f"(Score: {opp.score}/10)\n"
                if self._is_simple_report():
                    section += "     → Garde ce symbole dans ta liste, il pourrait bouger prochainement.\n"
        else:
            section += "  Aucune crypto à surveiller particulièrement\n"

        section += "\n"
        
        # À éviter
        section += "À éviter pour le moment :\n"
        avoid_recommendations = [item for item in sorted_opps if item[1].score < 5]
        
        if avoid_recommendations:
            for symbol, opp in avoid_recommendations:
                section += f"  ❌ {symbol} (Score: {opp.score}/10)\n"
                if self._is_simple_report():
                    section += "     → Mieux vaut patienter, le risque est jugé élevé.\n"
        else:
            section += "  Toutes les cryptos ont un score correct\n"

        section += "\n"

        return section

    def _generate_advanced_analysis(
        self,
        markets_data: Dict[str, MarketData],
        opportunities: Dict[str, OpportunityScore],
    ) -> str:
        section = "🔬 ANALYSES AVANCÉES\n"

        if not markets_data:
            section += "Aucune donnée de marché disponible pour les analyses avancées.\n\n"
            return section

        has_content = False

        for symbol in sorted(markets_data.keys()):
            market = markets_data[symbol]
            prices = self._extract_price_series(market)
            if len(prices) < 2:
                continue

            returns = self._compute_returns(prices)
            opp = opportunities.get(symbol)

            section += f"{symbol}\n"
            has_content = True

            if self._metric_enabled("volatility"):
                volatility = self._calculate_volatility(returns)
                if volatility is not None:
                    section += f"  • Volatilité (échantillon) : {volatility:.2f}%\n"

            if self._metric_enabled("drawdown"):
                drawdown = self._calculate_max_drawdown(prices)
                if drawdown is not None:
                    section += f"  • Drawdown maximum : {drawdown:.2f}%\n"

            if self._metric_enabled("trend_strength"):
                trend_strength = self._calculate_trend_strength(market)
                if trend_strength is not None:
                    section += f"  • Force de tendance : {trend_strength:.2f}/10\n"

            if self._metric_enabled("risk_score"):
                risk_label = self._calculate_risk_label(returns, opp)
                section += f"  • Profil de risque : {risk_label}\n"

            if self._metric_enabled("dca_projection") and self.config:
                dca_projection = self._calculate_dca_projection(prices, self.config.investment_amount)
                if dca_projection is not None and market.current_price:
                    dca_avg, quantity = dca_projection
                    diff = market.current_price.price_eur - dca_avg
                    diff_pct = (diff / dca_avg) * 100 if dca_avg else 0
                    section += (
                        f"  • Simulation DCA ({len(prices[-30:])} points) : {dca_avg:.2f}€"
                        f" ({diff_pct:+.2f}% vs prix actuel)\n"
                        f"    Quantité approximative achetée (budget {self.config.investment_amount:.2f}€) : {quantity:.4f} {symbol}\n"
                    )

            section += "\n"

        if self._metric_enabled("correlation") and len(markets_data) > 1:
            correlations = self._calculate_correlations(markets_data)
            if correlations:
                section += "Corrélations des rendements récents :\n"
                for pair, value in correlations:
                    section += f"  • {pair[0]} / {pair[1]} : {value:+.2f}\n"
                section += "\n"
                has_content = True

        if not has_content:
            section += "Pas assez de données pour produire des analyses avancées.\n\n"

        return section

    @staticmethod
    def _format_price(market: Optional[MarketData]) -> str:
        """Retourne une représentation textuelle robuste du prix."""

        if not market or not market.current_price or market.current_price.price_eur is None:
            return "prix indisponible"

        return f"{market.current_price.price_eur:.2f}€"

    @staticmethod
    def _format_change(market: Optional[MarketData]) -> str:
        if not market or not market.current_price:
            return "indisponible"

        change = market.current_price.change_24h
        if change is None:
            return "indisponible"

        return f"{change:+.2f}%"

    @staticmethod
    def _format_volume(market: Optional[MarketData]) -> str:
        if not market or not market.current_price:
            return "indisponible"

        volume = market.current_price.volume_24h
        if volume is None:
            return "indisponible"

        return f"{volume:,.0f}"

    @staticmethod
    def _format_rsi(market: Optional[MarketData]) -> str:
        if not market or not market.technical_indicators:
            return "indisponible"

        rsi = market.technical_indicators.rsi
        if rsi is None:
            return "indisponible"

        return f"{rsi:.0f}"

    @staticmethod
    def _collect_valid_changes(markets_data: Dict[str, MarketData]) -> List[float]:
        """Retourne toutes les variations 24h disponibles."""

        changes: List[float] = []
        for market in markets_data.values():
            if not market or not market.current_price:
                continue

            change = market.current_price.change_24h
            if change is not None:
                changes.append(change)

        return changes

    def _generate_stats_section(self, stats: Dict) -> str:
        """Section statistiques"""
        
        section = "📈 STATISTIQUES\n"
        
        section += f"Vérifications totales : {stats.get('total_checks', 0)}\n"
        section += f"Alertes envoyées : {stats.get('total_alerts', 0)}\n"
        section += f"Erreurs : {stats.get('total_errors', 0)}\n"
        section += f"Moyenne vérifications/jour : {stats.get('avg_checks_per_day', 0):.1f}\n\n"

        return section

    def _generate_inline_chart_text(self, markets_data: Dict[str, MarketData]) -> Optional[str]:
        if not markets_data or not self.config:
            return None
        if not self.config.report_include_chart:
            any_coin = any(self._coin_option(symbol, "include_chart", False) for symbol in markets_data)
            if not any_coin:
                return None
        else:
            any_coin = True
        if not any_coin:
            return None

        section = "📈 GRAPHIQUE 24H (TEXTE)\n"
        section += (
            "Cette section résume les variations principales du graphique sur 24h."
            " Pour obtenir l'image complète, active l'envoi du graphique dans le bot.\n\n"
        )

        for symbol in sorted(markets_data.keys()):
            if not self._include_symbol_report(symbol):
                continue
            if not self._coin_option(symbol, "include_chart", True):
                continue
            market = markets_data[symbol]
            change = market.current_price.change_24h if market.current_price else None
            section += f"• {symbol} : {self._describe_price_move(change or 0)} sur 24h"
            if change is not None:
                section += f" (variation : {change:+.2f}%)."
            section += "\n"

        section += "\nAstuce : combine ces infos avec les plans DCA pour décider quand lisser tes achats.\n"
        return section

    def _generate_inline_dca_text(
        self,
        markets_data: Dict[str, MarketData],
        predictions: Dict[str, Prediction],
        opportunities: Dict[str, OpportunityScore],
    ) -> Optional[str]:
        if not self.config:
            return None
        if not self.config.report_include_dca:
            any_coin = any(self._coin_option(symbol, "include_dca", False) for symbol in markets_data)
            if not any_coin:
                return None

        section = "💡 PLAN DCA EN VERSION TEXTE\n"
        section += (
            "Ce plan découpe le budget actuel en plusieurs paliers pour lisser les achats."
            " Utilise-le comme aide-mémoire si tu préfères agir manuellement.\n\n"
        )

        for symbol in sorted(markets_data.keys()):
            if not self._include_symbol_report(symbol):
                continue
            if not self._coin_option(symbol, "include_dca", True):
                continue
            market = markets_data[symbol]
            prediction = predictions.get(symbol)
            opportunity = opportunities.get(symbol)
            if not market or not prediction or not opportunity or not market.current_price:
                continue
            plan = DCAService().generate_dca_plan(
                symbol,
                self._coin_investment_amount(symbol),
                market.current_price.price_eur,
                market,
                prediction,
                opportunity,
            )
            section += f"{symbol} — Stratégie {plan['strategy']} sur {plan['timeframe_days']} jours\n"
            section += f"Budget total : {plan['total_investment']:.2f}€ (prix moyen cible {plan['expected_avg_price']:.2f}€)\n"
            for entry in plan['entries']:
                section += (
                    f"  • Palier #{entry['entry_number']} : {entry['amount_eur']:.2f}€ visé autour de {entry['target_price']:.2f}€"
                    f" — condition : {entry['condition']}\n"
                )
            section += "\n"

        return section if section.strip() else None

    def _generate_telegram_style_report(
        self,
        markets_data: Dict[str, MarketData],
        predictions: Dict[str, Prediction],
        opportunities: Dict[str, OpportunityScore],
        stats: Optional[Dict[str, Any]],
    ) -> str:
        filtered_markets = {
            symbol: market
            for symbol, market in markets_data.items()
            if self._include_symbol_report(symbol)
        }
        filtered_predictions = {
            symbol: pred
            for symbol, pred in predictions.items()
            if self._include_symbol_report(symbol)
        }
        filtered_opps = {
            symbol: opp
            for symbol, opp in opportunities.items()
            if self._include_symbol_report(symbol)
        }
        summary_service = SummaryService(self.config)
        summary = summary_service.generate_summary(
            filtered_markets,
            filtered_predictions,
            filtered_opps,
            simple=self.config.use_simple_language,
        )
        sections = [summary]

        chart_text = self._generate_inline_chart_text(filtered_markets)
        if chart_text:
            sections.append(chart_text)

        dca_text = self._generate_inline_dca_text(filtered_markets, filtered_predictions, filtered_opps)
        if dca_text:
            sections.append(dca_text)

        sections.append(self._generate_recommendations(filtered_markets, filtered_opps))

        if stats:
            sections.append(self._generate_stats_section(stats))

        return "\n\n".join(section.strip() for section in sections if section)

    # ------------------------------------------------------------------
    # Helpers analytiques
    # ------------------------------------------------------------------

    @staticmethod
    def _explain_prediction(prediction: Prediction) -> str:
        mapping = {
            "HAUSSIER": "le prix a plus de chances de monter dans les prochaines heures.",
            "LÉGÈREMENT HAUSSIER": "le prix pourrait monter doucement, sans certitude.",
            "NEUTRE": "aucun mouvement clair en vue, mieux vaut observer.",
            "LÉGÈREMENT BAISSIER": "le prix pourrait baisser un peu, prudence.",
            "BAISSIER": "le prix a plus de chances de baisser, éviter un achat impulsif.",
        }
        text = mapping.get(prediction.prediction_type.value, "le modèle reste incertain.")
        if prediction.confidence >= 75:
            text += " Confiance élevée : le scénario est assez probable."
        elif prediction.confidence <= 45:
            text += " Confiance faible : prendre l'information avec recul."
        else:
            text += " Confiance moyenne : considérer ce signal comme un avis, pas une certitude."
        return text

    @staticmethod
    def _extract_price_series(market: MarketData) -> List[float]:
        if market.price_history:
            return [p.price_eur for p in market.price_history if p.price_eur is not None]
        return []

    @staticmethod
    def _compute_returns(prices: List[float]) -> List[float]:
        if len(prices) < 2:
            return []
        returns: List[float] = []
        for prev, curr in zip(prices[:-1], prices[1:]):
            if prev:
                returns.append((curr - prev) / prev * 100)
        return returns

    @staticmethod
    def _calculate_volatility(returns: List[float]) -> Optional[float]:
        if len(returns) < 2:
            return None
        try:
            return stdev(returns)
        except Exception:
            return None

    @staticmethod
    def _calculate_max_drawdown(prices: List[float]) -> Optional[float]:
        if not prices:
            return None
        peak = prices[0]
        max_dd = 0.0
        for price in prices[1:]:
            if price > peak:
                peak = price
            elif peak:
                drawdown = (price - peak) / peak * 100
                if drawdown < max_dd:
                    max_dd = drawdown
        return max_dd

    @staticmethod
    def _calculate_trend_strength(market: MarketData) -> Optional[float]:
        change_24h = market.current_price.change_24h if market.current_price else None
        weekly = getattr(market, "weekly_change", None)
        ti = market.technical_indicators
        components: List[float] = []
        if change_24h is not None:
            components.append(max(-5.0, min(5.0, change_24h / 4)))
        if weekly is not None:
            components.append(max(-5.0, min(5.0, weekly / 10)))
        if ti and ti.macd_histogram is not None:
            components.append(max(-5.0, min(5.0, ti.macd_histogram * 5)))
        if ti and ti.rsi is not None:
            components.append(max(-5.0, min(5.0, (50 - abs(ti.rsi - 50)) / 10)))
        if not components:
            return None
        score = sum(components) / len(components) + 5
        return max(0.0, min(10.0, score))

    @staticmethod
    def _calculate_risk_label(returns: List[float], opportunity: Optional[OpportunityScore]) -> str:
        volatility = ReportService._calculate_volatility(returns) or 0
        avg_return = sum(returns) / len(returns) if returns else 0
        opp_score = opportunity.score if opportunity else 5
        risk_index = volatility - avg_return / 2 - opp_score
        if risk_index <= -5:
            return "🟢 Faible"
        if risk_index <= 2:
            return "🟡 Modéré"
        return "🔴 Élevé"

    @staticmethod
    def _calculate_dca_projection(prices: List[float], investment_amount: float) -> Optional[Tuple[float, float]]:
        if not prices or investment_amount <= 0:
            return None
        sample = prices[-min(30, len(prices)) :]
        if not sample:
            return None
        avg_price = sum(sample) / len(sample)
        if avg_price <= 0:
            return None
        quantity = investment_amount / avg_price
        return avg_price, quantity

    def _calculate_correlations(self, markets_data: Dict[str, MarketData]) -> List[Tuple[Tuple[str, str], float]]:
        results: List[Tuple[Tuple[str, str], float]] = []
        for left, right in combinations(sorted(markets_data.keys()), 2):
            left_returns = self._compute_returns(self._extract_price_series(markets_data[left]))
            right_returns = self._compute_returns(self._extract_price_series(markets_data[right]))
            n = min(len(left_returns), len(right_returns))
            if n < 5:
                continue
            corr = self._pearson_correlation(left_returns[-n:], right_returns[-n:])
            if corr is not None:
                results.append(((left, right), corr))
        return results

    @staticmethod
    def _pearson_correlation(series_a: List[float], series_b: List[float]) -> Optional[float]:
        n = min(len(series_a), len(series_b))
        if n == 0:
            return None
        mean_a = sum(series_a) / n
        mean_b = sum(series_b) / n
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(series_a, series_b))
        var_a = sum((a - mean_a) ** 2 for a in series_a)
        var_b = sum((b - mean_b) ** 2 for b in series_b)
        if var_a == 0 or var_b == 0:
            return None
        return cov / (var_a ** 0.5 * var_b ** 0.5)

    @staticmethod
    def _describe_price_move(change: float) -> str:
        if change > 10:
            return "fortement en hausse"
        if change > 3:
            return "plutôt en hausse"
        if change > 0.5:
            return "légèrement en hausse"
        if change > -0.5:
            return "quasi stable"
        if change > -3:
            return "légèrement en baisse"
        if change > -10:
            return "plutôt en baisse"
        return "fortement en baisse"

    def _format_gain_loss_text(self, market: MarketData) -> Optional[str]:
        if not self.config or self.config.investment_amount <= 0 or not market.current_price:
            return None
        change_24h = market.current_price.change_24h
        if change_24h is None:
            return None
        gain = self.config.investment_amount * (change_24h / 100)
        if abs(gain) < 0.5:
            return (
                f"Avec {self.config.investment_amount:.0f}€ investis hier, le résultat serait quasiment neutre"
            )
        verb = "gagné" if gain > 0 else "perdu"
        return (
            f"Avec {self.config.investment_amount:.0f}€ investis il y a 24h, tu aurais {verb} environ {abs(gain):.2f}€"
        )

    def _generate_price_comment(self, market: Optional[MarketData]) -> Optional[str]:
        if not market or not market.current_price or market.current_price.price_eur is None:
            return None
        ti = market.technical_indicators
        price = market.current_price.price_eur
        if ti and ti.support and ti.resistance:
            if price <= ti.support * 1.02:
                return "Tout proche du support, la zone actuelle attire les achats défensifs."
            if price >= ti.resistance * 0.98:
                return "Très proche de la résistance, une prise de profit rapide est fréquente."
        if ti and ti.ma20:
            diff_pct = (price - ti.ma20) / ti.ma20 * 100 if ti.ma20 else 0
            if abs(diff_pct) < 1:
                return "Prix quasiment aligné sur la moyenne mobile 20 périodes, tendance stable."
            if diff_pct > 0:
                return f"Prix {diff_pct:.1f}% au-dessus de la MA20 : momentum haussier confirmé."
            return f"Prix {abs(diff_pct):.1f}% sous la MA20 : le marché respire avant de décider."
        return "Prix dans une zone médiane sans niveau technique majeur."

    def _generate_change_comment(self, market: Optional[MarketData]) -> Optional[str]:
        if not market or not market.current_price:
            return None
        change = market.current_price.change_24h
        if change is None:
            return None
        if change >= 5:
            return "Hausse explosive sur 24h : attention aux retournements rapides."
        if change >= 1:
            return "Hausse modérée, le flux acheteur reste dominant."
        if change > -1:
            return "Variation quasi neutre, le marché est en observation."
        if change > -5:
            return "Baisse contrôlée, souvent une respiration saine si les fondamentaux restent bons."
        return "Chute marquée, ne pas se précipiter tant que le flux vendeur domine."

    def _generate_volume_comment(self, market: Optional[MarketData]) -> Optional[str]:
        if not market or not market.current_price:
            return None
        volume = market.current_price.volume_24h
        if volume is None:
            return None
        if volume >= 1_000_000:
            return "Volume très élevé : la décision actuelle est portée par un flux important."
        if volume >= 100_000:
            return "Volume solide, les mouvements sont soutenus par des échanges significatifs."
        return "Volume léger, les variations peuvent être influencées par quelques ordres."

    def _generate_rsi_comment(self, rsi: Optional[float]) -> Optional[str]:
        if rsi is None:
            return None
        if rsi >= 80:
            return "RSI très haut : scénario de surchauffe, surveiller un éventuel retournement."
        if rsi >= 70:
            return "RSI suracheté : gains rapides possibles mais risque de correction élevé."
        if rsi <= 20:
            return "RSI extrêmement bas : capitulation possible, surveiller un rebond technique."
        if rsi <= 30:
            return "RSI survendu : les acheteurs contrarians guettent souvent cette zone."
        return "RSI neutre : l'indicateur n'envoie pas de signal fort."

    def _generate_ma_comment(self, market: Optional[MarketData]) -> Optional[str]:
        if not market or not market.current_price:
            return None
        ti = market.technical_indicators
        if not ti or ti.ma20 is None or ti.ma20 == 0 or market.current_price.price_eur is None:
            return None
        diff_pct = (market.current_price.price_eur - ti.ma20) / ti.ma20 * 100
        if diff_pct > 3:
            return "Le prix évolue nettement au-dessus de la MA20, confirmant un biais haussier."
        if diff_pct < -3:
            return "Le prix reste nettement sous la MA20 : le marché met la pression sur les acheteurs."
        return "Le prix gravite autour de la MA20 : la tendance court terme est en équilibre."

    def _generate_support_resistance_comment(self, market: Optional[MarketData]) -> Optional[str]:
        if not market or not market.current_price or not market.technical_indicators:
            return None
        price = market.current_price.price_eur
        if price is None:
            return None
        ti = market.technical_indicators
        comments = []
        if ti.support:
            gap_support = (price - ti.support) / ti.support * 100
            if gap_support < 1:
                comments.append("Appuyé sur le support, réaction possible des acheteurs.")
        if ti.resistance:
            gap_resistance = (ti.resistance - price) / ti.resistance * 100
            if gap_resistance < 1:
                comments.append("À portée immédiate de la résistance, vigilance sur les prises de profit.")
        if not comments:
            return "Pas de proximité particulière avec support ou résistance majeurs."
        return " ".join(comments)

    def _generate_prediction_comment(self, prediction: Optional[Prediction]) -> Optional[str]:
        if not prediction:
            return None
        confidence = prediction.confidence
        if confidence >= 75:
            return "Signal jugé fiable par le modèle : on peut agir rapidement avec un money management strict."
        if confidence <= 45:
            return "Signal fragile, mieux vaut attendre une confirmation avant d'agir."
        trend = prediction.prediction_type.value
        if trend in ("HAUSSIER", "LÉGÈREMENT HAUSSIER"):
            return "Biais haussier mais sans certitude : fractionner les entrées limite le risque."
        if trend in ("BAISSIER", "LÉGÈREMENT BAISSIER"):
            return "Le modèle anticipe des pressions vendeuses, privilégier la prudence."
        return "Modèle neutre : se concentrer sur les supports et résistances pour décider."

    def _generate_fear_greed_comment(self, value: int) -> Optional[str]:
        if value <= 15:
            return "Peur extrême : historiquement, de bonnes opportunités apparaissent mais la volatilité reste forte."
        if value <= 25:
            return "Sentiment très craintif, idéal pour accumuler progressivement si les fondamentaux tiennent."
        if value >= 85:
            return "Euphorie extrême : les excès haussiers peuvent vite se renverser."
        if value >= 75:
            return "Marché très confiant, attention aux bull traps."
        return "Sentiment équilibré : aucune émotion dominante, la technique fait loi."

    def _generate_outlook_sentence(
        self,
        symbol: str,
        market: Optional[MarketData],
        prediction: Optional[Prediction],
        opportunity: Optional[OpportunityScore],
    ) -> Optional[str]:
        if not market:
            return None

        change_24h = None
        if market.current_price and market.current_price.change_24h is not None:
            change_24h = market.current_price.change_24h

        confidence = prediction.confidence if prediction else None
        outlook_core: Optional[str] = None

        if prediction:
            trend = prediction.prediction_type
            if trend == PredictionType.BULLISH:
                outlook_core = "la dynamique est très haussière et devrait poursuivre dans les prochains jours"
            elif trend == PredictionType.SLIGHTLY_BULLISH:
                outlook_core = "les acheteurs semblent prendre l'avantage et la progression peut continuer"
            elif trend == PredictionType.SLIGHTLY_BEARISH:
                outlook_core = "la pression vendeuse gagne du terrain, je m'attends à une consolidation"
            elif trend == PredictionType.BEARISH:
                outlook_core = "la tendance reste baissière et risque de s'accentuer dans les prochaines séances"
            else:
                outlook_core = "le marché reste hésitant, possiblement en range sur quelques jours"

        if not outlook_core and change_24h is not None:
            if change_24h >= 2:
                outlook_core = "les acheteurs dominent aujourd'hui, la hausse peut se prolonger si le flux reste positif"
            elif change_24h <= -2:
                outlook_core = "la baisse est marquée pour l'instant, prudence tant que la pression vendeuse continue"

        if not outlook_core:
            return None

        parts: List[str] = ["🧭 Mon ressenti :"]
        parts.append(outlook_core)

        if confidence is not None:
            parts.append(f"(confiance {confidence:.0f}%)")

        if opportunity and opportunity.score is not None:
            if opportunity.score >= 7:
                parts.append(f"→ Score opportunité {opportunity.score}/10, configuration attractive.")
            elif opportunity.score <= 4:
                parts.append(f"→ Score opportunité {opportunity.score}/10, vigilance.")

        if change_24h is not None:
            parts.append(f"(variation 24h {change_24h:+.1f}%)")

        return " ".join(parts)

    def _generate_notification_text(
        self,
        symbol: str,
        opportunity: Optional[OpportunityScore],
        prediction: Optional[Prediction],
    ) -> Optional[str]:
        recommendation = opportunity.recommendation if opportunity and opportunity.recommendation else ""
        if opportunity and opportunity.score >= 8:
            base = f"{symbol} prioritaire : {recommendation or 'opportunité de premier plan'}."
        elif opportunity and opportunity.score >= 6:
            base = f"{symbol} à surveiller sérieusement : {recommendation or 'bonne configuration'}."
        elif opportunity:
            fallback = "pas d'action urgente"
            base = f"{symbol} reste en watchlist : {recommendation or fallback}."
        else:
            base = f"{symbol} sans score d'opportunité : décider selon ton plan personnel."
        if prediction:
            trend = prediction.prediction_type.value.lower()
            base += f" Signal modèle : {trend} ({prediction.confidence:.0f}% confiance)."
        return base

    def generate_coin_notification(
        self,
        symbol: str,
        market: Optional[MarketData],
        prediction: Optional[Prediction],
        opportunity: Optional[OpportunityScore],
    ) -> Optional[str]:
        if not market or not market.current_price:
            return None

        if not self._coin_option(symbol, "include_notification", True):
            return None

        if not self._coin_hours_allowed(symbol, "notification_hours"):
            return None

        if not self._passes_notification_thresholds(symbol, market, opportunity):
            return None

        notification_opts = self.get_notification_options(symbol)
        show_price = notification_opts.get("show_price", True)
        show_curves = notification_opts.get(
            "show_curves",
            self.config.notification_include_chart if self.config else True,
        )
        show_prediction = notification_opts.get("show_prediction", True)
        show_opportunity = notification_opts.get("show_opportunity", True)
        show_brokers = notification_opts.get(
            "show_brokers",
            self.config.notification_include_brokers if self.config else True,
        )
        show_fear_greed = notification_opts.get("show_fear_greed", True)
        show_gain = notification_opts.get("show_gain", True)

        content_config = self._notification_content_config(symbol)
        context = self._build_notification_context(symbol, market, prediction, opportunity)

        title_template = content_config.get("title") if isinstance(content_config.get("title"), str) else ""
        title_line = self._format_template(title_template, context) if title_template else f"💎 {symbol} — Mise à jour dédiée"
        lines: List[str] = [title_line]

        intro_template = content_config.get("intro") if isinstance(content_config.get("intro"), str) else ""
        if intro_template:
            lines.append(self._format_template(intro_template, context))

        if show_price:
            lines.append(
                f"💰 Prix actuel : {self._format_price(market)} "
                f"(variation 24h : {self._format_change(market)}, volume 24h : {self._format_volume(market)})"
            )
            price_comment = self._generate_price_comment(market)
            change_comment = self._generate_change_comment(market)
            volume_comment = self._generate_volume_comment(market)
            for comment in (price_comment, change_comment, volume_comment):
                if comment:
                    lines.append(f"• {comment}")

        if show_curves and self.config and self.config.notification_include_chart:
            lines.append("📈 Un graphique détaillé arrive dans le message suivant.")

        if show_prediction and prediction:
            lines.append(f"🔮 Point de vue IA : {self._explain_prediction(prediction)}")

        if show_opportunity and opportunity:
            lines.append(f"⭐ Recommandation : {opportunity.recommendation} (score {opportunity.score}/10)")

        if show_fear_greed and market.fear_greed_index is not None:
            fg_line = f"😱 Sentiment marché : {market.fear_greed_index}/100"
            fg_comment = self._generate_fear_greed_comment(market.fear_greed_index)
            if fg_comment:
                fg_line += f" — {fg_comment}"
            lines.append(fg_line)

        if show_gain:
            gain_text = self._format_gain_loss_text(market)
            if gain_text:
                lines.append(f"📊 {gain_text}")

        custom_lines = content_config.get("custom_lines")
        if isinstance(custom_lines, list):
            for custom_line in custom_lines:
                if isinstance(custom_line, str) and custom_line.strip():
                    lines.append(self._format_template(custom_line, context))

        notification_text = self._generate_notification_text(symbol, opportunity, prediction)
        if notification_text:
            lines.append(f"🔔 {notification_text}")

        outlook_sentence = self._generate_outlook_sentence(symbol, market, prediction, opportunity)
        if outlook_sentence:
            lines.append(outlook_sentence)

        outro_template = content_config.get("outro") if isinstance(content_config.get("outro"), str) else ""
        if outro_template:
            lines.append(self._format_template(outro_template, context))

        glossary_cfg = content_config.get("glossary") if isinstance(content_config.get("glossary"), dict) else {}
        self._append_glossary_section(lines, glossary_cfg, context)

        if show_brokers:
            broker_quotes = self._get_broker_quotes(symbol, market)
            if broker_quotes:
                lines.append("🏦 Prix des courtiers :")
                for quote in broker_quotes:
                    lines.append(self._format_broker_quote(quote).strip())

        return "\n".join(line for line in lines if line is not None).strip()

    def generate_coin_notifications(
        self,
        markets: Dict[str, MarketData],
        predictions: Dict[str, Prediction],
        opportunities: Dict[str, OpportunityScore],
    ) -> List[str]:
        symbols: List[str]
        if self.config and self.config.crypto_symbols:
            symbols = [symbol for symbol in self.config.crypto_symbols if symbol in markets]
        else:
            symbols = sorted(set(markets.keys()) | set(predictions.keys()) | set(opportunities.keys()))

        notifications: List[str] = []
        for symbol in symbols:
            message = self.generate_coin_notification(
                symbol,
                markets.get(symbol),
                predictions.get(symbol),
                opportunities.get(symbol),
            )
            if message:
                notifications.append(message)
        return notifications

    def generate_glossary_notification(self) -> str:
        base_glossary = self._generate_glossary_section().strip()
        if not self.config:
            return base_glossary

        content_map = getattr(self.config, "notification_content_by_coin", {}) or {}
        if not isinstance(content_map, dict):
            return base_glossary

        symbols = self.config.crypto_symbols or sorted(content_map.keys())
        lines: List[str] = []
        entries_added = False

        for symbol in symbols:
            if symbol == "default":
                continue
            content_cfg = self._notification_content_config(symbol)
            glossary_cfg = content_cfg.get("glossary") if isinstance(content_cfg.get("glossary"), dict) else {}
            if not glossary_cfg.get("enabled", True):
                continue

            intro = glossary_cfg.get("intro") if isinstance(glossary_cfg.get("intro"), str) else ""
            entries = glossary_cfg.get("entries") if isinstance(glossary_cfg.get("entries"), list) else []
            cleaned_entries: List[Dict[str, str]] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                term = str(entry.get("term", "")).strip()
                definition = str(entry.get("definition", "")).strip()
                if term and definition:
                    cleaned_entries.append({"term": term, "definition": definition})

            if not intro and not cleaned_entries:
                continue

            context = {"symbol": symbol, "name": symbol}
            title_template = glossary_cfg.get("title") if isinstance(glossary_cfg.get("title"), str) else ""
            rendered_title = self._format_template(title_template, context) if title_template else f"{symbol} — notions clés"

            if not entries_added:
                lines.append("📘 Glossaire personnalisé par crypto")
            lines.append("")
            lines.append(rendered_title)
            if intro:
                lines.append(self._format_template(intro, context))
            for entry in cleaned_entries:
                lines.append(f"- {entry['term']} : {entry['definition']}")
            entries_added = True

        if entries_added:
            if base_glossary:
                lines.append("")
                lines.append(base_glossary)
            return "\n".join(line for line in lines if line is not None).strip()

        return base_glossary

    def _passes_notification_thresholds(
        self,
        symbol: str,
        market: MarketData,
        opportunity: Optional[OpportunityScore],
    ) -> bool:
        thresholds_map: Dict[str, Any] = {}
        if self.config and self.config.notification_thresholds:
            thresholds_map.update(self.config.notification_thresholds)

        coin_thresholds = self._coin_option(symbol, "notification_thresholds", None)
        symbol_key = symbol.upper()
        if isinstance(coin_thresholds, dict):
            thresholds_map[symbol_key] = {
                **thresholds_map.get(symbol_key, {}),
                **coin_thresholds,
            }

        if not thresholds_map:
            return True

        thresholds = thresholds_map.get(symbol_key)
        if thresholds is None:
            thresholds = thresholds_map.get("default")
        if not thresholds:
            return True

        score = opportunity.score if opportunity else None
        change_24h = market.current_price.change_24h if market.current_price else None

        min_score = thresholds.get("min_score")
        if min_score is not None and (score is None or score < min_score):
            return False

        max_score = thresholds.get("max_score")
        if max_score is not None and (score is not None and score > max_score):
            return False

        min_change = thresholds.get("min_change_pct")
        if min_change is not None and (change_24h is None or change_24h < min_change):
            return False

        max_change = thresholds.get("max_change_pct")
        if max_change is not None and (change_24h is not None and change_24h > max_change):
            return False

        return True

    def _get_broker_quotes(self, symbol: str, market: Optional[MarketData]) -> List[BrokerQuote]:
        if not market or not getattr(self, "broker_service", None):
            return []
        try:
            return self.broker_service.get_quotes(symbol, market)
        except Exception:
            return []

    @staticmethod
    def _format_broker_quote(quote: BrokerQuote) -> str:
        buy = f"{quote.buy_price:.2f}{quote.currency}"
        sell = f"{quote.sell_price:.2f}{quote.currency}"
        line = f"  • {quote.broker}: achat {buy}, vente {sell}"
        if quote.notes:
            line += f" — {quote.notes}"
        return line + "\n"

    def _generate_curves_text(
        self,
        market: Optional[MarketData],
        timeframes: Optional[List[int]] = None,
    ) -> Optional[str]:
        if not market:
            return None
        frames = self._normalize_timeframes_list(timeframes) if timeframes is not None else []
        if not frames:
            frames = [24, 168]
        parts: List[str] = []
        for hours in frames:
            label = f"{hours}h"
            if hours % 24 == 0:
                days = hours // 24
                if days == 7:
                    label = "7j"
                elif days >= 1:
                    label = f"{days}j"
            curve = self._build_curve_for_period(market, hours=hours, label=label)
            if curve:
                parts.append(curve)
        if not parts:
            return None
        return "\n".join(parts)

    def _build_curve_for_period(self, market: MarketData, hours: int, label: str) -> Optional[str]:
        prices = self._extract_prices_within_hours(market, hours)
        if len(prices) < 2:
            return None
        sparkline = self._make_ascii_sparkline(prices)
        start = prices[0]
        end = prices[-1]
        diff_pct = ((end - start) / start) * 100 if start else 0
        direction = "▲" if diff_pct > 0 else "▼" if diff_pct < 0 else "→"
        return f"{label} : {sparkline} ({direction} {diff_pct:+.2f}%)"

    def _extract_prices_within_hours(self, market: MarketData, hours: int) -> List[float]:
        if not market.price_history:
            return []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        filtered = [p.price_eur for p in market.price_history if p.price_eur is not None and p.timestamp >= cutoff]
        current_price = market.current_price.price_eur if market.current_price and market.current_price.price_eur is not None else None
        if current_price is not None:
            if not filtered:
                filtered = [current_price]
            elif abs(filtered[-1] - current_price) > 1e-6:
                filtered.append(current_price)
        return filtered

    @staticmethod
    def _make_ascii_sparkline(prices: List[float]) -> str:
        if not prices:
            return ""
        buckets = "._-~=^"
        min_price = min(prices)
        max_price = max(prices)
        if max_price - min_price == 0:
            return buckets[-1] * len(prices)
        # Downsample to at most 30 points for lisibility
        step = max(1, len(prices) // 30)
        sampled = prices[::step]
        result_chars = []
        for price in sampled:
            norm = (price - min_price) / (max_price - min_price)
            idx = int(norm * (len(buckets) - 1))
            result_chars.append(buckets[idx])
        return "".join(result_chars)

    def _generate_glossary_section(self) -> str:
        glossary_items = [
            (
                "Volatilité",
                "Mesure l'amplitude des variations récentes du prix. Plus elle est élevée, plus le marché bouge rapidement."
            ),
            (
                "Drawdown maximum",
                "Plus forte baisse observée depuis le dernier sommet. Cela renseigne sur la profondeur d'un repli récent."
            ),
            (
                "Force de tendance",
                "Score synthétique basé sur la tendance 24h/7j et plusieurs indicateurs (MACD, RSI). Au-dessus de 5, la dynamique est plutôt haussière."
            ),
            (
                "Profil de risque",
                "Combine volatilité, rendement récent et score d'opportunité pour estimer le risque global (🟢 faible, 🟡 modéré, 🔴 élevé)."
            ),
            (
                "RSI",
                "Relative Strength Index. Au-dessus de 70, un actif est jugé suracheté ; en dessous de 30, survendu."
            ),
            (
                "MA20",
                "Moyenne mobile sur 20 périodes. Elle lisse le prix pour visualiser la tendance de court terme."
            ),
            (
                "Support",
                "Zone de prix où la demande a récemment stoppé des baisses, ce qui peut servir de plancher potentiel."
            ),
            (
                "Résistance",
                "Zone de prix où l'offre a récemment limité les hausses, agissant comme plafond à court terme."
            ),
            (
                "Fear & Greed Index",
                "Indice de sentiment global (0 = peur extrême, 100 = euphorie). Les extrêmes signalent souvent des excès émotionnels."
            ),
        ]
        lines = ["", "ℹ️ GLOSSAIRE EXPRESS"]
        for term, description in glossary_items:
            lines.append(f"{term} : {description}")
        lines.append("")
        lines.append("🔔 Notification : conserve ce glossaire pour rappeler rapidement ce que signifient les indicateurs cités.")
        return "\n".join(lines) + "\n"
