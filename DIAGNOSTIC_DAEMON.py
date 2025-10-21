#!/usr/bin/env python3
"""
Diagnostic complet - Comprendre pourquoi le daemon envoie des alertes au lieu de résumés
"""

import sys
from pathlib import Path


def find_project_root():
    """Trouve la racine du projet"""
    current = Path.cwd()
    
    # Cherche main.py
    candidates = [
        current,
        current.parent,
        current / "cryptoFlow",
        Path.home() / "Downloads" / "cryptoFlow",
    ]
    
    for candidate in candidates:
        if (candidate / "main.py").exists():
            return candidate
    
    return None


def check_daemon(root):
    """Vérifie le daemon"""
    daemon_file = root / "daemon" / "daemon_service.py"
    
    if not daemon_file.exists():
        print(f"❌ Daemon non trouvé: {daemon_file}")
        return False
    
    print(f"✅ Daemon trouvé: {daemon_file}\n")
    
    content = daemon_file.read_text(encoding='utf-8')
    
    print("🔍 Vérifications:\n")
    
    checks = [
        ("Import SummaryService", "from core.services.summary_service import SummaryService"),
        ("Service créé dans __init__", "self.summary_service = SummaryService"),
        ("Méthode _check_cycle existe", "def _check_cycle(self):"),
        ("Utilise summary_service.generate_summary", "self.summary_service.generate_summary"),
        ("Envoie via telegram_api.send_message", "self.telegram_api.send_message(summary"),
        ("Vérifie heure programmée", "current_hour in self.config.summary_hours"),
    ]
    
    results = []
    for name, pattern in checks:
        present = pattern in content
        status = "✅" if present else "❌"
        print(f"  {status} {name}")
        results.append((name, present))
    
    # Diagnostics avancés
    print("\n🔬 Diagnostics avancés:\n")
    
    # Chercher comment _check_cycle est implémenté
    if "def _check_cycle(self):" in content:
        # Extraire un bout de la méthode
        start = content.find("def _check_cycle(self):")
        snippet = content[start:start+500]
        
        if "summary_service.generate_summary" in snippet:
            print("  ✅ _check_cycle utilise bien summary_service")
        else:
            print("  ❌ _check_cycle N'utilise PAS summary_service")
            print("  💡 C'est le problème ! La méthode doit être réécrite")
    
    # Vérifier si les alertes sont envoyées
    if "self.telegram_api.send_alert(alert)" in content:
        print("  ℹ️  Les alertes sont bien envoyées (normal)")
    
    # Vérifier summary_hours
    print(f"\n📋 Configuration dans config.yaml:")
    config_file = root / "config" / "config.yaml"
    if config_file.exists():
        config_content = config_file.read_text(encoding='utf-8')
        if "summary_hours:" in config_content:
            # Extraire les heures
            start = config_content.find("summary_hours:")
            end = config_content.find("\n", start + 100)
            hours_section = config_content[start:end]
            print(f"  {hours_section}")
    
    return all(r[1] for r in results)


def main():
    print("=" * 60)
    print("🔍 DIAGNOSTIC COMPLET DU DAEMON")
    print("=" * 60)
    print()
    
    # Trouver le projet
    root = find_project_root()
    
    if root is None:
        print("❌ Projet non trouvé")
        print()
        print("💡 Lance ce script depuis le dossier du projet:")
        print("   cd /chemin/vers/cryptoFlow")
        print("   python DIAGNOSTIC_DAEMON.py")
        print()
        return 1
    
    print(f"📁 Projet trouvé: {root}")
    print()
    
    # Vérifier le daemon
    if check_daemon(root):
        print()
        print("=" * 60)
        print("✅ DAEMON CORRECTEMENT CONFIGURÉ")
        print("=" * 60)
        print()
        print("🤔 Si tu reçois toujours des alertes au lieu de résumés:")
        print()
        print("1. Vérifie l'heure actuelle:")
        from datetime import datetime, timezone
        print(f"   Heure UTC maintenant: {datetime.now(timezone.utc).hour}h")
        print()
        print("2. Vérifie les heures programmées dans config.yaml")
        print()
        print("3. Redémarre le daemon:")
        print("   - Arrête le daemon dans l'app")
        print("   - Ferme l'app complètement")
        print("   - Relance: python main.py")
        print("   - Démarre le daemon")
        print()
        print("4. Attends une heure programmée")
        print()
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ PROBLÈME DÉTECTÉ")
        print("=" * 60)
        print()
        print("💡 Solutions:")
        print()
        print("1. La méthode _check_cycle n'utilise pas summary_service")
        print("   → Tu dois la remplacer complètement")
        print()
        print("2. Applique le fix force:")
        print(f"   cd {root}")
        print("   python FIX_DAEMON_FORCE.py")
        print()
        print("3. Ou modifie manuellement:")
        print("   Ouvre daemon/daemon_service.py")
        print("   Cherche def _check_cycle(self):")
        print("   Remplace TOUTE la méthode par celle dans FIX_DAEMON_MANUEL.py")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
