import os
import json
import base64
import argparse
import glob
from supabase import create_client
from dotenv import load_dotenv
from mistralai import Mistral, UserMessage

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion Supabase et Mistral
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
mistral_api_key = os.getenv('MISTRAL_API_KEY')

# Initialiser les clients
supabase = create_client(supabase_url, supabase_key)
mistral = Mistral(api_key=mistral_api_key)

def verify_with_vision(image_path, question_num):
    """
    Utilise l'API vision de Mistral pour vérifier les réponses correctes.
    """
    print(f"🔍 Analyse de l'image {image_path} pour la question {question_num}...")
    
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
    try:
        response = mistral.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
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
                
                return correct_answers
            else:
                print(f"⚠️ La réponse concerne la question {verified_num}, mais nous cherchions la question {question_num}")
        else:
            print(f"⚠️ Réponse API mal formatée pour la question {question_num}")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'appel API vision: {str(e)}")
        
    return None

def update_correct_answers(qcm_id, question_num, correct_letters):
    """
    Met à jour les réponses correctes pour une question spécifique.
    """
    # Récupérer l'ID de la question
    questions = supabase.table('questions').select('id').eq('qcm_id', qcm_id).eq('numero', question_num).execute()
    
    if not questions.data:
        print(f"⚠️ Question {question_num} non trouvée pour le QCM {qcm_id}")
        return False
    
    question_id = questions.data[0]['id']
    
    # Récupérer les propositions actuelles
    reponses = supabase.table('reponses').select('*').eq('question_id', question_id).execute()
    
    if not reponses.data:
        print(f"⚠️ Aucune proposition trouvée pour la question {question_num}")
        return False
    
    print("📊 Propositions actuelles:")
    current_correct = []
    for r in reponses.data:
        status = "✓" if r['est_correcte'] else "✗"
        print(f"Proposition {r['lettre']}: {status} {r['contenu']}")
        if r['est_correcte']:
            current_correct.append(r['lettre'])
    
    print(f"ℹ️ Réponses actuellement marquées comme correctes: {', '.join(sorted(current_correct))}")
    print(f"ℹ️ Nouvelles réponses correctes à appliquer: {', '.join(sorted(correct_letters))}")
    
    # Demander confirmation avant de mettre à jour
    confirm = input("Confirmer la mise à jour? (o/n): ").lower()
    if confirm != 'o':
        print("❌ Mise à jour annulée")
        return False
    
    # Mettre à jour les propositions
    updates = []
    for r in reponses.data:
        r_id = r['id']
        lettre = r['lettre']
        est_correcte = lettre in correct_letters
        
        # Mettre à jour dans Supabase
        result = supabase.table('reponses').update({"est_correcte": est_correcte}).eq('id', r_id).execute()
        
        if result.data:
            status = "correcte" if est_correcte else "incorrecte"
            print(f"✅ Proposition {lettre} mise à jour comme {status}")
            updates.append(r_id)
    
    print(f"✅ {len(updates)} propositions mises à jour")
    return True

def find_qcm_images(qcm_id):
    """
    Trouve les images associées à un QCM spécifique.
    """
    # Vérifier que le QCM existe
    qcm_info = supabase.table('qcm').select('*').eq('id', qcm_id).execute()
    if not qcm_info.data:
        print(f"❌ QCM ID {qcm_id} non trouvé dans la base de données")
        return None
    
    # Chercher dans tous les dossiers PDF disponibles
    pdf_folders = [d for d in os.listdir("qcm_extraction/temp/pdfs") if os.path.isdir(os.path.join("qcm_extraction/temp/pdfs", d))]
    
    for pdf_folder in pdf_folders:
        # Vérifier si les métadonnées correspondent au QCM ID
        metadata_path = f"qcm_extraction/temp/outputs/{pdf_folder}/metadata.json"
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    # Vérifier si ce QCM est celui qui nous intéresse
                    if "qcm_db_id" in metadata and metadata["qcm_db_id"] == qcm_id:
                        images_dir = f"qcm_extraction/temp/images/{pdf_folder}"
                        if os.path.exists(images_dir):
                            return images_dir
            except Exception as e:
                print(f"⚠️ Erreur lors de la lecture des métadonnées pour {pdf_folder}: {str(e)}")
    
    # Si on n'a pas trouvé par les métadonnées, chercher dans tous les dossiers d'images
    images_folders = glob.glob("qcm_extraction/temp/images/*")
    
    if images_folders:
        print(f"⚠️ QCM ID {qcm_id} non trouvé dans les métadonnées, mais {len(images_folders)} dossiers d'images trouvés.")
        print("Dossiers disponibles:")
        for i, folder in enumerate(images_folders):
            print(f"{i+1}. {os.path.basename(folder)}")
        
        try:
            choice = int(input("Entrez le numéro du dossier à utiliser (0 pour annuler): "))
            if choice == 0:
                return None
            elif 1 <= choice <= len(images_folders):
                return images_folders[choice-1]
        except ValueError:
            print("❌ Choix invalide")
            return None
    
    print(f"❌ Aucune image trouvée pour le QCM ID {qcm_id}")
    return None

