#!/usr/bin/env python3
"""
Correctif simple pour les problèmes d'extraction identifiés :
1. La question 9 n'existe pas dans ce PDF (seulement 29 questions)
2. Les propositions sont dupliquées (267 au lieu de 145)
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def fix_extraction_issues():
    """Corrige les problèmes d'extraction identifiés"""
    print("🔧 CORRECTIF SIMPLE POUR L'EXTRACTION")
    print("=" * 50)
    
    # URL du PDF de test
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("🧹 Phase 1: Nettoyage des données existantes...")
        
        # 1. Supprimer les données existantes pour ce PDF pour recommencer proprement
        try:
            # Identifier le QCM par son type et année
            existing_qcm = extractor.supabase.table("qcm").select("id").eq("type", "Concours Blanc N°1").eq("annee", "2021 / 2022").execute()
            
            if existing_qcm.data:
                qcm_id = existing_qcm.data[0]["id"]
                print(f"🔍 QCM existant trouvé (ID: {qcm_id}). Nettoyage...")
                
                # Supprimer d'abord les réponses
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
            print(f"⚠️ Erreur lors du nettoyage (peut être normal si pas de données existantes): {e}")
        
        print("\n🚀 Phase 2: Extraction propre...")
        
        # 2. Faire une nouvelle extraction
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if metadata:
            print("\n✅ Extraction terminée!")
            
            qcm_id = metadata.get('qcm_db_id')
            if qcm_id:
                print(f"\n📊 RÉSULTATS FINAUX pour QCM ID: {qcm_id}")
                
                # Vérifier les questions
                questions_result = extractor.supabase.table("questions").select("numero").eq("qcm_id", qcm_id).execute()
                
                if questions_result.data:
                    question_numbers = sorted([q["numero"] for q in questions_result.data])
                    print(f"✅ Questions: {len(question_numbers)}")
                    print(f"   Numéros: {question_numbers}")
                    
                    # Vérifier les attentes
                    if len(question_numbers) == 29 and 9 not in question_numbers:
                        print("🎉 PARFAIT: 29 questions comme attendu (pas de Q9)")
                    
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
                            elif q_props != 5:
                                print(f"⚠️ Question {q_data['numero']}: {q_props} propositions")
                    
                    print(f"✅ Propositions: {total_props}")
                    print(f"✅ Questions avec 5 propositions: {questions_with_5_props}/{len(question_numbers)}")
                    
                    # Calculer les pourcentages
                    expected_props = len(question_numbers) * 5  # 29 * 5 = 145
                    completeness = (total_props / expected_props) * 100 if expected_props > 0 else 0
                    
                    print(f"📈 Complétude: {completeness:.1f}%")
                    
                    if completeness == 100.0:
                        print("🎉 SUCCÈS COMPLET: Extraction parfaite!")
                    elif 95 <= completeness < 100:
                        print("✅ EXCELLENT: Extraction quasi-parfaite!")
                    elif 80 <= completeness < 95:
                        print("👍 BON: Extraction correcte avec quelques manques")
                    else:
                        print("⚠️ PROBLÈME: Extraction incomplète")
                    
                    # Vérifier si c'est exactement ce qu'on attend
                    if total_props == 145 and len(question_numbers) == 29:
                        print("\n🎯 OBJECTIF ATTEINT:")
                        print("   ✅ 29 questions (sans Q9)")
                        print("   ✅ 145 propositions (5 par question)")
                        print("   ✅ Aucun doublon")
                        return True
                    else:
                        print(f"\n⚠️ Écart avec l'objectif:")
                        print(f"   Questions: {len(question_numbers)}/29")
                        print(f"   Propositions: {total_props}/145")
                        return False
        
        return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_extraction_issues()
    
    if success:
        print("\n🎉 CORRECTIF RÉUSSI!")
    else:
        print("\n❌ Le correctif n'a pas résolu tous les problèmes.")
        print("   Vérifiez les messages d'erreur ci-dessus.") 