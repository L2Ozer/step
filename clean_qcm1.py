from qcm_extraction.extractor import QCMExtractor

# Initialiser l'extracteur
extractor = QCMExtractor()

# QCM ID à nettoyer
qcm_id = 1

print(f"🧹 Nettoyage des réponses du QCM ID {qcm_id}...")

# 1. Récupérer toutes les questions pour ce QCM
questions = extractor.supabase.table('questions').select('id').eq('qcm_id', qcm_id).execute()

if not questions.data:
    print(f"ℹ️ Aucune question trouvée pour le QCM ID {qcm_id}, rien à nettoyer.")
else:
    # 2. Réinitialiser les réponses (mettre est_correcte à False)
    updated_count = 0
    for q in questions.data:
        q_id = q['id']
        props = extractor.supabase.table('reponses').select('id').eq('question_id', q_id).execute()
        if props.data:
            for prop in props.data:
                # Mettre est_correcte à False
                update_result = extractor.supabase.table('reponses').update({"est_correcte": False}).eq('id', prop['id']).execute()
                if update_result.data:
                    updated_count += 1
    
    print(f"✅ {updated_count} réponses réinitialisées pour le QCM ID {qcm_id}")
    
print("🔍 État actuel du QCM ID 1, Question 1:")
# Vérifier l'état actuel de la question 1
questions = extractor.supabase.table('questions').select('id').eq('qcm_id', qcm_id).eq('numero', 1).execute()
if questions.data:
    q_id = questions.data[0]['id']
    print(f"ID Question 1: {q_id}")
    reponses = extractor.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
    for r in reponses.data:
        print(f"Proposition {r['lettre']}: est_correcte = {r['est_correcte']}") 