#!/usr/bin/env python3
"""
FIX ULTIME - Après analyse approfondie
Problèmes identifiés :
1. Le bouton résumé doit utiliser SummaryService, pas NotificationGenerator
2. NotificationGenerator ne génère que pour les heures programmées
3. Bouton crypto manager manquant
4. Sauvegarde notifications ne fonctionne pas
"""

import shutil
from pathlib import Path
from datetime import datetime


def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_ultime_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files = [
        "ui/main_window.py",
        "ui/settings_window.py",
        "core/services/advanced_notification_config_window.py"
    ]
    
    for file in files:
        src = Path(file)
        if src.exists():
            dst = backup_dir / file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    print(f"✅ Sauvegarde: {backup_dir}")


def fix_send_summary():
    """Corrige _send_summary pour utiliser SummaryService"""
    
    file = Path("ui/main_window.py")
    content = file.read_text(encoding='utf-8')
    
    # Trouver et remplacer la méthode complète
    old_start = '    def _send_summary(self):'
    
    # Nouvelle implémentation utilisant SummaryService
    new_method = '''    def _send_summary(self):
        """Envoie un résumé complet sur Telegram via SummaryService"""
        try:
            # Importer SummaryService
            from core.services.summary_service import SummaryService
            from api.enhanced_telegram_api import EnhancedTelegramAPI
            
            # Créer le service de résumé
            summary_service = SummaryService(self.config)
            
            # Collecter les données pour toutes les cryptos
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            self.logger.info("Collecte des données de marché...")
            
            for symbol in self.config.crypto_symbols:
                try:
                    # Utiliser le cache ou récupérer les données
                    if symbol in self.market_data_cache:
                        market = self.market_data_cache[symbol]
                    else:
                        market = self.market_service.get_market_data(symbol)
                        self.market_data_cache[symbol] = market
                    
                    if market:
                        markets_data[symbol] = market
                        
                        # Prédictions
                        if symbol in self.predictions_cache:
                            pred = self.predictions_cache[symbol]
                        else:
                            pred = self.market_service.predict_price_movement(market)
                            if pred:
                                self.predictions_cache[symbol] = pred
                        
                        if pred:
                            predictions[symbol] = pred
                        
                        # Opportunités
                        if symbol in self.opportunities_cache:
                            opp = self.opportunities_cache[symbol]
                        else:
                            opp = self.market_service.calculate_opportunity_score(market, pred)
                            if opp:
                                self.opportunities_cache[symbol] = opp
                        
                        if opp:
                            opportunities[symbol] = opp
                        
                        self.logger.info(f"  ✓ {symbol}: {market.current_price.price_eur:.2f}€")
                
                except Exception as e:
                    self.logger.error(f"Erreur récupération {symbol}: {e}")
            
            if not markets_data:
                QMessageBox.warning(
                    self,
                    "Aucune donnée",
                    "Aucune donnée de marché disponible. Rafraîchis d'abord les données."
                )
                return
            
            # Générer le résumé via SummaryService
            self.logger.info("Génération du résumé...")
            summary = summary_service.generate_summary(
                markets_data,
                predictions,
                opportunities,
                simple=self.config.use_simple_language
            )
            
            if not summary:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Impossible de générer le résumé"
                )
                return
            
            # Envoyer le résumé sur Telegram
            self.logger.info("Envoi du résumé sur Telegram...")
            telegram = EnhancedTelegramAPI(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            )
            
            success = telegram.send_message(summary, parse_mode="HTML")
            
            if success:
                self.logger.info("✓ Résumé envoyé avec succès")
                QMessageBox.information(
                    self,
                    "Résumé envoyé",
                    "✅ Résumé envoyé sur Telegram avec succès !"
                )
            else:
                self.logger.error("✗ Échec envoi résumé")
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Échec de l'envoi du résumé sur Telegram"
                )
        
        except Exception as e:
            self.logger.error(f"Erreur envoi résumé: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'envoi du résumé :\\n{e}"
            )'''
    
    # Trouver la position de la méthode
    start_pos = content.find(old_start)
    
    if start_pos == -1:
        print("⚠️ Méthode _send_summary non trouvée")
        return
    
    # Trouver la fin de la méthode (prochaine méthode)
    end_marker = "\n    def _generate_report(self):"
    end_pos = content.find(end_marker, start_pos)
    
    if end_pos == -1:
        print("⚠️ Fin de méthode non trouvée")
        return
    
    # Remplacer
    content = content[:start_pos] + new_method + "\n" + content[end_pos:]
    
    file.write_text(content, encoding='utf-8')
    print("✅ _send_summary corrigé (utilise maintenant SummaryService)")


