import os
import json
import re
from supabase import create_client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

# Initialiser le client Supabase
supabase = create_client(supabase_url, supabase_key)

def extract_correct_answers_from_text(file_path, question_num):
    """
    Extrait les réponses correctes du texte du PDF
    """
    print(f"🔍 Analyse du fichier pour la question {question_num}...")
    
    # Lire le contenu Markdown
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Patterns pour trouver les réponses correctes
    patterns = [
        # Pattern spécifique pour le format "Réponses justes : A, C, E."
        rf"## Q{question_num}[.\s\S]*?Réponses justes\s*:\s*([A-E][,\s]*(?:[A-E][,\s]*)*)[.\s]*",
        # Pattern 1: Réponses justes : X, Y, Z
        rf"(?:Q(?:uestion)?\s*{question_num}[^\n]*|^[^\d]*{question_num}[\.:)])[^\n]*(?:\n[^\n]+)*\n[^\n]*[Rr](?:é|e)ponses?\s+(?:correctes?|justes?|exactes?)\s*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*)",
        # Pattern 2: Question X. ... Réponses : A, B, C
        rf"(?:Q(?:uestion)?\s*{question_num})[^\n]*(?:\n[^\n]+)*\n[^\n]*[Rr]éponses?\s*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*)",
        # Pattern 3: Question X: A, B, C
        rf"(?:Q(?:uestion)?\s*{question_num}|^{question_num}[\.:)])[^\n]*:?\s*([A-E][,\s]*(?:[A-E][,\s]*)*\s*$)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
        for match in matches:
            answers_str = match.group(1)
            letters = re.findall(r'[A-E]', answers_str)
            
            if letters and 1 <= len(letters) <= 5:
                unique_letters = sorted(list(set(letters)))
                print(f"✅ Réponses trouvées: {', '.join(unique_letters)}")
                return unique_letters
    
    # Si aucun pattern n'a fonctionné, vérifier vrai/faux individuellement
    question_pattern = rf"## Q{question_num}[.\s\S]*?([A-E][.\s]*[^\n]*\n)"
    question_matches = re.finditer(question_pattern, content, re.MULTILINE | re.DOTALL)
    
    correct_letters = []
    for match in question_matches:
        question_context = match.group(0)
        vf_pattern = r'([A-E])\.?\s+([Vv]rai|[Ff]aux)'
        vf_matches = list(re.finditer(vf_pattern, question_context))
        
        for vf_match in vf_matches:
            letter = vf_match.group(1).upper()
            status = vf_match.group(2).lower()
            if status == 'vrai':
                correct_letters.append(letter)
        
        if correct_letters:
            print(f"✅ Réponses par vrai/faux: {', '.join(sorted(correct_letters))}")
            return sorted(correct_letters)
    
    # Si on arrive ici, on n'a pas trouvé de réponses
    print("⚠️ Pas de réponse trouvée")
    return None

def update_question(qcm_id, question_num, correct_letters):
    """
    Met à jour les réponses correctes pour une question spécifique.
    """
    # Si correct_letters n'est pas fourni, utiliser les réponses correctes connues pour Q1
    if not correct_letters:
        # Valeurs par défaut basées sur les questions
        default_answers = {
            1: ['A', 'C', 'E'],  # Q1: pompe Na+/K+
            2: ['C', 'E'],       # Q2: transporteurs GLUT
            3: ['B', 'C', 'D', 'E'],  # Q3: canaux ioniques
            4: ['C', 'D', 'E'],  # Q4: culture cellulaire
            5: ['A', 'B', 'E'],  # Q5: culture cellulaire
            6: ['A', 'C', 'E'],  # Q6: culture cellulaire
            7: ['B', 'C', 'E'],  # Q7: filaments du cytosquelette
            8: ['A', 'B', 'C', 'D', 'E'],  # Q8: protéines motrices
            9: ['B'],            # Q9: filaments du cytosquelette
            10: ['A', 'B'],      # Q10: centrosome
            11: ['C', 'D'],      # Q11: transport membranaire
            12: ['A', 'C', 'D', 'E']  # Q12: phagocytose
        }
        
        if question_num in default_answers:
            correct_letters = default_answers[question_num]
            print(f"ℹ️ Utilisation des réponses connues pour Q{question_num}: {', '.join(correct_letters)}")
        else:
            print(f"⚠️ Pas de réponses par défaut pour Q{question_num}")
            return
    
    # Récupérer l'ID de la question
    questions = supabase.table('questions').select('id').eq('qcm_id', qcm_id).eq('numero', question_num).execute()
    
    if not questions.data:
        print(f"⚠️ Question {question_num} non trouvée pour le QCM {qcm_id}")
        return
    
    question_id = questions.data[0]['id']
    print(f"✅ ID de la question trouvé: {question_id}")
    
    # Récupérer les propositions actuelles
    reponses = supabase.table('reponses').select('*').eq('question_id', question_id).execute()
    
    if not reponses.data:
        print(f"⚠️ Aucune proposition trouvée pour la question {question_num}")
        return
    
    print("📊 Propositions actuelles:")
    current_correct = []
    for r in reponses.data:
        status = "✓" if r['est_correcte'] else "✗"
        print(f"Proposition {r['lettre']}: {status} {r['contenu']}")
        if r['est_correcte']:
            current_correct.append(r['lettre'])
    
    print(f"ℹ️ Actuellement correctes: {', '.join(sorted(current_correct))}")
    print(f"ℹ️ Nouvelles correctes: {', '.join(sorted(correct_letters))}")
    
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
    
    # Vérifier les mises à jour
    reponses_updated = supabase.table('reponses').select('*').eq('question_id', question_id).execute()
    
    print("\n📊 Propositions après mise à jour:")
    correct_letters = []
    for r in reponses_updated.data:
        status = "✓" if r['est_correcte'] else "✗"
        print(f"Proposition {r['lettre']}: {status} {r['contenu']}")
        if r['est_correcte']:
            correct_letters.append(r['lettre'])
    
    print(f"\n✅ Bonnes réponses finales: {', '.join(sorted(correct_letters))}")

def main():
    print("🚀 Correction rapide des réponses pour le QCM 1...")
    
    # 1. Trouver le dossier correspondant
    target_folder = "ue1-correction-colle-2-s42-2021-49647"
    
    # 2. Chercher les réponses correctes dans le markdown
    markdown_path = f"qcm_extraction/temp/outputs/{target_folder}/content.md"
    
    # Demander quel numéro de question corriger
    try:
        question_num = int(input("Numéro de question corriger (1-20, ou 0 pour toutes): "))
    except ValueError:
        question_num = 1
    
    if question_num == 0:
        # Corriger toutes les questions
        for q_num in range(1, 21):  # Questions 1 à 20
            correct_answers = None
            if os.path.exists(markdown_path):
                correct_answers = extract_correct_answers_from_text(markdown_path, q_num)
            
            if correct_answers:
                update_question(1, q_num, correct_answers)
            else:
                # Utiliser les valeurs par défaut
                update_question(1, q_num, None)
    else:
        # Corriger uniquement la question spécifiée
        correct_answers = None
        if os.path.exists(markdown_path):
            correct_answers = extract_correct_answers_from_text(markdown_path, question_num)
        
        update_question(1, question_num, correct_answers)

if __name__ == "__main__":
    main() 