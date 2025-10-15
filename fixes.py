"""
Script de correction des bugs critiques du Crypto Bot v3.0
Exécuter ce script pour appliquer tous les correctifs automatiquement
"""

import os
import re
from pathlib import Path


def fix_timezone_issues():
    """Corrige les problèmes de timezone dans market_service.py"""
    print("🔧 Correction des problèmes de timezone...")
    
    file_path = Path("core/services/market_service.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Remplacer datetime.now() par datetime.now(timezone.utc)
    content = content.replace(
        "from datetime import datetime, timedelta",
        "from datetime import datetime, timedelta, timezone"
    )
    
    # Remplacer dans get_price_history
    content = re.sub(
        r'cutoff = datetime\.now\(\) - timedelta\(hours=hours\)',
        'cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)',
        content
    )
    
    file_path.write_text(content, encoding='utf-8')
    print("✅ Timezone fixé dans market_service.py")


def fix_main_window_class_name():
    """Corrige le nom de classe avec espace dans main_window.py"""
    print("🔧 Correction du nom de classe GUI...")
    
    for path in [Path("backups/20251014_155156/main_window.py"), Path("ui/main_window.py")]:
        if not path.exists():
            continue
        
        content = path.read_text(encoding='utf-8')
        
        # Corriger "CryptoBot GUI" -> "CryptoBotGUI"
        content = content.replace(
            "class CryptoBot GUI(ctk.CTk):",
            "class CryptoBotGUI(ctk.CTk):"
        )
        
        path.write_text(content, encoding='utf-8')
        print(f"✅ Nom de classe fixé dans {path}")


def fix_alert_service_imports():
    """Corrige les imports manquants dans alert_service.py"""
    print("🔧 Correction des imports dans alert_service.py...")
    
    for path in [Path("backups/20251014_155156/alert_service.py"), Path("core/services/alert_service.py")]:
        if not path.exists():
            continue
        
        content = path.read_text(encoding='utf-8')
        
        # Vérifier et corriger l'import
        if "from typing import List, Optional, Callable" in content:
            content = content.replace(
                "from typing import List, Optional, Callable",
                "from typing import List, Optional, Callable, Dict"
            )
        
        path.write_text(content, encoding='utf-8')
        print(f"✅ Imports fixés dans {path}")


def fix_binance_timezone():
    """Corrige les problèmes de timezone dans binance_api.py"""
    print("🔧 Correction timezone dans binance_api.py...")
    
    file_path = Path("api/binance_api.py")
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # S'assurer que timezone est importé
    if "from datetime import datetime, timezone" not in content:
        content = content.replace(
            "from datetime import datetime",
            "from datetime import datetime, timezone"
        )
    
    file_path.write_text(content, encoding='utf-8')
    print("✅ Timezone fixé dans binance_api.py")


def create_init_files():
    """Crée les fichiers __init__.py manquants"""
    print("🔧 Création des __init__.py manquants...")
    
    dirs = [
        "database",
        "ml",
        "strategies",
        "analysis",
        "optimizations"
    ]
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""\n{dir_name.title()} Package\n"""\n', encoding='utf-8')
            print(f"✅ Créé {init_file}")


def main():
    """Applique tous les correctifs"""
    print("\n" + "="*60)
    print("🔧 APPLICATION DES CORRECTIFS CRITIQUES")
    print("="*60 + "\n")
    
    fix_timezone_issues()
    fix_main_window_class_name()
    fix_alert_service_imports()
    fix_binance_timezone()
    create_init_files()
    
    print("\n" + "="*60)
    print("✅ TOUS LES CORRECTIFS ONT ÉTÉ APPLIQUÉS")
    print("="*60 + "\n")
    
    print("📝 Prochaines étapes:")
    print("  1. Vérifier que les corrections sont OK")
    print("  2. Tester le bot: python main.py --once")
    print("  3. Lancer l'interface: python main.py")
    print()


if __name__ == "__main__":
    main()