def create_crypto_manager():
    """Crée le gestionnaire de cryptos"""
    
    code = '''"""Gestionnaire de cryptomonnaies"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QFont
from core.models import BotConfiguration


class CryptoManagerWindow(QDialog):
    def __init__(self, config: BotConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("💰 Gestion des Cryptomonnaies")
        self.resize(800, 600)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("💰 Gère tes cryptomonnaies")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)
        
        list_group = QGroupBox("📋 Mes cryptos")
        list_layout = QVBoxLayout()
        
        self.crypto_list = QListWidget()
        self._refresh_list()
        list_layout.addWidget(self.crypto_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Ajouter")
        add_btn.clicked.connect(self._add)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ Configurer")
        edit_btn.clicked.connect(self._edit)
        btn_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("🗑️ Supprimer")
        remove_btn.clicked.connect(self._remove)
        btn_layout.addWidget(remove_btn)
        
        list_layout.addLayout(btn_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        global_group = QGroupBox("⚙️ Configuration globale")
        global_layout = QFormLayout()
        
        self.global_investment = QDoubleSpinBox()
        self.global_investment.setRange(0, 1000000)
        self.global_investment.setValue(self.config.investment_amount)
        self.global_investment.setSuffix(" €")
        global_layout.addRow("Montant par défaut:", self.global_investment)
        
        apply_btn = QPushButton("📢 Appliquer à toutes")
        apply_btn.clicked.connect(self._apply_global)
        global_layout.addRow("", apply_btn)
        
        global_group.setLayout(global_layout)
        layout.addWidget(global_group)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_list(self):
        self.crypto_list.clear()
        for symbol in self.config.crypto_symbols:
            investment = self.config.coin_settings.get(symbol, {}).get(
                'investment_amount', self.config.investment_amount
            )
            include = self.config.coin_settings.get(symbol, {}).get('include_summary', True)
            status = "✅" if include else "⏸️"
            self.crypto_list.addItem(f"{status} {symbol} - {investment:.0f}€")
    
    def _add(self):
        symbol, ok = QInputDialog.getText(self, "Ajouter", "Symbole (ex: BTC):")
        if ok and symbol:
            symbol = symbol.upper().strip()
            if symbol in self.config.crypto_symbols:
                QMessageBox.warning(self, "Erreur", f"{symbol} déjà présent")
                return
            
            self.config.crypto_symbols.append(symbol)
            if symbol not in self.config.coin_settings:
                self.config.coin_settings[symbol] = {}
            self.config.coin_settings[symbol]['investment_amount'] = self.config.investment_amount
            self.config.coin_settings[symbol]['include_summary'] = True
            self._refresh_list()
            QMessageBox.information(self, "Succès", f"✅ {symbol} ajouté")
    
    def _edit(self):
        item = self.crypto_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Sélection", "Sélectionne une crypto")
            return
        symbol = item.text().split(" ")[1]
        dialog = CryptoConfigDialog(symbol, self.config, self)
        if dialog.exec():
            self._refresh_list()
    
    def _remove(self):
        item = self.crypto_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Sélection", "Sélectionne une crypto")
            return
        symbol = item.text().split(" ")[1]
        reply = QMessageBox.question(
            self, "Confirmation", f"Supprimer {symbol} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.crypto_symbols.remove(symbol)
            if symbol in self.config.coin_settings:
                del self.config.coin_settings[symbol]
            self._refresh_list()
            QMessageBox.information(self, "Succès", f"✅ {symbol} supprimé")
    
    def _apply_global(self):
        investment = self.global_investment.value()
        reply = QMessageBox.question(
            self, "Confirmation",
            f"Appliquer {investment:.0f}€ à toutes les cryptos ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for symbol in self.config.crypto_symbols:
                if symbol not in self.config.coin_settings:
                    self.config.coin_settings[symbol] = {}
                self.config.coin_settings[symbol]['investment_amount'] = investment
            self.config.investment_amount = investment
            self._refresh_list()
            QMessageBox.information(self, "Succès", "✅ Appliqué à toutes")


class CryptoConfigDialog(QDialog):
    def __init__(self, symbol: str, config: BotConfiguration, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.config = config
        self.setWindowTitle(f"⚙️ {symbol}")
        self.resize(500, 400)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel(f"💎 {self.symbol}")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        form = QFormLayout()
        
        self.investment_spin = QDoubleSpinBox()
        self.investment_spin.setRange(0, 1000000)
        self.investment_spin.setSuffix(" €")
        current = self.config.coin_settings.get(self.symbol, {}).get(
            'investment_amount', self.config.investment_amount
        )
        self.investment_spin.setValue(current)
        form.addRow("💰 Montant:", self.investment_spin)
        
        self.hours_edit = QLineEdit()
        hours = self.config.coin_settings.get(self.symbol, {}).get(
            'notification_hours', self.config.summary_hours
        )
        self.hours_edit.setText(", ".join(map(str, hours)))
        self.hours_edit.setPlaceholderText("Ex: 9, 12, 18")
        form.addRow("🕐 Heures:", self.hours_edit)
        
        self.include_check = QCheckBox("Inclure dans résumés")
        self.include_check.setChecked(
            self.config.coin_settings.get(self.symbol, {}).get('include_summary', True)
        )
        form.addRow("📊", self.include_check)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _save(self):
        try:
            hours = []
            for h in self.hours_edit.text().split(','):
                h = h.strip()
                if h.isdigit() and 0 <= int(h) <= 23:
                    hours.append(int(h))
            
            if not hours:
                QMessageBox.warning(self, "Erreur", "Heures invalides (0-23)")
                return
            
            if self.symbol not in self.config.coin_settings:
                self.config.coin_settings[self.symbol] = {}
            
            self.config.coin_settings[self.symbol]['investment_amount'] = self.investment_spin.value()
            self.config.coin_settings[self.symbol]['notification_hours'] = sorted(set(hours))
            self.config.coin_settings[self.symbol]['include_summary'] = self.include_check.isChecked()
            
            QMessageBox.information(self, "Succès", f"✅ {self.symbol} configuré")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {e}")
'''
    
    Path("ui/crypto_manager_window.py").write_text(code, encoding='utf-8')
    print("✅ ui/crypto_manager_window.py créé")


