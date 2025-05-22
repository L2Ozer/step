import os
import argparse
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import urllib.parse

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
    parser.add_argument(
        "--skip-corrections",
        action="store_true",
        help="Ne pas extraire les corrections (réponses correctes)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forcer la réimportation même si le QCM existe déjà"
    )
    return parser

def process_qcm(url: str, skip_corrections: bool = False, force: bool = False) -> Dict[str, Any]:
    """Traite un QCM à partir de son URL."""
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        # Vérifier si le QCM existe déjà dans la base de données
        if not force:
            print(f"🔍 Vérification si le QCM existe déjà pour l'URL: {url}")
            # Extraire le nom de fichier de l'URL
            filename = Path(urllib.parse.unquote(url.split('/')[-1])).name
            
            # Extraire des informations du nom de fichier pour aider à la recherche
            parts = filename.split('-')
            if len(parts) >= 3:
                try:
                    # Essayer d'extraire l'UE et le type
                    ue_part = next((p for p in parts if p.startswith('ue')), None)
                    type_part = next((p for p in parts if p in ['correction', 'qcm', 'colle', 'cb']), None)
                    
                    if ue_part and type_part:
                        # Récupérer l'UE ID
                        ue_result = extractor.supabase.table("ue").select("id").ilike("numero", f"%{ue_part}%").execute()
                        
                        if ue_result.data:
                            ue_id = ue_result.data[0]["id"]
                            
                            # Rechercher les QCM correspondants
                            qcm_query = extractor.supabase.table("qcm").select("id").eq("ue_id", ue_id)
                            
                            # Ajouter des filtres supplémentaires si disponibles
                            if 'correction' in filename.lower():
                                qcm_query = qcm_query.like("type", "%correction%")
                            if 'colle' in filename.lower():
                                qcm_query = qcm_query.like("type", "%colle%")
                            if 'cb' in filename.lower() or 'concours' in filename.lower():
                                qcm_query = qcm_query.like("type", "%concours%")
                                
                            qcm_result = qcm_query.execute()
                            
                            if qcm_result.data:
                                qcm_id = qcm_result.data[0]["id"]
                                print(f"⚠️ Un QCM similaire a déjà été importé (ID: {qcm_id})")
                                
                                # Vérifier si des questions existent pour ce QCM
                                questions_query = extractor.supabase.table("questions").select("id").eq("qcm_id", qcm_id).execute()
                                
                                if questions_query.data:
                                    print(f"✅ {len(questions_query.data)} questions trouvées pour ce QCM")
                                    
                                    # Si demandé, mettre à jour les corrections
                                    if not skip_corrections:
                                        # Télécharger le PDF et extraire le Markdown
                                        pdf_path = extractor.download_pdf(url)
                                        markdown_path = extractor.convert_pdf_to_markdown(pdf_path, url)
                                        
                                        if markdown_path:
                                            with open(markdown_path, 'r', encoding='utf-8') as f:
                                                markdown_content = f.read()
                                            
                                            print(f"📑 Mise à jour des réponses correctes pour le QCM existant (ID: {qcm_id})...")
                                            extractor.extract_correct_answers(markdown_content, qcm_id)
                                    
                                    # Retourner les informations du QCM existant
                                    return {
                                        'success': True,
                                        'qcm_id': qcm_id,
                                        'existing': True,
                                        'metadata': {"filename": filename}
                                    }
                except Exception as e:
                    print(f"⚠️ Erreur lors de la vérification d'existence du QCM: {str(e)}")
                    # On continue l'importation en cas d'erreur de vérification
        
        # Extraire les métadonnées et traiter le QCM
        print(f"🚀 Lancement du traitement complet pour l'URL: {url}")
        processed_metadata = extractor.extract_metadata_from_path(url)
        
        if not processed_metadata:
            print("❌ Échec critique: Impossible d'obtenir les métadonnées initiales ou le QCM de base.")
            return {
                'success': False,
                'error': "Échec de l'extraction des métadonnées initiales ou de la conversion Markdown."
            }

        qcm_id_from_extraction = processed_metadata.get('qcm_db_id')
        
        if qcm_id_from_extraction:
            # Si on a un ID de QCM valide et que markdown_path existe, on peut extraire les corrections
            if not skip_corrections and 'markdown_path' in processed_metadata:
                markdown_path = processed_metadata['markdown_path']
                print(f"📑 Extraction des réponses correctes à partir du Markdown: {markdown_path}")
                
                # Lire le contenu du fichier Markdown
                try:
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                    
                    # Extraire les réponses correctes et mettre à jour la base de données
                    extractor.extract_correct_answers(markdown_content, qcm_id_from_extraction)
                except Exception as e:
                    print(f"⚠️ Erreur lors de l'extraction des réponses correctes: {str(e)}")
            elif skip_corrections:
                print("🔍 Extraction des réponses correctes ignorée (option --skip-corrections active)")
            else:
                print("⚠️ Impossible d'extraire les réponses correctes: chemin du fichier Markdown non trouvé")
            
            print(f"✅ Traitement du QCM (y compris questions/propositions) terminé. ID du QCM: {qcm_id_from_extraction}")
            return {
                'success': True,
                'qcm_id': qcm_id_from_extraction,
                'metadata': processed_metadata,
                'existing': False
            }
        else:
            print("❌ Échec lors du traitement du QCM ou de la sauvegarde de l'entité QCM principale.")
            print("   Les métadonnées de base pourraient avoir été extraites, mais l'enregistrement en BDD a pu échouer.")
            return {
                'success': False,
                'error': 'Échec de la sauvegarde du QCM principal dans la base de données ou ID manquant.',
                'metadata': processed_metadata
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
    
    result = process_qcm(args.pdf_url, skip_corrections=args.skip_corrections, force=args.force)
    
    if result["success"]:
        if result.get("existing", False):
            print("📚 QCM déjà existant en base de données, traitement terminé!")
        else:
            print("✨ Traitement terminé avec succès!")
    else:
        print(f"❌ Erreur: {result['error']}")
        exit(1)

if __name__ == "__main__":
    main() 