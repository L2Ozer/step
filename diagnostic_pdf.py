#!/usr/bin/env python3
"""
Script de diagnostic pour analyser les problèmes d'extraction dans un PDF
Permet d'identifier pourquoi certaines questions ou propositions sont manquantes
"""

import os
import sys
import re
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def diagnostic_question_manquante(markdown_content: str, question_num: int):
    """Diagnostic spécifique pour une question manquante"""
    print(f"\n🔍 DIAGNOSTIC: Question {question_num}")
    print("-" * 30)
    
    # Patterns de recherche pour la question
    patterns = [
        rf'Q\.?\s*{question_num}[\.:\)]',
        rf'Question\s*{question_num}[\.:\)]',
        rf'{question_num}\.(?!\d)',  # Éviter 19.5 etc.
        rf'{question_num}\)',
        rf'{question_num}:',
        rf'Q{question_num}[^0-9]',
    ]
    
    found_positions = []
    
    for i, pattern in enumerate(patterns):
        matches = list(re.finditer(pattern, markdown_content, re.IGNORECASE))
        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(markdown_content), match.end() + 200)
            context = markdown_content[start:end].replace('\n', ' ')
            found_positions.append({
                'pattern': i + 1,
                'position': match.start(),
                'context': context,
                'match': match.group()
            })
    
    if found_positions:
        print(f"✅ Question {question_num} trouvée {len(found_positions)} fois:")
        for fp in found_positions:
            print(f"  Pattern {fp['pattern']}: '{fp['match']}' à pos {fp['position']}")
            print(f"    Contexte: ...{fp['context']}...")
        
        # Analyser pourquoi elle n'a pas été extraite
        print("\n🤔 Analyse des raisons possibles:")
        print("  - Vérifiez si le texte de la question suit immédiatement")
        print("  - Vérifiez s'il y a des caractères spéciaux ou formatage étrange")
        print("  - Vérifiez si la question est coupée entre plusieurs pages")
    else:
        print(f"❌ Question {question_num} NON TROUVÉE dans le texte")
        
        # Recherche de variations possibles
        print("\n🔍 Recherche de variations possibles...")
        variations = [
            rf'{question_num}ème',
            rf'{question_num}e',
            rf'question\s*{question_num}',
            rf'n°\s*{question_num}',
        ]
        
        for var in variations:
            matches = list(re.finditer(var, markdown_content, re.IGNORECASE))
            if matches:
                for match in matches:
                    start = max(0, match.start() - 30)
                    end = min(len(markdown_content), match.end() + 100)
                    context = markdown_content[start:end].replace('\n', ' ')
                    print(f"  Trouvé variation: '{match.group()}' -> ...{context}...")

def diagnostic_propositions_manquantes(markdown_content: str, question_num: int):
    """Diagnostic pour les propositions manquantes d'une question"""
    print(f"\n🔍 DIAGNOSTIC: Propositions de la question {question_num}")
    print("-" * 40)
    
    # Trouver la position de la question
    question_pos = None
    question_patterns = [
        rf'Q\.?\s*{question_num}[\.:\)]',
        rf'Question\s*{question_num}[\.:\)]',
        rf'{question_num}\.',
    ]
    
    for pattern in question_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            question_pos = match.start()
            break
    
    if question_pos is None:
        print(f"❌ Impossible de localiser la question {question_num}")
        return
    
    # Analyser une zone autour de la question (2000 caractères)
    search_zone = markdown_content[question_pos:question_pos + 2000]
    
    print(f"📍 Question trouvée à la position {question_pos}")
    print("🔍 Recherche des propositions A, B, C, D, E...")
    
    found_props = {}
    missing_props = []
    
    for letter in "ABCDE":
        patterns = [
            rf'{letter}\.\s*([^\n]*?)(?=[A-E]\.|\n\n|$)',
            rf'{letter}\)\s*([^\n]*?)(?=[A-E]\)|\n\n|$)',
            rf'{letter}\s*:\s*([^\n]*?)(?=[A-E]\s*:|\n\n|$)',
            rf'{letter}\s*-\s*([^\n]*?)(?=[A-E]\s*-|\n\n|$)',
            rf'{letter}\s+([^\n]*?)(?=[A-E]\s|\n\n|$)'
        ]
        
        found = False
        for pattern in patterns:
            match = re.search(pattern, search_zone, re.IGNORECASE)
            if match:
                prop_text = match.group(1).strip()
                if len(prop_text) > 3:
                    found_props[letter] = prop_text[:50] + "..." if len(prop_text) > 50 else prop_text
                    found = True
                    break
        
        if not found:
            missing_props.append(letter)
    
    # Afficher les résultats
    print(f"\n✅ Propositions trouvées ({len(found_props)}/5):")
    for letter, text in found_props.items():
        print(f"  {letter}: {text}")
    
    if missing_props:
        print(f"\n❌ Propositions manquantes: {missing_props}")
        print("\n🔍 Recherche étendue dans la zone...")
        
        # Afficher le contexte brut pour inspection manuelle
        print("\n📄 Contexte brut (premiers 500 caractères):")
        print(search_zone[:500])
        print("\n📄 Contexte brut (derniers 500 caractères):")
        print(search_zone[-500:])
    else:
        print("\n🎉 Toutes les propositions trouvées!")

