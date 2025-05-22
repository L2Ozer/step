import os
import json
import re
import base64
import argparse
from supabase import create_client
from dotenv import load_dotenv
from mistralai import Mistral

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion Supabase et Mistral
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
mistral_api_key = os.getenv('MISTRAL_API_KEY')

# Initialiser les clients
supabase = create_client(supabase_url, supabase_key)
mistral = Mistral(api_key=mistral_api_key)

def extract_correct_answers_from_text(file_path, question_num):
    """
    Méthode 1 (RAPIDE): Extrait les réponses correctes du texte brut du PDF
    """
    print(f"🔍 Extraction textuelle pour la question {question_num}...")
    
    # Trouver le dossier outputs correspondant
    pdf_name = os.path.basename(os.path.dirname(file_path))
    markdown_path = f"qcm_extraction/temp/outputs/{pdf_name}/content.md"
    
    if not os.path.exists(markdown_path):
        print(f"⚠️ Markdown non trouvé pour {pdf_name}")
        return None
    
    # Lire le contenu Markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Patterns pour trouver les réponses correctes (du plus spécifique au plus général)
    patterns = [
        # Pattern 1: Question X. Réponses justes: A, B, C
        rf"(?:Q(?:uestion)?\s*{question_num}[^\n]*|^[^\d]*{question_num}[\.:)])[^\n]*(?:\n[^\n]+)*\n[^\n]*[Rr](?:é|e)ponses?\s+(?:correctes?|justes?|exactes?)\s*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*)",
        # Pattern 2: Question X. ... Réponses : A, B, C
        rf"(?:Q(?:uestion)?\s*{question_num})[^\n]*(?:\n[^\n]+)*\n[^\n]*[Rr]éponses?\s*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*)",
        # Pattern 3: Question X: A, B, C
        rf"(?:Q(?:uestion)?\s*{question_num}|^{question_num}[\.:)])[^\n]*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*\s*$)",
        # Pattern 4: Détection individuelle de vrai/faux pour chaque option
        rf"(?:Q(?:uestion)?\s*{question_num}|^{question_num}[\.:)])[^\n]*(?:\n[^\n]+)*\n[^\n]*"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            try:
                # Pour les patterns 1-3 qui capturent directement les réponses
                if len(match.groups()) > 0:
                    answers_str = match.group(1)
                    letters = re.findall(r'[A-E]', answers_str)
                    
                    if letters and 1 <= len(letters) <= 5:
                        unique_letters = sorted(list(set(letters)))
                        print(f"✅ Réponses extraites par pattern textuel: {', '.join(unique_letters)}")
                        return unique_letters
                # Pour le pattern 4 (vrai/faux individuel)
                else:
                    # Rechercher des indications individuelles vrai/faux dans le contexte de la question
                    question_context = match.group(0)
                    vf_pattern = r'([A-E])\.?\s+([Vv]rai|[Ff]aux|[Jj]uste|[Cc]orrect|[Ee]xact)'
                    vf_matches = list(re.finditer(vf_pattern, question_context))
                    
                    correct_letters = []
                    for vf_match in vf_matches:
                        letter = vf_match.group(1).upper()
                        status = vf_match.group(2).lower()
                        if status in ['vrai', 'juste', 'correct', 'exact']:
                            correct_letters.append(letter)
                    
                    if correct_letters and 1 <= len(correct_letters) <= 5:
                        print(f"✅ Réponses extraites par pattern vrai/faux: {', '.join(sorted(correct_letters))}")
                        return sorted(correct_letters)
            except Exception as e:
                print(f"⚠️ Erreur lors de l'extraction textuelle: {str(e)}")
    
    print("⚠️ Pas de réponse trouvée par méthode textuelle")
    return None

def verify_with_vision(image_path, question_num):
    """
    Méthode 2 (PRÉCISE MAIS LENTE): Utilise l'API vision pour vérifier les réponses
    """
    print(f"🔍 Analyse visuelle de l'image pour la question {question_num}...")
    
    try:
        # Encoder l'image en base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Construire la requête
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyse cette image d'un QCM médical et identifie les RÉPONSES CORRECTES pour la Question {question_num} uniquement.

CONSIGNES PRÉCISES:
1. Cherche UNIQUEMENT la Question {question_num} et ses réponses correctes
2. Cherche des indications comme "Réponses justes", "Réponses correctes", "Bonnes réponses"
3. Tu peux aussi repérer les réponses marquées comme "Vrai" ou "Faux"

RÉPONDS UNIQUEMENT AU FORMAT JSON:
{{
  "question_num": {question_num},
  "correct_answers": ["A", "C", "E"],
  "explanation": "Ma justification..."
}}"""
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{base64_image}"
                    }
                ]
            }
        ]
        
        # Faire l'appel API
        response = mistral.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        # Extraire le résultat
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        
        # Valider et retourner
        if "correct_answers" in result:
            letters = result["correct_answers"]
            if 1 <= len(letters) <= 5:
                print(f"✅ Réponses identifiées par vision: {', '.join(letters)}")
                return letters
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse visuelle: {str(e)}")
    
    print("⚠️ Pas de réponse trouvée par méthode visuelle")
    return None

def update_correct_answers(qcm_id, question_num, correct_letters, force=False):
    """
    Met à jour les réponses correctes dans la base de données
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
    
    print(f"ℹ️ Réponses actuelles: {', '.join(sorted(current_correct))}")
    print(f"ℹ️ Nouvelles réponses: {', '.join(sorted(correct_letters))}")
    
    if sorted(current_correct) == sorted(correct_letters):
        print("✅ Les réponses sont déjà correctes!")
        return True
    
    # Demander confirmation sauf si force=True
    if not force:
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

def main():
    parser = argparse.ArgumentParser(description="Correction intelligente des réponses QCM")
    parser.add_argument("qcm_id", type=int, help="ID du QCM à vérifier")
    parser.add_argument("question_num", type=int, help="Numéro de la question à vérifier")
    parser.add_argument("--page", type=int, help="Numéro de page spécifique à analyser (optionnel)")
    parser.add_argument("--mode", choices=["text", "vision", "smart"], default="smart", 
                       help="Mode d'extraction: text (rapide), vision (précis), smart (hybride)")
    parser.add_argument("--force", action="store_true", help="Appliquer les corrections sans confirmation")
    
    args = parser.parse_args()
    
    # Trouver les images pour ce QCM
    pdf_folders = os.listdir("qcm_extraction/temp/pdfs")
    pdf_folders = [d for d in pdf_folders if os.path.isdir(os.path.join("qcm_extraction/temp/pdfs", d))]
    
    target_folder = None
    for folder in pdf_folders:
        metadata_path = f"qcm_extraction/temp/outputs/{folder}/metadata.json"
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    if "qcm_db_id" in metadata and metadata["qcm_db_id"] == args.qcm_id:
                        target_folder = folder
                        break
            except Exception:
                pass
    
    if not target_folder:
        print(f"⚠️ Dossier non trouvé pour le QCM {args.qcm_id}")
        # Liste des dossiers disponibles
        print("Dossiers disponibles:")
        for i, folder in enumerate(pdf_folders):
            print(f"{i+1}. {folder}")
        try:
            choice = int(input("Choisir un dossier (0 pour annuler): "))
            if choice == 0:
                return
            target_folder = pdf_folders[choice-1]
        except:
            print("❌ Choix invalide")
            return
    
    # Chemins d'accès aux fichiers
    images_dir = f"qcm_extraction/temp/images/{target_folder}"
    
    # Choix des pages à analyser
    if args.page:
        pages_to_check = [args.page]
    else:
        # Estimation heuristique des pages (on suppose ~2 questions par page)
        base_page = max(1, (args.question_num // 2) + 2)  # +2 pour les pages d'entête
        pages_to_check = range(max(1, base_page-2), base_page+3)  # Pages autour de l'estimation
    
    # Mode TEXT : extraction textuelle uniquement (RAPIDE)
    if args.mode == "text":
        markdown_path = f"qcm_extraction/temp/outputs/{target_folder}/content.md"
        if os.path.exists(markdown_path):
            correct_answers = extract_correct_answers_from_text(markdown_path, args.question_num)
            if correct_answers:
                update_correct_answers(args.qcm_id, args.question_num, correct_answers, args.force)
            else:
                print("❌ Impossible de trouver les réponses par méthode textuelle")
        else:
            print(f"❌ Fichier markdown non trouvé: {markdown_path}")
    
    # Mode VISION : utilisation de l'API vision (PRÉCIS MAIS LENT)
    elif args.mode == "vision":
        for page in pages_to_check:
            image_path = f"{images_dir}/page_{page}.jpg"
            if os.path.exists(image_path):
                print(f"🔍 Analyse de la page {page}...")
                correct_answers = verify_with_vision(image_path, args.question_num)
                if correct_answers:
                    update_correct_answers(args.qcm_id, args.question_num, correct_answers, args.force)
                    break  # Arrêter dès qu'on trouve
        else:
            print(f"❌ Aucune réponse trouvée sur les pages {list(pages_to_check)}")
    
    # Mode SMART : hybride (ÉQUILIBRÉ)
    else:  # mode == "smart"
        # 1. D'abord essayer extraction textuelle (rapide)
        markdown_path = f"qcm_extraction/temp/outputs/{target_folder}/content.md"
        correct_answers = None
        
        if os.path.exists(markdown_path):
            correct_answers = extract_correct_answers_from_text(markdown_path, args.question_num)
        
        # 2. Si pas trouvé ou résultat ambigu, utiliser vision (lent mais précis)
        if not correct_answers:
            print("ℹ️ Passage à la méthode visuelle...")
            for page in pages_to_check:
                image_path = f"{images_dir}/page_{page}.jpg"
                if os.path.exists(image_path):
                    correct_answers = verify_with_vision(image_path, args.question_num)
                    if correct_answers:
                        break
        
        # 3. Mettre à jour si on a trouvé des réponses
        if correct_answers:
            update_correct_answers(args.qcm_id, args.question_num, correct_answers, args.force)
        else:
            print(f"❌ Impossible de déterminer les réponses pour la question {args.question_num}")

if __name__ == "__main__":
    main() 