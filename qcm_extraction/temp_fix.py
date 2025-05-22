"""
Code temporaire pour corriger la fonction _extract_and_save_questions_only
A copier-coller dans extractor.py
"""

def _extract_and_save_questions_only(self, markdown_text: str, qcm_id: int) -> List[Dict[str, Any]]:
    """Phase 1: Extrait UNIQUEMENT les questions du texte Markdown page par page,
    les sauvegarde dans Supabase, et retourne les détails des questions sauvegardées."""
    print(f"📝 Phase 1: Extraction des questions uniquement pour QCM ID: {qcm_id}...")
    
    # Vérifier si des questions existent déjà pour ce QCM
    try:
        existing_questions = self.supabase.table("questions").select("numero").eq("qcm_id", qcm_id).execute()
        existing_question_numbers = set()
        if existing_questions.data:
            existing_question_numbers = {q["numero"] for q in existing_questions.data if "numero" in q}
            print(f"ℹ️ {len(existing_question_numbers)} questions existent déjà pour ce QCM")
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification des questions existantes: {str(e)}")
        existing_question_numbers = set()
    
    # Améliorer le découpage des pages pour éviter les pertes
    page_sections = []
    header_matches = list(re.finditer(r'^# Page \d+', markdown_text, flags=re.MULTILINE))
    
    if not header_matches:
        if markdown_text.strip(): 
            page_sections.append(markdown_text.strip())
            print("    📄 Document sans marqueurs de page, traité comme une seule section")
    else:
        # Extraire les sections de page avec une meilleure gestion des limites
        for i, match in enumerate(header_matches):
            start_content = match.end()
            end_content = header_matches[i+1].start() if (i + 1) < len(header_matches) else len(markdown_text)
            page_content = markdown_text[start_content:end_content].strip()
            
            # Extraire le numéro de page pour référence
            page_header = match.group(0)
            page_num = re.search(r'Page (\d+)', page_header)
            page_num = int(page_num.group(1)) if page_num else i + 1
            
            # Ajouter un chevauchement pour éviter de perdre des questions à la frontière des pages
            if i > 0 and page_content:
                # Ajouter les 200 derniers caractères de la page précédente
                prev_start = header_matches[i-1].end()
                prev_content = markdown_text[prev_start:start_content].strip()
                overlap = prev_content[-200:] if len(prev_content) > 200 else prev_content
                page_content = overlap + "\n\n" + page_content
            
            if page_content: 
                page_sections.append(page_content)
                print(f"    📄 Section de page {i+1} correspond à la Page {page_num} du PDF")
            else:
                print(f"    ⚠️ Section de page {i+1} (Page {page_num} du PDF) est vide après nettoyage")

    if not page_sections:
        print("ℹ️ Aucun contenu de page trouvé pour l'extraction des questions.")
        return []

    # Traiter toutes les pages d'un coup si contenu total raisonnable
    total_content_length = sum(len(section) for section in page_sections)
    all_questions_from_all_pages_api_data = []
    
    # Stratégie adaptative: traiter en une fois si contenu petit, sinon par pages
    if total_content_length < 40000 and len(page_sections) <= 3:
        print(f"📄 Document de taille raisonnable ({total_content_length} caractères), traitement en une fois...")
        combined_content = "\n\n".join(page_sections)
        
        # Tronquer si nécessaire tout en gardant un maximum de contenu
        truncated_content = combined_content[:40000]
        
        # Utiliser un prompt plus précis pour extraire toutes les questions
        prompt = f"""Tu es un expert en analyse de QCM (Questionnaires à Choix Multiples).
        À partir du contenu Markdown d'un document QCM fourni ci-dessous, identifie et extrais CHAQUE question.
        
        INSTRUCTIONS CRUCIALES:
        1. Assure-toi d'identifier TOUTES les questions, en particulier celles numérotées de 1 à 50.
        2. VÉRIFIE ATTENTIVEMENT que les numéros de questions se suivent correctement (1, 2, 3, etc.).
        3. SI TU REPÈRES DES NUMÉROS MANQUANTS (par exemple, si tu vois Q15 puis Q19), RECHERCHE SPÉCIFIQUEMENT ces questions manquantes.
        4. Examine minutieusement tout le texte pour trouver les questions qui pourraient être mal formatées ou difficiles à détecter.
        5. Accorde une attention particulière aux sections de texte qui pourraient contenir les questions Q16, Q17 et Q18 qui sont souvent manquantes.

        Pour chaque question, tu dois fournir :
        1. Le numéro de la question (par exemple, 1, 2, 3) tel qu'il apparaît dans le document.
        2. Le texte intégral de la question uniquement (sans les choix de réponses A,B,C,D,E).
        
        Contenu Markdown du document à analyser :
        ---
        {truncated_content}
        ---

        Retourne les questions extraites sous la forme d'un objet JSON avec cette structure:
        {{
          "questions": [
            {{"numero": 1, "contenu": "Texte de la question 1"}},
            {{"numero": 2, "contenu": "Texte de la question 2"}},
            ...etc pour toutes les questions...
          ]
        }}
        """
        
        try:
            # Utiliser un modèle plus puissant pour l'extraction complète
            messages = [UserMessage(content=prompt)]
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-medium-latest", 
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # Vérifier si l'appel API a échoué
            if response is None:
                print("    ❌ Échec de l'appel API pour l'extraction globale des questions")
                # Continuer avec les autres méthodes d'extraction
                pass
            elif response.choices and response.choices[0].message and response.choices[0].message.content:
                extracted_data_str = response.choices[0].message.content
                try:
                    raw_data = json.loads(extracted_data_str)
                    if isinstance(raw_data, dict) and "questions" in raw_data and isinstance(raw_data["questions"], list):
                        all_questions_from_all_pages_api_data = raw_data["questions"]
                        print(f"    ✅ Extraction globale réussie: {len(all_questions_from_all_pages_api_data)} questions trouvées")
                except json.JSONDecodeError as e_json:
                    print(f"    ⚠️ Erreur JSON dans l'extraction globale: {e_json}")
            else:
                print(f"    ⚠️ Réponse API invalide pour l'extraction globale")
        except Exception as e_api:
            print(f"    🔥 Erreur API pour l'extraction globale: {str(e_api)}")
    
    # Si l'extraction globale a échoué ou n'a pas été tentée, traiter page par page
    if not all_questions_from_all_pages_api_data:
        print(f"📄 Traitement page par page ({len(page_sections)} sections)...")
        
        for i, page_markdown_content in enumerate(page_sections):
            print(f"📄 Traitement section {i + 1}/{len(page_sections)} pour questions...")
            
            if not page_markdown_content.strip():
                print(f"    ⏩ Section de page {i + 1} vide, ignorée pour questions.")
                continue

            truncated_page_markdown = page_markdown_content[:25000]

            # Ajouter une instruction spécifique pour chercher les questions souvent manquantes
            prompt = f"""Tu es un expert en analyse de QCM (Questionnaires à Choix Multiples).
            À partir du contenu Markdown d'une section de page d'un document QCM fourni ci-dessous, identifie et extrais chaque question.

            INSTRUCTIONS CRUCIALES:
            1. Cherche ATTENTIVEMENT toutes les questions, particulièrement les questions Q16, Q17 et Q18 qui sont souvent manquantes.
            2. Examine chaque paragraphe, même ceux qui semblent mal formatés.
            3. Une question commence généralement par "Q" suivi d'un numéro (ex: Q16, Q17).
            4. Assure-toi de ne manquer AUCUNE question, même si elle est mal formatée.

            Pour chaque question, tu dois fournir :
            1. Le numéro de la question (par exemple, 1, 2, 3) tel qu'il apparaît sur la page.
            2. Le texte intégral de la question. Cela inclut toute phrase d'introduction ou contexte faisant partie de la question elle-même.
               EXCLUS IMPÉRATIVEMENT : Les options à choix multiples (A,B,C,D,E), les corrections, ou les justifications.
            
            IMPORTANT: Assure-toi d'extraire TOUTES les questions présentes dans ce texte, même si elles semblent incomplètes.

            Contenu Markdown de la section de page à analyser :
            ---
            {truncated_page_markdown}
            ---

            Retourne les questions extraites sous la forme d'un objet JSON. Cet objet doit contenir une unique clé "questions",
            dont la valeur est une liste d'objets. Chaque objet dans la liste représente une question et doit avoir
            les clés "numero" (un entier) et "contenu" (une chaîne de caractères pour le texte de la question).
            Si aucune question n'est trouvée sur cette section de page, la liste "questions" doit être vide.

            Exemple de format de retour attendu :
            {{
              "questions": [
                {{"numero": 1, "contenu": "Quelle est la formule chimique de l'eau ?"}},
                {{"numero": 2, "contenu": "Concernant la photosynthèse, laquelle des affirmations suivantes est correcte ?"}}
              ]
            }}
            """
            try:
                messages = [UserMessage(content=prompt)]
                response = self._call_api_with_retry(
                    self.client.chat.complete,
                    model="mistral-small-latest", 
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                
                # Vérifier si l'appel API a échoué
                if response is None:
                    print(f"    ❌ Échec de l'appel API pour l'extraction de la section {i+1}")
                    continue
                
                if response.choices and response.choices[0].message and response.choices[0].message.content:
                    extracted_data_str = response.choices[0].message.content
                    try:
                        raw_page_data = json.loads(extracted_data_str)
                        page_questions_list = []
                        if isinstance(raw_page_data, dict):
                            page_questions_list = raw_page_data.get("questions", [])
                        elif isinstance(raw_page_data, list): 
                            page_questions_list = raw_page_data
                        
                        if not isinstance(page_questions_list, list):
                            print(f"    ⚠️ Format de questions inattendu pour section {i+1} (pas une liste). Reçu: {page_questions_list}")
                            continue
                        
                        # Déballage amélioré de la liste des questions
                        actual_questions_for_page = []
                        if not page_questions_list: # Gère une liste vide retournée par .get("questions", []) ou par l'API
                            pass # actual_questions_for_page reste vide
                        elif len(page_questions_list) == 1 and \
                             isinstance(page_questions_list[0], dict) and \
                             "questions" in page_questions_list[0] and \
                             isinstance(page_questions_list[0]["questions"], list):  # Gérer le cas où l'API retourne un dict imbriqué
                            actual_questions_for_page = page_questions_list[0]["questions"]
                        else:
                            actual_questions_for_page = page_questions_list
                        
                        # Ajouter les questions de cette page
                        print(f"    ✅ {len(actual_questions_for_page)} questions trouvées dans la section {i+1}")
                        all_questions_from_all_pages_api_data.extend(actual_questions_for_page)
                    except json.JSONDecodeError as e:
                        print(f"    ⚠️ Erreur JSON dans l'extraction pour la section {i+1}: {str(e)}")
                else:
                    print(f"    ⚠️ Réponse API invalide pour la section {i+1}")
            except Exception as e:
                print(f"    ⚠️ Erreur lors de l'extraction des questions pour la section {i+1}: {str(e)}")
            
            time.sleep(2)  # Réduit à 2 secondes au lieu de 5

    # Après avoir extrait toutes les questions, vérifier s'il y a des numéros manquants
    all_questions = all_questions_from_all_pages_api_data
    
    # Trier les questions par numéro
    all_questions.sort(key=lambda q: q["numero"] if isinstance(q["numero"], int) else int(q["numero"]))
    
    # Vérifier s'il manque des numéros de questions (trous dans la séquence)
    if all_questions:
        question_numbers = [q["numero"] if isinstance(q["numero"], int) else int(q["numero"]) for q in all_questions]
        expected_numbers = list(range(min(question_numbers), max(question_numbers) + 1))
        missing_numbers = set(expected_numbers) - set(question_numbers)
        
        if missing_numbers:
            print(f"⚠️ ATTENTION: Questions manquantes détectées: {sorted(missing_numbers)}")
            print(f"   Vérifiez le PDF source pour ces questions.")
    
    if not all_questions_from_all_pages_api_data:
        print("ℹ️ Aucune question trouvée dans le document après traitement de toutes les pages.")
        return []

    print(f"📊 Total de {len(all_questions_from_all_pages_api_data)} questions collectées (brutes API).")
    
    # Déduplication des questions par numéro
    # Nous conservons la question avec le contenu le plus long pour chaque numéro
    questions_by_number = {}
    for q_api_data in all_questions_from_all_pages_api_data:
        if not isinstance(q_api_data, dict):
            continue
        
        try:
            numero = int(q_api_data["numero"])
            contenu_text = str(q_api_data["contenu"]).strip()
            
            if not contenu_text:
                print(f"⚠️ Contenu de question vide pour numéro {numero} (API), ignoré.")
                continue
            
            # Si le numéro existe déjà, garde la version avec le contenu le plus long
            if numero in questions_by_number:
                existing_content = questions_by_number[numero]["contenu"]
                if len(contenu_text) > len(existing_content):
                    questions_by_number[numero] = {"numero": numero, "contenu": contenu_text}
            else:
                questions_by_number[numero] = {"numero": numero, "contenu": contenu_text}
            
        except (ValueError, TypeError) as e:
            print(f"⚠️ Erreur de type/valeur pour q API data {q_api_data}: {e}")
            continue
    
    # Vérifier s'il y a des écarts dans les numéros de questions
    all_question_numbers = sorted(questions_by_number.keys())
    if all_question_numbers:
        expected_range = list(range(min(all_question_numbers), max(all_question_numbers) + 1))
        missing_questions = set(expected_range) - set(all_question_numbers)
        if missing_questions:
            print(f"⚠️ Questions manquantes dans la séquence: {sorted(missing_questions)}")
    
    # Créer liste finale pour insertion, en filtrant les questions déjà existantes
    questions_to_insert_in_supabase = []
    for numero, q_data in questions_by_number.items():
        # Ne pas réinsérer les questions qui existent déjà
        if numero in existing_question_numbers:
            print(f"ℹ️ Question {numero} existe déjà, ignorée pour insertion.")
            continue
            
        questions_to_insert_in_supabase.append({
            "qcm_id": qcm_id,
            "numero": numero, 
            "contenu": json.dumps({"text": q_data["contenu"]}),  # Converti en JSON pour le champ jsonb
            "uuid": str(uuid.uuid4()) 
        })

    saved_questions_details = []
    
    # Si certaines questions existent déjà, récupérer leurs détails
    if existing_question_numbers:
        try:
            for numero in existing_question_numbers:
                result = self.supabase.table("questions").select("id", "uuid").eq("qcm_id", qcm_id).eq("numero", numero).execute()
                if result.data:
                    for q in result.data:
                        saved_questions_details.append({
                            "db_uuid": q.get("id"),
                            "qcm_id": qcm_id,
                            "numero": numero
                        })
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des questions existantes: {str(e)}")
    
    # Insérer les nouvelles questions
    if questions_to_insert_in_supabase:
        print(f"💾 Sauvegarde de {len(questions_to_insert_in_supabase)} nouvelles questions dans Supabase...")
        try:
            # Insertion par lots pour améliorer les performances
            chunk_size = 50
            for i in range(0, len(questions_to_insert_in_supabase), chunk_size):
                chunk = questions_to_insert_in_supabase[i:i + chunk_size]
                result_q = self.supabase.table("questions").insert(chunk).execute()
                
                if result_q.data:
                    print(f"✅ Lot de {len(result_q.data)} questions sauvegardé dans Supabase.")
                    for db_q_data in result_q.data:
                        saved_questions_details.append({
                            "db_uuid": db_q_data.get("id"),
                            "qcm_id": db_q_data.get("qcm_id"), 
                            "numero": db_q_data.get("numero")  
                        })
                else:
                    print(f"⚠️ Aucune donnée retournée par Supabase pour un lot de {len(chunk)} questions.")
        except Exception as e_insert_q: 
            print(f"🔥 Erreur lors de l\'insertion des questions dans Supabase: {str(e_insert_q)}")
    else:
        print("ℹ️ Aucune nouvelle question à sauvegarder.")
    
    # Filtrer les entrées incomplètes
    saved_questions_details = [
        q for q in saved_questions_details 
        if q.get("db_uuid") and q.get("qcm_id") is not None and q.get("numero") is not None
    ]
    
    print(f"📊 Total de {len(saved_questions_details)} questions disponibles pour la suite du traitement.")
    return saved_questions_details 