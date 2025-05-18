import os
import argparse
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from .database import Database
from .extractor import QCMExtractor
from .models import QCM, Question, Option, Image

def setup_argparse() -> argparse.ArgumentParser:
    """Configure le parseur d'arguments"""
    parser = argparse.ArgumentParser(description="Extraction et import de QCM vers Supabase")
    parser.add_argument(
        "pdf_url",
        help="URL du PDF à traiter"
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Extraire uniquement les métadonnées sans traiter le contenu"
    )
    return parser

def process_qcm(url: str) -> Dict[str, Any]:
    """Traite un QCM à partir de son URL."""
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        # Extraire les métadonnées et traiter le QCM (questions et propositions)
        # La méthode extract_metadata_from_path s'occupe maintenant de tout, 
        # y compris la sauvegarde du QCM, des questions et des propositions.
        # Elle retourne les métadonnées enrichies, incluant potentiellement 'qcm_db_id'.
        print(f"🚀 Lancement du traitement complet pour l'URL: {url}")
        processed_metadata = extractor.extract_metadata_from_path(url)
        
        if not processed_metadata:
            # Cela peut arriver si download_pdf échoue ou si la conversion markdown échoue.
            print("❌ Échec critique: Impossible d'obtenir les métadonnées initiales ou le QCM de base.")
            return {
                'success': False,
                'error': "Échec de l'extraction des métadonnées initiales ou de la conversion Markdown."
            }

        qcm_id_from_extraction = processed_metadata.get('qcm_db_id')
        
        if qcm_id_from_extraction:
            print(f"✅ Traitement du QCM (y compris questions/propositions) terminé. ID du QCM: {qcm_id_from_extraction}")
            return {
                'success': True,
                'qcm_id': qcm_id_from_extraction,
                'metadata': processed_metadata  # Retourne toutes les métadonnées collectées
            }
        else:
            # Ce cas peut survenir si la sauvegarde initiale du QCM dans save_to_supabase a échoué
            # ou si qcm_db_id n'a pas été ajouté correctement aux métadonnées retournées.
            # Les logs dans extractor.py devraient donner plus de détails.
            print("❌ Échec lors du traitement du QCM ou de la sauvegarde de l'entité QCM principale.")
            print("   Les métadonnées de base pourraient avoir été extraites, mais l'enregistrement en BDD a pu échouer.")
            # On retourne quand même les métadonnées si elles existent, pour le débogage.
            return {
                'success': False,
                'error': 'Échec de la sauvegarde du QCM principal dans la base de données ou ID manquant.',
                'metadata': processed_metadata # peut contenir des infos utiles même en cas d'échec partiel
            }
            
    except Exception as e:
        import traceback
        print(f"❌ Erreur majeure imprévue lors du traitement du QCM: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': f"Erreur majeure: {str(e)}"
        }

def main():
    """Point d'entrée principal"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    result = process_qcm(args.pdf_url)
    
    if result["success"]:
        print("✨ Traitement terminé avec succès!")
    else:
        print(f"❌ Erreur: {result['error']}")
        exit(1)

if __name__ == "__main__":
    main() 