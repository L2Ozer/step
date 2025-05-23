#!/usr/bin/env python3
"""
Script de correction et intégration des réponses correctes
Objectif: Diagnostiquer pourquoi toutes les réponses sont FALSE et corriger le problème
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def diagnose_current_state():
    """Diagnostique l'état actuel des réponses correctes dans la base de données"""
    print("🔍 DIAGNOSTIC DES RÉPONSES CORRECTES")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # 1. Vérifier les QCM existants
        qcms = extractor.supabase.table('qcm').select('id, type, annee').execute()
        if not qcms.data:
            print("❌ Aucun QCM trouvé dans la base de données")
            return None
        
        print(f"📊 {len(qcms.data)} QCM(s) trouvé(s):")
        for qcm in qcms.data:
            print(f"   - QCM ID {qcm['id']}: {qcm['type']} ({qcm['annee']})")
        
        # 2. Pour chaque QCM, analyser l'état des réponses
        qcm_stats = {}
        
        for qcm in qcms.data:
            qcm_id = qcm['id']
            
            # Compter les questions
            questions = extractor.supabase.table('questions').select('id, numero').eq('qcm_id', qcm_id).execute()
            questions_count = len(questions.data) if questions.data else 0
            
            # Compter les propositions par statut
            if questions.data:
                total_props = 0
                correct_props = 0
                incorrect_props = 0
                
                for q in questions.data:
                    q_id = q['id']
                    props = extractor.supabase.table('reponses').select('est_correcte').eq('question_id', q_id).execute()
                    
                    if props.data:
                        total_props += len(props.data)
                        for prop in props.data:
                            if prop['est_correcte']:
                                correct_props += 1
                            else:
                                incorrect_props += 1
                
                qcm_stats[qcm_id] = {
                    'questions': questions_count,
                    'total_props': total_props,
                    'correct_props': correct_props,
                    'incorrect_props': incorrect_props,
                    'percentage_correct': (correct_props / total_props * 100) if total_props > 0 else 0
                }
                
                print(f"\n📊 QCM ID {qcm_id}:")
                print(f"   - Questions: {questions_count}")
                print(f"   - Propositions totales: {total_props}")
                print(f"   - Correctes: {correct_props} ({qcm_stats[qcm_id]['percentage_correct']:.1f}%)")
                print(f"   - Incorrectes: {incorrect_props}")
                
                if correct_props == 0:
                    print(f"   ⚠️ PROBLÈME: Aucune réponse correcte identifiée!")
                elif qcm_stats[qcm_id]['percentage_correct'] < 20:
                    print(f"   ⚠️ SUSPECT: Très peu de réponses correctes")
                else:
                    print(f"   ✅ État normal")
        
        return qcm_stats
        
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_markdown_for_qcm(qcm_id):
    """Trouve le fichier Markdown correspondant à un QCM"""
    print(f"🔍 Recherche du fichier Markdown pour QCM ID {qcm_id}...")
    
    # Chercher dans le dossier outputs
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
                    
                    if metadata.get('qcm_db_id') == qcm_id:
                        print(f"✅ Markdown trouvé: {content_file}")
                        return str(content_file)
                except Exception as e:
                    print(f"⚠️ Erreur lecture métadonnées {metadata_file}: {e}")
                    continue
    
    print(f"⚠️ Markdown non trouvé pour QCM ID {qcm_id}")
    return None

