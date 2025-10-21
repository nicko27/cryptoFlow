#!/usr/bin/env python3
"""
Fix pour lancer le daemon dans un thread séparé depuis le GUI
"""

import os
import sys

def fix_gui_daemon():
    """Modifie le GUI pour lancer le daemon dans un thread"""
    
    filepath = "ui/main_window.py"
    
    if not os.path.exists(filepath):
        print(f"❌ Fichier non trouvé : {filepath}")
        return False
    
    print(f"🔧 Modification de {filepath}...\n")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Backup
        backup = filepath + ".backup_thread"
        with open(backup, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Backup : {backup}")
        
        # Vérifier si déjà corrigé
        if 'daemon_thread = Thread(' in content or 'QThread' in content:
            print("ℹ️  Le daemon est déjà lancé dans un thread")
            return True
        
        # Ajouter l'import Thread si absent
        if 'from threading import Thread' not in content:
            # Trouver la section des imports
            import_pos = content.find('import sys')
            if import_pos == -1:
                import_pos = content.find('import os')
            
            if import_pos != -1:
                # Insérer après la ligne
                line_end = content.find('\n', import_pos)
                content = content[:line_end+1] + 'from threading import Thread\n' + content[line_end+1:]
                print("✓ Import Thread ajouté")
        
        # Trouver la méthode _start_daemon ou start_daemon
        daemon_start_methods = [
            'def _start_daemon(self)',
            'def start_daemon(self)',
            'self.daemon_service.start()'
        ]
        
        found_method = None
        for method in daemon_start_methods:
            if method in content:
                found_method = method
                break
        
        if not found_method:
            print("⚠️  Méthode de démarrage daemon non trouvée")
            print("   Cherchez manuellement où daemon.start() est appelé")
            return False
        
        print(f"✓ Trouvé : {found_method}")
        
        # Remplacer l'appel direct par un thread
        if 'self.daemon_service.start()' in content:
            # Cas 1 : appel direct
            old_code = 'self.daemon_service.start()'
            new_code = '''# Lancer le daemon dans un thread séparé pour ne pas bloquer le GUI
        self.daemon_thread = Thread(target=self.daemon_service.start, daemon=True)
        self.daemon_thread.start()
        print("✓ Daemon démarré dans un thread séparé")'''
            
            content = content.replace(old_code, new_code)
            print("✓ Appel daemon.start() remplacé par Thread")
        
        # Sauvegarder
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n" + "="*70)
        print("✅ MODIFICATION TERMINÉE")
        print("="*70 + "\n")
        
        print("📋 Changements :")
        print("  • Import threading.Thread ajouté")
        print("  • daemon.start() lancé dans un thread séparé")
        print("  • Le GUI ne sera plus bloqué")
        
        print("\n🎯 Testez maintenant :")
        print("   python3 main.py")
        print("   Puis cliquez sur 'Démarrer daemon' dans l'interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*70)
    print("🔧 FIX : Daemon bloque l'interface graphique")
    print("="*70 + "\n")
    
    if not os.path.exists("ui"):
        print("❌ Répertoire ui/ non trouvé")
        return False
    
    success = fix_gui_daemon()
    
    if not success:
        print("\n💡 SOLUTION MANUELLE :")
        print("\n1. Ouvrez ui/main_window.py")
        print("\n2. Ajoutez en haut :")
        print("   from threading import Thread")
        print("\n3. Cherchez : self.daemon_service.start()")
        print("\n4. Remplacez par :")
        print("   self.daemon_thread = Thread(")
        print("       target=self.daemon_service.start,")
        print("       daemon=True")
        print("   )")
        print("   self.daemon_thread.start()")
    
    print("\n" + "="*70 + "\n")
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