def fix_settings_window():
    """Ajoute le bouton dans settings"""
    
    file = Path("ui/settings_window.py")
    content = file.read_text(encoding='utf-8')
    
    # Ajouter import
    if "from ui.crypto_manager_window import CryptoManagerWindow" not in content:
        pos = content.find("from core.models")
        content = (
            content[:pos] +
            "from ui.crypto_manager_window import CryptoManagerWindow\n" +
            content[pos:]
        )
    
    # Remplacer section crypto
    old = '''    def _create_crypto_section(self):
        """Crée la section des cryptos"""
        group = QGroupBox("💰 Cryptomonnaies")
        layout = QFormLayout(group)

        self._line_edits["crypto_symbols"] = QLineEdit()
        self._line_edits["crypto_symbols"].setPlaceholderText("Ex: BTC, ETH, SOL")
        layout.addRow("Symboles (séparés par virgule):", self._line_edits["crypto_symbols"])'''
    
    new = '''    def _create_crypto_section(self):
        """Crée la section des cryptos"""
        group = QGroupBox("💰 Cryptomonnaies")
        layout = QFormLayout(group)
        
        manage_btn = QPushButton("💰 Gérer les cryptomonnaies")
        manage_btn.clicked.connect(self._open_crypto_manager)
        layout.addRow("", manage_btn)

        self._line_edits["crypto_symbols"] = QLineEdit()
        self._line_edits["crypto_symbols"].setReadOnly(True)
        layout.addRow("Cryptos suivies:", self._line_edits["crypto_symbols"])'''
    
    content = content.replace(old, new)
    
    # Ajouter méthode
    if "_open_crypto_manager" not in content:
        method = '''
    def _open_crypto_manager(self):
        """Ouvre le gestionnaire"""
        dialog = CryptoManagerWindow(self.config, self)
        if dialog.exec():
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.save_config(self.config)
            self._line_edits["crypto_symbols"].setText(", ".join(self.config.crypto_symbols))
            QMessageBox.information(self, "Succès", "✅ Configuration sauvegardée")
'''
        pos = content.find("    def _on_save_clicked(self):")
        content = content[:pos] + method + "\n" + content[pos:]
    
    file.write_text(content, encoding='utf-8')
    print("✅ ui/settings_window.py modifié")