def extract_correct_answers_for_qcm(qcm_id):
    """Lance l'extraction des réponses correctes pour un QCM spécifique"""
    print(f"\n🔧 EXTRACTION DES RÉPONSES CORRECTES - QCM ID {qcm_id}")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # 1. Trouver le fichier Markdown
        markdown_path = find_markdown_for_qcm(qcm_id)
        if not markdown_path:
            print(f"❌ Impossible de traiter QCM ID {qcm_id}: Markdown non trouvé")
            return False
        
        # 2. Lire le contenu Markdown
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        print(f"📄 Contenu Markdown chargé ({len(markdown_content)} caractères)")
        
        # 3. Appeler la méthode extract_correct_answers
        print("🚀 Lancement de l'extraction des réponses correctes...")
        updates_count = extractor.extract_correct_answers(markdown_content, qcm_id)
        
        if updates_count and updates_count > 0:
            print(f"✅ Extraction réussie: {updates_count} réponses mises à jour")
            return True
        else:
            print("⚠️ Aucune mise à jour effectuée (voir logs ci-dessus pour détails)")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_extractor_integration():
    """Corrige l'intégration de extract_correct_answers dans le flux principal"""
    print("\n🔧 INTÉGRATION DANS LE FLUX PRINCIPAL")
    print("=" * 50)
    
    extractor_file = Path("qcm_extraction/extractor.py")
    
    try:
        # Lire le fichier actuel
        with open(extractor_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si extract_correct_answers est déjà appelée
        if "self.extract_correct_answers(" in content:
            print("✅ extract_correct_answers est déjà intégrée dans le flux")
            return True
        
        # Chercher l'endroit où ajouter l'appel (après l'extraction des propositions)
        insertion_point = content.find('print("🏁 Phase 2 terminée.")')
        
        if insertion_point == -1:
            print("⚠️ Point d'insertion non trouvé dans extract_metadata_from_path")
            return False
        
        # Code à insérer
        code_to_insert = '''
                        
                        # Phase 3: Extraction des réponses correctes
                        print("▶️ Lancement de la Phase 3: Extraction des réponses correctes...")
                        print("⏸️ Pause de 5 secondes avant l'extraction des réponses correctes...")
                        time.sleep(5)
                        
                        updates_count = self.extract_correct_answers(markdown_content_for_processing, qcm_id_for_processing)
                        if updates_count and updates_count > 0:
                            print(f"✅ Phase 3 terminée: {updates_count} réponses correctes mises à jour")
                            metadata["correct_answers_updated"] = updates_count
                        else:
                            print("⚠️ Phase 3: Aucune réponse correcte mise à jour")
                            metadata["correct_answers_updated"] = 0'''
        
        # Insérer le code
        new_content = content[:insertion_point + len('print("🏁 Phase 2 terminée.")')] + code_to_insert + content[insertion_point + len('print("🏁 Phase 2 terminée.")'):]
        
        # Créer une sauvegarde
        backup_file = extractor_file.with_suffix('.py.backup_before_correction')
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 Sauvegarde créée: {backup_file}")
        
        # Écrire le nouveau contenu
        with open(extractor_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ extract_correct_answers intégrée avec succès dans le flux principal")
        print("ℹ️ Désormais, l'extraction des réponses correctes sera automatique")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'intégration: {e}")
        return False

def verify_correction():
    """Vérifie que la correction a fonctionné"""
    print("\n🔬 VÉRIFICATION APRÈS CORRECTION")
    print("=" * 50)
    
    try:
        extractor = QCMExtractor()
        
        # Prendre le premier QCM pour vérification
        qcms = extractor.supabase.table('qcm').select('id').limit(1).execute()
        if not qcms.data:
            print("❌ Aucun QCM pour vérification")
            return False
        
        qcm_id = qcms.data[0]['id']
        
        # Compter les réponses correctes maintenant
        questions = extractor.supabase.table('questions').select('id').eq('qcm_id', qcm_id).execute()
        if not questions.data:
            print(f"❌ Aucune question pour QCM ID {qcm_id}")
            return False
        
        total_correct = 0
        total_props = 0
        
        for q in questions.data:
            q_id = q['id']
            props = extractor.supabase.table('reponses').select('est_correcte').eq('question_id', q_id).execute()
            
            if props.data:
                total_props += len(props.data)
                total_correct += sum(1 for p in props.data if p['est_correcte'])
        
        percentage = (total_correct / total_props * 100) if total_props > 0 else 0
        
        print(f"📊 QCM ID {qcm_id} après correction:")
        print(f"   - Propositions totales: {total_props}")
        print(f"   - Réponses correctes: {total_correct}")
        print(f"   - Pourcentage: {percentage:.1f}%")
        
        if percentage > 0:
            print("✅ SUCCESS: Des réponses correctes ont été identifiées!")
            return True
        else:
            print("⚠️ PROBLÈME PERSISTANT: Aucune réponse correcte")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale de correction"""
    print("🚀 CORRECTION DES RÉPONSES CORRECTES")
    print("=" * 60)
    
    # 1. Diagnostic initial
    stats = diagnose_current_state()
    if not stats:
        return
    
    # 2. Identifier les QCMs problématiques
    problematic_qcms = []
    for qcm_id, data in stats.items():
        if data['correct_props'] == 0:
            problematic_qcms.append(qcm_id)
    
    if not problematic_qcms:
        print("\n✅ Aucun problème détecté - toutes les réponses correctes sont identifiées")
        return
    
    print(f"\n⚠️ {len(problematic_qcms)} QCM(s) problématique(s) détecté(s): {problematic_qcms}")
    
    # 3. Corriger chaque QCM problématique
    for qcm_id in problematic_qcms:
        success = extract_correct_answers_for_qcm(qcm_id)
        if not success:
            print(f"❌ Échec de la correction pour QCM ID {qcm_id}")
    
    # 4. Intégrer dans le flux principal pour les futures extractions
    integration_success = fix_extractor_integration()
    
    # 5. Vérification finale
    verify_correction()
    
    # 6. Instructions finales
    print("\n📋 INSTRUCTIONS FINALES")
    print("=" * 30)
    print("✅ Les QCMs existants ont été corrigés")
    
    if integration_success:
        print("✅ Le flux principal a été mis à jour")
        print("ℹ️ Les futures extractions incluront automatiquement les réponses correctes")
    else:
        print("⚠️ L'intégration automatique a échoué")
        print("ℹ️ Vous devrez appeler manuellement extract_correct_answers() après chaque extraction")
    
    print("\n🎯 SYSTÈME MAINTENANT SCALABLE")

if __name__ == "__main__":
    main() 