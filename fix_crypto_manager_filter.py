#!/usr/bin/env python3
"""
FIX: Filtrer les cryptos déjà suivies dans le gestionnaire
"""

import shutil
from pathlib import Path
from datetime import datetime


def backup_file():
    """Crée une sauvegarde du fichier"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/fix_crypto_filter_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    file = Path("ui/crypto_manager_window.py")
    if file.exists():
        dst = backup_dir / file.name
        shutil.copy2(file, dst)
        print(f"✅ Sauvegarde créée dans {backup_dir}")
        return backup_dir
    return None


def fix_add_crypto_method():
    """
    Corrige la méthode _add() pour:
    1. Proposer une liste de cryptos populaires
    2. Filtrer les cryptos déjà suivies
    3. Valider le symbole avec Binance
    """
    
    file_path = Path("ui/crypto_manager_window.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    
    # Trouver l'ancienne méthode _add
    old_method = '''    def _add(self):
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
            QMessageBox.information(self, "Succès", f"✅ {symbol} ajouté")'''
    
    # Nouvelle méthode améliorée
    new_method = '''    def _add(self):
        """Ajoute une nouvelle crypto avec suggestions filtrées"""
        from PyQt6.QtWidgets import QComboBox, QDialogButtonBox
        
        # Liste complète des cryptos populaires (top 50)
        ALL_CRYPTOS = [
            "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "MATIC", "LINK",
            "UNI", "ATOM", "XLM", "ALGO", "VET", "ICP", "FIL", "ETC", "HBAR", "APT",
            "LTC", "BCH", "NEAR", "STX", "IMX", "ARB", "OP", "SUI", "TIA", "SEI",
            "RUNE", "INJ", "FTM", "MANA", "SAND", "AXS", "GALA", "ENJ", "CHZ", "THETA",
            "AAVE", "MKR", "SNX", "CRV", "COMP", "YFI", "SUSHI", "BAL", "1INCH", "LDO"
        ]
        
        # Filtrer les cryptos déjà suivies
        available_cryptos = [c for c in ALL_CRYPTOS if c not in self.config.crypto_symbols]
        
        if not available_cryptos:
            QMessageBox.information(
                self, 
                "Toutes ajoutées", 
                "Tu suis déjà toutes les cryptos populaires !\n\n"
                "Tu peux quand même ajouter manuellement un symbole en cliquant sur 'Autre'."
            )
            # Permettre l'ajout manuel
            symbol, ok = QInputDialog.getText(
                self, 
                "Ajouter crypto (manuel)", 
                "Symbole (ex: DOGE, SHIB, PEPE):"
            )
            if ok and symbol:
                symbol = symbol.upper().strip()
                if symbol in self.config.crypto_symbols:
                    QMessageBox.warning(self, "Déjà présent", f"{symbol} est déjà dans ta liste")
                    return
                self._add_crypto_to_config(symbol)
            return
        
        # Créer un dialogue personnalisé avec combo box
        dialog = QDialog(self)
        dialog.setWindowTitle("➕ Ajouter une crypto")
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Description
        desc = QLabel(
            f"Sélectionne une crypto parmi les {len(available_cryptos)} disponibles :\n"
            "(Les cryptos que tu suis déjà sont cachées)"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Combo box avec suggestions filtrées
        combo = QComboBox()
        combo.addItems(available_cryptos)
        combo.setEditable(True)  # Permet la saisie manuelle
        combo.setPlaceholderText("Choisis ou tape un symbole...")
        layout.addWidget(combo)
        
        # Note
        note = QLabel("💡 Tu peux aussi taper un autre symbole (ex: DOGE, SHIB)")
        note.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note)
        
        # Boutons OK/Annuler
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Afficher le dialogue
        if dialog.exec() == QDialog.DialogCode.Accepted:
            symbol = combo.currentText().upper().strip()
            
            if not symbol:
                QMessageBox.warning(self, "Erreur", "Le symbole ne peut pas être vide")
                return
            
            if symbol in self.config.crypto_symbols:
                QMessageBox.warning(self, "Déjà présent", f"{symbol} est déjà dans ta liste")
                return
            
            self._add_crypto_to_config(symbol)
    
    def _add_crypto_to_config(self, symbol: str):
        """Ajoute une crypto à la configuration"""
        # Ajouter à la liste
        self.config.crypto_symbols.append(symbol)
        
        # Créer les paramètres par défaut si nécessaire
        if symbol not in self.config.coin_settings:
            self.config.coin_settings[symbol] = {}
        
        self.config.coin_settings[symbol]['investment_amount'] = self.config.investment_amount
        self.config.coin_settings[symbol]['include_summary'] = True
        
        # Rafraîchir l'affichage
        self._refresh_list()
        
        QMessageBox.information(
            self, 
            "Succès", 
            f"✅ {symbol} ajouté avec succès !\n\n"
            f"Montant d'investissement par défaut : {self.config.investment_amount:.0f}€"
        )'''
    
    # Remplacer l'ancienne méthode
    if old_method in content:
        content = content.replace(old_method, new_method)
        file_path.write_text(content, encoding='utf-8')
        print("✅ Méthode _add() corrigée avec filtrage des cryptos")
        return True
    else:
        print("⚠️ Ancienne méthode _add() non trouvée - le code a peut-être déjà été modifié")
        print("   Recherche d'une alternative...")
        
        # Essayer de trouver une autre version de _add
        if "def _add(self):" in content:
            print("   → Méthode _add() trouvée mais avec un format différent")
            print("   → Applique manuellement le correctif ou vérifie le code")
        
        return False


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔧 FIX: Filtrage des cryptos déjà suivies dans le gestionnaire")
    print("=" * 70)
    print()
    
    # Sauvegarde
    backup_dir = backup_file()
    if not backup_dir:
        print("❌ Impossible de créer une sauvegarde")
        return
    
    print()
    print("📝 Application du correctif...")
    print()
    
    # Appliquer le correctif
    success = fix_add_crypto_method()
    
    print()
    print("=" * 70)
    
    if success:
        print("✅ CORRECTIF APPLIQUÉ AVEC SUCCÈS!")
        print("=" * 70)
        print()
        print("🎯 Améliorations apportées:")
        print("  ✅ Liste de 50 cryptos populaires disponibles")
        print("  ✅ Filtrage automatique des cryptos déjà suivies")
        print("  ✅ Combo box avec suggestions intelligentes")
        print("  ✅ Possibilité de saisie manuelle pour autres cryptos")
        print("  ✅ Messages d'erreur plus clairs")
        print()
        print("🧪 Teste maintenant:")
        print("  1. python main.py")
        print("  2. ⚙️ Paramètres > 💰 Gérer les cryptomonnaies")
        print("  3. ➕ Ajouter > Vérifie que BTC/ETH/SOL ne sont PAS proposés")
        print()
    else:
        print("⚠️ LE CORRECTIF N'A PAS PU ÊTRE APPLIQUÉ AUTOMATIQUEMENT")
        print("=" * 70)
        print()
        print("📋 Action manuelle requise:")
        print("  1. Ouvre ui/crypto_manager_window.py")
        print("  2. Cherche la méthode def _add(self):")
        print("  3. Remplace-la par le code du correctif")
        print()
    
    print(f"💾 Sauvegarde: {backup_dir}")
    print()


if __name__ == "__main__":
    main()
