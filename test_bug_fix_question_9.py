#!/usr/bin/env python3
"""
Test pour valider la correction du bug de la question 9
Ce script teste la nouvelle approche intelligente qui ne perd plus la question 9
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def test_question_9_fix():
    """Test complet pour vérifier que la question 9 est maintenant extraite"""
    print("🧪 TEST DE CORRECTION DU BUG DE LA QUESTION 9")
    print("=" * 60)
    
    # URL du PDF problématique
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("🧹 Phase 1: Nettoyage des données existantes...")
        
        # Supprimer les données existantes pour recommencer proprement
        try:
            existing_qcm = extractor.supabase.table("qcm").select("id").eq("type", "Concours Blanc N°1").eq("annee", "2021 / 2022").execute()
            
            if existing_qcm.data:
                qcm_id = existing_qcm.data[0]["id"]
                print(f"🔍 QCM existant trouvé (ID: {qcm_id}). Nettoyage...")
                
                # Supprimer les réponses
                questions = extractor.supabase.table("questions").select("id").eq("qcm_id", qcm_id).execute()
                if questions.data:
                    for q in questions.data:
                        extractor.supabase.table("reponses").delete().eq("question_id", q["id"]).execute()
                
                # Supprimer les questions
                extractor.supabase.table("questions").delete().eq("qcm_id", qcm_id).execute()
                
                # Supprimer le QCM
                extractor.supabase.table("qcm").delete().eq("id", qcm_id).execute()
                
                print("✅ Données existantes supprimées")
        except Exception as e:
            print(f"ℹ️ Pas de données existantes à nettoyer: {e}")
        
        print("\n🚀 Phase 2: Test de la nouvelle extraction...")
        
        # Lancer l'extraction avec la nouvelle logique
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if metadata:
            print("\n✅ Extraction terminée avec la nouvelle logique!")
            
            qcm_id = metadata.get('qcm_db_id')
            if qcm_id:
                print(f"\n📊 RÉSULTATS DU TEST pour QCM ID: {qcm_id}")
                
                # Vérifier les questions
                questions_result = extractor.supabase.table("questions").select("numero").eq("qcm_id", qcm_id).execute()
                
                if questions_result.data:
                    question_numbers = sorted([q["numero"] for q in questions_result.data])
                    print(f"✅ Questions extraites: {len(question_numbers)}")
                    print(f"   Numéros: {question_numbers}")
                    
                    # TEST CRITIQUE: Vérifier si la question 9 est présente
                    if 9 in question_numbers:
                        print("\n🎉 SUCCESS! LA QUESTION 9 EST MAINTENANT EXTRAITE!")
                        print("✅ Le bug a été corrigé avec succès")
                        
                        # Vérifier combien de questions on a au total
                        if len(question_numbers) == 30:
                            print("🎯 PARFAIT: 30 questions comme attendu")
                        elif len(question_numbers) == 29:
                            print("⚠️ Toujours 29 questions - vérifier s'il y a d'autres questions manquantes")
                        
                        # Analyser les questions manquantes dans la séquence 1-30
                        expected_30 = set(range(1, 31))
                        missing_from_30 = expected_30 - set(question_numbers)
                        
                        if missing_from_30:
                            print(f"⚠️ Questions manquantes dans la séquence 1-30: {sorted(missing_from_30)}")
                        else:
                            print("🎉 SUCCÈS TOTAL: Toutes les questions 1-30 sont présentes!")
                            
                    else:
                        print("\n❌ ÉCHEC: La question 9 est toujours manquante")
                        print("🔍 Analyse nécessaire pour comprendre pourquoi...")
                        
                        # Analyser les questions autour de 9
                        around_9 = [n for n in question_numbers if 6 <= n <= 12]
                        print(f"📊 Questions autour de 9 (6-12): {around_9}")
                    
                    # Compter les propositions
                    total_props = 0
                    questions_with_5_props = 0
                    
                    for q_data in questions_result.data:
                        if "id" in q_data:
                            props_result = extractor.supabase.table("reponses").select("lettre").eq("question_id", q_data["id"]).execute()
                            q_props = len(props_result.data) if props_result.data else 0
                            total_props += q_props
                            
                            if q_props == 5:
                                questions_with_5_props += 1
                    
                    print(f"\n📊 Statistiques des propositions:")
                    print(f"   Total propositions: {total_props}")
                    print(f"   Questions avec 5 propositions: {questions_with_5_props}/{len(question_numbers)}")
                    
                    # Calculer la complétude
                    expected_props = len(question_numbers) * 5
                    completeness = (total_props / expected_props) * 100 if expected_props > 0 else 0
                    print(f"   Complétude: {completeness:.1f}%")
                    
                    # Verdict final
                    print(f"\n🏁 VERDICT FINAL:")
                    if 9 in question_numbers and completeness >= 95:
                        print("🎉 TEST RÉUSSI: Bug corrigé avec succès!")
                        return True
                    elif 9 in question_numbers:
                        print("✅ Question 9 trouvée mais problèmes de propositions")
                        return False
                    else:
                        print("❌ Question 9 toujours manquante - bug non corrigé")
                        return False
                else:
                    print("❌ Aucune question trouvée après extraction")
                    return False
            else:
                print("❌ QCM ID non disponible")
                return False
        else:
            print("❌ Échec de l'extraction")
            return False
            
    except Exception as e:
        print(f"❌ Erreur pendant le test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Test de la correction du bug de la question 9...")
    print("   Si la question 9 est sur la page 7, elle devrait maintenant être extraite")
    print("   grâce à la nouvelle logique intelligente qui utilise l'API de vision")
    print()
    
    success = test_question_9_fix()
    
    if success:
        print("\n🎉 FÉLICITATIONS: Le bug a été corrigé!")
        print("   La question 9 sera maintenant extraite pour n'importe quel PDF de QCM.")
    else:
        print("\n🔍 Le test n'a pas réussi complètement.")
        print("   Une analyse plus approfondie peut être nécessaire.") 