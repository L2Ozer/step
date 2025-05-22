#!/usr/bin/env python3
"""
Script pour nettoyer les QCM dupliqués dans la base de données Supabase
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, List, Any
from datetime import datetime
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_duplicates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_argparse() -> argparse.ArgumentParser:
    """Configure le parseur d'arguments"""
    parser = argparse.ArgumentParser(description="Outil de nettoyage des QCM dupliqués")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (n'effectue aucune modification)"
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Supprimer les QCM dupliqués au lieu de les fusionner"
    )
    return parser

def find_duplicate_qcms(supabase: Client) -> Dict[str, List[Dict[str, Any]]]:
    """Trouve les QCM dupliqués par nom de fichier"""
    logger.info("Recherche des QCM dupliqués...")
    
    # Récupérer tous les QCM
    result = supabase.table("qcm").select("id", "ue_id", "type", "annee", "metadata", "created_at").execute()
    if not result.data:
        logger.info("Aucun QCM trouvé dans la base de données")
        return {}
    
    # Grouper par nom de fichier
    qcms_by_filename = {}
    for qcm in result.data:
        metadata = qcm.get("metadata", {})
        if not metadata or not isinstance(metadata, dict):
            continue
            
        filename = metadata.get("filename")
        if not filename:
            continue
            
        if filename not in qcms_by_filename:
            qcms_by_filename[filename] = []
        qcms_by_filename[filename].append(qcm)
    
    # Filtrer pour ne garder que les groupes avec plus d'un QCM
    duplicate_qcms = {filename: qcms for filename, qcms in qcms_by_filename.items() if len(qcms) > 1}
    
    if duplicate_qcms:
        logger.info(f"Trouvé {len(duplicate_qcms)} fichiers PDF avec QCM dupliqués")
        for filename, qcms in duplicate_qcms.items():
            logger.info(f"- {filename}: {len(qcms)} entrées (IDs: {', '.join(str(q['id']) for q in qcms)})")
    else:
        logger.info("Aucun QCM dupliqué trouvé")
    
    return duplicate_qcms

