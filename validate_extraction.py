#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def main():
    """Test avec validation du nombre réel de questions"""
    print("🧪 VALIDATION DE L'EXTRACTION")
    print("=" * 50)
    
    # URL du PDF de test
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        print("📥 Lancement de l'extraction...")
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        if metadata:
            print("\n✅ Extraction terminée!")
            
            # Récupérer les statistiques depuis Supabase
            qcm_id = metadata.get('qcm_db_id')
            if qcm_id:
                print(f"\n📊 VALIDATION depuis Supabase pour QCM ID: {qcm_id}")
                
                # Compter les questions
                questions_result = extractor.supabase.table("questions").select("numero").eq("qcm_id", qcm_id).execute()
                
                if questions_result.data:
                    question_numbers = sorted([q["numero"] for q in questions_result.data])
                    print(f"✅ Questions extraites: {len(question_numbers)}")
                    print(f"   Numéros: {question_numbers}")
                    
                    # Identifier les questions manquantes
                    if question_numbers:
                        expected_range = list(range(min(question_numbers), max(question_numbers) + 1))
                        missing = [n for n in expected_range if n not in question_numbers]
                        
                        if missing:
                            print(f"⚠️ Questions manquantes: {missing}")
                        else:
                            print("✅ Séquence de questions complète")
                    
                    # Compter les propositions
                    props_count = 0
                    for q_data in questions_result.data:
                        if "id" in q_data:
                            # Compter les propositions pour cette question
                            props_result = extractor.supabase.table("reponses").select("lettre").eq("question_id", q_data["id"]).execute()
                            q_props = len(props_result.data) if props_result.data else 0
                            props_count += q_props
                            
                            if q_props != 5:
                                print(f"⚠️ Question {q_data['numero']}: {q_props} propositions au lieu de 5")
                    
                    print(f"✅ Total propositions: {props_count}")
                    expected_props = len(question_numbers) * 5
                    print(f"   Attendu: {expected_props} (5 par question)")
                    
                    if props_count == expected_props:
                        print("🎉 PARFAIT: Nombre exact de propositions!")
                    elif props_count > expected_props:
                        print(f"⚠️ SURPLUS: {props_count - expected_props} propositions en trop")
                    else:
                        print(f"⚠️ MANQUE: {expected_props - props_count} propositions manquantes")
                    
                    # Calculer le pourcentage
                    completeness = (props_count / expected_props) * 100 if expected_props > 0 else 0
                    print(f"📈 Complétude: {completeness:.1f}%")
                    
                    # Vérifier spécifiquement la question 9
                    if 9 not in question_numbers:
                        print("\n❌ CONFIRME: La question 9 n'existe pas dans ce PDF")
                        print("   Le PDF contient probablement seulement 29 questions, pas 30")
                    else:
                        print("\n✅ Question 9 trouvée!")
                        
                else:
                    print("❌ Aucune question trouvée dans Supabase")
            else:
                print("❌ QCM ID non disponible")
        else:
            print("❌ Échec de l'extraction")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 