def run_full_diagnostic():
    """Diagnostic complet du PDF"""
    print("🔬 DIAGNOSTIC COMPLET DU PDF")
    print("=" * 50)
    
    # URL du PDF de test
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Initialiser l'extracteur
        extractor = QCMExtractor()
        
        # Télécharger et convertir en markdown
        print("📥 Téléchargement et conversion du PDF...")
        pdf_path = extractor.download_pdf(pdf_url)
        markdown_path = extractor.convert_pdf_to_markdown(pdf_path, pdf_url)
        
        if not markdown_path:
            print("❌ Échec de la conversion en markdown")
            return
        
        # Lire le contenu markdown
        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        
        print(f"📄 Markdown généré: {len(markdown_content)} caractères")
        
        # Diagnostic général
        print("\n🔍 ANALYSE GÉNÉRALE:")
        print(f"  - Longueur du texte: {len(markdown_content)} caractères")
        lines_count = len(markdown_content.split('\n'))
        print(f"  - Nombre de lignes: {lines_count}")
        
        # Détecter les pages
        pages = re.findall(r'^# Page \d+', markdown_content, re.MULTILINE)
        print(f"  - Pages détectées: {len(pages)}")
        
        # Détecter tous les numéros de questions
        all_question_matches = re.findall(r'(?:Q\.?\s*(\d+)|Question\s*(\d+)|(\d+)\.)', markdown_content, re.IGNORECASE)
        detected_numbers = set()
        for match in all_question_matches:
            for group in match:
                if group:
                    try:
                        num = int(group)
                        if 1 <= num <= 50:  # Filtre raisonnable
                            detected_numbers.add(num)
                    except ValueError:
                        pass
        
        detected_numbers = sorted(detected_numbers)
        print(f"  - Numéros de questions détectés: {detected_numbers}")
        
        if detected_numbers:
            expected_range = list(range(min(detected_numbers), max(detected_numbers) + 1))
            missing_in_sequence = set(expected_range) - set(detected_numbers)
            if missing_in_sequence:
                print(f"  - Questions manquantes dans la séquence: {sorted(missing_in_sequence)}")
            else:
                print("  - ✅ Séquence de questions complète")
        
        # Diagnostic spécifique pour la question 9
        if 9 not in detected_numbers:
            diagnostic_question_manquante(markdown_content, 9)
        else:
            print("\n✅ Question 9 détectée dans l'analyse générale")
            diagnostic_propositions_manquantes(markdown_content, 9)
        
        # Diagnostic pour quelques autres questions critiques
        critical_questions = [1, 15, 16, 20, 25, 30]
        for q_num in critical_questions:
            if q_num not in detected_numbers:
                diagnostic_question_manquante(markdown_content, q_num)
            else:
                # Vérification rapide des propositions
                question_pos = None
                for pattern in [rf'Q\.?\s*{q_num}[\.:\)]', rf'{q_num}\.']:
                    match = re.search(pattern, markdown_content, re.IGNORECASE)
                    if match:
                        question_pos = match.start()
                        break
                
                if question_pos:
                    search_zone = markdown_content[question_pos:question_pos + 1000]
                    props_found = len(re.findall(r'[A-E]\.', search_zone))
                    print(f"✅ Question {q_num}: ~{props_found} propositions détectées")
        
        print("\n🎯 RECOMMANDATIONS:")
        print("1. Vérifiez les questions manquantes identifiées ci-dessus")
        print("2. Examinez le formatage des questions problématiques")
        print("3. Vérifiez si certaines questions sont coupées entre les pages")
        print("4. Relancez l'extraction après corrections si nécessaire")
        
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_full_diagnostic() 