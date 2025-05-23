#!/usr/bin/env python3
"""
QCM Medical Extraction System - Interface Principale
Point d'entrée unique pour toutes les opérations
"""

import sys
import argparse
from pathlib import Path

def print_banner():
    """Affiche la bannière du système"""
    print("🏥 QCM MEDICAL EXTRACTION SYSTEM v2.0.0")
    print("=" * 55)
    print("Système d'extraction automatisé et scalable")
    print("Support: UE1-UE7, tous formats QCM médicaux")
    print()

def show_commands():
    """Affiche les commandes disponibles"""
    print("📋 COMMANDES DISPONIBLES:")
    print()
    
    print("🚀 EXTRACTION:")
    print("  python extract_qcm.py <URL_PDF>")
    print("    # Extraction complète d'un QCM PDF")
    print("    # Exemple: python extract_qcm.py https://example.com/qcm.pdf")
    print()
    
    print("🔧 SETUP & MAINTENANCE:")
    print("  python scripts/setup.py")
    print("    # Installation et configuration du système")
    print()
    
    print("📊 VALIDATION:")
    print("  python extract_qcm.py <URL_PDF> --verbose")
    print("    # Extraction avec détails complets")
    print()
    
    print("💡 AIDE:")
    print("  python extract_qcm.py --help")
    print("    # Aide détaillée sur les options")
    print()

def show_examples():
    """Affiche des exemples d'utilisation"""
    print("💡 EXEMPLES D'UTILISATION:")
    print()
    
    print("# Extraction UE3 Nancy:")
    print("python extract_qcm.py \"https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE3/QCM/ue3-correction-cb1-s40-21-22-48479.pdf\"")
    print()
    
    print("# Extraction avec logs détaillés:")
    print("python extract_qcm.py \"<URL_PDF>\" --verbose")
    print()
    
    print("# Vérification version:")
    print("python extract_qcm.py --version")
    print()

def show_architecture():
    """Affiche l'architecture du système"""
    print("🏗️  ARCHITECTURE DU SYSTÈME:")
    print()
    
    print("📁 Structure:")
    print("  extract_qcm.py          # ✅ Commande principale (point d'entrée)")
    print("  qcm_extraction/         # 🔧 Module core d'extraction")
    print("  ├── extractor.py        # 🧠 Logique principale")
    print("  ├── database.py         # 🗄️  Interface Supabase")
    print("  └── utils.py            # 🛠️  Utilitaires")
    print("  scripts/                # 📋 Scripts de maintenance")
    print("  ├── setup.py            # ⚙️  Installation automatique")
    print("  └── main.py             # 💡 Interface d'aide")
    print()
    
    print("🔄 Processus d'extraction (3 phases):")
    print("  Phase 1: Extraction des questions      (API + Regex fallback)")
    print("  Phase 2: Extraction des propositions  (Batch optimisé)")
    print("  Phase 3: Identification réponses      (Multi-méthodes)")
    print()

def main():
    """Interface principale"""
    parser = argparse.ArgumentParser(
        description="QCM Medical Extraction System - Interface principale",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'action',
        nargs='?',
        choices=['commands', 'examples', 'architecture', 'help'],
        default='help',
        help='Action à effectuer'
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.action == 'commands':
        show_commands()
    elif args.action == 'examples':
        show_examples()
    elif args.action == 'architecture':
        show_architecture()
    else:
        print("🎯 UTILISATION RAPIDE:")
        print("  python extract_qcm.py <URL_PDF>  # Extraire un QCM")
        print("  python scripts/main.py commands  # Voir toutes les commandes")
        print("  python scripts/main.py examples  # Voir des exemples")
        print()
        
        print("📖 DOCUMENTATION COMPLÈTE:")
        print("  README.md                         # Guide complet")
        print("  python extract_qcm.py --help     # Aide de la commande")
        print()

if __name__ == "__main__":
    main() 