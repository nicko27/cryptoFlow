"""
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
            f"Supprimer {symbol} de la liste ?Cette action est irréversible.",
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
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la sauvegarde :{e}")
