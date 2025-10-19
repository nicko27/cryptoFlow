"""
Script de migration de l'ancien système vers le nouveau
Convertit automatiquement les configurations existantes
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from core.models.notification_config import (
    GlobalNotificationSettings,
    CoinNotificationProfile,
    ScheduledNotificationConfig,
    PriceBlock, PredictionBlock, OpportunityBlock,
    ChartBlock, BrokersBlock, FearGreedBlock,
    GainLossBlock, InvestmentSuggestionBlock, GlossaryBlock
)


class NotificationConfigMigrator:
    """Migre l'ancienne configuration vers le nouveau système"""
    
    def __init__(self):
        self.warnings = []
        self.info = []
    
    def migrate_from_yaml(self, old_config_path: str) -> GlobalNotificationSettings:
        """
        Migre depuis l'ancien fichier config.yaml
        
        Args:
            old_config_path: Chemin vers l'ancien config.yaml
            
        Returns:
            GlobalNotificationSettings configuré
        """
        
        print("🔄 Début de la migration...")
        
        # Charger ancienne config
        with open(old_config_path, 'r', encoding='utf-8') as f:
            old_config = yaml.safe_load(f)
        
        # Créer nouvelle configuration
        settings = GlobalNotificationSettings()
        
        # Migrer paramètres globaux
        self._migrate_global_settings(old_config, settings)
        
        # Migrer cryptos
        self._migrate_crypto_settings(old_config, settings)
        
        print(f"✅ Migration terminée !")
        print(f"ℹ️  {len(self.info)} informations")
        print(f"⚠️  {len(self.warnings)} avertissements")
        
        return settings
    
    def _migrate_global_settings(self, old_config: Dict, settings: GlobalNotificationSettings):
        """Migre les paramètres globaux"""
        
        print("📋 Migration des paramètres globaux...")
        
        # Notifications
        notifications = old_config.get('notifications', {})
        
        settings.enabled = notifications.get('per_coin', True)
        self.info.append("Notifications activées par défaut")
        
        # Mode enfant
        features = old_config.get('features', {})
        settings.kid_friendly_mode = old_config.get('use_simple_language', True) or \
                                     old_config.get('educational_mode', True)
        
        if settings.kid_friendly_mode:
            self.info.append("Mode adapté enfants activé")
        
        # Horaires
        timing = old_config.get('timing', {})
        summary_hours = timing.get('summary_hours', [9, 12, 18])
        if isinstance(summary_hours, list):
            settings.default_scheduled_hours = summary_hours
            self.info.append(f"Horaires par défaut : {summary_hours}")
        
        # Heures silencieuses
        quiet = old_config.get('quiet_hours', {})
        if quiet.get('enable', False):
            settings.respect_quiet_hours = True
            settings.quiet_start = quiet.get('start', 23)
            settings.quiet_end = quiet.get('end', 7)
            self.info.append(f"Mode nuit : {settings.quiet_start}h-{settings.quiet_end}h")
    
    def _migrate_crypto_settings(self, old_config: Dict, settings: GlobalNotificationSettings):
        """Migre les paramètres par crypto"""
        
        print("💰 Migration des cryptos...")
        
        crypto_config = old_config.get('crypto', {})
        symbols = crypto_config.get('symbols', ['BTC'])
        
        coins_config = old_config.get('coins', {})
        
        for symbol in symbols:
            print(f"  📍 {symbol}...")
            
            # Créer profil
            profile = CoinNotificationProfile(
                symbol=symbol,
                enabled=True
            )
            
            # Configuration spécifique de la crypto
            coin_settings = coins_config.get(symbol, {})
            
            # Migrer les notifications programmées
            self._migrate_scheduled_notifications(
                symbol,
                coin_settings,
                old_config,
                profile
            )
            
            # Ajouter au settings
            settings.coin_profiles[symbol] = profile
            
            self.info.append(f"Crypto {symbol} migrée avec {len(profile.scheduled_notifications)} notification(s)")
    
    def _migrate_scheduled_notifications(
        self,
        symbol: str,
        coin_settings: Dict,
        old_config: Dict,
        profile: CoinNotificationProfile
    ):
        """Migre les notifications programmées d'une crypto"""
        
        # Récupérer horaires
        notification_hours = coin_settings.get('notification_hours')
        if notification_hours is None:
            # Utiliser horaires globaux
            timing = old_config.get('timing', {})
            notification_hours = timing.get('summary_hours', [9, 12, 18])
        
        if isinstance(notification_hours, str):
            notification_hours = [int(h.strip()) for h in notification_hours.split(',')]
        elif not isinstance(notification_hours, list):
            notification_hours = [9, 12, 18]
        
        # Créer une notification pour chaque horaire
        for hour in notification_hours:
            config = ScheduledNotificationConfig(
                name=f"Notification {hour}h",
                hours=[hour],
                enabled=True
            )
            
            # Migrer options de notification
            notification_options = coin_settings.get('notification_options', {})
            
            # Prix
            config.price_block.enabled = notification_options.get('show_price', True)
            config.price_block.show_variation_24h = notification_options.get('show_variation_24h', True)
            config.price_block.show_volume = notification_options.get('show_volume', True)
            
            # Graphiques
            config.chart_block.enabled = notification_options.get('show_curves', True)
            chart_timeframes = coin_settings.get('chart_timeframes')
            if chart_timeframes:
                config.chart_block.timeframes = chart_timeframes
            else:
                # Utiliser timeframes globaux
                notifications = old_config.get('notifications', {})
                global_timeframes = notifications.get('chart_timeframes', [24, 168])
                config.chart_block.timeframes = global_timeframes
            
            # Prédiction
            config.prediction_block.enabled = notification_options.get('show_prediction', True)
            
            # Opportunité
            config.opportunity_block.enabled = notification_options.get('show_opportunity', True)
            
            # Courtiers
            config.brokers_block.enabled = notification_options.get('show_brokers', True)
            
            # Fear & Greed
            config.fear_greed_block.enabled = notification_options.get('show_fear_greed', True)
            
            # Gain/Perte
            config.gain_loss_block.enabled = notification_options.get('show_gain', True)
            
            # 🆕 Suggestions (nouveau - activé par défaut avec params raisonnables)
            config.investment_suggestions_block.enabled = True
            config.investment_suggestions_block.max_suggestions = 3
            config.investment_suggestions_block.min_opportunity_score = 7
            config.investment_suggestions_block.prefer_trending = True
            config.investment_suggestions_block.prefer_undervalued = True
            
            # Glossaire
            config.glossary_block.enabled = old_config.get('notification_send_glossary', True)
            
            # Mode enfant
            config.kid_friendly_mode = old_config.get('use_simple_language', True)
            
            # Ajouter au profil
            profile.add_scheduled_notification(config)
    
    def save_to_yaml(self, settings: GlobalNotificationSettings, output_path: str):
        """
        Sauvegarde la nouvelle configuration en YAML
        
        Args:
            settings: Configuration à sauvegarder
            output_path: Chemin du fichier de sortie
        """
        
        print(f"💾 Sauvegarde dans {output_path}...")
        
        config_dict = {
            'notifications': {
                'enabled': settings.enabled,
                'kid_friendly_mode': settings.kid_friendly_mode,
                'max_message_length': settings.max_message_length,
                'default_scheduled_hours': settings.default_scheduled_hours,
                'quiet_hours': {
                    'enabled': settings.respect_quiet_hours,
                    'start': settings.quiet_start,
                    'end': settings.quiet_end,
                },
                'global_header_template': settings.global_header_template,
                'global_footer_template': settings.global_footer_template,
            },
            'coins': {}
        }
        
        # Sauvegarder chaque crypto
        for symbol, profile in settings.coin_profiles.items():
            coin_config = {
                'enabled': profile.enabled,
                'nickname': profile.nickname,
                'custom_emoji': profile.custom_emoji,
                'intro_message': profile.intro_message,
                'outro_message': profile.outro_message,
                'detail_level': profile.detail_level,
                'scheduled_notifications': []
            }
            
            # Sauvegarder notifications programmées
            for notif in profile.scheduled_notifications:
                notif_config = self._notification_to_dict(notif)
                coin_config['scheduled_notifications'].append(notif_config)
            
            config_dict['coins'][symbol] = coin_config
        
        # Écrire fichier
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print("✅ Sauvegarde terminée !")
    
    def _notification_to_dict(self, notif: ScheduledNotificationConfig) -> Dict[str, Any]:
        """Convertit une ScheduledNotificationConfig en dictionnaire"""
        
        return {
            'name': notif.name,
            'description': notif.description,
            'enabled': notif.enabled,
            'hours': notif.hours,
            'days_of_week': notif.days_of_week,
            'blocks_order': notif.blocks_order,
            'header_message': notif.header_message,
            'footer_message': notif.footer_message,
            'kid_friendly_mode': notif.kid_friendly_mode,
            'use_emojis_everywhere': notif.use_emojis_everywhere,
            'explain_everything': notif.explain_everything,
            'avoid_technical_terms': notif.avoid_technical_terms,
            'send_only_if_change_above': notif.send_only_if_change_above,
            'send_only_if_opportunity_above': notif.send_only_if_opportunity_above,
            'price_block': self._block_to_dict(notif.price_block, 'price'),
            'chart_block': self._block_to_dict(notif.chart_block, 'chart'),
            'prediction_block': self._block_to_dict(notif.prediction_block, 'prediction'),
            'opportunity_block': self._block_to_dict(notif.opportunity_block, 'opportunity'),
            'brokers_block': self._block_to_dict(notif.brokers_block, 'brokers'),
            'fear_greed_block': self._block_to_dict(notif.fear_greed_block, 'fear_greed'),
            'gain_loss_block': self._block_to_dict(notif.gain_loss_block, 'gain_loss'),
            'investment_suggestions_block': self._block_to_dict(notif.investment_suggestions_block, 'suggestions'),
            'glossary_block': self._block_to_dict(notif.glossary_block, 'glossary'),
        }
    
    def _block_to_dict(self, block: Any, block_type: str) -> Dict[str, Any]:
        """Convertit un bloc en dictionnaire"""
        
        result = {
            'enabled': block.enabled,
            'title': block.title,
            'show_emoji': block.show_emoji,
        }
        
        # Ajouter champs spécifiques selon type
        if block_type == 'price':
            result.update({
                'show_price_eur': block.show_price_eur,
                'show_variation_24h': block.show_variation_24h,
                'show_variation_7d': block.show_variation_7d,
                'show_volume': block.show_volume,
                'add_price_comment': block.add_price_comment,
            })
        
        elif block_type == 'chart':
            result.update({
                'show_sparklines': block.show_sparklines,
                'send_full_chart': block.send_full_chart,
                'timeframes': block.timeframes,
            })
        
        elif block_type == 'prediction':
            result.update({
                'show_prediction_type': block.show_prediction_type,
                'show_confidence': block.show_confidence,
                'min_confidence_to_show': block.min_confidence_to_show,
            })
        
        elif block_type == 'opportunity':
            result.update({
                'show_score': block.show_score,
                'show_recommendation': block.show_recommendation,
                'min_score_to_show': block.min_score_to_show,
            })
        
        elif block_type == 'suggestions':
            result.update({
                'max_suggestions': block.max_suggestions,
                'min_opportunity_score': block.min_opportunity_score,
                'exclude_current': block.exclude_current,
                'prefer_low_volatility': block.prefer_low_volatility,
                'prefer_trending': block.prefer_trending,
                'prefer_undervalued': block.prefer_undervalued,
            })
        
        elif block_type == 'glossary':
            result.update({
                'auto_detect_terms': block.auto_detect_terms,
                'custom_terms': block.custom_terms,
            })
        
        return result
    
    def print_report(self):
        """Affiche le rapport de migration"""
        
        print("\n" + "="*60)
        print("📊 RAPPORT DE MIGRATION")
        print("="*60)
        
        if self.info:
            print("\nℹ️  INFORMATIONS:")
            for msg in self.info:
                print(f"  • {msg}")
        
        if self.warnings:
            print("\n⚠️  AVERTISSEMENTS:")
            for msg in self.warnings:
                print(f"  • {msg}")
        
        print("\n" + "="*60)