def main():
    parser = argparse.ArgumentParser(description="Vérification et correction des réponses QCM avec API vision")
    parser.add_argument("qcm_id", type=int, help="ID du QCM à vérifier")
    parser.add_argument("question_num", type=int, help="Numéro de la question à vérifier")
    parser.add_argument("--page", type=int, help="Numéro de page spécifique à analyser (optionnel)")
    parser.add_argument("--force", action="store_true", help="Appliquer les corrections sans demander de confirmation")
    
    args = parser.parse_args()
    
    # Trouver les images pour ce QCM
    images_dir = find_qcm_images(args.qcm_id)
    
    if not images_dir:
        return
    
    # Déterminer les pages à analyser
    if args.page:
        pages_to_check = [args.page]
    else:
        # Page estimée en fonction du numéro de question (heuristique)
        question_num = args.question_num
        # Estimer les pages potentielles (on suppose environ 1 question par page + 3 pages d'en-tête)
        estimated_page = question_num + 3
        # Vérifier les pages autour de l'estimation
        pages_to_check = [max(1, estimated_page - 2), estimated_page - 1, estimated_page, estimated_page + 1, estimated_page + 2]
    
    # Vérifie que les pages existent
    valid_pages = []
    for page in pages_to_check:
        image_path = os.path.join(images_dir, f"page_{page}.jpg")
        if os.path.exists(image_path):
            valid_pages.append((page, image_path))
    
    if not valid_pages:
        print(f"❌ Aucune page valide trouvée pour la question {args.question_num}")
        return
    
    # Analyser les pages avec vision
    correct_answers = None
    for page, image_path in valid_pages:
        print(f"🔍 Analyse de la page {page} pour la question {args.question_num}...")
        result = verify_with_vision(image_path, args.question_num)
        
        if result:
            correct_answers = result
            print(f"✅ Réponses identifiées sur la page {page}: {', '.join(result)}")
            break
    
    if not correct_answers:
        print(f"❌ Impossible d'identifier les réponses correctes pour la question {args.question_num}")
        return
    
    # Mettre à jour les réponses dans la base de données
    if args.force:
        update_correct_answers(args.qcm_id, args.question_num, correct_answers)
    else:
        # Vérifier l'état actuel avant mise à jour
        questions = supabase.table('questions').select('id').eq('qcm_id', args.qcm_id).eq('numero', args.question_num).execute()
        if questions.data:
            question_id = questions.data[0]['id']
            reponses = supabase.table('reponses').select('*').eq('question_id', question_id).execute()
            
            current_correct = []
            for r in reponses.data:
                if r['est_correcte']:
                    current_correct.append(r['lettre'])
            
            # Si les réponses actuelles diffèrent des nouvelles, proposer une mise à jour
            if sorted(current_correct) != sorted(correct_answers):
                print(f"\n⚠️ Différence détectée:")
                print(f"- Réponses actuelles: {', '.join(sorted(current_correct))}")
                print(f"- Nouvelles réponses: {', '.join(sorted(correct_answers))}")
                
                update_correct_answers(args.qcm_id, args.question_num, correct_answers)
            else:
                print(f"\n✅ Les réponses actuelles sont déjà correctes: {', '.join(sorted(current_correct))}")
        else:
            print(f"⚠️ Question {args.question_num} non trouvée pour le QCM {args.qcm_id}")

if __name__ == "__main__":
    main() 