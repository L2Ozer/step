#!/usr/bin/env python3

import os
import sys
import time
from qcm_extraction.extractor import QCMExtractor

def main():
    # URL du PDF à utiliser
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE1/QCM/ue1-correction-colle-2-s42-2021-49647.pdf"
    
    print(f"Test avec le PDF: {pdf_url}")
    
    # Initialiser l'extracteur
    extractor = QCMExtractor()
    
    # Vérifier si un QCM existe déjà pour ce PDF
    # Extraire l'information du nom du fichier
    filename = pdf_url.split('/')[-1]
    qcm_type = "Colle" if "colle" in filename.lower() else "Concours Blanc"
    ue_match = "UE1" if "ue1" in filename.lower() else None
    
    print(f"Recherche d'un QCM existant pour: {filename}")
    
    # Chercher dans la base de données
    existing_qcm = None
    
    try:
        # Chercher dans la table QCM
        qcms = extractor.supabase.table('qcm').select('*').execute()
        
        if qcms.data:
            print(f"Nombre de QCMs trouvés: {len(qcms.data)}")
            
            # Afficher les 3 premiers QCMs pour information
            for i, qcm in enumerate(qcms.data[:3]):
                print(f"QCM {i+1}: ID={qcm.get('id')}, Type={qcm.get('type')}, Année={qcm.get('annee')}")
            
            # Utiliser le premier QCM pour le test
            if qcms.data:
                existing_qcm = qcms.data[0]
                print(f"QCM sélectionné pour le test: ID={existing_qcm.get('id')}")
        else:
            print("Aucun QCM trouvé dans la base de données")
    except Exception as e:
        print(f"Erreur lors de la recherche de QCMs: {str(e)}")
    
    if not existing_qcm:
        print("❌ Aucun QCM existant trouvé pour le test")
        
        # Si aucun QCM n'est trouvé, on peut créer un en extrayant les métadonnées du PDF
        print("Création d'un nouveau QCM à partir du PDF...")
        result = extractor.extract_metadata_from_path(pdf_url)
        
        if not result or not result.get('qcm_db_id'):
            print("❌ Échec de la création du QCM")
            return 1
            
        qcm_id = result.get('qcm_db_id')
        print(f"✅ Nouveau QCM créé avec l'ID: {qcm_id}")
    else:
        qcm_id = existing_qcm.get('id')
    
    # Vérifier si des questions existent pour ce QCM
    questions = extractor.supabase.table('questions').select('id', 'numero').eq('qcm_id', qcm_id).execute()
    
    if not questions.data:
        print(f"❌ Aucune question trouvée pour le QCM ID {qcm_id}")
        return 1
    
    print(f"✅ {len(questions.data)} questions trouvées pour ce QCM")
    
    # Trouver le fichier Markdown correspondant ou générer un nouveau
    markdown_path = None
    
    # Chercher dans les dossiers de sortie
    base_dir = os.path.join('qcm_extraction', 'temp', 'outputs')
    if os.path.exists(base_dir):
        for folder in os.listdir(base_dir):
            potential_path = os.path.join(base_dir, folder, 'content.md')
            if os.path.exists(potential_path):
                # Vérifier si ce fichier correspond au QCM
                print(f"Fichier Markdown trouvé: {potential_path}")
                markdown_path = potential_path
                break
    
    # Si aucun fichier Markdown n'est trouvé, générer un nouveau
    if not markdown_path:
        print("Génération d'un nouveau fichier Markdown à partir du PDF...")
        pdf_downloaded = extractor.download_pdf(pdf_url)
        markdown_path = extractor.convert_pdf_to_markdown(pdf_downloaded, pdf_url)
        
        if not markdown_path:
            print("❌ Échec de la génération du fichier Markdown")
            return 1
            
        print(f"✅ Nouveau fichier Markdown généré: {markdown_path}")
    
    # Lire le contenu Markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    # Réinitialiser les réponses correctes (mettre tout à False) pour le test
    print("\n===== RÉINITIALISATION DES RÉPONSES CORRECTES =====")
    for question in questions.data:
        q_id = question.get('id')
        try:
            extractor.supabase.table('reponses').update({'est_correcte': False}).eq('question_id', q_id).execute()
        except Exception as e:
            print(f"Erreur lors de la réinitialisation des réponses pour la question {question.get('numero')}: {str(e)}")
    
    print("✅ Toutes les réponses ont été réinitialisées à FALSE")
    
    # Laisser un peu de temps pour que les mises à jour soient effectuées
    time.sleep(2)
    
    # Tester l'extraction des réponses correctes
    print("\n===== TEST DE L'EXTRACTION DES RÉPONSES CORRECTES =====")
    updates_count = extractor.extract_correct_answers(markdown_content, qcm_id)
    
    if updates_count is None or updates_count == 0:
        print("⚠️ Aucune mise à jour effectuée. Vérification du résultat...")
    else:
        print(f"✅ Nombre de mises à jour effectuées: {updates_count}")
    
    # Vérifier les résultats dans la base de données
    print("\n===== VÉRIFICATION DES RÉPONSES CORRECTES DANS SUPABASE =====")
    
    # Obtenir les statistiques des réponses
    correct_answers_count = 0
    questions_with_correct_answers = 0
    
    for question in questions.data:
        q_id = question.get('id')
        q_num = question.get('numero')
        
        # Obtenir les réponses pour cette question
        responses = extractor.supabase.table('reponses').select('lettre', 'est_correcte').eq('question_id', q_id).execute()
        
        if responses.data:
            correct_responses = [r.get('lettre') for r in responses.data if r.get('est_correcte')]
            correct_answers_count += len(correct_responses)
            
            if correct_responses:
                questions_with_correct_answers += 1
                print(f"Question {q_num}: Réponses correctes = {', '.join(correct_responses)}")
            else:
                print(f"Question {q_num}: Aucune réponse correcte")
    
    print(f"\n===== RÉSULTATS FINAUX =====")
    print(f"Total des questions: {len(questions.data)}")
    print(f"Questions avec au moins une réponse correcte: {questions_with_correct_answers}")
    print(f"Pourcentage de questions avec réponses correctes: {(questions_with_correct_answers/len(questions.data))*100:.1f}%")
    print(f"Nombre total de réponses correctes: {correct_answers_count}")
    
    if questions_with_correct_answers > 0:
        print("✅ TEST RÉUSSI: Des réponses correctes ont été identifiées")
        return 0
    else:
        print("❌ TEST ÉCHOUÉ: Aucune réponse correcte n'a été identifiée")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 