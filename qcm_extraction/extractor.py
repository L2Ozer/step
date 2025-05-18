import os
import re
import base64
import json
import time
import uuid
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path
import requests
from PIL import Image
from pdf2image import convert_from_path
from mistralai import Mistral, UserMessage
from io import BytesIO
from supabase import create_client, Client

class QCMExtractor:
    def __init__(self, api_key: str = None, supabase_url: str = None, supabase_key: str = None):
        """Initialise l'extracteur avec la clé API Mistral et les credentials Supabase"""
        # Configuration Mistral
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("La clé API Mistral est requise")
        
        self.client = Mistral(api_key=self.api_key)
        
        # Configuration Supabase
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Les credentials Supabase sont requis")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Créer la structure de dossiers
        self.base_dir = Path("qcm_extraction")
        self.temp_dir = self.base_dir / "temp"
        self.pdfs_dir = self.temp_dir / "pdfs"
        self.images_dir = self.temp_dir / "images"
        self.outputs_dir = self.temp_dir / "outputs"
        self.logs_dir = self.base_dir / "logs"
        
        # Créer tous les dossiers nécessaires
        for dir_path in [self.temp_dir, self.pdfs_dir, self.images_dir, self.outputs_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _call_api_with_retry(self, func, *args, max_retries=3, delay=2, **kwargs):
        """Appelle une fonction API avec retry en cas d'erreur"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "rate limit exceeded" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Rate limit atteint, attente de {delay} secondes...")
                    time.sleep(delay)
                    delay *= 2  # Augmenter le délai à chaque tentative
                else:
                    raise e
    
    def download_pdf(self, url: str) -> str:
        """Télécharge un PDF depuis une URL"""
        response = requests.get(url)
        response.raise_for_status()
        
        # Créer un dossier unique pour ce PDF
        pdf_name = Path(url).name
        pdf_stem = Path(url).stem
        pdf_dir = self.pdfs_dir / pdf_stem
        pdf_dir.mkdir(exist_ok=True)
        
        # Sauvegarder le PDF
        pdf_path = pdf_dir / pdf_name
        with open(pdf_path, "wb") as f:
            f.write(response.content)
            
        return str(pdf_path)
    
    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convertit un PDF en images"""
        pdf_path = Path(pdf_path)
        pdf_stem = pdf_path.stem
        
        # Créer un dossier pour les images de ce PDF
        output_dir = self.images_dir / pdf_stem
        output_dir.mkdir(exist_ok=True)
        
        # Convertir le PDF en images
        images = convert_from_path(str(pdf_path))
        
        # Sauvegarder les images
        image_paths = []
        for i, image in enumerate(images):
            image_path = output_dir / f"page_{i+1}.jpg"
            image.save(str(image_path), "JPEG")
            image_paths.append(str(image_path))
            
        return image_paths
    
    def save_metadata(self, metadata: Dict[str, Any], pdf_path: str) -> str:
        """Sauvegarde les métadonnées dans un fichier JSON"""
        pdf_stem = Path(pdf_path).stem
        output_dir = self.outputs_dir / pdf_stem
        output_dir.mkdir(exist_ok=True)
        
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        return str(metadata_path)
    
    def convert_pdf_to_markdown(self, pdf_path: str, original_url: str) -> str:
        """Convertit un PDF en Markdown en utilisant l'OCR Mistral"""
        try:
            print("📝 Conversion du PDF en Markdown...")
            
            # Utiliser l'URL originale pour l'API OCR
            document_input = {"type": "document_url", "document_url": original_url}
            
            # Appeler l'API OCR pour extraire le texte avec retry
            ocr_response = self._call_api_with_retry(
                self.client.ocr.process,
                model="mistral-ocr-latest",
                document=document_input,
                include_image_base64=False
            )
            
            # Extraire le texte de toutes les pages
            markdown_content = ""
            for i, page in enumerate(ocr_response.pages):
                markdown_content += f"# Page {i+1}\n\n"
                markdown_content += page.markdown + "\n\n"
            
            # Sauvegarder le Markdown
            pdf_stem = Path(pdf_path).stem
            output_dir = self.outputs_dir / pdf_stem
            output_dir.mkdir(exist_ok=True)
            
            markdown_path = output_dir / "content.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"💾 Markdown sauvegardé: {markdown_path}")
            return str(markdown_path)
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion en Markdown: {str(e)}")
            return None

    def save_to_supabase(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sauvegarde les métadonnées dans Supabase"""
        try:
            print("💾 Sauvegarde dans Supabase...")
            
            # Chercher l'ue_id correspondant dans la table 'ue'
            if metadata["ue"]:
                result = self.supabase.table("ue").select("id").eq("numero", metadata["ue"]).execute()
                if result.data:
                    ue_id = result.data[0]["id"]
                else:
                    print(f"⚠️ UE {metadata['ue']} non trouvée dans la table 'ue'")
                    return None
            else:
                print("⚠️ Impossible de déterminer l'UE")
                return None
            
            # Préparer les données pour Supabase
            supabase_data = {
                "ue_id": ue_id,
                "type": metadata["type"],
                "annee": metadata["annee"],
                "uuid": str(uuid.uuid4())  # Générer un UUID unique
            }
            
            # Insérer dans Supabase dans la table 'qcm'
            result = self.supabase.table("qcm").insert(supabase_data).execute()
            
            print("✅ Données sauvegardées dans Supabase")
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la sauvegarde dans Supabase: {str(e)}")
            return None

    def extract_metadata_from_path(self, url):
        """Extrait les métadonnées d'un PDF à partir de son URL."""
        print("🔍 Extraction des métadonnées...")
        
        try:
            # Télécharger le PDF
            pdf_path = self.download_pdf(url)
            print(f"📥 PDF téléchargé: {pdf_path}")
            
            # Convertir le PDF en Markdown en utilisant l'URL originale
            markdown_path = self.convert_pdf_to_markdown(pdf_path, url)
            if not markdown_path:
                return None
            
            # Lire le contenu Markdown
            with open(markdown_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Extraire les métadonnées du nom de fichier
            filename = url.split('/')[-1]
            
            type_doc = "Unknown"
            annee = None
            ue = None
            
            # Utiliser l'IA pour extraire le type de document, l'année et l'UE
            prompt = f"""Tu es un agent spécialisé dans l'analyse de documents PDF de QCM et corrections.
            Voici un exemple de ce que je veux :
            - Pour un fichier 'ue3-correction-cb1-s40-21-22-48479.pdf', le type doit être 'Concours Blanc N°1'
            - Pour le texte 'SESSION 2021 / 2022', l'année doit être '2021 / 2022'
            - Pour le texte 'UE2', l'UE doit être 'UE2'
            
            Analyse le texte suivant et détermine :
            1. Le type de document (exactement 'Concours Blanc N°1' si c'est une correction de concours blanc, ou 'Colle N°1' si c'est une colle)
            2. L'année de la session (format: 'XXXX / XXXX')
            3. L'UE (format: 'UE1', 'UE2', etc.)
            
            Texte à analyser :
            {text[:1000]}
            
            Réponds uniquement avec le format suivant, sans autre texte :
            TYPE: [type]
            ANNEE: [année]
            UE: [ue]"""
            
            messages = [UserMessage(content=prompt)]
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-small-latest",
                messages=messages,
                temperature=0.0
            )
            
            # Parser la réponse de l'IA
            response_text = response.choices[0].message.content.strip()
            type_match = re.search(r'TYPE:\s*(.*)', response_text)
            annee_match = re.search(r'ANNEE:\s*(.*)', response_text)
            ue_match = re.search(r'UE:\s*(.*)', response_text)
            
            if type_match:
                type_doc = type_match.group(1).strip()
            if annee_match:
                annee = annee_match.group(1).strip()
            if ue_match:
                ue = ue_match.group(1).strip()

            metadata = {
                'filename': filename,
                'ue': ue,
                'type': type_doc,
                'annee': annee,
                'markdown_path': markdown_path,
                'url': url  # Ajouter l'URL originale
            }
            
            print(f"✅ Métadonnées extraites: {metadata}")
            
            # Sauvegarder les métadonnées localement
            metadata_path = self.save_metadata(metadata, pdf_path)
            print(f"💾 Métadonnées sauvegardées localement: {metadata_path}")
            
            # Sauvegarder dans Supabase
            qcm_table_entry = self.save_to_supabase(metadata)
            if not qcm_table_entry:
                print("⚠️ Échec de la sauvegarde des métadonnées QCM dans Supabase")
                return metadata # Retourne les métadonnées extraites même si la sauvegarde Supabase échoue pour le QCM
            
            # Ajouter l'ID du QCM créé aux métadonnées qui seront retournées
            if qcm_table_entry and isinstance(qcm_table_entry, dict) and 'id' in qcm_table_entry:
                metadata['qcm_db_id'] = qcm_table_entry['id']
            else:
                print("⚠️ L'ID du QCM sauvegardé n'a pas pu être ajouté aux métadonnées retournées.")
                # On continue quand même, qcm_id_for_processing sera utilisé en interne

            # PAUSE pour éviter le rate limiting de l'API
            # print("⏸️ Pause de 10 secondes avant l'extraction des questions pour éviter le rate limiting...")
            # time.sleep(10) # Pause de 10 secondes - Déplacé avant chaque phase d'extraction majeure

            # Extraire et sauvegarder les questions et ensuite les propositions
            qcm_id_for_processing = qcm_table_entry.get('id')
            markdown_file_path = metadata.get('markdown_path') 

            if qcm_id_for_processing and markdown_file_path:
                try:
                    with open(markdown_file_path, "r", encoding="utf-8") as f:
                        markdown_content_for_processing = f.read()
                    
                    print("▶️ Lancement de la Phase 1: Extraction des questions...")
                    # Pause avant la première série d'appels API pour les questions
                    print("⏸️ Pause de 5 secondes avant l'extraction des questions...")
                    time.sleep(5)
                    saved_questions_details = self._extract_and_save_questions_only(markdown_content_for_processing, qcm_id_for_processing)
                    
                    if saved_questions_details:
                        print(f"ℹ️ Phase 1 terminée. {len(saved_questions_details)} question(s) ont des détails sauvegardés.")
                        print("▶️ Lancement de la Phase 2: Extraction des propositions...")
                        # Pause avant la deuxième série d'appels API pour les propositions
                        print("⏸️ Pause de 10 secondes avant l'extraction des propositions...")
                        time.sleep(10) 
                        self._extract_and_save_propositions(markdown_content_for_processing, qcm_id_for_processing, saved_questions_details)
                        print("🏁 Phase 2 terminée.")
                    else:
                        print("⚠️ Aucune question n'a été sauvegardée en Phase 1, donc la Phase 2 (propositions) est ignorée.")

                except FileNotFoundError:
                    print(f"⚠️ Fichier Markdown non trouvé à {markdown_file_path}")
                except Exception as e:
                    # Log plus détaillé de l'erreur
                    import traceback
                    print(f"🔥 Erreur majeure lors du traitement des questions/propositions pour QCM ID {qcm_id_for_processing}: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")
            else:
                missing_info = []
                if not qcm_id_for_processing: missing_info.append("qcm_id de la table qcm")
                if not markdown_file_path: missing_info.append("markdown_path des métadonnées")
                print(f"⚠️ Impossible d'extraire les questions/propositions: {', '.join(missing_info)} manquant.")
            
            return metadata
            
        except Exception as e:
            print(f"⚠️ Erreur lors de l'extraction des métadonnées: {str(e)}")
            return None

    def encode_image_to_base64(self, image_path: str, max_size: int = 1000) -> str:
        """Encode une image en Base64 avec redimensionnement si nécessaire"""
        with Image.open(image_path) as img:
            # Convertir en RGB si nécessaire
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculer le ratio de redimensionnement
            width, height = img.size
            if width > max_size or height > max_size:
                ratio = min(max_size/width, max_size/height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Améliorer le contraste
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # Sauvegarder en JPEG avec compression
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85, optimize=True)
            
            # Encoder en Base64
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image using Mistral API."""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract and describe all the text content from this image. Focus on mathematical formulas, chemical equations, and any other technical content."
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]

            response = self.client.chat.complete(
                model="mistral-small-latest",
                messages=messages,
                temperature=0.0,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    def extract_qcm_from_pdf(self, pdf_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Extrait les métadonnées d'un PDF en utilisant l'OCR Mistral"""
        # Extraire les métadonnées de base
        metadata = self.extract_metadata_from_path(pdf_path)
        
        # Convertir le PDF en images
        image_paths = self.pdf_to_images(pdf_path)
        if not image_paths:
            return metadata, []
            
        # Utiliser l'OCR Mistral sur la première page
        try:
            with open(image_paths[0], "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                }
            )
            
            # Pour l'instant, on ne retourne que les métadonnées
            return metadata, []
            
        except Exception as e:
            print(f"Error during OCR processing: {e}")
            return metadata, []

    def _extract_and_save_questions_only(self, markdown_text: str, qcm_id: int) -> List[Dict[str, Any]]:
        """Phase 1: Extrait UNIQUEMENT les questions du texte Markdown page par page,
        les sauvegarde dans Supabase, et retourne les détails des questions sauvegardées."""
        print(f"📝 Phase 1: Extraction des questions uniquement pour QCM ID: {qcm_id}...")
        
        page_sections = []
        # Regex pour trouver les en-têtes comme "# Page 1\\n\\n"
        # La regex précédente ne fonctionne pas, on la remplace par une expression plus souple
        header_matches = list(re.finditer(r'^# Page \d+', markdown_text, flags=re.MULTILINE))

        if not header_matches:
            print("⚠️ Aucun en-tête de page standard ('# Page X') trouvé. Traitement du document entier comme une seule section.")
            if markdown_text.strip():
                page_sections.append(markdown_text.strip())
        else:
            for i, match in enumerate(header_matches):
                start_content = match.end()
                end_content = header_matches[i+1].start() if (i + 1) < len(header_matches) else len(markdown_text)
                page_content = markdown_text[start_content:end_content].strip()
                if page_content:
                    page_sections.append(page_content)
                    
            print(f"🔎 Trouvé {len(header_matches)} en-têtes de page dans le document.")
        
        if not page_sections:
            print("ℹ️ Aucun contenu de page trouvé après le découpage du Markdown pour les questions.")
            return []

        print(f"📄 Document divisé en {len(page_sections)} section(s) de page pour l'extraction des questions.")
        all_questions_from_all_pages_api_data = []

        for i, page_markdown_content in enumerate(page_sections):
            print(f"📄 Traitement section {i + 1}/{len(page_sections)} pour questions...")
            
            if not page_markdown_content.strip():
                print(f"    ⏩ Section de page {i + 1} vide, ignorée pour questions.")
                continue

            truncated_page_markdown = page_markdown_content[:25000]

            prompt = f"""Tu es un expert en analyse de QCM (Questionnaires à Choix Multiples).
            À partir du contenu Markdown d'une section de page d'un document QCM fourni ci-dessous, identifie et extrais chaque question.

            Pour chaque question, tu dois fournir :
            1. Le numéro de la question (par exemple, 1, 2, 3) tel qu'il apparaît sur la page.
            2. Le texte intégral de la question. Cela inclut toute phrase d'introduction ou contexte faisant partie de la question elle-même.
               EXCLUS IMPÉRATIVEMENT : Les options à choix multiples (A,B,C,D,E), les corrections, ou les justifications.

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
                             isinstance(page_questions_list[0]["questions"], list):
                            # Cas où l'API retourne: [{"questions": [q1, q2, ...]}]
                            actual_questions_for_page = page_questions_list[0]["questions"]
                            print(f"    ℹ️ Liste de questions imbriquée trouvée et déballée ({len(actual_questions_for_page)} questions).")
                        else:
                            # Cas normal où page_questions_list est déjà la liste de questions [q1, q2, ...]
                            # ou pourrait être une liste d'items malformés, vérifiés plus tard.
                            actual_questions_for_page = page_questions_list
                        
                        if actual_questions_for_page:
                            print(f"    👍 {len(actual_questions_for_page)} question(s) à traiter pour la section {i+1} (après déballage si nécessaire).")
                            all_questions_from_all_pages_api_data.extend(actual_questions_for_page)
                        else:
                            # Couvre le cas où page_questions_list était vide initialement, ou si actual_questions_for_page est restée vide.
                            print(f"    ℹ️ Aucune question trouvée ou valide sur la section {i+1} après traitement API.")
                            # ---- AJOUT DES LOGS ----
                            if 'extracted_data_str' in locals() and extracted_data_str:
                                print(f"    [DEBUG] Contenu brut de la réponse API (questions) pour section {i+1} qui a mené à aucune question valide: {extracted_data_str}")
                            else:
                                print(f"    [DEBUG] Pas de contenu de réponse API à logger pour section {i+1}.")
                            print(f"""    [DEBUG] Contenu Markdown envoyé à Mistral pour la section {i+1} (qui n'a retourné aucune question valide):
---
{truncated_page_markdown}
---""")
                            # ---- FIN AJOUT DES LOGS ----
                    except json.JSONDecodeError as e_json:
                        print(f"    ⚠️ Erreur JSON pour section {i+1}: {e_json}. Réponse: {extracted_data_str}")
                        # ---- AJOUT DES LOGS (copie pour être sûr en cas d'erreur JSON aussi) ----
                        if 'extracted_data_str' in locals() and extracted_data_str:
                            print(f"    [DEBUG] Contenu brut de la réponse API (questions) pour section {i+1} (ERREUR JSON): {extracted_data_str}")
                        print(f"""    [DEBUG] Contenu Markdown envoyé à Mistral pour la section {i+1} (ERREUR JSON):
---
{truncated_page_markdown}
---""")
                        # ---- FIN AJOUT DES LOGS ----
                else:
                    print(f"    ⚠️ Réponse API invalide/contenu manquant pour section {i+1}.")
                    # ---- AJOUT DES LOGS ----
                    print(f"""    [DEBUG] Contenu Markdown envoyé à Mistral pour la section {i+1} (Réponse API invalide/contenu manquant):
---
{truncated_page_markdown}
---""")
                    # ---- FIN AJOUT DES LOGS ----
            except Exception as e_api: 
                print(f"    🔥 Erreur API majeure pour section {i+1} (questions): {str(e_api)}")

            if i < len(page_sections) - 1:
                print(f"    ⏸️ Pause de 5s avant section suivante...")
                time.sleep(5)
        
        if not all_questions_from_all_pages_api_data:
            print("ℹ️ Aucune question trouvée dans le document après traitement de toutes les pages.")
            return []

        print(f"📊 Total de {len(all_questions_from_all_pages_api_data)} questions collectées (brutes API).")
        
        questions_to_insert_in_supabase = []
        for q_api_data in all_questions_from_all_pages_api_data:
            if not isinstance(q_api_data, dict) or "numero" not in q_api_data or "contenu" not in q_api_data:
                print(f"⚠️ Donnée de question API malformée ignorée: {q_api_data}")
                continue
            try:
                numero = int(q_api_data["numero"])
                contenu_text = str(q_api_data["contenu"])
                if not contenu_text.strip(): 
                    print(f"⚠️ Contenu de question vide pour numéro {numero} (API), ignoré.")
                    continue
                
                questions_to_insert_in_supabase.append({
                    "qcm_id": qcm_id,
                    "numero": numero, 
                    "contenu": {"text": contenu_text}, 
                    "uuid": str(uuid.uuid4()) 
                })
            except (ValueError, TypeError) as e:
                print(f"⚠️ Erreur de type/valeur pour q API data {q_api_data}: {e}")
                continue

        saved_questions_details = []
        if questions_to_insert_in_supabase:
            print(f"💾 Sauvegarde de {len(questions_to_insert_in_supabase)} questions formatées dans Supabase...")
            try:
                result_q = self.supabase.table("questions").insert(questions_to_insert_in_supabase).execute()
                if result_q.data:
                    print(f"✅ {len(result_q.data)} questions sauvegardées dans Supabase.")
                    for db_q_data in result_q.data:
                        saved_questions_details.append({
                            "db_uuid": db_q_data.get("uuid"),
                            "qcm_id": db_q_data.get("qcm_id"), 
                            "numero": db_q_data.get("numero")  
                        })
                    # Filtrer ceux où uuid, qcm_id, ou numero pourraient être None
                    saved_questions_details = [
                        q for q in saved_questions_details 
                        if q.get("db_uuid") and q.get("qcm_id") is not None and q.get("numero") is not None
                    ]
                    if len(saved_questions_details) != len(result_q.data):
                        print(f"⚠️ Discordance dans les détails des questions sauvegardées collectées ({len(saved_questions_details)} vs {len(result_q.data)}).")
                else:
                    print(f"⚠️ Aucune donnée retournée par Supabase après tentative d\'insertion des questions.")
            except Exception as e_insert_q: 
                print(f"🔥 Erreur lors de l\'insertion des questions dans Supabase: {str(e_insert_q)}")
        else:
            print("ℹ️ Aucune question valide à sauvegarder après filtrage des données API.")
        
        return saved_questions_details

    def _extract_and_save_propositions(self, markdown_text: str, qcm_id: int, saved_questions_details: List[Dict[str, Any]]):
        """Phase 2: Extrait les propositions pour des questions déjà sauvegardées et les insère dans Supabase."""
        if not saved_questions_details:
            print("ℹ️ Phase 2 Propositions: Aucune question sauvegardée fournie, donc pas de propositions à extraire.")
            return

        print(f"📝 Phase 2: Extraction des propositions pour {len(saved_questions_details)} questions du QCM ID: {qcm_id}...")

        # Récupérer les UUIDs actuels des questions directement depuis Supabase
        # C'est crucial car les UUIDs peuvent changer si nous réexécutons le script
        try:
            print(f"🔍 Récupération des UUIDs des questions depuis Supabase pour le QCM ID: {qcm_id}...")
            result = self.supabase.table("questions").select("id", "uuid", "numero").eq("qcm_id", qcm_id).execute()
            
            if not result.data:
                print(f"⚠️ Aucune question trouvée dans Supabase pour le QCM ID: {qcm_id}")
                return
                
            # Création du mappage par numéro en utilisant les données de Supabase
            question_map_by_numero = {}
            for q in result.data:
                if "numero" in q and "id" in q and q["numero"] is not None and q["id"] is not None:
                    question_map_by_numero[q["numero"]] = q["id"]
            
            question_id_list = [q["id"] for q in result.data if "id" in q and q["id"] is not None]
            
            print(f"📌 Nombre de questions mappées par numéro depuis Supabase: {len(question_map_by_numero)}")
            print(f"📌 Numéros des questions en base de données: {sorted(question_map_by_numero.keys())}")
            
            if not question_map_by_numero:
                print("⚠️ Aucune question n'a pu être mappée par numéro depuis Supabase.")
                return
                
        except Exception as e:
            print(f"🔥 Erreur lors de la récupération des IDs des questions depuis Supabase: {str(e)}")
            # Utiliser les données fournies en argument comme fallback
            question_map_by_numero = {q["numero"]: q["db_uuid"] for q in saved_questions_details if q.get("numero") is not None and q.get("db_uuid")}
            question_id_list = [q["db_uuid"] for q in saved_questions_details if q.get("db_uuid")]
            print(f"📌 Utilisation du mappage fourni en argument (fallback): {len(question_map_by_numero)} questions")

        original_num_count = len(saved_questions_details)
        mapped_num_count = len(question_map_by_numero)
        if mapped_num_count < original_num_count:
            print(f"⚠️ {original_num_count - mapped_num_count} question(s) sauvegardée(s) n'ont pas pu être mappées par numéro (numero/db_uuid manquant?).")

        page_sections = []
        header_matches = list(re.finditer(r'^# Page \d+', markdown_text, flags=re.MULTILINE))
        if not header_matches:
            if markdown_text.strip(): page_sections.append(markdown_text.strip())
        else:
            for i, match in enumerate(header_matches):
                start_content = match.end()
                end_content = header_matches[i+1].start() if (i + 1) < len(header_matches) else len(markdown_text)
                page_content = markdown_text[start_content:end_content].strip()
                if page_content: page_sections.append(page_content)

        if not page_sections:
            print("ℹ️ Aucun contenu de page trouvé pour l'extraction des propositions.")
            return

        all_reponses_to_insert_in_supabase = []
        total_api_calls_for_propositions = 0

        for i, page_markdown_content in enumerate(page_sections):
            print(f"📄 Traitement section {i + 1}/{len(page_sections)} pour propositions...")
            if not page_markdown_content.strip():
                print(f"    ⏩ Section de page {i + 1} vide, ignorée pour propositions.")
                continue
            
            # Tronquer le contenu pour éviter de dépasser les limites de prompt de l'API
            truncated_page_markdown_props = page_markdown_content[:20000] 

            prompt_props = f"""Tu es un expert en analyse de QCM.
            À partir du contenu Markdown d'UNE SEULE section de page de QCM ci-dessous:
            Identifie CHAQUE question présente sur CETTE page par son numéro.
            Pour CHAQUE question identifiée sur CETTE page, extrais ses propositions de réponses (A, B, C, D, E).

            Contenu Markdown de la section de page à analyser :
            ---
            {truncated_page_markdown_props}
            ---

            Retourne un objet JSON. Cet objet doit contenir une unique clé "questions_propositions",
            dont la valeur est une LISTE d'objets. Chaque objet dans la liste représente une question trouvée sur la page
            et doit avoir les clés :
            - "numero_question_sur_page" (un entier, le numéro de la question tel qu'identifié sur la page)
            - "propositions" (un objet avec les clés "A", "B", "C", "D", "E" pour le texte des propositions. Utilise null si une proposition est manquante).

            Si aucune question ou proposition n'est trouvée sur cette page, la liste "questions_propositions" doit être vide.

            Exemple de format de retour attendu pour UNE page :
            {{
              "questions_propositions": [
                {{
                  "numero_question_sur_page": 1,
                  "propositions": {{"A": "Texte A1", "B": "Texte B1", "C": "Texte C1", "D": "Texte D1", "E": "Texte E1"}}
                }},
                {{
                  "numero_question_sur_page": 2,
                  "propositions": {{"A": "Texte A2", "B": "Texte B2", "C": null, "D": "Texte D2", "E": null}}
                }}
              ]
            }}
            """
            try:
                total_api_calls_for_propositions +=1
                messages_props = [UserMessage(content=prompt_props)]
                response_props = self._call_api_with_retry(
                    self.client.chat.complete,
                    model="mistral-small-latest",
                    messages=messages_props,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )

                if response_props.choices and response_props.choices[0].message and response_props.choices[0].message.content:
                    extracted_props_str = response_props.choices[0].message.content
                    try:
                        raw_page_props_data = json.loads(extracted_props_str)
                        
                        questions_propositions_on_page = []
                        if isinstance(raw_page_props_data, dict):
                             questions_propositions_on_page = raw_page_props_data.get("questions_propositions", [])
                        
                        if not isinstance(questions_propositions_on_page, list):
                            print(f"    ⚠️ Format de 'questions_propositions' inattendu (pas une liste) pour section {i+1}. Reçu: {questions_propositions_on_page}")
                            continue

                        if questions_propositions_on_page:
                            print(f"    👍 {len(questions_propositions_on_page)} ensemble(s) de propositions extraits de la section {i+1}.")
                            # Ajout du log pour voir les numéros des questions pour cette page
                            question_nums_on_page = [item.get("numero_question_sur_page") for item in questions_propositions_on_page if isinstance(item, dict) and "numero_question_sur_page" in item]
                            print(f"        🔢 Numéros des questions identifiées sur cette page: {sorted(question_nums_on_page)}")
                            
                            for item in questions_propositions_on_page:
                                if not isinstance(item, dict) or "numero_question_sur_page" not in item or "propositions" not in item:
                                    print(f"        ⚠️ Item de propositions malformé ignoré: {item}")
                                    continue
                                
                                num_on_page = item.get("numero_question_sur_page")
                                props_dict = item.get("propositions")

                                if not isinstance(num_on_page, int) or not isinstance(props_dict, dict):
                                    print(f"        ⚠️ Type de numéro ou propositions invalide pour item: {item}")
                                    continue

                                question_db_uuid = question_map_by_numero.get(num_on_page)
                                if not question_db_uuid:
                                    # Ce log est important pour le débogage
                                    print(f"        ❓ Le numéro de question {num_on_page} (extrait par l'API sur la page) n'a pas été trouvé dans les questions initialement sauvegardées ou leur mappage. Propositions ignorées pour ce numéro.")
                                    continue

                                for lettre, texte_proposition in props_dict.items():
                                    if lettre in ["A", "B", "C", "D", "E"]:
                                        if texte_proposition is not None:
                                            cleaned_texte = str(texte_proposition).strip()
                                            if cleaned_texte:
                                                # Vérifier que l'UUID de la question existe bien dans la liste des UUIDs collectés en phase 1
                                                if question_db_uuid in question_id_list:
                                                    all_reponses_to_insert_in_supabase.append({
                                                        "question_id": question_db_uuid,
                                                        "lettre": lettre,
                                                        "contenu": {"text": cleaned_texte},
                                                        "uuid": str(uuid.uuid4()),
                                                        "est_correcte": False, 
                                                        "latex": None 
                                                    })
                                                else:
                                                    print(f"        ⚠️ L'ID {question_db_uuid} pour la question {num_on_page} n'est pas dans la liste des IDs valides. Proposition {lettre} ignorée.")
                        else:
                            print(f"    ℹ️ Aucune proposition trouvée sur la section {i+1} par l'API.")
                    except json.JSONDecodeError as e_json_props:
                        print(f"    ⚠️ Erreur JSON pour propositions section {i+1}: {e_json_props}. Réponse: {extracted_props_str}")
                else:
                    print(f"    ⚠️ Réponse API invalide/contenu manquant pour propositions section {i+1}.")
            except Exception as e_api_props:
                print(f"    🔥 Erreur API majeure pour propositions section {i+1}: {str(e_api_props)}")
            
            if i < len(page_sections) - 1: 
                print(f"    ⏸️ Pause de 5s avant section suivante pour propositions...")
                time.sleep(5)
        
        print(f"📞 Total d'appels API pour propositions: {total_api_calls_for_propositions}")

        if all_reponses_to_insert_in_supabase:
            print(f"💾 Sauvegarde de {len(all_reponses_to_insert_in_supabase)} propositions de réponses (total) dans Supabase...")
            chunk_size = 50 # Réduire la taille du chunk pour plus de sécurité
            total_inserted_count = 0
            for i_chunk in range(0, len(all_reponses_to_insert_in_supabase), chunk_size):
                chunk = all_reponses_to_insert_in_supabase[i_chunk:i_chunk + chunk_size]
                try:
                    result_r = self.supabase.table("reponses").insert(chunk).execute()
                    if result_r.data:
                        total_inserted_count += len(result_r.data)
                    else:
                        print(f"    ⚠️ Aucune donnée retournée pour un chunk de {len(chunk)} propositions, mais pas d'erreur explicite (possible ON CONFLICT DO NOTHING?).")
                except Exception as e_r_batch:
                    print(f"    🔥 Erreur lors de l'insertion d'un chunk de propositions: {str(e_r_batch)}")
                    # Log du premier élément du chunk problématique pour aider au débogage
                    if chunk:
                         print(f"        Premier élément du chunk problématique: {chunk[0]}")
            
            if total_inserted_count > 0:
                 print(f"✅ {total_inserted_count} propositions de réponses sauvegardées au total dans Supabase.")
            if total_inserted_count < len(all_reponses_to_insert_in_supabase):
                 print(f"⚠️ {len(all_reponses_to_insert_in_supabase) - total_inserted_count} propositions n'ont peut-être pas été sauvegardées correctement.")
        else:
            print("ℹ️ Aucune proposition de réponse valide à sauvegarder après traitement de toutes les pages.")
            
    # --- Fin des méthodes refactorées ---