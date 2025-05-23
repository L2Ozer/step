#!/usr/bin/env python3
"""
Test FINAL pour l'extraction exhaustive et parfaite
Cette version teste la nouvelle logique qui devrait extraire TOUTES les questions
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def test_ultimate_extraction():
    """Test final pour extraction exhaustive de TOUTES les questions"""
    print("🚀 TEST FINAL - EXTRACTION EXHAUSTIVE ET PARFAITE")
    print("=" * 70)
    
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("🧹 Vérification de l'état de la base de données...")
        
        # Vérifier s'il y a déjà des données
        qcms = extractor.supabase.table('qcm').select('id').execute()
        if qcms.data:
            print(f"ℹ️ {len(qcms.data)} QCM(s) trouvé(s) en base")
        else:
            print("✅ Base de données vide, prête pour l'extraction")
        
        print("📥 Lancement de l'extraction exhaustive...")
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if not metadata:
            print("❌ Échec de l'extraction")
            return
        
        print("\n" + "="*50)
        print("📊 RÉSULTATS DE L'EXTRACTION EXHAUSTIVE")
        print("="*50)
        
        # Vérifier les questions
        qcm_id = metadata.get('id')
        if qcm_id:
            questions_result = extractor.supabase.table('questions').select('numero, id').eq('qcm_id', qcm_id).order('numero').execute()
            questions = questions_result.data if questions_result.data else []
            
            question_numbers = [q['numero'] for q in questions]
            print(f"🎯 Questions extraites: {len(questions)}/30")
            print(f"📋 Numéros trouvés: {sorted(question_numbers)}")
            
            # Vérifier la question 9 spécifiquement
            if 9 in question_numbers:
                print("✅ Question 9 TROUVÉE !")
            else:
                print("❌ Question 9 MANQUANTE")
            
            # Vérifier la question 26
            if 26 in question_numbers:
                print("✅ Question 26 TROUVÉE !")
            else:
                print("❌ Question 26 MANQUANTE")
            
            # Identifier les questions manquantes
            if questions:
                expected_questions = set(range(1, 31))
                found_questions = set(question_numbers)
                missing_questions = expected_questions - found_questions
                if missing_questions:
                    print(f"⚠️ Questions manquantes: {sorted(missing_questions)}")
                else:
                    print("🎉 TOUTES les questions sont présentes !")
            
            # Vérifier les propositions
            total_propositions = 0
            questions_with_5_props = 0
            
            for q in questions:
                props_result = extractor.supabase.table('reponses').select('lettre').eq('question_id', q['id']).execute()
                props_count = len(props_result.data) if props_result.data else 0
                total_propositions += props_count
                
                if props_count == 5:
                    questions_with_5_props += 1
                elif props_count != 5:
                    print(f"⚠️ Q{q['numero']}: {props_count} propositions au lieu de 5")
            
            print(f"📄 Propositions extraites: {total_propositions}")
            print(f"✅ Questions avec 5 propositions: {questions_with_5_props}/{len(questions)}")
            
            # Évaluation globale
            completeness_score = len(questions) / 30 * 100
            print(f"\n🎯 SCORE DE COMPLÉTUDE: {completeness_score:.1f}%")
            
            if completeness_score >= 100:
                print("🏆 EXTRACTION PARFAITE - TOUTES LES QUESTIONS TROUVÉES !")
            elif completeness_score >= 90:
                print("🥈 EXTRACTION EXCELLENTE - Presque parfaite")
            elif completeness_score >= 80:
                print("🥉 EXTRACTION BONNE - Acceptable")
            else:
                print("❌ EXTRACTION INSUFFISANTE - Nécessite amélioration")
            
            # Recommandations
            if missing_questions:
                print(f"\n💡 RECOMMANDATIONS:")
                print(f"   - Vérifier manuellement les questions {sorted(missing_questions)} dans le PDF")
                print(f"   - Analyser le formatage de ces questions dans le markdown")
                
        else:
            print("❌ Impossible de récupérer l'ID du QCM")
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ultimate_extraction() 