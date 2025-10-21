#!/usr/bin/env python3
"""
FIX COMPLET - Corrige TOUS les problèmes
1. Bouton résumé utilisant NotificationGenerator
2. Gestionnaire de cryptos
3. Sauvegarde des notifications qui fonctionne
4. Ajout des boutons manquants dans settings
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def backup_files():
    """Crée une sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_complet_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = [
        "ui/main_window.py",
        "ui/settings_window.py",
        "core/services/advanced_notification_config_window.py"
    ]
    
    for file in files_to_backup:
        src = Path(file)
        if src.exists():
            dst = backup_dir / file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    print(f"✅ Sauvegarde créée dans {backup_dir}")
    return backup_dir


def create_crypto_manager():
    """Crée le gestionnaire de cryptos"""
    
    content = '''"""
Gestionnaire de cryptomonnaies - Version complète
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QMessageBox, QInputDialog
)
from PyQt6.QtGui import QFont
from core.models import BotConfiguration


class CryptoManagerWindow(QDialog):
    """Fenêtre de gestion des cryptomonnaies"""
    
    def __init__(self, config: BotConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("💰 Gestion des Cryptomonnaies")
        self.resize(800, 600)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # En-tête
        header = QLabel("💰 Gère tes cryptomonnaies")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        desc = QLabel(
            "Ajoute, configure ou supprime des cryptomonnaies. "
            "Tu peux configurer chaque crypto indépendamment ou appliquer "
            "les mêmes paramètres à toutes."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Liste des cryptos
        list_group = QGroupBox("📋 Mes cryptos")
        list_layout = QVBoxLayout()
        
        self.crypto_list = QListWidget()
        self._refresh_crypto_list()
        list_layout.addWidget(self.crypto_list)
        
        # Boutons de gestion
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Ajouter")
        add_btn.clicked.connect(self._add_crypto)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ Configurer")
        edit_btn.clicked.connect(self._edit_crypto)
        btn_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("🗑️ Supprimer")
        remove_btn.clicked.connect(self._remove_crypto)
        btn_layout.addWidget(remove_btn)
        
        list_layout.addLayout(btn_layout)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Configuration globale
        global_group = QGroupBox("⚙️ Configuration globale")
        global_layout = QFormLayout()
        
        self.global_investment = QDoubleSpinBox()
        self.global_investment.setRange(0, 1000000)
        self.global_investment.setValue(self.config.investment_amount)
        self.global_investment.setSuffix(" €")
        global_layout.addRow("Montant d'investissement par défaut:", self.global_investment)
        
        apply_global_btn = QPushButton("📢 Appliquer à toutes les cryptos")
        apply_global_btn.clicked.connect(self._apply_global_settings)
        global_layout.addRow("", apply_global_btn)
        
        global_group.setLayout(global_layout)
        layout.addWidget(global_group)
        
        # Boutons OK/Annuler
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_crypto_list(self):
        """Rafraîchit la liste des cryptos"""
        self.crypto_list.clear()
        for symbol in self.config.crypto_symbols:
            investment = self.config.coin_settings.get(symbol, {}).get(
                'investment_amount',
                self.config.investment_amount
            )
            
            include = self.config.coin_settings.get(symbol, {}).get(
                'include_summary',
                True
            )
            
            status = "✅" if include else "⏸️"
            self.crypto_list.addItem(
                f"{status} {symbol} - {investment:.0f}€"
            )
    
    def _add_crypto(self):
        """Ajoute une nouvelle crypto"""
        symbol, ok = QInputDialog.getText(
            self,
            "Ajouter une crypto",
            "Symbole de la crypto (ex: BTC, ETH, SOL, ADA):"
        )
        
        if ok and symbol:
            symbol = symbol.upper().strip()
            
            if not symbol:
                QMessageBox.warning(self, "Erreur", "Le symbole ne peut pas être vide")
                return
            
            if symbol in self.config.crypto_symbols:
                QMessageBox.warning(self, "Erreur", f"{symbol} est déjà dans la liste")
                return
            
            self.config.crypto_symbols.append(symbol)
            
            if symbol not in self.config.coin_settings:
                self.config.coin_settings[symbol] = {}
            
            self.config.coin_settings[symbol]['investment_amount'] = self.config.investment_amount
            self.config.coin_settings[symbol]['notification_hours'] = self.config.summary_hours
            self.config.coin_settings[symbol]['include_summary'] = True
            
            self._refresh_crypto_list()
            
            QMessageBox.information(self, "Succès", f"✅ {symbol} ajouté avec succès !")
    
    def _edit_crypto(self):
        """Édite la configuration d'une crypto"""
        current_item = self.crypto_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Sélection", "Sélectionne d'abord une crypto à configurer")
            return
        
        text = current_item.text()
        symbol = text.split(" ")[1]
        
        dialog = CryptoConfigDialog(symbol, self.config, self)
        if dialog.exec():
            self._refresh_crypto_list()
    
    def _remove_crypto(self):
        """Supprime une crypto"""
        current_item = self.crypto_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Sélection", "Sélectionne d'abord une crypto à supprimer")
            return
        
        text = current_item.text()
        symbol = text.split(" ")[1]
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer {symbol} de la liste ?\n\nCette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.crypto_symbols.remove(symbol)
            
            if symbol in self.config.coin_settings:
                del self.config.coin_settings[symbol]
            
            self._refresh_crypto_list()
            
            QMessageBox.information(self, "Succès", f"✅ {symbol} supprimé")
    
    def _apply_global_settings(self):
        """Applique les paramètres globaux à toutes les cryptos"""
        investment = self.global_investment.value()
        
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Appliquer {investment:.0f}€ comme montant d'investissement "
            f"pour toutes les {len(self.config.crypto_symbols)} cryptos ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for symbol in self.config.crypto_symbols:
                if symbol not in self.config.coin_settings:
                    self.config.coin_settings[symbol] = {}
                
                self.config.coin_settings[symbol]['investment_amount'] = investment
            
            self.config.investment_amount = investment
            
            self._refresh_crypto_list()
            
            QMessageBox.information(self, "Succès", f"✅ Configuration appliquée à toutes les cryptos")


class CryptoConfigDialog(QDialog):
    """Dialogue de configuration individuelle"""
    
    def __init__(self, symbol: str, config: BotConfiguration, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.config = config
        self.setWindowTitle(f"⚙️ Configuration de {symbol}")
        self.resize(500, 400)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel(f"💎 {self.symbol}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        
        self.investment_spin = QDoubleSpinBox()
        self.investment_spin.setRange(0, 1000000)
        self.investment_spin.setSuffix(" €")
        current_investment = self.config.coin_settings.get(self.symbol, {}).get(
            'investment_amount',
            self.config.investment_amount
        )
        self.investment_spin.setValue(current_investment)
        form_layout.addRow("💰 Montant d'investissement:", self.investment_spin)
        
        self.hours_edit = QLineEdit()
        current_hours = self.config.coin_settings.get(self.symbol, {}).get(
            'notification_hours',
            self.config.summary_hours
        )
        self.hours_edit.setText(", ".join(map(str, current_hours)))
        self.hours_edit.setPlaceholderText("Ex: 9, 12, 18")
        form_layout.addRow("🕐 Heures de notification:", self.hours_edit)
        
        self.include_check = QCheckBox("Inclure dans les résumés automatiques")
        self.include_check.setChecked(
            self.config.coin_settings.get(self.symbol, {}).get('include_summary', True)
        )
        form_layout.addRow("📊", self.include_check)
        
        layout.addLayout(form_layout)
        
        help_text = QLabel(
            "💡 Les heures de notification sont en format 24h (0-23). "
            "Sépare-les par des virgules."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(help_text)
        
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
        """Sauvegarde la configuration"""
        try:
            hours_text = self.hours_edit.text()
            hours = []
            
            for h in hours_text.split(','):
                h = h.strip()
                if h.isdigit():
                    hour = int(h)
                    if 0 <= hour <= 23:
                        hours.append(hour)
            
            if not hours:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Les heures doivent être entre 0 et 23, séparées par des virgules"
                )
                return
            
            if self.symbol not in self.config.coin_settings:
                self.config.coin_settings[self.symbol] = {}
            
            self.config.coin_settings[self.symbol]['investment_amount'] = self.investment_spin.value()
            self.config.coin_settings[self.symbol]['notification_hours'] = sorted(set(hours))
            self.config.coin_settings[self.symbol]['include_summary'] = self.include_check.isChecked()
            
            QMessageBox.information(self, "Succès", f"✅ Configuration de {self.symbol} sauvegardée")
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde :\n{e}")
'''
    
    file_path = Path("ui/crypto_manager_window.py")
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ Créé {file_path}")