def clean_duplicate_qcms(supabase: Client, duplicates: Dict[str, List[Dict[str, Any]]], 
                         dry_run: bool = True, force_delete: bool = False) -> None:
    """Nettoie les QCM dupliqués en gardant le plus récent et en fusionnant/supprimant les autres"""
    if not duplicates:
        logger.info("Aucun QCM dupliqué à nettoyer")
        return
    
    logger.info(f"Nettoyage de {len(duplicates)} groupes de QCM dupliqués (dry_run: {dry_run}, force_delete: {force_delete})")
    
    for filename, qcms in duplicates.items():
        logger.info(f"Traitement des doublons pour {filename}")
        
        # Trier les QCM par date de création (le plus récent en premier)
        sorted_qcms = sorted(qcms, key=lambda q: q.get("created_at", ""), reverse=True)
        
        # Garder le QCM le plus récent
        qcm_to_keep = sorted_qcms[0]
        qcms_to_clean = sorted_qcms[1:]
        
        logger.info(f"  QCM à conserver: ID {qcm_to_keep['id']}")
        logger.info(f"  QCMs à traiter: {len(qcms_to_clean)} entrées")
        
        for qcm_to_clean in qcms_to_clean:
            qcm_id = qcm_to_clean["id"]
            logger.info(f"  - Traitement du QCM ID {qcm_id}")
            
            # Récupérer les questions associées à ce QCM
            questions_result = supabase.table("questions").select("id", "numero").eq("qcm_id", qcm_id).execute()
            
            if not questions_result.data:
                logger.info(f"    Aucune question trouvée pour ce QCM")
                if not dry_run:
                    if force_delete:
                        logger.info(f"    Suppression du QCM ID {qcm_id}")
                        supabase.table("qcm").delete().eq("id", qcm_id).execute()
                    else:
                        logger.info(f"    Mise à jour de la métadonnée pour marquer comme dupliqué")
                        metadata = qcm_to_clean.get("metadata", {})
                        if not metadata:
                            metadata = {}
                        metadata["is_duplicate"] = True
                        metadata["original_qcm_id"] = qcm_to_keep["id"]
                        metadata["cleaned_at"] = datetime.now().isoformat()
                        supabase.table("qcm").update({"metadata": metadata}).eq("id", qcm_id).execute()
                continue
            
            # Pour chaque question, récupérer ses réponses
            questions_map = {q["numero"]: q["id"] for q in questions_result.data}
            logger.info(f"    {len(questions_map)} questions trouvées")
            
            # Pour chaque question, vérifier si elle existe dans le QCM à conserver
            main_questions_result = supabase.table("questions").select("id", "numero").eq("qcm_id", qcm_to_keep["id"]).execute()
            
            if not main_questions_result.data:
                logger.info(f"    Le QCM principal n'a pas de questions. Déplacement des questions...")
                if not dry_run:
                    # Déplacer toutes les questions vers le QCM principal
                    for q_id in [q["id"] for q in questions_result.data]:
                        supabase.table("questions").update({"qcm_id": qcm_to_keep["id"]}).eq("id", q_id).execute()
                    
                    # Supprimer ou marquer le QCM dupliqué
                    if force_delete:
                        logger.info(f"    Suppression du QCM ID {qcm_id}")
                        supabase.table("qcm").delete().eq("id", qcm_id).execute()
                    else:
                        logger.info(f"    Mise à jour de la métadonnée pour marquer comme dupliqué")
                        metadata = qcm_to_clean.get("metadata", {})
                        if not metadata:
                            metadata = {}
                        metadata["is_duplicate"] = True
                        metadata["original_qcm_id"] = qcm_to_keep["id"]
                        metadata["cleaned_at"] = datetime.now().isoformat()
                        supabase.table("qcm").update({"metadata": metadata}).eq("id", qcm_id).execute()
                continue
            
            # Cartographier les questions du QCM principal
            main_questions_map = {q["numero"]: q["id"] for q in main_questions_result.data}
            
            # Pour chaque question du QCM dupliqué
            for numero, question_id in questions_map.items():
                # Si la question existe déjà dans le QCM principal
                if numero in main_questions_map:
                    main_question_id = main_questions_map[numero]
                    logger.info(f"    Question {numero} existe déjà dans le QCM principal (ID: {main_question_id})")
                    
                    # Vérifier les réponses
                    responses_result = supabase.table("reponses").select("id", "lettre", "est_correcte").eq("question_id", question_id).execute()
                    if responses_result.data:
                        logger.info(f"    Vérification de {len(responses_result.data)} réponses pour la question {numero}")
                        
                        # Récupérer les réponses de la question principale
                        main_responses_result = supabase.table("reponses").select("id", "lettre", "est_correcte").eq("question_id", main_question_id).execute()
                        
                        # Si la question principale n'a pas de réponses mais la dupliquée en a
                        if not main_responses_result.data and responses_result.data:
                            logger.info(f"    Déplacement des réponses vers la question principale")
                            if not dry_run:
                                for response in responses_result.data:
                                    # Mettre à jour question_id pour les réponses
                                    supabase.table("reponses").update({"question_id": main_question_id}).eq("id", response["id"]).execute()
                                
                        # Si les deux questions ont des réponses, mettre à jour est_correcte si nécessaire
                        elif main_responses_result.data:
                            main_responses_map = {r["lettre"]: (r["id"], r["est_correcte"]) for r in main_responses_result.data}
                            
                            for response in responses_result.data:
                                lettre = response["lettre"]
                                est_correcte = response["est_correcte"]
                                
                                if lettre in main_responses_map:
                                    main_resp_id, main_est_correcte = main_responses_map[lettre]
                                    
                                    # Si la réponse dupliquée a est_correcte=True mais pas la principale
                                    if est_correcte and not main_est_correcte:
                                        logger.info(f"    Mise à jour de est_correcte pour la réponse {lettre} de la question {numero}")
                                        if not dry_run:
                                            supabase.table("reponses").update({"est_correcte": True}).eq("id", main_resp_id).execute()
                    
                    # Supprimer la question dupliquée si nécessaire
                    if not dry_run and force_delete:
                        logger.info(f"    Suppression de la question dupliquée {numero} (ID: {question_id})")
                        # Supprimer d'abord toutes les réponses
                        supabase.table("reponses").delete().eq("question_id", question_id).execute()
                        # Puis la question
                        supabase.table("questions").delete().eq("id", question_id).execute()
                else:
                    # La question n'existe pas dans le QCM principal, déplacer
                    logger.info(f"    Déplacement de la question {numero} vers le QCM principal")
                    if not dry_run:
                        supabase.table("questions").update({"qcm_id": qcm_to_keep["id"]}).eq("id", question_id).execute()
            
            # Une fois toutes les questions traitées, supprimer ou marquer le QCM dupliqué
            if not dry_run:
                if force_delete:
                    logger.info(f"    Suppression du QCM ID {qcm_id}")
                    supabase.table("qcm").delete().eq("id", qcm_id).execute()
                else:
                    logger.info(f"    Mise à jour de la métadonnée pour marquer comme dupliqué")
                    metadata = qcm_to_clean.get("metadata", {})
                    if not metadata:
                        metadata = {}
                    metadata["is_duplicate"] = True
                    metadata["original_qcm_id"] = qcm_to_keep["id"]
                    metadata["cleaned_at"] = datetime.now().isoformat()
                    supabase.table("qcm").update({"metadata": metadata}).eq("id", qcm_id).execute()
    
    logger.info("Nettoyage terminé")

def main():
    """Point d'entrée principal"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    load_dotenv()
    
    # Vérifier les variables d'environnement requises
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Variables d'environnement SUPABASE_URL et SUPABASE_KEY requises")
        sys.exit(1)
    
    try:
        # Connexion à Supabase
        supabase = create_client(supabase_url, supabase_key)
        
        # Trouver les QCM dupliqués
        duplicates = find_duplicate_qcms(supabase)
        
        # Nettoyer les doublons
        if duplicates:
            if args.dry_run:
                logger.info("Mode simulation activé - aucune modification ne sera effectuée")
            
            clean_duplicate_qcms(
                supabase, 
                duplicates, 
                dry_run=args.dry_run, 
                force_delete=args.force_delete
            )
            
            if args.dry_run:
                logger.info("Pour appliquer les modifications, relancez sans l'option --dry-run")
        else:
            logger.info("Aucun nettoyage nécessaire")
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des QCM dupliqués: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 