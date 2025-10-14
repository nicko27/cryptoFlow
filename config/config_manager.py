"""
Configuration Manager - Gestion de la configuration
"""

import yaml
import os
from pathlib import Path
from typing import Optional, Dict, Any
from core.models import BotConfiguration


class ConfigManager:
    """Gestionnaire de configuration"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
    
    def config_exists(self) -> bool:
        """Vérifie si le fichier de configuration existe"""
        return self.config_path.exists()
    
    def load_config(self) -> BotConfiguration:
        """
        Charge la configuration depuis le fichier YAML
        
        Returns:
            BotConfiguration
        
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValueError: Si la configuration est invalide
        """
        if not self.config_exists():
            raise FileNotFoundError(f"Configuration non trouvée : {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._dict_to_config(data)
    
    def save_config(self, config: BotConfiguration):
        """
        Sauvegarde la configuration dans le fichier YAML
        
        Args:
            config: Configuration à sauvegarder
        """
        # Créer le répertoire si nécessaire
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Convertir en dict
        data = self._config_to_dict(config)
        
        # Sauvegarder
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BotConfiguration:
        """Convertit un dict en BotConfiguration"""
        
        return BotConfiguration(
            # Telegram
            telegram_bot_token=data.get("telegram", {}).get("bot_token", ""),
            telegram_chat_id=data.get("telegram", {}).get("chat_id", ""),
            
            # Cryptos
            crypto_symbols=data.get("crypto", {}).get("symbols", ["BTC"]),
            investment_amount=data.get("crypto", {}).get("investment_amount", 100.0),
            
            # Alertes
            enable_alerts=data.get("alerts", {}).get("enable", True),
            price_lookback_minutes=data.get("alerts", {}).get("lookback_minutes", 120),
            price_drop_threshold=data.get("alerts", {}).get("drop_threshold", 10.0),
            price_spike_threshold=data.get("alerts", {}).get("spike_threshold", 10.0),
            funding_negative_threshold=data.get("alerts", {}).get("funding_threshold", -0.03),
            oi_delta_threshold=data.get("alerts", {}).get("oi_delta", 3.0),
            fear_greed_max=data.get("alerts", {}).get("fear_greed_max", 30),
            
            # Niveaux de prix
            enable_price_levels=data.get("price_levels", {}).get("enable", True),
            price_levels=data.get("price_levels", {}).get("levels", {}),
            level_buffer_eur=data.get("price_levels", {}).get("buffer_eur", 2.0),
            level_cooldown_minutes=data.get("price_levels", {}).get("cooldown_minutes", 30),
            
            # Features
            enable_opportunity_score=data.get("features", {}).get("opportunity_score", True),
            opportunity_threshold=data.get("features", {}).get("opportunity_threshold", 7),
            enable_predictions=data.get("features", {}).get("predictions", True),
            enable_timeline=data.get("features", {}).get("timeline", True),
            enable_gain_loss_calc=data.get("features", {}).get("gain_loss_calc", True),
            enable_dca_suggestions=data.get("features", {}).get("dca_suggestions", True),
            use_simple_language=data.get("features", {}).get("simple_language", True),
            educational_mode=data.get("features", {}).get("educational_mode", True),
            
            # Timing
            check_interval_seconds=data.get("timing", {}).get("check_interval", 900),
            summary_hours=data.get("timing", {}).get("summary_hours", [9, 12, 18]),
            enable_quiet_hours=data.get("timing", {}).get("quiet_hours", {}).get("enable", False),
            quiet_start_hour=data.get("timing", {}).get("quiet_hours", {}).get("start", 23),
            quiet_end_hour=data.get("timing", {}).get("quiet_hours", {}).get("end", 7),
            quiet_allow_critical=data.get("timing", {}).get("quiet_hours", {}).get("allow_critical", True),
            
            # Display
            enable_graphs=data.get("display", {}).get("graphs", True),
            show_levels_on_graph=data.get("display", {}).get("show_levels", True),
            enable_startup_summary=data.get("display", {}).get("startup_summary", True),
            
            # Mode
            daemon_mode=data.get("mode", {}).get("daemon", False),
            gui_mode=data.get("mode", {}).get("gui", True),
            detail_level=data.get("mode", {}).get("detail_level", "normal"),
            
            # Logging
            log_file=data.get("logging", {}).get("file", "logs/crypto_bot.log"),
            log_level=data.get("logging", {}).get("level", "INFO"),
            
            # Database
            database_path=data.get("database", {}).get("path", "data/crypto_bot.db"),
            keep_history_days=data.get("database", {}).get("keep_days", 30)
        )
    
    def _config_to_dict(self, config: BotConfiguration) -> Dict[str, Any]:
        """Convertit BotConfiguration en dict pour YAML"""
        
        return {
            "telegram": {
                "bot_token": config.telegram_bot_token,
                "chat_id": config.telegram_chat_id
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
                "funding_threshold": config.funding_negative_threshold,
                "oi_delta": config.oi_delta_threshold,
                "fear_greed_max": config.fear_greed_max
            },
            
            "price_levels": {
                "enable": config.enable_price_levels,
                "levels": config.price_levels,
                "buffer_eur": config.level_buffer_eur,
                "cooldown_minutes": config.level_cooldown_minutes
            },
            
            "features": {
                "opportunity_score": config.enable_opportunity_score,
                "opportunity_threshold": config.opportunity_threshold,
                "predictions": config.enable_predictions,
                "timeline": config.enable_timeline,
                "gain_loss_calc": config.enable_gain_loss_calc,
                "dca_suggestions": config.enable_dca_suggestions,
                "simple_language": config.use_simple_language,
                "educational_mode": config.educational_mode
            },
            
            "timing": {
                "check_interval": config.check_interval_seconds,
                "summary_hours": config.summary_hours,
                "quiet_hours": {
                    "enable": config.enable_quiet_hours,
                    "start": config.quiet_start_hour,
                    "end": config.quiet_end_hour,
                    "allow_critical": config.quiet_allow_critical
                }
            },
            
            "display": {
                "graphs": config.enable_graphs,
                "show_levels": config.show_levels_on_graph,
                "startup_summary": config.enable_startup_summary
            },
            
            "mode": {
                "daemon": config.daemon_mode,
                "gui": config.gui_mode,
                "detail_level": config.detail_level
            },
            
            "logging": {
                "file": config.log_file,
                "level": config.log_level
            },
            
            "database": {
                "path": config.database_path,
                "keep_days": config.keep_history_days
            }
        }
    
    def create_default_config(self) -> BotConfiguration:
        """Crée une configuration par défaut"""
        return BotConfiguration()
    
    def validate_config(self, config: BotConfiguration) -> tuple[bool, list[str]]:
        """
        Valide une configuration
        
        Returns:
            (valid, errors) - tuple avec validation et liste d'erreurs
        """
        errors = []
        
        # Telegram
        if not config.telegram_bot_token:
            errors.append("Token Telegram manquant")
        
        if not config.telegram_chat_id:
            errors.append("Chat ID Telegram manquant")
        
        # Cryptos
        if not config.crypto_symbols:
            errors.append("Aucune crypto configurée")
        
        # Valeurs numériques
        if config.investment_amount <= 0:
            errors.append("Montant d'investissement invalide")
        
        if config.check_interval_seconds < 30:
            errors.append("Intervalle de vérification trop court (min 30s)")
        
        return (len(errors) == 0, errors)