def fix_notification_save():
    """Corrige sauvegarde notifications"""
    
    file = Path("core/services/advanced_notification_config_window.py")
    content = file.read_text(encoding='utf-8')
    
    # Remplacer accept
    old = '''    def accept(self):
        """Valide et ferme le dialogue"""
        try:
            self._collect_settings_from_ui()
            self._collect_coin_settings_from_ui()
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Validation", str(e))'''
    
    new = '''    def accept(self):
        """Valide, sauvegarde et ferme"""
        try:
            self._collect_settings_from_ui()
            self._collect_coin_settings_from_ui()
            self._save_to_yaml()
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur:\\n{e}")'''
    
    content = content.replace(old, new)
    
    # Ajouter méthode sauvegarde
    if "_save_to_yaml" not in content:
        method = '''
    def _save_to_yaml(self):
        """Sauvegarde dans config/notifications.yaml"""
        import yaml
        from pathlib import Path
        
        path = Path("config/notifications.yaml")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'enabled': self.settings.enabled,
            'kid_friendly_mode': self.settings.kid_friendly_mode,
            'use_emojis_everywhere': self.settings.use_emojis_everywhere,
            'explain_everything': self.settings.explain_everything,
            'respect_quiet_hours': self.settings.respect_quiet_hours,
            'quiet_start': self.settings.quiet_start,
            'quiet_end': self.settings.quiet_end,
            'default_scheduled_hours': self.settings.default_scheduled_hours
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Sauvegardé: {path}")
'''
        pos = content.find("    def accept(self):")
        content = content[:pos] + method + "\n" + content[pos:]
    
    file.write_text(content, encoding='utf-8')
    print("✅ core/services/advanced_notification_config_window.py modifié")


def main():
    print("=" * 60)
    print("🚀 FIX ULTIME - La vraie solution")
    print("=" * 60)
    print()
    
    backup()
    print()
    
    print("📝 Corrections...")
    fix_send_summary()  # ← Le vrai fix
    create_crypto_manager()
    fix_settings_window()
    fix_notification_save()
    
    print()
    print("=" * 60)
    print("✅ TERMINÉ")
    print("=" * 60)
    print()
    print("💡 Changements importants :")
    print("  • Bouton résumé → utilise SummaryService (format complet)")
    print("  • NotificationGenerator → garde pour les heures programmées")
    print("  • Crypto manager → ajouté")
    print("  • Sauvegarde notifications → corrigée")
    print()
    print("🧪 Teste :")
    print("  python main.py")
    print("  📊 Résumé Telegram (devrait marcher sans daemon)")
    print("  ⚙️ Paramètres > Gérer les cryptomonnaies")
    print()


if __name__ == "__main__":
    main()
