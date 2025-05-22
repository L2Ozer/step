#!/usr/bin/env python3

import os
import sys
from qcm_extraction.extractor import QCMExtractor

def main():
    # URL du PDF à utiliser
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE1/QCM/ue1-correction-colle-2-s42-2021-49647.pdf"
    
    print(f"Extraction du QCM à partir de: {pdf_url}")
    
    # Initialiser l'extracteur
    extractor = QCMExtractor()
    
    # Extraire les métadonnées et créer le QCM
    result = extractor.extract_metadata_from_path(pdf_url)
    
    if not result:
        print("❌ Erreur lors de l'extraction des métadonnées du PDF")
        return 1
    
    qcm_id = result.get('qcm_db_id')
    
    if not qcm_id:
        print("❌ Aucun ID de QCM n'a été retourné après l'extraction")
        return 1
    
    print(f"✅ QCM créé avec l'ID: {qcm_id}")
    print(f"✅ Type: {result.get('type')}")
    print(f"✅ Année: {result.get('annee')}")
    print(f"✅ UE: {result.get('ue')}")
    
    # Obtenir le chemin du fichier Markdown généré
    markdown_path = result.get('markdown_path')
    
    if not markdown_path or not os.path.exists(markdown_path):
        print("❌ Fichier Markdown non trouvé")
        return 1
    
    print(f"✅ Fichier Markdown généré: {markdown_path}")
    
    # Lire le contenu Markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    # Tester l'extraction des réponses correctes
    print("\n===== TEST DE L'EXTRACTION DES RÉPONSES CORRECTES =====")
    updates_count = extractor.extract_correct_answers(markdown_content, qcm_id)
    
    if updates_count is None:
        print("❌ Échec: Aucune mise à jour effectuée")
        return 1
    
    print(f"✅ Nombre de mises à jour effectuées: {updates_count}")
    
    # Vérifier les résultats dans la base de données
    print("\n===== VÉRIFICATION DES RÉPONSES CORRECTES DANS SUPABASE =====")
    
    # Obtenir toutes les questions de ce QCM
    questions_result = extractor.supabase.table("questions").select("id", "numero").eq("qcm_id", qcm_id).execute()
    
    if not questions_result.data:
        print("❌ Aucune question trouvée pour ce QCM")
        return 1
    
    for question in questions_result.data[:5]:  # Afficher seulement les 5 premières pour éviter trop de sortie
        q_id = question.get("id")
        q_num = question.get("numero")
        
        # Obtenir les réponses pour cette question
        responses = extractor.supabase.table("reponses").select("lettre", "est_correcte").eq("question_id", q_id).execute()
        
        if responses.data:
            correct_responses = [r.get("lettre") for r in responses.data if r.get("est_correcte")]
            print(f"Question {q_num}: Réponses correctes = {', '.join(correct_responses) if correct_responses else 'Aucune'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 