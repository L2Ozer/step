from qcm_extraction.extractor import QCMExtractor

# Initialiser l'extracteur
extractor = QCMExtractor()

# QCM ID à nettoyer
qcm_id = 2

print(f"🧹 Nettoyage complet du QCM ID {qcm_id}...")

# 1. Récupérer toutes les questions pour ce QCM
questions = extractor.supabase.table('questions').select('id').eq('qcm_id', qcm_id).execute()

if not questions.data:
    print(f"ℹ️ Aucune question trouvée pour le QCM ID {qcm_id}, rien à nettoyer.")
else:
    # 2. Supprimer toutes les propositions pour chaque question
    for q in questions.data:
        q_id = q['id']
        props = extractor.supabase.table('reponses').select('id').eq('question_id', q_id).execute()
        if props.data:
            delete_result = extractor.supabase.table('reponses').delete().eq('question_id', q_id).execute()
            print(f"🗑️ Suppression de {len(props.data)} propositions pour la question ID {q_id}")
    
    # 3. Supprimer toutes les questions
    delete_result = extractor.supabase.table('questions').delete().eq('qcm_id', qcm_id).execute()
    print(f"🗑️ Suppression de {len(questions.data)} questions pour le QCM ID {qcm_id}")

print("✅ Nettoyage complet effectué") 