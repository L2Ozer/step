import os
import json
from supabase import create_client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

# Initialiser le client Supabase
supabase = create_client(supabase_url, supabase_key)

def update_question1_answers():
    """
    Met à jour directement les réponses correctes pour la question 1 du QCM 1.
    Les bonnes réponses devraient être A, C, E.
    """
    print("🚀 Correction des réponses pour la question 1 du QCM 1...")
    
    # QCM ID et numéro de question
    qcm_id = 1
    numero = 1
    
    # Les bonnes réponses selon le PDF
    bonnes_reponses = ['A', 'C', 'E']
    
    # Récupérer l'ID de la question
    questions = supabase.table('questions').select('id').eq('qcm_id', qcm_id).eq('numero', numero).execute()
    
    if not questions.data:
        print(f"⚠️ Question {numero} non trouvée pour le QCM {qcm_id}")
        return
    
    question_id = questions.data[0]['id']
    print(f"✅ ID de la question trouvé: {question_id}")
    
    # Récupérer les propositions actuelles
    reponses = supabase.table('reponses').select('*').eq('question_id', question_id).execute()
    
    if not reponses.data:
        print(f"⚠️ Aucune proposition trouvée pour la question {numero}")
        return
    
    print("📊 Propositions actuelles:")
    for r in reponses.data:
        status = "✓" if r['est_correcte'] else "✗"
        print(f"Proposition {r['lettre']}: {status} {r['contenu']}")
    
    # Mettre à jour les propositions
    updates = []
    for r in reponses.data:
        r_id = r['id']
        lettre = r['lettre']
        est_correcte = lettre in bonnes_reponses
        
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

if __name__ == "__main__":
    update_question1_answers() 