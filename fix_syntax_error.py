#!/usr/bin/env python3
import re

def fix_syntax_errors():
    file_path = "qcm_extraction/extractor.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Corrections spécifiques pour les erreurs d'indentation
    
    # 1. Corriger le continue mal indenté
    content = re.sub(
        r'(\s+)# Si la question n\'a pas de numéro, la sauter\n(\s+)if "numero_question" not in q or not q\["numero_question"\]:\n(\s+)continue',
        r'\1# Si la question n\'a pas de numéro, la sauter\n\1if "numero_question" not in q or not q["numero_question"]:\n\1    continue',
        content
    )
    
    # 2. Corriger les lignes avec mauvais alignement dans saved_questions_details.append
    content = re.sub(
        r'(\s+)# Question existante, ajouter ses détails \(y compris l\'UUID de la BD\)\n(\s+)saved_questions_details\.append\(\{\n(\s+)"db_uuid": existing_questions_db\[numero\]\["uuid"\], # Important: UUID de la BD\n(\s+)"db_id": existing_questions_db\[numero\]\["id"\],     # ID entier de la BD\n(\s+)"qcm_id": qcm_id,',
        r'\1# Question existante, ajouter ses détails (y compris l\'UUID de la BD)\n\1saved_questions_details.append({\n\1    "db_uuid": existing_questions_db[numero]["uuid"], # Important: UUID de la BD\n\1    "db_id": existing_questions_db[numero]["id"],     # ID entier de la BD\n\1    "qcm_id": qcm_id,',
        content
    )
    
    # 3. Corriger les indentations dans la boucle d'insertion
    content = re.sub(
        r'(\s+)for q_inserted in insert_result\.data:\n(\s+)saved_questions_details\.append\(\{\n(\s+)"db_uuid": q_inserted\.get\("uuid"\),',
        r'\1for q_inserted in insert_result.data:\n\1    saved_questions_details.append({\n\1        "db_uuid": q_inserted.get("uuid"),',
        content
    )
    
    # 4. Corriger le else mal placé
    content = re.sub(
        r'(\s+)except Exception as e_insert_q_new:\n(\s+)print\(f"    🔥 Erreur lors de l\'insertion de NOUVELLES questions: \{str\(e_insert_q_new\)\}"\)\n(\s+)else:\n(\s+)print\("    ℹ️ Aucune nouvelle question à insérer\. Toutes les questions extraites existaient déjà\."\)',
        r'\1    except Exception as e_insert_q_new:\n\1        print(f"    🔥 Erreur lors de l\'insertion de NOUVELLES questions: {str(e_insert_q_new)}")\n\1else:\n\1    print("    ℹ️ Aucune nouvelle question à insérer. Toutes les questions extraites existaient déjà.")',
        content
    )
    
    # 5. Corriger le return mal indenté
    content = re.sub(
        r'(\s+)print\("   Assurez-vous que _extract_and_save_questions_only retourne des détails valides avec \'numero\' et \'db_id\'\."\)\n(\s+)return',
        r'\1print("   Assurez-vous que _extract_and_save_questions_only retourne des détails valides avec \'numero\' et \'db_id\'.")\n\1return',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Corrections de syntaxe appliquées!")

if __name__ == "__main__":
    fix_syntax_errors() 