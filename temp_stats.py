from qcm_extraction.extractor import QCMExtractor

extractor = QCMExtractor()
questions = extractor.supabase.table('questions').select('*').eq('qcm_id', 2).execute()

total_reponses = 0
total_correctes = 0

print(f'QCM ID: 2 - Nombre de questions: {len(questions.data)}')

for q in questions.data:
    reponses = extractor.supabase.table('reponses').select('*').eq('question_id', q['id']).execute()
    correctes = sum(1 for r in reponses.data if r['est_correcte'])
    total_reponses += len(reponses.data)
    total_correctes += correctes
    print(f'Question {q["numero"]}: {len(reponses.data)} réponses, dont {correctes} correctes')

print(f'\nStatistiques globales:')
print(f'- {len(questions.data)} questions extraites')
print(f'- {total_reponses} réponses extraites')
print(f'- {total_correctes} réponses marquées comme correctes')
print(f'- {total_correctes/total_reponses*100:.1f}% des réponses sont correctes') 