#!/usr/bin/env python3
"""
Script pour tester l'extraction des réponses correctes à partir d'un QCM
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from qcm_extraction.extractor import QCMExtractor
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_correct_answers.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_argparse() -> argparse.ArgumentParser:
    """Configure le parseur d'arguments"""
    parser = argparse.ArgumentParser(description="Test d'extraction des réponses correctes")
    parser.add_argument(
        "qcm_id",
        help="ID du QCM dans la base de données Supabase",
        type=int
    )
    parser.add_argument(
        "markdown_path",
        help="Chemin vers le fichier Markdown contenant le QCM et les corrections"
    )
    return parser

def main():
    # Récupérer le QCM ID depuis la ligne de commande ou utiliser une valeur par défaut
    qcm_id = 1  # L'ID du QCM que nous venons de traiter
    
    # Initialiser l'extracteur
    extractor = QCMExtractor()
    
    # Chemin vers le fichier Markdown généré
    temp_outputs_dir = "qcm_extraction/temp/outputs"
    
    # Rechercher le fichier Markdown pour ce QCM
    markdown_path = None
    for root, dirs, files in os.walk(temp_outputs_dir):
        for dir_name in dirs:
            content_path = os.path.join(root, dir_name, "content.md")
            if os.path.exists(content_path):
                print(f"Fichier Markdown trouvé: {content_path}")
                # Vérifier si ce fichier correspond au QCM ID
                try:
                    # Vérifier la présence du fichier metadata.json
                    metadata_path = os.path.join(root, dir_name, "metadata.json")
                    if os.path.exists(metadata_path):
                        import json
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            if metadata.get("qcm_db_id") == qcm_id:
                                markdown_path = content_path
                                print(f"✅ Markdown correspondant au QCM ID {qcm_id} trouvé!")
                                break
                except Exception as e:
                    print(f"⚠️ Erreur lors de la vérification du fichier: {str(e)}")
        
        if markdown_path:
            break
    
    if not markdown_path:
        # Si aucun fichier metadata.json n'a le QCM ID, utiliser le premier fichier trouvé
        for root, dirs, files in os.walk(temp_outputs_dir):
            for dir_name in dirs:
                content_path = os.path.join(root, dir_name, "content.md")
                if os.path.exists(content_path):
                    markdown_path = content_path
                    print(f"Utilisation du premier fichier Markdown trouvé: {markdown_path}")
                    break
            if markdown_path:
                break
    
    if not markdown_path:
        print("❌ Aucun fichier Markdown trouvé. Assurez-vous d'avoir exécuté l'extraction complète d'abord.")
        return
    
    # Lire le contenu du Markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    print(f"\n===== TEST D'EXTRACTION DES RÉPONSES CORRECTES POUR LE QCM ID {qcm_id} =====")
    print(f"Fichier Markdown utilisé: {markdown_path}")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Exécuter l'extraction des réponses correctes
    updates_count = extractor.extract_correct_answers(markdown_content, qcm_id)
    
    # Calculer le temps d'exécution
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n===== RÉSULTAT DU TEST =====")
    print(f"Temps d'exécution: {duration:.2f} secondes")
    
    if updates_count is None:
        print("❌ TEST ÉCHOUÉ: La méthode a retourné None. Aucune donnée trouvée dans Supabase.")
    else:
        print(f"Nombre de mises à jour effectuées: {updates_count}")
        if updates_count > 0:
            print("✅ TEST RÉUSSI: Des réponses correctes ont été identifiées et mises à jour dans Supabase.")
        else:
            print("⚠️ TEST ÉCHOUÉ: Aucune réponse n'a été mise à jour. Vérifiez les logs pour plus de détails.")

if __name__ == "__main__":
    main() 