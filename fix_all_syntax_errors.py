#!/usr/bin/env python3
import re
import ast

def fix_all_syntax_errors():
    file_path = "qcm_extraction/extractor.py"
    
    print("🔧 Lecture du fichier et correction des erreurs de syntaxe...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Corriger les regex mal échappées (remplacer \\d+ par \d+, etc.)
    print("1. Correction des regex mal échappées...")
    content = re.sub(r'\\\\([dswDSW]\+)', r'\\\1', content)
    content = re.sub(r'\\\\([.()[\]{}+*?^$|])', r'\\\1', content)
    
    # 2. Corriger les indentations dans les blocs try/except
    print("2. Correction des blocs try/except...")
    
    # 3. Corriger le continue mal indenté  
    print("3. Correction du continue mal indenté...")
    content = re.sub(
        r'(\s+)# Si la question n\'a pas de numéro, la sauter\n\s+if "numero_question" not in q or not q\["numero_question"\]:\n\s+continue',
        r'\1# Si la question n\'a pas de numéro, la sauter\n\1if "numero_question" not in q or not q["numero_question"]:\n\1    continue',
        content
    )
    
    # 4. Corriger les blocs saved_questions_details.append mal indentés
    print("4. Correction des blocs saved_questions_details.append...")
    content = re.sub(
        r'(\s+)# Question existante, ajouter ses détails \(y compris l\'UUID de la BD\)\n\s+saved_questions_details\.append\(\{\n\s+"db_uuid": existing_questions_db\[numero\]\["uuid"\], # Important: UUID de la BD\n\s+"db_id": existing_questions_db\[numero\]\["id"\],     # ID entier de la BD\n\s+"qcm_id": qcm_id,',
        r'\1# Question existante, ajouter ses détails (y compris l\'UUID de la BD)\n\1saved_questions_details.append({\n\1    "db_uuid": existing_questions_db[numero]["uuid"], # Important: UUID de la BD\n\1    "db_id": existing_questions_db[numero]["id"],     # ID entier de la BD\n\1    "qcm_id": qcm_id,',
        content
    )
    
    # 5. Corriger les boucles for dans l'insertion de questions
    print("5. Correction des boucles d'insertion...")
    content = re.sub(
        r'(\s+)for q_inserted in insert_result\.data:\n\s+saved_questions_details\.append\(\{\n\s+"db_uuid": q_inserted\.get\("uuid"\),',
        r'\1for q_inserted in insert_result.data:\n\1    saved_questions_details.append({\n\1        "db_uuid": q_inserted.get("uuid"),',
        content
    )
    
    # 6. Corriger les else mal placés
    print("6. Correction des else mal placés...")
    content = re.sub(
        r'(\s+)except Exception as e_insert_q_new:\n\s+print\(f"    🔥 Erreur lors de l\'insertion de NOUVELLES questions: \{str\(e_insert_q_new\)\}"\)\n\s+else:\n\s+print\("    ℹ️ Aucune nouvelle question à insérer\. Toutes les questions extraites existaient déjà\."\)',
        r'\1    except Exception as e_insert_q_new:\n\1        print(f"    🔥 Erreur lors de l\'insertion de NOUVELLES questions: {str(e_insert_q_new)}")\n\1else:\n\1    print("    ℹ️ Aucune nouvelle question à insérer. Toutes les questions extraites existaient déjà.")',
        content
    )
    
    # 7. Corriger les return mal indentés
    print("7. Correction des return mal indentés...")
    content = re.sub(
        r'(\s+)print\("   Assurez-vous que _extract_and_save_questions_only retourne des détails valides avec \'numero\' et \'db_id\'\."\)\n\s+return',
        r'\1print("   Assurez-vous que _extract_and_save_questions_only retourne des détails valides avec \'numero\' et \'db_id\'.")\n\1return',
        content
    )
    
    # 8. Correction spécifique des regex dans _get_correct_answers_with_chat_api
    print("8. Correction des regex dans _get_correct_answers_with_chat_api...")
    
    # Corriger les patterns problématiques
    fixes = [
        (r'vrai_faux_pattern = r\'(?:Question\\\\s+)?\\\\(\\\\d+\\\\)\\\\[\\\\.:\\\\)]\\\\s*(?:[^\\\\n]+\\\\n+)?\\\\([A-E]\\\\)\\\\.?\\\\s+\\\\([Vv]rai|[Ff]aux|[Jj]uste|[Cc]orrect|[Ee]xact\\\\)\'',
         r'vrai_faux_pattern = r\'(?:Question\\s+)?(\\d+)[\\.:\\)]\\s*(?:[^\\n]+\\n+)?([A-E])\\.?\\s+([Vv]rai|[Ff]aux|[Jj]uste|[Cc]orrect|[Ee]xact)\''),
        
        (r'multi_answer_pattern = r\'(?:Question\\\\s+)?\\\\(\\\\d+\\\\)\\\\s*\\\\[\\\\.:\\\\)]\\\\s*\\\\([A-E][,\\\\s]*(?:[A-E][,\\\\s]*)*\\\\)\'',
         r'multi_answer_pattern = r\'(?:Question\\s+)?(\\d+)\\s*[\\.:\\)]\\s*([A-E][,\\s]*(?:[A-E][,\\s]*)*)\'''),
        
        (r'question_pattern_deduction = r\'(?:Question|Q\\\\.\\\\?)?\\\\s*\\\\(\\\\d+\\\\)(?:\\\\s*:|\\\\.|\\\\\\\\)\\\\)\' # Correction ici: \\\\\\\\)',
         r'question_pattern_deduction = r\'(?:Question|Q\\.?)?\\s*(\\d+)(?:\\s*:|\\.|\\\))\''),
        
        (r'proposition_pattern_deduction = r\'\\\\([A-E]\\\\)\\\\.\\\\?\\\\s+\\\\([Ff]aux\\\\)\' # Cherche explicitement "Faux"',
         r'proposition_pattern_deduction = r\'([A-E])\\.?\\s+([Ff]aux)\' # Cherche explicitement "Faux"'),
    ]
    
    for old_pattern, new_pattern in fixes:
        content = re.sub(re.escape(old_pattern.replace('\\\\', '\\')), new_pattern, content)
    
    # 9. Corriger les indentations générales
    print("9. Correction des indentations générales...")
    
    # Corriger les blocs if/elif/else mal indentés
    lines = content.split('\n')
    corrected_lines = []
    
    for i, line in enumerate(lines):
        # Vérifier s'il y a des problèmes d'indentation évidents
        if line.strip().startswith('if ') or line.strip().startswith('elif ') or line.strip().startswith('else:'):
            # Vérifier l'indentation de la ligne précédente pour déterminer le bon niveau
            if i > 0:
                prev_line = lines[i-1]
                if prev_line.strip() and not prev_line.strip().endswith(':'):
                    # Maintenir le même niveau d'indentation que la ligne précédente
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent != prev_indent:
                        line = ' ' * prev_indent + line.strip()
        
        corrected_lines.append(line)
    
    content = '\n'.join(corrected_lines)
    
    # 10. Écrire le fichier corrigé
    print("10. Écriture du fichier corrigé...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 11. Vérifier la syntaxe
    print("11. Vérification de la syntaxe...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            test_content = f.read()
        ast.parse(test_content)
        print("✅ Syntaxe Python valide!")
        return True
    except SyntaxError as e:
        print(f"❌ Erreur de syntaxe restante: {e}")
        print(f"   Ligne {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Autre erreur: {e}")
        return False

if __name__ == "__main__":
    success = fix_all_syntax_errors()
    if success:
        print("\n🎉 Toutes les corrections ont été appliquées avec succès!")
        print("Vous pouvez maintenant lancer 'python run_test.py' avec n'importe quel PDF.")
    else:
        print("\n⚠️ Certaines erreurs persistent. Vérification manuelle nécessaire.") 