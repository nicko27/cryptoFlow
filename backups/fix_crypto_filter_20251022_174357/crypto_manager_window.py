"""Gestionnaire de cryptomonnaies"""

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
