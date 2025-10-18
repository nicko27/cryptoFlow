"""Configuration Manager - Gestion de la configuration"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.models import BotConfiguration

class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
    
    def config_exists(self) -> bool:
        return self.config_path.exists()
    
    def load_config(self) -> BotConfiguration:
        if not self.config_exists():
            raise FileNotFoundError(f"Configuration non trouvée : {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return self._dict_to_config(data)
    
    def save_config(self, config: BotConfiguration):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._config_to_dict(config)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BotConfiguration:
        telegram_cfg = data.get("telegram", {}) or {}
        display_cfg = telegram_cfg.get("display", {}) or {}
        thresholds_cfg = telegram_cfg.get("thresholds", {}) or {}
        crypto_cfg = data.get("crypto", {}) or {}
        alerts_cfg = data.get("alerts", {}) or {}
        price_levels_cfg = data.get("price_levels", {}) or {}
        timing_cfg = data.get("timing", {}) or {}
        summaries_cfg = data.get("summaries", {}) or {}
        quiet_cfg = data.get("quiet_hours", {}) or {}
        features_cfg = data.get("features", {}) or {}
        report_cfg = data.get("report", {}) or {}
        report_sections_cfg = report_cfg.get("sections", {}) or {}
        report_metrics_cfg = report_cfg.get("metrics", {}) or {}
        modes_cfg = data.get("modes", {}) or {}
        database_cfg = data.get("database", {}) or {}
        logging_cfg = data.get("logging", {}) or {}
        coins_cfg = data.get("coins", {}) or {}
        brokers_cfg = data.get("brokers", {}) or {}
        notifications_cfg = data.get("notifications", {}) or {}

        summary_hours_value = summaries_cfg.get(
            "hours",
            timing_cfg.get("summary_hours", [9, 12, 18])
        )

        summary_hours: List[int] = []
        if isinstance(summary_hours_value, (int, float)):
            summary_hours = [int(summary_hours_value)]
        elif isinstance(summary_hours_value, str):
            parts = [p.strip() for p in summary_hours_value.split(",")]
            summary_hours = [int(p) for p in parts if p.isdigit()]
        elif isinstance(summary_hours_value, list):
            for hour in summary_hours_value:
                if isinstance(hour, (int, float)):
                    summary_hours.append(int(hour))
                elif isinstance(hour, str) and hour.isdigit():
                    summary_hours.append(int(hour))
        summary_hours = summary_hours or [9, 12, 18]

        symbols_value = crypto_cfg.get("symbols", ["BTC"])
        if isinstance(symbols_value, str):
            symbols = [s.strip() for s in symbols_value.split(",") if s.strip()]
        elif isinstance(symbols_value, list):
            symbols = [str(s).strip().upper() for s in symbols_value if str(s).strip()]
        else:
            symbols = ["BTC"]

        def _normalize_hours_list(value) -> List[int]:
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
            return result

        def _normalize_timeframes_list(value) -> List[int]:
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
            return result

        def _normalize_notification_content(value) -> Dict[str, Any]:
            if not isinstance(value, dict):
                return {}

            normalized: Dict[str, Any] = {}
            title = value.get("title")
            if isinstance(title, str) and title.strip():
                normalized["title"] = title.strip()

            intro = value.get("intro")
            if isinstance(intro, str) and intro.strip():
                normalized["intro"] = intro.strip()

            outro = value.get("outro")
            if isinstance(outro, str) and outro.strip():
                normalized["outro"] = outro.strip()

            custom_lines_value = value.get("custom_lines", [])
            custom_lines: List[str] = []
            if isinstance(custom_lines_value, str):
                custom_lines = [
                    line.strip()
                    for line in custom_lines_value.splitlines()
                    if line.strip()
                ]
            elif isinstance(custom_lines_value, list):
                for line in custom_lines_value:
                    if isinstance(line, str) and line.strip():
                        custom_lines.append(line.strip())
            if custom_lines:
                normalized["custom_lines"] = custom_lines

            glossary_cfg = value.get("glossary", {})
            if isinstance(glossary_cfg, dict):
                glossary_normalized: Dict[str, Any] = {
                    "enabled": bool(glossary_cfg.get("enabled", True))
                }
                glossary_title = glossary_cfg.get("title")
                if isinstance(glossary_title, str) and glossary_title.strip():
                    glossary_normalized["title"] = glossary_title.strip()
                glossary_intro = glossary_cfg.get("intro")
                if isinstance(glossary_intro, str) and glossary_intro.strip():
                    glossary_normalized["intro"] = glossary_intro.strip()

                entries_cfg = glossary_cfg.get("entries", [])
                entries: List[Dict[str, str]] = []
                if isinstance(entries_cfg, list):
                    for entry in entries_cfg:
                        term = ""
                        definition = ""
                        if isinstance(entry, dict):
                            term = str(entry.get("term", "")).strip()
                            definition = str(entry.get("definition", "")).strip()
                        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                            term = str(entry[0]).strip()
                            definition = str(entry[1]).strip()
                        if term and definition:
                            entries.append({"term": term, "definition": definition})
                if entries:
                    glossary_normalized["entries"] = entries

                normalized["glossary"] = glossary_normalized

            return normalized

        normalized_coin_settings: Dict[str, Dict[str, Any]] = {}
        for raw_symbol, settings in coins_cfg.items():
            symbol_key = str(raw_symbol).upper()
            if not isinstance(settings, dict):
                normalized_coin_settings[symbol_key] = {}
                continue
            normalized = dict(settings)
            normalized["report_hours"] = _normalize_hours_list(settings.get("report_hours"))
            normalized["notification_hours"] = _normalize_hours_list(settings.get("notification_hours"))
            for opt_key in ("report_options", "notification_options"):
                opt_value = settings.get(opt_key)
                if isinstance(opt_value, dict):
                    opt_copy = dict(opt_value)
                    if "chart_timeframes" in opt_copy:
                        opt_copy["chart_timeframes"] = _normalize_timeframes_list(opt_copy.get("chart_timeframes"))
                    normalized[opt_key] = opt_copy
            normalized_coin_settings[symbol_key] = normalized

        content_cfg = notifications_cfg.get("content", {}) or {}
        normalized_notification_content: Dict[str, Dict[str, Any]] = {}
        if isinstance(content_cfg, dict):
            for raw_symbol, content in content_cfg.items():
                key = str(raw_symbol)
                if key.upper() != "DEFAULT":
                    key = key.upper()
                else:
                    key = "default"
                normalized_notification_content[key] = _normalize_notification_content(content)

        chart_timeframes_value = notifications_cfg.get("chart_timeframes", [24, 168])
        chart_timeframes: List[int] = []
        if isinstance(chart_timeframes_value, (int, float)):
            chart_timeframes = [int(chart_timeframes_value)]
        elif isinstance(chart_timeframes_value, str):
            parts = [p.strip() for p in chart_timeframes_value.split(",")]
            for part in parts:
                if part.isdigit():
                    chart_timeframes.append(int(part))
        elif isinstance(chart_timeframes_value, list):
            for item in chart_timeframes_value:
                if isinstance(item, (int, float)):
                    chart_timeframes.append(int(item))
                elif isinstance(item, str) and item.strip().isdigit():
                    chart_timeframes.append(int(item.strip()))
        chart_timeframes = chart_timeframes or [24, 168]

        enabled_brokers_value = brokers_cfg.get("enabled", ["binance", "revolut"])
        if isinstance(enabled_brokers_value, str):
            enabled_brokers = [s.strip() for s in enabled_brokers_value.split(",") if s.strip()]
        elif isinstance(enabled_brokers_value, list):
            enabled_brokers = [str(s).strip().lower() for s in enabled_brokers_value if str(s).strip()]
        else:
            enabled_brokers = ["binance", "revolut"]

        return BotConfiguration(
            telegram_bot_token=telegram_cfg.get("bot_token", ""),
            telegram_chat_id=telegram_cfg.get("chat_id", ""),
            telegram_message_delay=telegram_cfg.get("message_delay", 0.5),
            telegram_show_prices=display_cfg.get("show_prices", True),
            telegram_show_trend_24h=display_cfg.get("show_trend_24h", True),
            telegram_show_trend_7d=display_cfg.get("show_trend_7d", True),
            telegram_show_recommendations=display_cfg.get("show_recommendations", True),
            trend_buy_threshold_24h=thresholds_cfg.get("buy_24h", 2.0),
            trend_sell_threshold_24h=thresholds_cfg.get("sell_24h", -2.0),
            trend_buy_threshold_7d=thresholds_cfg.get("buy_7d", 5.0),
            trend_sell_threshold_7d=thresholds_cfg.get("sell_7d", -5.0),
            crypto_symbols=symbols,
            investment_amount=crypto_cfg.get("investment_amount", 100.0),
            enable_alerts=alerts_cfg.get("enable", True),
            price_lookback_minutes=alerts_cfg.get("lookback_minutes", 120),
            price_drop_threshold=alerts_cfg.get("drop_threshold", 10.0),
            price_spike_threshold=alerts_cfg.get("spike_threshold", 10.0),
            funding_negative_threshold=alerts_cfg.get("funding_negative_threshold", -0.03),
            oi_delta_threshold=alerts_cfg.get("oi_delta_threshold", 3.0),
            fear_greed_max=alerts_cfg.get("fear_greed_max", 30),
            enable_price_levels=price_levels_cfg.get("enable", True),
            price_levels=price_levels_cfg.get("levels") or {},
            level_buffer_eur=price_levels_cfg.get("buffer_eur", 2.0),
            level_cooldown_minutes=price_levels_cfg.get("cooldown_minutes", 30),
            check_interval_seconds=timing_cfg.get("check_interval", 900),
            summary_hours=summary_hours,
            enable_quiet_hours=quiet_cfg.get("enable", False),
            quiet_start_hour=quiet_cfg.get("start_hour", 23),
            quiet_end_hour=quiet_cfg.get("end_hour", 7),
            quiet_allow_critical=quiet_cfg.get("allow_critical", True),
            enable_graphs=features_cfg.get("graphs", True),
            show_levels_on_graph=features_cfg.get("show_levels_on_graph", True),
            enable_startup_summary=features_cfg.get("startup_summary", True),
            send_summary_chart=features_cfg.get("send_summary_chart", False),
            send_summary_dca=features_cfg.get("send_summary_dca", False),
            report_enabled_sections={
                "executive_summary": bool(report_sections_cfg.get("executive_summary", True)),
                "per_crypto": bool(report_sections_cfg.get("per_crypto", True)),
                "comparison": bool(report_sections_cfg.get("comparison", True)),
                "recommendations": bool(report_sections_cfg.get("recommendations", True)),
                "advanced_analysis": bool(report_sections_cfg.get("advanced_analysis", True)),
                "statistics": bool(report_sections_cfg.get("statistics", True)),
            },
            report_advanced_metrics={
                "volatility": bool(report_metrics_cfg.get("volatility", True)),
                "drawdown": bool(report_metrics_cfg.get("drawdown", True)),
                "trend_strength": bool(report_metrics_cfg.get("trend_strength", True)),
                "risk_score": bool(report_metrics_cfg.get("risk_score", True)),
                "dca_projection": bool(report_metrics_cfg.get("dca_projection", False)),
                "correlation": bool(report_metrics_cfg.get("correlation", False)),
            },
            report_detail_level=str(report_cfg.get("detail_level", "detailed")).lower(),
            report_include_summary=report_cfg.get("include_summary", False),
            report_include_telegram_report=report_cfg.get("include_telegram_report", False),
            report_include_chart=report_cfg.get("include_chart", False),
            report_include_dca=report_cfg.get("include_dca", False),
            coin_settings=normalized_coin_settings,
            enabled_brokers=enabled_brokers,
            broker_settings=brokers_cfg.get("overrides", {}) or {},
            report_include_broker_prices=report_cfg.get("include_broker_prices", True),
            notification_per_coin=notifications_cfg.get("per_coin", True),
            notification_include_chart=notifications_cfg.get("include_chart", True),
            notification_chart_timeframes=chart_timeframes,
            notification_include_brokers=notifications_cfg.get("include_brokers", True),
            notification_send_glossary=notifications_cfg.get("send_glossary", True),
            notification_thresholds=notifications_cfg.get("thresholds", {}) or {},
            notification_content_by_coin=normalized_notification_content,
            enable_opportunity_score=features_cfg.get("opportunity_score", True),
            opportunity_threshold=features_cfg.get("opportunity_threshold", 7),
            enable_predictions=features_cfg.get("predictions", True),
            enable_timeline=features_cfg.get("timeline", True),
            enable_gain_loss_calc=features_cfg.get("gain_loss_calc", True),
            enable_dca_suggestions=features_cfg.get("dca_suggestions", True),
            use_simple_language=features_cfg.get("simple_language", True),
            educational_mode=features_cfg.get("educational_mode", True),
            detail_level=features_cfg.get("detail_level", "normal"),
            daemon_mode=modes_cfg.get("daemon", False),
            gui_mode=modes_cfg.get("gui", True),
            log_file=logging_cfg.get("file", "logs/crypto_bot.log"),
            log_level=logging_cfg.get("level", "INFO"),
            database_path=database_cfg.get("path", "data/crypto_bot.db"),
            keep_history_days=database_cfg.get("keep_history_days", 30),
        )

    def _config_to_dict(self, config: BotConfiguration) -> Dict[str, Any]:
        def _serialize_notification_content(content_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for key, content in content_map.items():
                if not isinstance(content, dict):
                    continue
                serialized: Dict[str, Any] = {}
                for field_name in ("title", "intro", "outro"):
                    value = content.get(field_name)
                    if isinstance(value, str) and value.strip():
                        serialized[field_name] = value
                lines = content.get("custom_lines")
                if isinstance(lines, list):
                    serialized["custom_lines"] = [
                        str(line)
                        for line in lines
                        if isinstance(line, str) and line.strip()
                    ]
                glossary = content.get("glossary")
                if isinstance(glossary, dict):
                    glossary_serialized: Dict[str, Any] = {
                        "enabled": bool(glossary.get("enabled", True))
                    }
                    glossary_title = glossary.get("title")
                    if isinstance(glossary_title, str) and glossary_title.strip():
                        glossary_serialized["title"] = glossary_title
                    glossary_intro = glossary.get("intro")
                    if isinstance(glossary_intro, str) and glossary_intro.strip():
                        glossary_serialized["intro"] = glossary_intro
                    entries = glossary.get("entries")
                    if isinstance(entries, list):
                        serialized_entries: List[Dict[str, str]] = []
                        for entry in entries:
                            if not isinstance(entry, dict):
                                continue
                            term = str(entry.get("term", "")).strip()
                            definition = str(entry.get("definition", "")).strip()
                            if term and definition:
                                serialized_entries.append({"term": term, "definition": definition})
                        if serialized_entries:
                            glossary_serialized["entries"] = serialized_entries
                    serialized["glossary"] = glossary_serialized
                key_name = key if key == "default" else key.upper()
                result[key_name] = serialized
            return result

        return {
            "telegram": {
                "bot_token": config.telegram_bot_token,
                "chat_id": config.telegram_chat_id,
                "message_delay": config.telegram_message_delay,
                "display": {
                    "show_prices": config.telegram_show_prices,
                    "show_trend_24h": config.telegram_show_trend_24h,
                    "show_trend_7d": config.telegram_show_trend_7d,
                    "show_recommendations": config.telegram_show_recommendations,
                },
                "thresholds": {
                    "buy_24h": config.trend_buy_threshold_24h,
                    "sell_24h": config.trend_sell_threshold_24h,
                    "buy_7d": config.trend_buy_threshold_7d,
                    "sell_7d": config.trend_sell_threshold_7d,
                },
            },
            "crypto": {
                "symbols": config.crypto_symbols,
                "investment_amount": config.investment_amount
            },
            "alerts": {
                "enable": config.enable_alerts,
                "lookback_minutes": config.price_lookback_minutes,
                "drop_threshold": config.price_drop_threshold,
                "spike_threshold": config.price_spike_threshold,
                "funding_negative_threshold": config.funding_negative_threshold,
                "oi_delta_threshold": config.oi_delta_threshold,
                "fear_greed_max": config.fear_greed_max,
            },
            "price_levels": {
                "enable": config.enable_price_levels,
                "levels": config.price_levels,
                "buffer_eur": config.level_buffer_eur,
                "cooldown_minutes": config.level_cooldown_minutes,
            },
            "timing": {
                "check_interval": config.check_interval_seconds,
            },
            "summaries": {
                "hours": sorted({int(h) for h in config.summary_hours}),
            },
            "quiet_hours": {
                "enable": config.enable_quiet_hours,
                "start_hour": config.quiet_start_hour,
                "end_hour": config.quiet_end_hour,
                "allow_critical": config.quiet_allow_critical,
            },
            "features": {
                "graphs": config.enable_graphs,
                "show_levels_on_graph": config.show_levels_on_graph,
                "startup_summary": config.enable_startup_summary,
                "send_summary_chart": config.send_summary_chart,
                "send_summary_dca": config.send_summary_dca,
                "opportunity_score": config.enable_opportunity_score,
                "opportunity_threshold": config.opportunity_threshold,
                "predictions": config.enable_predictions,
                "timeline": config.enable_timeline,
                "gain_loss_calc": config.enable_gain_loss_calc,
                "dca_suggestions": config.enable_dca_suggestions,
                "simple_language": config.use_simple_language,
                "educational_mode": config.educational_mode,
                "detail_level": config.detail_level,
            },
            "report": {
                "detail_level": config.report_detail_level,
                "sections": dict(config.report_enabled_sections),
                "metrics": dict(config.report_advanced_metrics),
                "include_summary": config.report_include_summary,
                "include_telegram_report": config.report_include_telegram_report,
                "include_chart": config.report_include_chart,
                "include_dca": config.report_include_dca,
                "include_broker_prices": config.report_include_broker_prices,
            },
            "brokers": {
                "enabled": config.enabled_brokers,
                "overrides": config.broker_settings,
            },
            "notifications": {
                "per_coin": config.notification_per_coin,
                "include_chart": config.notification_include_chart,
                "chart_timeframes": config.notification_chart_timeframes,
                "include_brokers": config.notification_include_brokers,
                "send_glossary": config.notification_send_glossary,
                "thresholds": config.notification_thresholds,
                "content": _serialize_notification_content(config.notification_content_by_coin),
            },
            "coins": config.coin_settings,
            "modes": {
                "daemon": config.daemon_mode,
                "gui": config.gui_mode,
            },
            "database": {
                "path": config.database_path,
                "keep_history_days": config.keep_history_days,
            },
            "logging": {
                "file": config.log_file,
                "level": config.log_level
            }
        }
