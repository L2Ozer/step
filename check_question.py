from qcm_extraction.extractor import QCMExtractor
import sys

def check_question(qcm_id, numero):
    extractor = QCMExtractor()
    
    # Récupérer la question
    questions = extractor.supabase.table('questions').select('*').eq('qcm_id', qcm_id).eq('numero', numero).execute()
    
    if not questions.data:
        print(f"Question {numero} non trouvée pour le QCM {qcm_id}")
        return
    
    question = questions.data[0]
    print(f"\n===== QUESTION {numero} =====")
    print(f"ID: {question['id']}")
    print(f"Contenu: {question['contenu']}")
    
    # Récupérer les propositions
    props = extractor.supabase.table('reponses').select('*').eq('question_id', question['id']).execute()
    
    print(f"\n----- PROPOSITIONS ({len(props.data)}) -----")
    
    # Trier par lettre (A, B, C, D, E)
    sorted_props = sorted(props.data, key=lambda p: p['lettre'])
    
    for p in sorted_props:
        correct = "✓" if p['est_correcte'] else "✗"
        print(f"{p['lettre']}. [{correct}] {p['contenu']}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_question.py <qcm_id> <question_numero>")
        sys.exit(1)
    
    qcm_id = int(sys.argv[1])
    numero = int(sys.argv[2])
    
    check_question(qcm_id, numero) 