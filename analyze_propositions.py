#!/usr/bin/env python3
"""
Analyser les propositions par question pour identifier le problème des 145 au lieu de 150
"""

import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def analyze_propositions():
    """Analyser les propositions par question"""
    print("📊 ANALYSE DES PROPOSITIONS PAR QUESTION")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # Récupérer toutes les questions
        questions = extractor.supabase.table('questions').select('numero, id').eq('qcm_id', 1).order('numero').execute()
        
        if not questions.data:
            print("❌ Aucune question trouvée")
            return
        
        print(f"📋 Analyse de {len(questions.data)} questions:")
        
        total_props = 0
        perfect_questions = 0
        problematic_questions = []
        
        for q in questions.data:
            # Récupérer les propositions pour cette question
            props = extractor.supabase.table('reponses').select('lettre, contenu').eq('question_id', q['id']).order('lettre').execute()
            prop_count = len(props.data) if props.data else 0
            total_props += prop_count
            
            if prop_count == 5:
                perfect_questions += 1
                print(f"✅ Q{q['numero']}: {prop_count} propositions (A,B,C,D,E)")
            else:
                problematic_questions.append((q['numero'], prop_count))
                letters = [p['lettre'] for p in props.data] if props.data else []
                missing_letters = set(['A', 'B', 'C', 'D', 'E']) - set(letters)
                print(f"⚠️ Q{q['numero']}: {prop_count} propositions - Lettres: {sorted(letters)} - Manquantes: {sorted(missing_letters)}")
        
        print(f"\n📈 STATISTIQUES FINALES:")
        print(f"   Total questions: {len(questions.data)}")
        print(f"   Questions parfaites (5 props): {perfect_questions}")
        print(f"   Questions problématiques: {len(problematic_questions)}")
        print(f"   Total propositions: {total_props}")
        print(f"   Attendu: {len(questions.data) * 5}")
        print(f"   Manquant: {len(questions.data) * 5 - total_props}")
        
        if problematic_questions:
            print(f"\n⚠️ QUESTIONS PROBLÉMATIQUES:")
            for q_num, prop_count in problematic_questions:
                print(f"   Q{q_num}: {prop_count} propositions")
        
        # Analyser si on a Q26 ou pas
        question_numbers = [q['numero'] for q in questions.data]
        if 26 not in question_numbers:
            print(f"\n❌ PROBLÈME PRINCIPAL: Question 26 absente!")
            print(f"   Questions présentes: {sorted(question_numbers)}")
            print(f"   Questions manquantes: {sorted(set(range(1, 31)) - set(question_numbers))}")
        else:
            print(f"\n✅ Question 26 présente")
        
        return total_props, len(questions.data), perfect_questions
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0

if __name__ == "__main__":
    analyze_propositions() 