def main():
    """Point d'entrée du script de migration"""
    
    print("="*60)
    print("🔄 MIGRATION CONFIGURATION NOTIFICATIONS")
    print("="*60)
    print()
    
    # Chemins
    old_config_path = "config/config.yaml"
    new_config_path = "config/notifications.yaml"
    backup_path = "config/config.yaml.backup"
    
    # Vérifier existence ancien fichier
    if not Path(old_config_path).exists():
        print(f"❌ Fichier {old_config_path} introuvable")
        return
    
    # Créer backup
    print(f"💾 Création backup : {backup_path}")
    import shutil
    shutil.copy2(old_config_path, backup_path)
    print("✅ Backup créé")
    print()
    
    # Migration
    migrator = NotificationConfigMigrator()
    
    try:
        settings = migrator.migrate_from_yaml(old_config_path)
        print()
        migrator.save_to_yaml(settings, new_config_path)
        print()
        migrator.print_report()
        
        print()
        print("✅ Migration réussie !")
        print()
        print(f"📄 Nouvelle configuration : {new_config_path}")
        print(f"💾 Backup ancienne config : {backup_path}")
        print()
        print("🎯 Prochaines étapes :")
        print("  1. Vérifie le fichier de configuration généré")
        print("  2. Ajuste si nécessaire")
        print("  3. Lance l'application pour tester")
        print("  4. Utilise l'interface graphique pour peaufiner")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration : {e}")
        import traceback
        traceback.print_exc()
        print(f"\n💾 Ton ancienne config est sauvegardée dans {backup_path}")


if __name__ == "__main__":
    main()
