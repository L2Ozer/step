from qcm_extraction.extractor import QCMExtractor
import base64
import json
import os
import re

# QCM ID spécifique à vérifier
QCM_ID = 1

def verify_correct_answers_with_vision(image_path, question_num):
    """
    Utilise l'API vision pour vérifier les réponses correctes à une question spécifique.
    """
    try:
        print(f"🔍 Analyse de l'image {image_path} pour la question {question_num}...")
        
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        # Encoder l'image en base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Construire les messages pour l'API vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": f"""Analyse cette image d'un QCM médical et identifie les RÉPONSES CORRECTES pour la Question {question_num} uniquement.

CONSIGNES PRÉCISES:
1. Cherche UNIQUEMENT la Question {question_num} et ses réponses correctes
2. Cherche des indications comme "Réponses justes", "Réponses correctes", "Bonnes réponses", etc.
3. Tu peux aussi repérer les réponses marquées individuellement comme "Vrai" ou "Faux" 
4. Si plusieurs réponses sont correctes, liste-les toutes (A, B, C, D, E)

RÉPONDS UNIQUEMENT AU FORMAT JSON:
{{
  "question_num": {question_num},
  "correct_answers": ["A", "C", "E"],  // Liste des lettres correctes uniquement (A, B, C, D, E)
  "confidence": 0.95,  // Ta confiance dans ta réponse de 0 à 1
  "explanation": "J'ai trouvé ces réponses car..."  // Brève explication
}}

N'ajoute AUCUN texte avant ou après ce JSON."""
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }
        ]
        
        # Appeler l'API vision
        response = extractor._call_api_with_retry(
            extractor.client.chat.complete,
            model="mistral-large-latest",  # Utiliser le modèle large qui a de meilleures capacités de vision
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        if response is None:
            print(f"❌ Échec de l'appel API vision pour la question {question_num}")
            return None
        
        try:
            # Extraire le JSON de la réponse
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            # Vérifier que la structure du résultat est correcte
            if "question_num" in result and "correct_answers" in result:
                verified_num = result["question_num"]
                
                # Vérifier que la réponse concerne bien la question demandée
                if verified_num == question_num:
                    correct_answers = result["correct_answers"]
                    confidence = result.get("confidence", 0)
                    explanation = result.get("explanation", "")
                    
                    print(f"✅ Réponses identifiées par vision pour Q{question_num}: {', '.join(correct_answers)} (confiance: {confidence:.2f})")
                    print(f"ℹ️ Explication: {explanation}")
                    
                    return result
                else:
                    print(f"⚠️ La réponse concerne la question {verified_num}, mais nous cherchions la question {question_num}")
            else:
                print(f"⚠️ Réponse API mal formatée pour la question {question_num}")
                
        except json.JSONDecodeError:
            print(f"⚠️ Impossible de décoder la réponse JSON pour la question {question_num}")
            
        return None
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des réponses avec vision: {str(e)}")
        return None

def update_correct_answers(qcm_id, question_num, correct_letters):
    """
    Met à jour les réponses correctes pour une question spécifique.
    """
    extractor = QCMExtractor()
    
    # Récupérer l'ID de la question
    questions = extractor.supabase.table('questions').select('id').eq('qcm_id', qcm_id).eq('numero', question_num).execute()
    
    if not questions.data:
        print(f"⚠️ Question {question_num} non trouvée dans la base de données")
        return False
    
    question_id = questions.data[0]['id']
    
    # Récupérer toutes les réponses pour cette question
    responses = extractor.supabase.table('reponses').select('id', 'lettre').eq('question_id', question_id).execute()
    
    if not responses.data:
        print(f"⚠️ Aucune réponse trouvée pour la question {question_num}")
        return False
    
    # Mettre à jour chaque réponse
    update_count = 0
    for response in responses.data:
        response_id = response['id']
        lettre = response['lettre']
        
        # Déterminer si cette réponse est correcte
        est_correcte = lettre in correct_letters
        
        # Mettre à jour dans Supabase
        result = extractor.supabase.table('reponses').update({"est_correcte": est_correcte}).eq('id', response_id).execute()
        
        if result.data:
            update_count += 1
            status = "correcte" if est_correcte else "incorrecte"
            print(f"✅ Proposition {lettre} marquée comme {status}")
    
    print(f"✅ {update_count} propositions mises à jour pour la question {question_num}")
    return update_count > 0

def main():
    print(f"🚀 Vérification et correction des réponses pour le QCM ID {QCM_ID}...")
    
    # Initialiser l'extracteur
    extractor = QCMExtractor()
    
    # Télécharger le PDF si nécessaire
    qcm_info = extractor.supabase.table('qcm').select('*').eq('id', QCM_ID).execute()
    if not qcm_info.data:
        print(f"❌ QCM ID {QCM_ID} non trouvé dans la base de données")
        return
    
    # Récupérer les images des pages pour ce QCM
    # Trouver le chemin des images en fonction du QCM
    pdf_files = [f for f in os.listdir("qcm_extraction/temp/pdfs") if os.path.isdir(os.path.join("qcm_extraction/temp/pdfs", f))]
    
    for pdf_folder in pdf_files:
        images_dir = f"qcm_extraction/temp/images/{pdf_folder}"
        if os.path.exists(images_dir):
            # Vérifier si ce dossier correspond au QCM 1
            # Pour cela, on vérifie si un fichier dans le dossier outputs contient les métadonnées de ce QCM
            metadata_path = f"qcm_extraction/temp/outputs/{pdf_folder}/metadata.json"
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        # Vérifier si ce QCM est celui qui nous intéresse
                        if "qcm_db_id" in metadata and metadata["qcm_db_id"] == QCM_ID:
                            print(f"✅ Trouvé les images pour le QCM ID {QCM_ID} dans {images_dir}")
                            
                            # Vérifier la question 1 avec les pages 1-4
                            question_num = 1
                            for page_num in range(1, 6):  # Pages 1 à 5
                                image_path = f"{images_dir}/page_{page_num}.jpg"
                                if os.path.exists(image_path):
                                    print(f"🔍 Vérification de la question {question_num} avec la page {page_num}...")
                                    result = verify_correct_answers_with_vision(image_path, question_num)
                                    
                                    if result and "correct_answers" in result:
                                        correct_letters = result["correct_answers"]
                                        print(f"✅ Réponses correctes pour la question {question_num}: {', '.join(correct_letters)}")
                                        
                                        # Mettre à jour dans la base de données
                                        update_correct_answers(QCM_ID, question_num, correct_letters)
                                        break
                except Exception as e:
                    print(f"❌ Erreur lors de la lecture des métadonnées: {str(e)}")
    
    # Si on n'a pas trouvé de dossier pour ce QCM, afficher un message d'erreur
    print("\n🔍 Vérification de l'état actuel de la question 1:")
    questions = extractor.supabase.table('questions').select('id').eq('qcm_id', QCM_ID).eq('numero', 1).execute()
    if questions.data:
        q_id = questions.data[0]['id']
        reponses = extractor.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
        correct_letters = []
        for r in reponses.data:
            status = "✓" if r['est_correcte'] else "✗"
            print(f"Proposition {r['lettre']}: {status} {r['contenu']}")
            if r['est_correcte']:
                correct_letters.append(r['lettre'])
        
        print(f"\n✅ Bonnes réponses actuelles: {', '.join(correct_letters)}")

if __name__ == "__main__":
    main() 