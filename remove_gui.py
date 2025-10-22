#!/usr/bin/env python3
"""
Script de suppression de l'interface graphique du Crypto Bot
Supprime tous les fichiers GUI PyQt6 et les dépendances associées
"""

import os
import sys
import shutil
from pathlib import Path


def confirm_deletion():
    """Demande confirmation avant suppression"""
    print("⚠️  ATTENTION : Ce script va supprimer DÉFINITIVEMENT :")
    print("   • Tous les fichiers du dossier ui/")
    print("   • Les dépendances PyQt6 dans requirements.txt")
    print("   • Le mode GUI dans main.py")
    print()
    response = input("Voulez-vous continuer ? (tapez 'OUI' en majuscules) : ")
    return response == "OUI"


def remove_ui_directory():
    """Supprime le dossier ui/ contenant l'interface graphique"""
    ui_path = Path("ui")
    
    if ui_path.exists() and ui_path.is_dir():
        print(f"🗑️  Suppression du dossier {ui_path}/...")
        shutil.rmtree(ui_path)
        print(f"✅ Dossier {ui_path}/ supprimé")
    else:
        print(f"ℹ️  Le dossier {ui_path}/ n'existe pas")


def clean_requirements_txt():
    """Supprime les dépendances GUI de requirements.txt"""
    req_file = Path("requirements.txt")
    
    if not req_file.exists():
        print("ℹ️  requirements.txt n'existe pas")
        return
    
    print("📝 Nettoyage de requirements.txt...")
    
    # Dépendances GUI à supprimer
    gui_deps = [
        "PyQt6",
        "PyQt6-Charts",
        "customtkinter",
        "matplotlib",  # Souvent utilisé pour GUI
        "plotly",      # Souvent utilisé pour GUI
    ]
    
    with open(req_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Filtrer les lignes
    new_lines = []
    removed = []
    
    for line in lines:
        line_lower = line.lower().strip()
        if any(dep.lower() in line_lower for dep in gui_deps):
            removed.append(line.strip())
        else:
            new_lines.append(line)
    
    # Écrire le nouveau fichier
    with open(req_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    if removed:
        print("✅ Dépendances GUI supprimées de requirements.txt :")
        for dep in removed:
            print(f"   • {dep}")
    else:
        print("ℹ️  Aucune dépendance GUI trouvée dans requirements.txt")


def update_main_py():
    """Supprime le mode GUI de main.py"""
    main_file = Path("main.py")
    
    if not main_file.exists():
        print("ℹ️  main.py n'existe pas")
        return
    
    print("📝 Modification de main.py...")
    
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Supprimer la fonction run_gui_mode
    gui_function_start = content.find("def run_gui_mode(")
    if gui_function_start != -1:
        # Trouver la fin de la fonction (prochaine fonction ou fin de fichier)
        next_function = content.find("\ndef ", gui_function_start + 1)
        if next_function == -1:
            next_function = len(content)
        
        content = content[:gui_function_start] + content[next_function:]
        print("✅ Fonction run_gui_mode() supprimée")
    
    # Modifier la condition de lancement par défaut
    if "run_gui_mode" in content:
        # Remplacer l'appel à run_gui_mode par run_daemon_mode
        content = content.replace(
            "run_gui_mode(config)",
            "print('❌ Mode GUI supprimé. Utilisez --daemon ou --once')\n    sys.exit(1)"
        )
        print("✅ Appel à run_gui_mode() remplacé par message d'erreur")
    
    # Écrire le fichier modifié seulement s'il y a eu des changements
    if content != original_content:
        # Créer une sauvegarde
        backup_file = main_file.with_suffix('.py.backup')
        shutil.copy(main_file, backup_file)
        print(f"💾 Sauvegarde créée : {backup_file}")
        
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ main.py modifié")
    else:
        print("ℹ️  Aucune modification nécessaire dans main.py")


def create_summary():
    """Affiche un résumé des modifications"""
    print()
    print("=" * 70)
    print("📊 RÉSUMÉ DES MODIFICATIONS")
    print("=" * 70)
    print()
    print("✅ Interface graphique complètement supprimée")
    print()
    print("📋 Modes disponibles :")
    print("   • python3 main.py --daemon   (mode démon en arrière-plan)")
    print("   • python3 main.py --once     (exécution unique)")
    print()
    print("🔧 Pour restaurer l'interface graphique :")
    print("   1. Restaurez main.py.backup si nécessaire")
    print("   2. Récupérez le dossier ui/ depuis votre sauvegarde")
    print("   3. Réinstallez : pip3 install PyQt6 PyQt6-Charts")
    print()
    print("=" * 70)


def main():
    """Fonction principale"""
    print()
    print("=" * 70)
    print("🔧 SUPPRESSION DE L'INTERFACE GRAPHIQUE")
    print("=" * 70)
    print()
    
    # Vérifier qu'on est dans le bon répertoire
    if not Path("main.py").exists():
        print("❌ Erreur : main.py non trouvé")
        print("   Exécutez ce script depuis le répertoire racine du projet")
        return 1
    
    # Demander confirmation
    if not confirm_deletion():
        print()
        print("❌ Opération annulée par l'utilisateur")
        return 0
    
    print()
    print("🚀 Début de la suppression...")
    print()
    
    try:
        # Supprimer le dossier ui/
        remove_ui_directory()
        print()
        
        # Nettoyer requirements.txt
        clean_requirements_txt()
        print()
        
        # Modifier main.py
        update_main_py()
        print()
        
        # Afficher le résumé
        create_summary()
        
        return 0
        
    except Exception as e:
        print()
        print(f"❌ Erreur lors de la suppression : {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
