from qcm_extraction.extractor import QCMExtractor

extractor = QCMExtractor()

# Récupérer toutes les questions pour le QCM ID 2
questions = extractor.supabase.table('questions').select('id,numero').eq('qcm_id', 2).execute()

print(f"Nombre total de questions: {len(questions.data)}")

# Tableau pour stocker le compte des propositions pour chaque question
proposition_counts = {}

# Pour chaque question, compter les propositions
for question in questions.data:
    q_id = question['id']
    q_num = question['numero']
    
    # Récupérer les propositions pour cette question
    props = extractor.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
    
    # Stocker le compte
    proposition_counts[q_num] = len(props.data)

# Afficher les résultats triés par numéro de question
print("\nNombre de propositions par question:")
for num in sorted(proposition_counts.keys()):
    count = proposition_counts[num]
    if count != 5:
        status = "⚠️ ERREUR" if count > 5 else "⚠️ MANQUE"
    else:
        status = "✅ OK"
    print(f"Question {num}: {count} propositions - {status}")

# Statistiques
total_props = sum(proposition_counts.values())
print(f"\nTotal des propositions: {total_props}")
print(f"Moyenne: {total_props / len(proposition_counts):.1f} propositions par question")

# Vérifier les erreurs
errors = [num for num, count in proposition_counts.items() if count != 5]
if errors:
    print(f"\n⚠️ Questions avec un nombre incorrect de propositions: {errors}")
else:
    print("\n✅ Toutes les questions ont exactement 5 propositions") 