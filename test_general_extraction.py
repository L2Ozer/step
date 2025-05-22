#!/usr/bin/env python3
import os
import argparse
import logging
from dotenv import load_dotenv
from qcm_extraction.extractor import QCMExtractor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_general_extraction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Script de test pour l'approche générale d'extraction de QCM"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Vérifier les variables d'environnement requises
    required_env_vars = ["MISTRAL_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        exit(1)
    
    # Parsing des arguments
    parser = argparse.ArgumentParser(description="Test de l'approche générale d'extraction de QCM")
    parser.add_argument("pdf_url", help="URL du PDF à traiter")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug avec plus de logs")
    args = parser.parse_args()
    
    # Ajuster le niveau de logging si mode debug
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    
    try:
        # Initialiser l'extracteur
        logger.info("Initialisation de l'extracteur")
        extractor = QCMExtractor()
        
        # Traiter le PDF
        logger.info(f"Traitement du PDF: {args.pdf_url}")
        metadata = extractor.extract_metadata_from_path(args.pdf_url)
        
        if metadata and metadata.get("qcm_db_id"):
            logger.info(f"Traitement réussi! QCM ID: {metadata['qcm_db_id']}")
            
            # Afficher les statistiques
            if "questions_count" in metadata:
                logger.info(f"Nombre de questions extraites: {metadata['questions_count']}")
            if "propositions_count" in metadata:
                logger.info(f"Nombre de propositions extraites: {metadata['propositions_count']}")
                
            logger.info("Vérifiez les logs complets dans test_general_extraction.log")
        else:
            logger.error("Échec du traitement du PDF")
            exit(1)
    
    except Exception as e:
        import traceback
        logger.error(f"Erreur lors de l'exécution: {str(e)}")
        logger.debug(traceback.format_exc())
        exit(1)

if __name__ == "__main__":
    main() 