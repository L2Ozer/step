#!/usr/bin/env python3
"""
Script de correction et intégration des réponses correctes - Version 2
Objectif: Correction robuste même quand qcm_db_id n'est pas dans metadata.json
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def find_markdown_for_qcm_enhanced(qcm_id):
    """Trouve le fichier Markdown avec méthode améliorée et multiple critères"""
    print(f"🔍 Recherche avancée du Markdown pour QCM ID {qcm_id}...")
    
    try:
        extractor = QCMExtractor()
        
        # 1. D'abord, récupérer les infos du QCM depuis la base
        qcm_info = extractor.supabase.table('qcm').select('type, annee, ue_id').eq('id', qcm_id).execute()
        
        if not qcm_info.data:
            print(f"❌ QCM ID {qcm_id} non trouvé en base")
            return None
        
        qcm_data = qcm_info.data[0]
        qcm_type = qcm_data['type']
        qcm_annee = qcm_data['annee']
        ue_id = qcm_data['ue_id']
        
        # Récupérer l'UE
        ue_info = extractor.supabase.table('ue').select('numero').eq('id', ue_id).execute()
        ue_numero = ue_info.data[0]['numero'] if ue_info.data else None
        
        print(f"🎯 Recherche pour: {qcm_type} - {qcm_annee} - {ue_numero}")
        
        # 2. Chercher dans le dossier outputs par correspondance
        outputs_dir = Path("qcm_extraction/temp/outputs")
        if not outputs_dir.exists():
            print(f"⚠️ Dossier outputs non trouvé: {outputs_dir}")
            return None
        
        # Parcourir tous les sous-dossiers
        for folder in outputs_dir.iterdir():
            if folder.is_dir():
                content_file = folder / "content.md"
                metadata_file = folder / "metadata.json"
                
                if content_file.exists() and metadata_file.exists():
                    try:
                        import json
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # Méthode 1: correspondance exacte par qcm_db_id
                        if metadata.get('qcm_db_id') == qcm_id:
                            print(f"✅ Markdown trouvé par qcm_db_id: {content_file}")
                            return str(content_file)
                        
                        # Méthode 2: correspondance par type, année et UE
                        file_type = metadata.get('type')
                        file_annee = metadata.get('annee')
                        file_ue = metadata.get('ue')
                        
                        if (file_type == qcm_type and 
                            file_annee == qcm_annee and 
                            file_ue == ue_numero):
                            print(f"✅ Markdown trouvé par correspondance métadonnées: {content_file}")
                            
                            # Optionnel: mettre à jour les métadonnées avec qcm_db_id
                            metadata['qcm_db_id'] = qcm_id
                            with open(metadata_file, 'w', encoding='utf-8') as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=2)
                            print(f"📝 Métadonnées mises à jour avec qcm_db_id")
                            
                            return str(content_file)
                        
                    except Exception as e:
                        print(f"⚠️ Erreur lecture métadonnées {metadata_file}: {e}")
                        continue
        
        print(f"⚠️ Markdown non trouvé pour QCM ID {qcm_id} avec toutes les méthodes")
        return None
        
    except Exception as e:
        print(f"❌ Erreur lors de la recherche améliorée: {e}")
        return None

def extract_correct_answers_for_qcm_v2(qcm_id):
    """Version améliorée de l'extraction des réponses correctes"""
    print(f"\n🔧 EXTRACTION DES RÉPONSES CORRECTES V2 - QCM ID {qcm_id}")
    print("=" * 60)
    
    try:
        extractor = QCMExtractor()
        
        # 1. Trouver le fichier Markdown avec méthode améliorée
        markdown_path = find_markdown_for_qcm_enhanced(qcm_id)
        if not markdown_path:
            print(f"❌ Impossible de traiter QCM ID {qcm_id}: Markdown non trouvé")
            return False
        
        # 2. Lire le contenu Markdown
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        print(f"📄 Contenu Markdown chargé ({len(markdown_content)} caractères)")
        
        # 3. Afficher un échantillon du contenu pour vérifier
        print("📋 Échantillon du contenu Markdown:")
        lines = markdown_content.split('\n')
        for i, line in enumerate(lines[:10]):
            if line.strip():
                print(f"   {i+1}: {line[:100]}...")
        
        # 4. Appeler la méthode extract_correct_answers
        print("🚀 Lancement de l'extraction des réponses correctes...")
        updates_count = extractor.extract_correct_answers(markdown_content, qcm_id)
        
        # 5. Vérifier le résultat et retourner les compteurs
        return updates_count if updates_count and updates_count > 0 else 0
            
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

