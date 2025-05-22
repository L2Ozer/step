#!/usr/bin/env python3

import re

def fix_indentation_issues():
    # Chemin du fichier
    file_path = "qcm_extraction/extractor.py"
    
    # Lire le contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Corrections à appliquer (recherche -> remplacement)
    replacements = [
        # Correction 1: Question Num et Traitement Vrai/Faux
        (r'question_num = int\(match\.group\(1\)\)\s+# Ne traiter que si la question n\'a pas déjà été traitée par la méthode principale\s+if question_num not in questions_with_answers:\s+lettre = match\.group\(2\)\.upper\(\)\s+vf_status = match\.group\(3\)\.lower\(\)',
         'question_num = int(match.group(1))\n                            # Ne traiter que si la question n\'a pas déjà été traitée par la méthode principale\n                            if question_num not in questions_with_answers:\n                                lettre = match.group(2).upper()\n                                vf_status = match.group(3).lower()'),
         
        # Correction 2: Traitement vrai/juste/correct
        (r'# Ajouter seulement si c\'est vrai/juste/correct\s+if vf_status in \[\'vrai\', \'juste\', \'correct\', \'exact\'\]:\s+vrai_faux_by_question\[question_num\]\.append\(lettre\)\s+print',
         '                                    # Ajouter seulement si c\'est vrai/juste/correct\n                                    if vf_status in [\'vrai\', \'juste\', \'correct\', \'exact\']:\n                                        vrai_faux_by_question[question_num].append(lettre)\n                                        print'),
         
        # Correction 3: Traitement multi-réponses
        (r'question_num = int\(match\.group\(1\)\)\s+# Ne traiter que si la question n\'a pas déjà été traitée par d\'autres méthodes\s+if question_num not in questions_with_answers:\s+answers_str = match\.group\(2\)',
         'question_num = int(match.group(1))\n                        # Ne traiter que si la question n\'a pas déjà été traitée par d\'autres méthodes\n                        if question_num not in questions_with_answers:\n                            answers_str = match.group(2)'),
         
        # Correction 4: Ajout aux corrections
        (r'corrections_data\[question_num\] = unique_letters\s+questions_with_answers\.add\(question_num\)\s+print',
         'corrections_data[question_num] = unique_letters\n                            questions_with_answers.add(question_num)\n                            print')
    ]
    
    # Appliquer toutes les corrections
    modified_content = content
    for old, new in replacements:
        modified_content = re.sub(old, new, modified_content)
    
    # Écrire le contenu modifié dans le fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print("Corrections d'indentation appliquées avec succès!")

if __name__ == "__main__":
    fix_indentation_issues() 