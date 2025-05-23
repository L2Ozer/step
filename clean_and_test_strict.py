#!/usr/bin/env python3
"""
Script de nettoyage et test strict pour les propositions
Objectif: EXACTEMENT 150 propositions pour 30 questions (5 par question)
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def clean_duplicates():
    """Nettoie les doublons dans la base de données"""
    print("🧹 NETTOYAGE DES DOUBLONS")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # 1. Analyser l'état actuel
        print("📊 Analyse de l'état actuel...")
        
        questions = extractor.supabase.table('questions').select('id, numero').eq('qcm_id', 1).execute()
        if not questions.data:
            print("❌ Aucune question trouvée")
            return
        
        print(f"✅ {len(questions.data)} questions trouvées")
        
        # 2. Compter les propositions par question
        duplicates_found = 0
        questions_with_duplicates = []
        
        for q in questions.data:
            question_id = q['id']
            question_num = q['numero']
            
            # Compter par lettre
            props_count = {}
            total_props = 0
            
            for lettre in 'ABCDE':
                result = extractor.supabase.table('reponses').select('id').eq('question_id', question_id).eq('lettre', lettre).execute()
                count = len(result.data) if result.data else 0
                props_count[lettre] = count
                total_props += count
                
                if count > 1:
                    duplicates_found += count - 1
                    questions_with_duplicates.append(f"Q{question_num} prop {lettre} ({count} fois)")
            
            if total_props != 5:
                print(f"⚠️ Q{question_num}: {total_props}/5 propositions - {props_count}")
        
        print(f"📊 Total doublons détectés: {duplicates_found}")
        if questions_with_duplicates:
            print(f"📋 Questions avec doublons: {questions_with_duplicates[:10]}...")  # Afficher les 10 premiers
        
        # 3. Nettoyer les doublons
        if duplicates_found > 0:
            print("\n🔧 Suppression des doublons...")
            
            for q in questions.data:
                question_id = q['id']
                question_num = q['numero']
                
                for lettre in 'ABCDE':
                    # Récupérer toutes les propositions pour cette combinaison
                    result = extractor.supabase.table('reponses').select('id, contenu').eq('question_id', question_id).eq('lettre', lettre).execute()
                    
                    if result.data and len(result.data) > 1:
                        # Garder le premier (ou le plus long) et supprimer les autres
                        to_keep = result.data[0]  # Ou choisir le plus long contenu
                        to_delete = result.data[1:]
                        
                        print(f"   Q{question_num} {lettre}: gardé 1, supprimé {len(to_delete)}")
                        
                        # Supprimer les doublons
                        for dup in to_delete:
                            try:
                                extractor.supabase.table('reponses').delete().eq('id', dup['id']).execute()
                            except Exception as e:
                                print(f"     ⚠️ Erreur suppression {dup['id']}: {e}")
        
        # 4. Vérification finale
        print("\n📊 État après nettoyage:")
        total_final = 0
        questions_ok = 0
        
        for q in questions.data:
            question_id = q['id']
            question_num = q['numero']
            
            result = extractor.supabase.table('reponses').select('id').eq('question_id', question_id).execute()
            count = len(result.data) if result.data else 0
            total_final += count
            
            if count == 5:
                questions_ok += 1
            else:
                print(f"   ⚠️ Q{question_num}: {count}/5 propositions")
        
        print(f"✅ Total final: {total_final} propositions")
        print(f"✅ Questions complètes: {questions_ok}/{len(questions.data)}")
        print(f"🎯 Objectif: {len(questions.data) * 5} propositions exactement")
        
        if total_final == len(questions.data) * 5:
            print("🏆 PARFAIT ! Nombre exact de propositions atteint")
        else:
            print(f"⚠️ Écart: {total_final - len(questions.data) * 5} propositions")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def test_strict_extraction():
    """Test l'extraction avec la nouvelle logique stricte"""
    print("\n🧪 TEST D'EXTRACTION STRICTE")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # Compter avant
        props_before = extractor.supabase.table('reponses').select('id').execute()
        count_before = len(props_before.data) if props_before.data else 0
        print(f"📊 Propositions avant: {count_before}")
        
        # Lancer l'extraction (doit détecter les doublons et ne rien ajouter)
        pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
        
        print("📥 Test avec nouvelle logique de déduplication...")
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        # Compter après
        props_after = extractor.supabase.table('reponses').select('id').execute()
        count_after = len(props_after.data) if props_after.data else 0
        print(f"📊 Propositions après: {count_after}")
        
        difference = count_after - count_before
        print(f"📈 Différence: {difference} propositions")
        
        if difference == 0:
            print("✅ PARFAIT ! Aucun doublon ajouté")
        else:
            print(f"⚠️ {difference} propositions ajoutées (possible si des propositions manquaient)")
        
        # Validation finale stricte
        questions = extractor.supabase.table('questions').select('id, numero').eq('qcm_id', 1).execute()
        if questions.data:
            expected_total = len(questions.data) * 5
            if count_after == expected_total:
                print(f"🏆 SUCCÈS TOTAL ! Exactement {expected_total} propositions pour {len(questions.data)} questions")
            else:
                print(f"⚠️ Problème: {count_after} au lieu de {expected_total} propositions attendues")
    
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")

if __name__ == "__main__":
    clean_duplicates()
    test_strict_extraction() 