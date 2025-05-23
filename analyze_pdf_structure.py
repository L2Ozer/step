#!/usr/bin/env python3

import re
import requests
import os
from pathlib import Path

def download_and_analyze():
    """Télécharge et analyse directement le PDF pour comprendre sa structure"""
    print("🔍 ANALYSE DIRECTE DE LA STRUCTURE DU PDF")
    print("=" * 60)
    
    # URL du PDF
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    # Utiliser le markdown déjà extrait s'il existe
    markdown_path = "qcm_extraction/temp/outputs/ue2-correction-colle1-s38-21-22-47305/content.md"
    
    if not os.path.exists(markdown_path):
        print("❌ Fichier markdown non trouvé. Utilisez d'abord l'extracteur pour générer le markdown.")
        return
    
    # Lire le contenu markdown
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"📄 Markdown lu: {len(content)} caractères")
    
    # 1. ANALYSER LES NUMÉROS DE QUESTIONS
    print("\n1️⃣ ANALYSE DES NUMÉROS DE QUESTIONS")
    print("-" * 40)
    
    # Patterns pour détecter les questions
    question_patterns = [
        r'Q\.?\s*(\d+)[\.:]',      # Q16. ou Q.16: 
        r'Question\s*(\d+)[\.:]',   # Question 16.
        r'^(\d+)[\.\)]',           # 16. ou 16) en début de ligne
        r'##\s*Q(\d+)\.',          # ## Q16.
    ]
    
    all_question_numbers = set()
    
    for i, pattern in enumerate(question_patterns):
        matches = re.findall(pattern, content, re.MULTILINE)
        numbers = [int(m) for m in matches if m.isdigit()]
        valid_numbers = [n for n in numbers if 1 <= n <= 50]  # Filtre raisonnable
        
        print(f"Pattern {i+1} ({pattern}): {len(valid_numbers)} questions trouvées")
        if valid_numbers:
            print(f"   Numéros: {sorted(set(valid_numbers))}")
        
        all_question_numbers.update(valid_numbers)
    
    print(f"\n📊 TOTAL: {len(all_question_numbers)} questions uniques détectées")
    sorted_questions = sorted(all_question_numbers)
    print(f"   Numéros: {sorted_questions}")
    
    # Vérifier les trous dans la séquence
    if sorted_questions:
        expected_range = list(range(min(sorted_questions), max(sorted_questions) + 1))
        missing = [n for n in expected_range if n not in sorted_questions]
        
        if missing:
            print(f"⚠️ Questions manquantes dans la séquence: {missing}")
        else:
            print("✅ Séquence complète de questions")
    
    # 2. RECHERCHE SPÉCIFIQUE DE LA QUESTION 9
    print("\n2️⃣ RECHERCHE SPÉCIFIQUE DE LA QUESTION 9")
    print("-" * 40)
    
    # Chercher tous les "9" avec contexte
    nine_contexts = []
    for match in re.finditer(r'.{50}9.{100}', content):
        context = match.group().replace('\n', ' ')
        nine_contexts.append({
            'position': match.start() + 50,
            'context': context,
            'is_question': any(keyword in context.lower() for keyword in ['question', 'q9', 'soit', 'calcul'])
        })
    
    print(f"🔍 Trouvé {len(nine_contexts)} occurrences du chiffre '9':")
    
    for i, ctx in enumerate(nine_contexts):
        status = "🎯 QUESTION POTENTIELLE" if ctx['is_question'] else "ℹ️ Contexte"
        print(f"\n{i+1}. {status} (pos {ctx['position']}):")
        print(f"   ...{ctx['context']}...")
    
    # 3. ANALYSER LES PROPOSITIONS
    print("\n3️⃣ ANALYSE DES PROPOSITIONS")
    print("-" * 40)
    
    # Compter les propositions par question
    propositions_by_question = {}
    
    # Patterns pour les propositions
    prop_patterns = [
        r'([A-E])\.\s+([^\n]+)',   # A. texte
        r'([A-E])\)\s+([^\n]+)',   # A) texte  
        r'([A-E]):\s+([^\n]+)',    # A: texte
        r'([A-E])\s+([^\n]+?)(?=[A-E]\.|\n\n|$)',  # A texte (sans ponctuation)
    ]
    
    all_props = []
    for pattern in prop_patterns:
        matches = re.findall(pattern, content)
        all_props.extend(matches)
    
    print(f"🔍 Total: {len(all_props)} propositions détectées")
    
    # Grouper par lettre
    props_by_letter = {}
    for letter, text in all_props:
        if letter not in props_by_letter:
            props_by_letter[letter] = 0
        props_by_letter[letter] += 1
    
    print("📊 Répartition par lettre:")
    for letter in ['A', 'B', 'C', 'D', 'E']:
        count = props_by_letter.get(letter, 0)
        print(f"   {letter}: {count} propositions")
    
    # 4. CALCUL DE LA COMPLÉTUDE THÉORIQUE
    print("\n4️⃣ CALCUL DE LA COMPLÉTUDE")
    print("-" * 40)
    
    if sorted_questions:
        num_questions = len(sorted_questions)
        expected_props = num_questions * 5
        actual_props = len(all_props)
        completeness = (actual_props / expected_props) * 100 if expected_props > 0 else 0
        
        print(f"📊 Questions détectées: {num_questions}")
        print(f"📊 Propositions attendues: {expected_props} (5 par question)")
        print(f"📊 Propositions détectées: {actual_props}")
        print(f"📊 Complétude: {completeness:.1f}%")
        
        if completeness > 100:
            excess = actual_props - expected_props
            print(f"⚠️ SURPLUS: {excess} propositions en trop (doublons probables)")
        elif completeness < 100:
            deficit = expected_props - actual_props
            print(f"⚠️ DÉFICIT: {deficit} propositions manquantes")
        else:
            print("🎉 PARFAIT: Nombre exact de propositions!")
    
    # 5. RECOMMANDATIONS
    print("\n5️⃣ RECOMMANDATIONS")
    print("-" * 40)
    
    if 9 not in all_question_numbers:
        print("❌ CONFIRME: La question 9 n'existe pas dans ce PDF")
        print("   ✅ SOLUTION: Ajuster l'attente à 29 questions au lieu de 30")
    
    if len(all_props) > len(sorted_questions) * 5:
        print("⚠️ PROBLÈME: Propositions dupliquées détectées")
        print("   ✅ SOLUTION: Améliorer la déduplication lors de l'extraction")
    
    # Calculer les attentes réalistes
    realistic_questions = len(sorted_questions)
    realistic_props = realistic_questions * 5
    
    print(f"\n🎯 ATTENTES RÉALISTES pour ce PDF:")
    print(f"   - Questions: {realistic_questions}")
    print(f"   - Propositions: {realistic_props}")
    print(f"   - Questions présentes: {sorted_questions}")

if __name__ == "__main__":
    download_and_analyze() 