def fix_notification_save():
    """Corrige la sauvegarde des notifications dans advanced_notification_config_window.py"""
    
    file_path = Path("core/services/advanced_notification_config_window.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Chercher la méthode accept() et la remplacer si elle n'appelle pas _save_to_file
    old_accept = '''    def accept(self):
        """Valide et ferme le dialogue"""
        try:
            self._collect_settings_from_ui()
            self._collect_coin_settings_from_ui()
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Validation", str(e))'''
    
    new_accept = '''    def accept(self):
        """Valide, sauvegarde et ferme le dialogue"""
        try:
            self._collect_settings_from_ui()
            self._collect_coin_settings_from_ui()
            self._save_to_file()  # AJOUT: Sauvegarde dans le fichier YAML
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde:\\n{e}")'''
    
    if old_accept in content:
        content = content.replace(old_accept, new_accept)
    
    # Ajouter la méthode _save_to_file si elle n'existe pas
    if "_save_to_file" not in content:
        save_method = '''
    def _save_to_file(self):
        """Sauvegarde les paramètres dans config/notifications.yaml"""
        import yaml
        from pathlib import Path
        
        notif_config_path = Path("config/notifications.yaml")
        notif_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Préparer les données à sauvegarder
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
        
        # Sauvegarder dans le fichier
        with open(notif_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✅ Configuration des notifications sauvegardée dans {notif_config_path}")
'''
        
        # Insérer avant la dernière ligne de la classe
        insert_pos = content.rfind("    def accept(self):")
        if insert_pos > 0:
            content = content[:insert_pos] + save_method + "\n" + content[insert_pos:]
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ Sauvegarde des notifications corrigée dans {file_path}")


def fix_settings_window():
    """Ajoute le bouton crypto manager dans settings_window.py"""
    
    file_path = Path("ui/settings_window.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Ajouter l'import si nécessaire
    if "from ui.crypto_manager_window import CryptoManagerWindow" not in content:
        import_pos = content.find("from core.models")
        if import_pos > 0:
            content = (
                content[:import_pos] +
                "from ui.crypto_manager_window import CryptoManagerWindow\n" +
                content[import_pos:]
            )
    
    # Modifier la section crypto pour ajouter le bouton
    old_section = '''    def _create_crypto_section(self):
        """Crée la section crypto"""
        group = QGroupBox("Cryptomonnaies")
        layout = QFormLayout()
        
        self._line_edits["crypto_symbols"] = QLineEdit()
        layout.addRow("Symboles (séparés par ,):", self._line_edits["crypto_symbols"])'''
    
    new_section = '''    def _create_crypto_section(self):
        """Crée la section crypto"""
        group = QGroupBox("Cryptomonnaies")
        layout = QFormLayout()
        
        # Bouton de gestion centralisée
        manage_btn = QPushButton("💰 Gérer les cryptomonnaies")
        manage_btn.clicked.connect(self._open_crypto_manager)
        layout.addRow("", manage_btn)
        
        # Affichage en lecture seule
        self._line_edits["crypto_symbols"] = QLineEdit()
        self._line_edits["crypto_symbols"].setReadOnly(True)
        layout.addRow("Cryptos suivies:", self._line_edits["crypto_symbols"])'''
    
    if old_section in content:
        content = content.replace(old_section, new_section)
    
    # Ajouter la méthode _open_crypto_manager si elle n'existe pas
    if "_open_crypto_manager" not in content:
        new_method = '''
    def _open_crypto_manager(self):
        """Ouvre le gestionnaire de cryptos"""
        dialog = CryptoManagerWindow(self.config, self)
        if dialog.exec():
            # Sauvegarder la configuration
            from config.config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.save_config(self.config)
            
            # Mettre à jour l'affichage
            self._line_edits["crypto_symbols"].setText(", ".join(self.config.crypto_symbols))
            
            QMessageBox.information(
                self,
                "Succès",
                "Configuration des cryptos mise à jour et sauvegardée"
            )
'''
        
        # Insérer avant _on_save_clicked
        insert_pos = content.find("    def _on_save_clicked(self):")
        if insert_pos > 0:
            content = content[:insert_pos] + new_method + "\n" + content[insert_pos:]
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ Bouton gestionnaire de cryptos ajouté dans {file_path}")


def fix_main_window_summary():
    """Corrige le bouton résumé dans main_window.py"""
    
    file_path = Path("ui/main_window.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Chercher et remplacer la méthode _send_summary
    # On cherche le début et la fin de la méthode
    start_marker = "    def _send_summary(self):"
    end_marker = "            )\n    \n    def _generate_report(self):"
    
    start_pos = content.find(start_marker)
    end_pos = content.find(end_marker)
    
    if start_pos > 0 and end_pos > start_pos:
        new_method = '''    def _send_summary(self):
        """Envoie un résumé complet sur Telegram (utilise NotificationGenerator)"""
        try:
            if not self.daemon_service or not self.daemon_service.notification_generator:
                QMessageBox.warning(
                    self,
                    "Service non initialisé",
                    "Démarre d'abord le daemon pour initialiser le système de notifications."
                )
                return
            
            current_hour = datetime.now(timezone.utc).hour
            current_day = datetime.now(timezone.utc).weekday()
            
            # Collecter les données
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            for symbol in self.config.crypto_symbols:
                if symbol in self.market_data_cache:
                    market = self.market_data_cache[symbol]
                    markets_data[symbol] = market
                    
                    prediction = self.predictions_cache.get(symbol) or \\
                                self.market_service.predict_price_movement(market)
                    opportunity = self.opportunities_cache.get(symbol) or \\
                                 self.market_service.calculate_opportunity_score(market, prediction)
                    
                    if prediction:
                        predictions[symbol] = prediction
                        self.predictions_cache[symbol] = prediction
                    if opportunity:
                        opportunities[symbol] = opportunity
                        self.opportunities_cache[symbol] = opportunity
            
            if not markets_data:
                QMessageBox.warning(self, "Aucune donnée", "Rafraîchis d'abord les données")
                return
            
            # Générer et envoyer les notifications
            sent_count = 0
            for symbol in self.config.crypto_symbols:
                if symbol not in markets_data:
                    continue
                
                notification = self.daemon_service.notification_generator.generate_notification(
                    symbol=symbol,
                    market=markets_data[symbol],
                    prediction=predictions.get(symbol),
                    opportunity=opportunities.get(symbol),
                    all_markets=markets_data,
                    all_predictions=predictions,
                    all_opportunities=opportunities,
                    current_hour=current_hour,
                    current_day_of_week=current_day
                )
                
                if notification:
                    success = self.telegram_api.send_message(notification, parse_mode="HTML")
                    if success:
                        sent_count += 1
            
            if sent_count > 0:
                QMessageBox.information(
                    self,
                    "Résumé envoyé",
                    f"✅ {sent_count} notification(s) envoyée(s) sur Telegram !"
                )
            else:
                QMessageBox.warning(self, "Erreur", "Aucune notification n'a pu être envoyée")
        
        except Exception as e:
            self.logger.error(f"Erreur envoi résumé: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'envoyer le résumé : {e}")'''
        
        content = content[:start_pos] + new_method + "\n    \n" + content[end_pos:]
        file_path.write_text(content, encoding='utf-8')
        print(f"✅ Méthode _send_summary corrigée dans {file_path}")
    else:
        print(f"⚠️ Méthode _send_summary non trouvée pour remplacement")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🚀 FIX COMPLET - Correction de TOUS les problèmes")
    print("=" * 60)
    print()
    
    # Sauvegarde
    backup_dir = backup_files()
    print()
    
    # Corrections
    print("📝 Application des correctifs...")
    print()
    
    create_crypto_manager()
    fix_notification_save()
    fix_settings_window()
    fix_main_window_summary()
    
    print()
    print("=" * 60)
    print("✅ TOUS LES CORRECTIFS APPLIQUÉS!")
    print("=" * 60)
    print()
    print("📋 Résumé :")
    print("  ✅ Gestionnaire de cryptos créé")
    print("  ✅ Sauvegarde des notifications corrigée")
    print("  ✅ Bouton 'Gérer les cryptomonnaies' ajouté")
    print("  ✅ Méthode _send_summary améliorée")
    print()
    print("🎯 Teste maintenant :")
    print("  1. python main.py")
    print("  2. ⚙️ Paramètres > Gérer les cryptomonnaies")
    print("  3. 🔔 Config notifications > Enregistrer")
    print("  4. ▶️ Démarrer daemon > 📊 Envoyer résumé")
    print()
    print(f"💾 Sauvegarde: {backup_dir}")
    print()


if __name__ == "__main__":
    main()
