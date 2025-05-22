from qcm_extraction.extractor import QCMExtractor
import time

def clean_duplicate_propositions(qcm_id, delete_questions=False):
    """
    Nettoie les propositions dupliquées pour un QCM donné.
    La stratégie est de garder les 5 propositions les plus récentes pour chaque question
    et de supprimer les doublons.
    
    Args:
        qcm_id (int): ID du QCM à nettoyer
        delete_questions (bool): Si True, supprime aussi les questions en double
    """
    extractor = QCMExtractor()
    
    print(f"🔍 Vérification des questions pour le QCM ID: {qcm_id}")
    
    # Détection des questions dupliquées
    questions = extractor.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute()
    
    if not questions.data:
        print(f"⚠️ Aucune question trouvée pour le QCM ID: {qcm_id}")
        return
    
    print(f"✅ {len(questions.data)} questions trouvées")
    
    # Organiser les questions par numéro
    questions_by_number = {}
    for q in questions.data:
        num = q["numero"]
        if num not in questions_by_number:
            questions_by_number[num] = []
        questions_by_number[num].append(q)
    
    # Vérifier les duplications de questions
    duplicate_questions = {num: qs for num, qs in questions_by_number.items() if len(qs) > 1}
    
    if duplicate_questions and delete_questions:
        print(f"\n⚠️ Détection de questions en double: {len(duplicate_questions)} numéros de question dupliqués")
        
        for num, dupes in duplicate_questions.items():
            print(f"Question {num}: {len(dupes)} duplications (IDs: {[q['id'] for q in dupes]})")
            
            # Trier par ID (garder l'ID le plus élevé, probablement le plus récent)
            dupes.sort(key=lambda q: q['id'])
            
            # Garder la question avec l'ID le plus élevé et supprimer les autres
            keep = dupes[-1]
            delete = dupes[:-1]
            
            print(f"  ✅ Conservation de la question {num} (ID: {keep['id']})")
            
            for q_to_delete in delete:
                try:
                    # D'abord, supprimer toutes les propositions liées à cette question
                    delete_props = extractor.supabase.table('reponses').delete().eq('question_id', q_to_delete['id']).execute()
                    print(f"  🗑️ Suppression de {len(delete_props.data) if delete_props.data else 0} propositions pour la question {num} (ID: {q_to_delete['id']})")
                    
                    # Ensuite, supprimer la question elle-même
                    delete_q = extractor.supabase.table('questions').delete().eq('id', q_to_delete['id']).execute()
                    print(f"  🗑️ Question {num} en double (ID: {q_to_delete['id']}) supprimée")
                    
                    # Pause pour éviter de surcharger l'API
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  ❌ Erreur lors de la suppression de la question {num} (ID: {q_to_delete['id']}): {str(e)}")
    
    # Maintenant obtenir une liste à jour des questions
    questions = extractor.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute()
    
    questions_to_fix = []
    
    # Vérifier combien de propositions a chaque question
    for question in questions.data:
        q_id = question['id']
        q_num = question['numero']
        
        # Récupérer les propositions pour cette question
        props = extractor.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
        prop_count = len(props.data)
        
        if prop_count != 5:
            print(f"⚠️ Question {q_num} (ID: {q_id}): {prop_count} propositions - nécessite nettoyage")
            questions_to_fix.append({
                'id': q_id,
                'numero': q_num,
                'propositions': props.data
            })
        else:
            print(f"✅ Question {q_num} (ID: {q_id}): 5 propositions - OK")
    
    if not questions_to_fix:
        print("✅ Toutes les questions ont exactement 5 propositions. Aucun nettoyage nécessaire.")
        return
    
    # Nettoyer les questions qui ont des propositions dupliquées
    for question in questions_to_fix:
        q_id = question['id']
        q_num = question['numero']
        propositions = question['propositions']
        
        print(f"\n🧹 Nettoyage de la question {q_num} (ID: {q_id}) avec {len(propositions)} propositions")
        
        # Trier les propositions par ID (les plus récents en dernier)
        propositions.sort(key=lambda x: x['id'])
        
        # Garder uniquement une proposition par lettre (A, B, C, D, E)
        # en privilégiant celle avec l'ID le plus élevé (la plus récente)
        props_by_letter = {}
        for prop in propositions:
            lettre = prop['lettre']
            if lettre in props_by_letter:
                # Si l'ID est plus élevé, remplacer
                if prop['id'] > props_by_letter[lettre]['id']:
                    props_by_letter[lettre] = prop
            else:
                props_by_letter[lettre] = prop
        
        # Vérifier qu'on a bien 5 propositions (A, B, C, D, E)
        expected_letters = ['A', 'B', 'C', 'D', 'E']
        
        if set(props_by_letter.keys()) != set(expected_letters):
            print(f"⚠️ Lettres manquantes: {set(expected_letters) - set(props_by_letter.keys())}")
            print(f"⚠️ Lettres supplémentaires: {set(props_by_letter.keys()) - set(expected_letters)}")
            continue
        
        # Collecter les IDs à supprimer (tous sauf ceux qu'on garde)
        kept_ids = [prop['id'] for prop in props_by_letter.values()]
        to_delete_ids = [prop['id'] for prop in propositions if prop['id'] not in kept_ids]
        
        if to_delete_ids:
            print(f"🗑️ Suppression de {len(to_delete_ids)} propositions dupliquées: {to_delete_ids}")
            
            # Supprimer les propositions dupliquées
            for delete_id in to_delete_ids:
                try:
                    result = extractor.supabase.table('reponses').delete().eq('id', delete_id).execute()
                    print(f"  ✅ Proposition ID {delete_id} supprimée")
                    # Petite pause pour éviter de surcharger l'API
                    time.sleep(0.1)
                except Exception as e:
                    print(f"  ❌ Erreur lors de la suppression de la proposition ID {delete_id}: {str(e)}")
        else:
            print("✅ Aucune proposition à supprimer")
    
    # Vérification finale
    print("\n✅ Nettoyage terminé. Vérification finale:")
    
    all_ok = True
    for question in extractor.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute().data:
        q_id = question['id']
        q_num = question['numero']
        
        # Récupérer les propositions pour cette question
        props = extractor.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
        prop_count = len(props.data)
        
        if prop_count != 5:
            print(f"⚠️ Question {q_num}: {prop_count} propositions - toujours un problème!")
            all_ok = False
        else:
            print(f"✅ Question {q_num}: 5 propositions - OK")
    
    if all_ok:
        print("\n🎉 Toutes les questions ont maintenant exactement 5 propositions!")
    else:
        print("\n⚠️ Certaines questions ont toujours un nombre incorrect de propositions.")

if __name__ == "__main__":
    # QCM ID à nettoyer
    qcm_id = 2
    clean_duplicate_propositions(qcm_id, delete_questions=True) 