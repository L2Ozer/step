#!/usr/bin/env python3
"""
QCM Medical Extraction System - Setup Script
Automatise l'installation et la configuration du projet
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Affiche un en-tête formaté"""
    print("\n" + "="*60)
    print(f"🚀 {text}")
    print("="*60)

def print_step(step, text):
    """Affiche une étape"""
    print(f"\n{step}. {text}")

def check_python_version():
    """Vérifie la version de Python"""
    print_step("1", "Vérification de la version Python...")
    
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ requis")
        print(f"📊 Version actuelle: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} détecté")

def create_virtual_environment():
    """Crée un environnement virtuel"""
    print_step("2", "Création de l'environnement virtuel...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("⚠️ Environnement virtuel déjà existant")
        response = input("Voulez-vous le recréer? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree(venv_path)
        else:
            print("✅ Utilisation de l'environnement existant")
            return
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Environnement virtuel créé")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de la création de l'environnement virtuel")
        sys.exit(1)

def install_dependencies():
    """Installe les dépendances"""
    print_step("3", "Installation des dépendances...")
    
    # Déterminer le chemin Python dans l'environnement virtuel
    if os.name == 'nt':  # Windows
        python_path = "venv/Scripts/python"
        pip_path = "venv/Scripts/pip"
    else:  # Unix/Linux/Mac
        python_path = "venv/bin/python"
        pip_path = "venv/bin/pip"
    
    try:
        # Mise à jour de pip
        subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Installation des dépendances
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dépendances installées")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        sys.exit(1)

def setup_environment_file():
    """Configure le fichier d'environnement"""
    print_step("4", "Configuration du fichier d'environnement...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("⚠️ Fichier .env déjà existant")
        return
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Fichier .env créé à partir du template")
        print("⚠️ IMPORTANT: Configurez vos clés API dans .env")
        print("   - MISTRAL_API_KEY")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_KEY")
    else:
        print("⚠️ Template env.example non trouvé")
        create_basic_env_file()

def create_basic_env_file():
    """Crée un fichier .env basique"""
    env_content = """# QCM Medical Extraction System - Configuration
# ==============================================

# Mistral AI Configuration
MISTRAL_API_KEY=your_mistral_api_key_here

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Fichier .env basique créé")

def create_directories():
    """Crée les dossiers nécessaires"""
    print_step("5", "Création des dossiers...")
    
    directories = [
        "qcm_extraction/temp/pdfs",
        "qcm_extraction/temp/images", 
        "qcm_extraction/temp/outputs",
        "logs",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Dossiers créés")

def verify_installation():
    """Vérifie l'installation"""
    print_step("6", "Vérification de l'installation...")
    
    # Déterminer le chemin Python
    if os.name == 'nt':
        python_path = "venv/Scripts/python"
    else:
        python_path = "venv/bin/python"
    
    try:
        # Test d'import des modules principaux
        test_script = """
import sys
try:
    import requests
    import supabase
    import mistralai
    from PIL import Image
    import pdf2image
    print("✅ Tous les modules principaux importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)
"""
        
        result = subprocess.run([python_path, "-c", test_script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("❌ Erreur lors de la vérification:")
            print(result.stderr)
            
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de la vérification")

def print_next_steps():
    """Affiche les prochaines étapes"""
    print_header("Installation terminée!")
    
    print("\n📋 PROCHAINES ÉTAPES:")
    print("1. Configurez vos clés API dans le fichier .env")
    print("2. Exécutez le schéma de base de données dans Supabase:")
    print("   - Ouvrez database/schema.sql")
    print("   - Copiez/collez dans l'éditeur SQL de Supabase")
    print("3. Activez l'environnement virtuel:")
    
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("4. Testez l'installation:")
    print("   python clean_and_test_strict.py")
    
    print("\n🚀 UTILISATION:")
    print("   from qcm_extraction.extractor import QCMExtractor")
    print("   extractor = QCMExtractor()")
    print("   metadata = extractor.extract_metadata_from_path('url_du_pdf')")
    
    print("\n📚 DOCUMENTATION:")
    print("   Consultez README.md pour plus d'informations")

def main():
    """Fonction principale"""
    print_header("Setup QCM Medical Extraction System")
    
    try:
        check_python_version()
        create_virtual_environment()
        install_dependencies()
        setup_environment_file()
        create_directories()
        verify_installation()
        print_next_steps()
        
    except KeyboardInterrupt:
        print("\n❌ Installation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 