def detailed_verification():
    """Vérification détaillée avec exemples de réponses"""
    print("\n🔬 VÉRIFICATION DÉTAILLÉE")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # Récupérer le QCM 1
        qcm_id = 1
        questions = extractor.supabase.table('questions').select('id, numero').eq('qcm_id', qcm_id).order('numero').execute()
        
        if not questions.data:
            print(f"❌ Aucune question pour QCM ID {qcm_id}")
            return False
        
        print(f"📊 Analyse détaillée pour QCM ID {qcm_id} ({len(questions.data)} questions):")
        
        total_correct = 0
        total_props = 0
        questions_with_correct = 0
        
        # Analyser les 3 premières questions en détail
        for i, q in enumerate(questions.data[:3]):
            q_id = q['id']
            q_num = q['numero']
            
            props = extractor.supabase.table('reponses').select('lettre, est_correcte, contenu').eq('question_id', q_id).order('lettre').execute()
            
            if props.data:
                correct_count = sum(1 for p in props.data if p['est_correcte'])
                total_props += len(props.data)
                total_correct += correct_count
                
                if correct_count > 0:
                    questions_with_correct += 1
                
                print(f"\n   Question {q_num} (ID: {q_id}):")
                print(f"     Propositions: {len(props.data)}, Correctes: {correct_count}")
                
                for prop in props.data:
                    status = "✓" if prop['est_correcte'] else "✗"
                    content_preview = str(prop['contenu'])[:50] + "..." if len(str(prop['contenu'])) > 50 else str(prop['contenu'])
                    print(f"       {prop['lettre']}: {status} {content_preview}")
        
        # Statistiques globales
        for q in questions.data[3:]:
            q_id = q['id']
            props = extractor.supabase.table('reponses').select('est_correcte').eq('question_id', q_id).execute()
            
            if props.data:
                correct_count = sum(1 for p in props.data if p['est_correcte'])
                total_props += len(props.data)
                total_correct += correct_count
                
                if correct_count > 0:
                    questions_with_correct += 1
        
        percentage = (total_correct / total_props * 100) if total_props > 0 else 0
        
        print(f"\n📈 RÉSUMÉ FINAL:")
        print(f"   - Questions totales: {len(questions.data)}")
        print(f"   - Questions avec réponses correctes: {questions_with_correct}")
        print(f"   - Propositions totales: {total_props}")
        print(f"   - Réponses correctes: {total_correct}")
        print(f"   - Pourcentage: {percentage:.1f}%")
        
        if percentage > 0:
            print("✅ SUCCESS: Des réponses correctes ont été identifiées!")
            return True
        else:
            print("⚠️ PROBLÈME: Aucune réponse correcte")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale améliorée"""
    print("🚀 CORRECTION DES RÉPONSES CORRECTES V2")
    print("=" * 60)
    
    # 1. Diagnostic simple
    try:
        extractor = QCMExtractor()
        qcms = extractor.supabase.table('qcm').select('id').execute()
        
        if not qcms.data:
            print("❌ Aucun QCM en base")
            return
        
        qcm_id = qcms.data[0]['id']  # Prendre le premier QCM
        print(f"🎯 Traitement du QCM ID {qcm_id}")
        
        # 2. Extraction avec méthode améliorée
        updates_count = extract_correct_answers_for_qcm_v2(qcm_id)
        
        if updates_count:
            print(f"✅ {updates_count} réponses mises à jour!")
        else:
            print("⚠️ Aucune mise à jour")
        
        # 3. Vérification détaillée
        detailed_verification()
        
        print("\n🎯 CORRECTION TERMINÉE")
        
    except Exception as e:
        print(f"❌ Erreur principale: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 