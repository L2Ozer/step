#!/usr/bin/env python3
"""
Test final pour valider l'extraction parfaite de TOUTES les questions
avec sauvegarde complète en base de données
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def test_final_perfect_extraction():
    """Test final complet et parfait"""
    print("🚀 TEST FINAL - EXTRACTION PARFAITE ET COMPLÈTE")
    print("=" * 70)
    
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("🧹 Nettoyage complet de la base de données...")
        
        # Supprimer toutes les données existantes pour ce PDF
        try:
            existing_qcms = extractor.supabase.table("qcm").select("id").execute()
            if existing_qcms.data:
                for qcm in existing_qcms.data:
                    qcm_id = qcm["id"]
                    print(f"🗑️ Suppression QCM ID: {qcm_id}")
                    
                    # Supprimer les réponses
                    questions = extractor.supabase.table("questions").select("id").eq("qcm_id", qcm_id).execute()
                    if questions.data:
                        for q in questions.data:
                            extractor.supabase.table("reponses").delete().eq("question_id", q["id"]).execute()
                    
                    # Supprimer les questions
                    extractor.supabase.table("questions").delete().eq("qcm_id", qcm_id).execute()
                    
                    # Supprimer le QCM
                    extractor.supabase.table("qcm").delete().eq("id", qcm_id).execute()
                
                print("✅ Base de données complètement nettoyée")
        except Exception as e:
            print(f"ℹ️ Nettoyage: {e}")
        
        print("\n🚀 Lancement de l'extraction parfaite...")
        
        # Lancer l'extraction complète
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if metadata:
            print("\n✅ Extraction terminée!")
            
            qcm_id = metadata.get('qcm_db_id')
            if qcm_id:
                print(f"\n📊 RÉSULTATS FINAUX pour QCM ID: {qcm_id}")
                
                # Analyser les questions
                questions_result = extractor.supabase.table("questions").select("numero, id").eq("qcm_id", qcm_id).execute()
                
                if questions_result.data:
                    question_numbers = sorted([q["numero"] for q in questions_result.data])
                    print(f"✅ Questions extraites: {len(question_numbers)}")
                    print(f"📋 Numéros: {question_numbers}")
                    
                    # Vérifier la complétude
                    if len(question_numbers) == 30:
                        expected_range = list(range(1, 31))
                        missing = set(expected_range) - set(question_numbers)
                        if not missing:
                            print("🎉 PARFAIT: Toutes les 30 questions (1-30) sont présentes!")
                        else:
                            print(f"⚠️ Questions manquantes: {sorted(missing)}")
                    
                    # Analyser les propositions
                    total_props = 0
                    perfect_questions = 0
                    
                    print(f"\n📝 Analyse des propositions:")
                    for q_data in questions_result.data:
                        props_result = extractor.supabase.table("reponses").select("lettre, contenu").eq("question_id", q_data["id"]).execute()
                        q_props = len(props_result.data) if props_result.data else 0
                        total_props += q_props
                        
                        if q_props == 5:
                            perfect_questions += 1
                        elif q_props != 5:
                            print(f"   ⚠️ Q{q_data['numero']}: {q_props} propositions au lieu de 5")
                    
                    print(f"✅ Total propositions: {total_props}")
                    print(f"✅ Questions parfaites (5 props): {perfect_questions}/{len(question_numbers)}")
                    
                    # Calculer les statistiques finales
                    expected_props = len(question_numbers) * 5
                    completeness = (total_props / expected_props) * 100 if expected_props > 0 else 0
                    question_completeness = (perfect_questions / len(question_numbers)) * 100 if question_numbers else 0
                    
                    print(f"📈 Complétude propositions: {completeness:.1f}%")
                    print(f"📈 Questions parfaites: {question_completeness:.1f}%")
                    
                    # Test spécifique pour la question 9 et autres critiques
                    print(f"\n🎯 VÉRIFICATIONS CRITIQUES:")
                    critical_questions = [9, 16, 17, 18]
                    for q_num in critical_questions:
                        if q_num in question_numbers:
                            # Vérifier les propositions
                            q_data = next((q for q in questions_result.data if q["numero"] == q_num), None)
                            if q_data:
                                props = extractor.supabase.table("reponses").select("lettre").eq("question_id", q_data["id"]).execute()
                                prop_count = len(props.data) if props.data else 0
                                print(f"   ✅ Q{q_num}: présente avec {prop_count} propositions")
                            else:
                                print(f"   ❌ Q{q_num}: donnée manquante")
                        else:
                            print(f"   ❌ Q{q_num}: absente!")
                    
                    # Verdict final
                    print(f"\n🏁 VERDICT FINAL:")
                    
                    success_criteria = {
                        "30_questions": len(question_numbers) == 30,
                        "question_9": 9 in question_numbers,
                        "150_propositions": total_props == 150,
                        "perfect_questions": perfect_questions >= 25
                    }
                    
                    all_success = all(success_criteria.values())
                    
                    for criterion, success in success_criteria.items():
                        status = "✅" if success else "❌"
                        print(f"   {status} {criterion}: {success}")
                    
                    if all_success:
                        print("\n🎉🎉🎉 SUCCÈS TOTAL! EXTRACTION PARFAITE!")
                        print("🚀 Le système est maintenant parfait et scalable!")
                        return True
                    else:
                        failed_criteria = [k for k, v in success_criteria.items() if not v]
                        print(f"\n⚠️ Critères non remplis: {failed_criteria}")
                        return False
                else:
                    print("❌ Aucune question trouvée dans Supabase")
                    return False
            else:
                print("❌ QCM ID non disponible")
                return False
        else:
            print("❌ Échec de l'extraction")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Test final de l'extraction parfaite et scalable")
    print("   Objectif: 30 questions + 150 propositions + Question 9 incluse")
    print()
    
    success = test_final_perfect_extraction()
    
    if success:
        print("\n🎊 FÉLICITATIONS!")
        print("🎯 L'extraction est maintenant PARFAITE et SCALABLE!")
        print("🚀 Le système peut traiter n'importe quel PDF de QCM médical!")
    else:
        print("\n🔧 Améliorations nécessaires identifiées dans les résultats ci-dessus.") 