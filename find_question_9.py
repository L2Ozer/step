#!/usr/bin/env python3

import re

def find_question_9():
    # Lire le markdown 
    with open('qcm_extraction/temp/outputs/ue2-correction-colle1-s38-21-22-47305/content.md', 'r', encoding='utf-8') as f:
        content = f.read()

    print('🔍 Recherche exhaustive de la question 9...')
    print('=' * 50)
    
    # Chercher tous les "9" dans le texte avec contexte
    matches_found = 0
    for match in re.finditer(r'.{100}9.{200}', content):
        text = match.group()
        pos = match.start() + 100  # Position du "9"
        
        # Filtrer pour les candidats qui semblent être des questions
        if any(keyword in text.lower() for keyword in ['question', 'q9', 'soit', 'calculer', 'equation', 'qcm', 'a.', 'b.', 'c.']):
            matches_found += 1
            print(f'\n📍 CANDIDAT #{matches_found} à position {pos}:')
            print('-' * 30)
            
            # Afficher avec formatage plus lisible
            clean_text = text.replace('\n', ' ').strip()
            print(f'Contexte: {clean_text}')
            
            # Vérifier si c'est vraiment une question 9
            if re.search(r'(?:^|[^0-9])9[\.\):]', text):
                print('✅ POTENTIELLE QUESTION 9 !')
            
    print(f'\n📊 Total: {matches_found} candidats trouvés')
    
    # Recherche spécifique de patterns problématiques
    print('\n🔍 Recherche de patterns spéciaux...')
    
    # Patterns alternatifs pour la question 9
    special_patterns = [
        r'(?:Q|Question)\s*9[^0-9]',
        r'9\s*[\.\):\-]',
        r'(?:neuf|9)[eè]me\s*question',
        r'question\s*n[°o]\s*9',
    ]
    
    for i, pattern in enumerate(special_patterns):
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            print(f'Pattern {i+1} ("{pattern}") trouvé {len(matches)} fois:')
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 100)
                context = content[start:end].replace('\n', ' ')
                print(f'  -> ...{context}...')
    
    # Analyser la structure autour des questions connues
    print('\n🔍 Analyse de la structure des questions...')
    question_positions = {}
    for i in range(1, 31):
        if i == 9:
            continue
        pattern = rf'(?:Q|Question)\s*{i}[^0-9]'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            question_positions[i] = match.start()
    
    # Regarder entre les questions 8 et 10
    if 8 in question_positions and 10 in question_positions:
        start_pos = question_positions[8]
        end_pos = question_positions[10]
        between_8_and_10 = content[start_pos:end_pos]
        
        print(f'\n📝 Contenu entre Q8 (pos {start_pos}) et Q10 (pos {end_pos}):')
        print('=' * 50)
        print(between_8_and_10[:1000] + ('...' if len(between_8_and_10) > 1000 else ''))

if __name__ == "__main__":
    find_question_9() 