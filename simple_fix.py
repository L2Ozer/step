#!/usr/bin/env python3
import re

def simple_fix():
    file_path = "qcm_extraction/extractor.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Correction spécifique de la ligne 947 - continue mal indenté
    content = content.replace(
        '                        if "numero_question" not in q or not q["numero_question"]:\n                    continue',
        '                        if "numero_question" not in q or not q["numero_question"]:\n                            continue'
    )
    
    # 2. Correction des blocs avec des lignes vides mal placées
    # Chercher et corriger les patterns spécifiques problématiques
    content = re.sub(
        r'(\s+)# Question existante, ajouter ses détails \(y compris l\'UUID de la BD\)\n\s+saved_questions_details\.append\(\{\n\s+"db_uuid"',
        r'\1# Question existante, ajouter ses détails (y compris l\'UUID de la BD)\n\1saved_questions_details.append({\n\1    "db_uuid"',
        content
    )
    
    # 3. Correction des else mal alignés
    content = re.sub(
        r'(\s+)else:\n(\s+)print\("    ℹ️ Aucune nouvelle question à insérer\. Toutes les questions extraites existaient déjà\."\)',
        r'\1else:\n\1    print("    ℹ️ Aucune nouvelle question à insérer. Toutes les questions extraites existaient déjà.")',
        content
    )
    
    # 4. Correction simple des return mal indentés
    content = re.sub(
        r'(\s+)return\n(\s+)$',
        r'\1return\n',
        content, flags=re.MULTILINE
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Corrections simples appliquées!")

if __name__ == "__main__":
    simple_fix() 