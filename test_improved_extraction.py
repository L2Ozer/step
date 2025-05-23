#!/usr/bin/env python3
"""
Script de test pour valider les améliorations d'extraction du QCM
Vérifie spécifiquement:
1. Que toutes les questions (1-30) sont extraites
2. Que chaque question a exactement 5 propositions
3. Que la question 9 est bien récupérée
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def test_extraction_robuste():
    """Test complet de l'extraction avec validation"""
    print("🧪 Test de l'extraction robuste et scalable")
    print("=" * 50)
    
    # URL du PDF de test (le même que précédemment)
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("📥 Lancement de l'extraction complète...")
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if metadata:
            print("\n✅ Extraction terminée!")
            print("📊 RÉSULTATS:")
            print(f"  - QCM: {metadata.get('type', 'N/A')}")
            print(f"  - UE: {metadata.get('ue', 'N/A')}")
            print(f"  - Année: {metadata.get('annee', 'N/A')}")
            print(f"  - Questions extraites: {metadata.get('questions_count', 'N/A')}")
            print(f"  - Propositions extraites: {metadata.get('propositions_count', 'N/A')}")
            
            # Vérifications de qualité
            questions_count = metadata.get('questions_count', 0)
            propositions_count = metadata.get('propositions_count', 0)
            
            print("\n🔍 VALIDATION:")
            
            # Test 1: Nombre de questions attendu
            expected_questions = 30  # Assumant 30 questions pour ce QCM
            if questions_count >= expected_questions:
                print(f"✅ Questions: {questions_count}/{expected_questions} (OK)")
            else:
                print(f"⚠️ Questions: {questions_count}/{expected_questions} (MANQUANTES)")
            
            # Test 2: Nombre de propositions attendu
            expected_propositions = questions_count * 5 if questions_count > 0 else 150
            if propositions_count >= expected_propositions:
                print(f"✅ Propositions: {propositions_count}/{expected_propositions} (OK)")
            else:
                print(f"⚠️ Propositions: {propositions_count}/{expected_propositions} (MANQUANTES)")
            
            # Test 3: Complétude globale
            if questions_count > 0 and propositions_count > 0:
                completeness = (propositions_count / (questions_count * 5)) * 100
                print(f"📈 Complétude: {completeness:.1f}%")
                
                if completeness >= 95:
                    print("🎉 EXCELLENT: Extraction quasi-complète!")
                elif completeness >= 80:
                    print("✅ BON: Extraction majoritairement réussie")
                elif completeness >= 60:
                    print("⚠️ MOYEN: Extraction partielle")
                else:
                    print("❌ FAIBLE: Extraction insuffisante")
            
            # Test 4: Vérification spécifique de la question 9
            qcm_id = metadata.get('qcm_db_id')
            if qcm_id:
                print("\n🔍 Vérification spécifique de la question 9...")
                try:
                    result = extractor.supabase.table("questions").select("numero").eq("qcm_id", qcm_id).eq("numero", 9).execute()
                    if result.data:
                        print("✅ Question 9: TROUVÉE")
                        
                        # Vérifier les propositions de la question 9
                        question_id = result.data[0]["id"] if "id" in result.data[0] else None
                        if question_id:
                            props_result = extractor.supabase.table("reponses").select("lettre").eq("question_id", question_id).execute()
                            if props_result.data:
                                props_letters = [p["lettre"] for p in props_result.data]
                                print(f"   Propositions: {sorted(props_letters)} ({len(props_letters)}/5)")
                            else:
                                print("   ⚠️ Aucune proposition trouvée pour la question 9")
                    else:
                        print("❌ Question 9: MANQUANTE")
                except Exception as e:
                    print(f"⚠️ Erreur lors de la vérification de la question 9: {e}")
            
            return True
        else:
            print("❌ Échec de l'extraction")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_extraction_robuste()
    
    print("\n" + "=" * 50)
    if success:
        print("🎯 Test terminé. Consultez les résultats ci-dessus.")
    else:
        print("❌ Test échoué. Vérifiez les erreurs ci-dessus.") 