#!/usr/bin/env python3
"""
Analyse détaillée des résultats d'extraction pour comprendre les limitations
"""

import os
import sys
import re
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def analyze_extraction_completeness():
    """Analyse détaillée de l'extraction"""
    print("🔍 ANALYSE DÉTAILLÉE DE L'EXTRACTION")
    print("=" * 60)
    
    try:
        extractor = QCMExtractor()
        
        # 1. ANALYSER LE MARKDOWN GÉNÉRÉ
        markdown_path = "qcm_extraction/temp/outputs/ue2-correction-colle1-s38-21-22-47305/content.md"
        
        if os.path.exists(markdown_path):
            with open(markdown_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            print(f"📄 Contenu Markdown: {len(content)} caractères")
            
            # Rechercher toutes les questions dans le markdown
            question_patterns = [
                r'Q\.?\s*(\d+)[\.:]',      # Q16. ou Q.16: 
                r'Question\s*(\d+)[\.:]',   # Question 16.
                r'^(\d+)[\.\)]',           # 16. ou 16) en début de ligne
                r'##\s*Q(\d+)\.',          # ## Q16.
            ]
            
            all_question_numbers = set()
            
            for pattern in question_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                numbers = [int(m) for m in matches if m.isdigit()]
                valid_numbers = [n for n in numbers if 1 <= n <= 50]
                all_question_numbers.update(valid_numbers)
            
            sorted_questions = sorted(all_question_numbers)
            print(f"✅ Questions détectées dans le Markdown: {len(sorted_questions)}")
            print(f"   Numéros: {sorted_questions}")
            
            # Vérifier spécifiquement la question 9
            if 9 in sorted_questions:
                print("🎉 Question 9 CONFIRMÉE dans le Markdown!")
            else:
                print("❌ Question 9 ABSENTE du Markdown")
            
            # 2. ANALYSER CE QUI EST DANS SUPABASE
            print(f"\n📊 COMPARAISON MARKDOWN vs SUPABASE:")
            
            questions_db = extractor.supabase.table("questions").select("numero").eq("qcm_id", 1).execute()
            if questions_db.data:
                db_numbers = sorted([q["numero"] for q in questions_db.data])
                print(f"   Supabase: {len(db_numbers)} questions - {db_numbers}")
                print(f"   Markdown: {len(sorted_questions)} questions - {sorted_questions}")
                
                # Questions dans Markdown mais pas dans Supabase
                missing_in_db = set(sorted_questions) - set(db_numbers)
                if missing_in_db:
                    print(f"⚠️ Questions dans Markdown mais PAS extraites: {sorted(missing_in_db)}")
                else:
                    print("✅ Toutes les questions du Markdown ont été extraites")
                
                # Questions dans Supabase mais pas dans Markdown
                extra_in_db = set(db_numbers) - set(sorted_questions)
                if extra_in_db:
                    print(f"🤔 Questions extraites mais pas visibles dans Markdown: {sorted(extra_in_db)}")
            
            # 3. ANALYSER LES SECTIONS DE PAGES
            print(f"\n📄 ANALYSE DES SECTIONS DE PAGES:")
            
            # Compter les pages
            page_sections = re.findall(r'^# Page \d+', content, re.MULTILINE)
            print(f"   Pages détectées: {len(page_sections)}")
            
            # Analyser chaque page
            page_matches = list(re.finditer(r'^# Page (\d+)', content, re.MULTILINE))
            
            for i, match in enumerate(page_matches):
                page_num = int(match.group(1))
                start_pos = match.end()
                end_pos = page_matches[i+1].start() if (i + 1) < len(page_matches) else len(content)
                page_content = content[start_pos:end_pos]
                
                # Compter les questions sur cette page
                page_questions = set()
                for pattern in question_patterns:
                    matches = re.findall(pattern, page_content, re.MULTILINE)
                    numbers = [int(m) for m in matches if m.isdigit()]
                    valid_numbers = [n for n in numbers if 1 <= n <= 50]
                    page_questions.update(valid_numbers)
                
                if page_questions:
                    print(f"   Page {page_num}: {len(page_questions)} questions - {sorted(page_questions)}")
                else:
                    print(f"   Page {page_num}: Aucune question détectée")
            
            # 4. RECOMMANDATIONS
            print(f"\n💡 RECOMMANDATIONS:")
            
            total_expected = 30  # Selon le contexte utilisateur
            total_found = len(sorted_questions)
            
            if total_found < total_expected:
                missing_count = total_expected - total_found
                print(f"⚠️ {missing_count} questions manquent encore")
                print("   - Vérifiez si l'API de vision a besoin d'améliorations")
                print("   - Possibilité que le PDF n'ait réellement que cette quantité de questions")
                
                # Analyser si on a une séquence complète
                if sorted_questions:
                    expected_range = list(range(min(sorted_questions), max(sorted_questions) + 1))
                    missing_in_sequence = set(expected_range) - set(sorted_questions)
                    if missing_in_sequence:
                        print(f"   - Questions manquantes dans la séquence: {sorted(missing_in_sequence)}")
            
            elif total_found == total_expected:
                print("🎉 EXTRACTION COMPLÈTE! Toutes les questions sont présentes")
            
            else:
                print(f"🤔 Plus de questions trouvées que prévu ({total_found} vs {total_expected})")
        
        else:
            print(f"❌ Fichier Markdown non trouvé: {markdown_path}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_extraction_completeness() 