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
from tqdm import tqdm

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
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if "rate limit exceeded" in str(e).lower() and attempt < max_retries - 1:
                    print(f"⚠️ Rate limit atteint, attente de {delay} secondes...")
                    time.sleep(delay)
                    delay *= 2  # Augmenter le délai à chaque tentative
                else:
                    print(f"⚠️ Erreur API (tentative {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"⏳ Nouvelle tentative dans {delay} secondes...")
                        time.sleep(delay)
        
        # Si on arrive ici, toutes les tentatives ont échoué
        print(f"❌ Échec après {max_retries} tentatives. Dernière erreur: {str(last_error)}")
        return None
    
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
            
            # Vérifier si l'appel API a échoué
            if ocr_response is None:
                print("❌ Échec de l'appel API OCR pour la conversion en Markdown")
                return None
            
            # Convertir le PDF en images dès le début pour pouvoir utiliser la méthode alternative si nécessaire
            pdf_images = self.pdf_to_images(pdf_path)
            if not pdf_images:
                print("❌ Impossible de convertir le PDF en images")
                return None
                
            print(f"✅ PDF converti en {len(pdf_images)} images")
            
            # Extraire le texte de toutes les pages
            markdown_content = ""
            replaced_pages = {}  # Garder une trace des pages remplacées
            
            for i, page in enumerate(ocr_response.pages):
                markdown_content += f"# Page {i+1}\n\n"
                
                # Vérification de la qualité du texte extrait
                page_markdown = page.markdown
                
                # Liste des patterns qui indiquent une extraction de mauvaise qualité
                low_quality_patterns = [
                    r'00000000000000',  # Séries de zéros (erreur OCR)
                    r'1111111111',      # Séries de uns (erreur OCR)
                    r'[^\w\s.,;:!?()-]{{20,}}',  # Longues séquences de caractères spéciaux
                    r'(\w)\1{10,}',     # Répétition du même caractère plus de 10 fois
                ]
                
                # Détection de critères objectifs de mauvaise qualité
                quality_check_failed = False
                
                # Vérifier si le texte est trop court
                if len(page_markdown.strip()) < 200:  # Page significativement courte
                    quality_check_failed = True
                    print(f"⚠️ Page {i+1} trop courte, seulement {len(page_markdown.strip())} caractères détectés")
                
                # Vérifier les patterns de mauvaise qualité
                for pattern in low_quality_patterns:
                    if re.search(pattern, page_markdown):
                        quality_check_failed = True
                        print(f"⚠️ Page {i+1} contient des patterns typiques d'erreur OCR")
                        break
                
                # Vérifier qu'il existe au moins une question sur cette page
                # Un QCM typique devrait avoir des questions numérotées comme "Question 1", "Q2", etc.
                question_pattern = r'(?:[Qq](?:uestion)?\s*\d+|^\d+\s*[\.\)])'
                if not re.search(question_pattern, page_markdown) and i > 0:  # Ignorer la première page qui peut être un en-tête
                    print(f"⚠️ Page {i+1} ne contient aucune question détectable")
                    # Ne pas échouer automatiquement, mais augmenter la probabilité d'utiliser l'alternative
                    if len(page_markdown.strip()) < 400:  # Si en plus le texte est assez court
                        quality_check_failed = True
                
                # Si l'extraction est de mauvaise qualité, essayer une méthode alternative basée sur la vision
                if quality_check_failed and i < len(pdf_images):
                    print(f"⚠️ Qualité OCR faible détectée pour la page {i+1}, utilisation de l'API vision...")
                    
                    try:
                        # Utiliser l'API de vision pour extraire le texte de l'image
                        alt_text = self.extract_text_from_image_with_vision(pdf_images[i])
                        
                        if alt_text and len(alt_text.strip()) > 200:  # Vérifier que le texte extrait est suffisant
                            page_markdown = alt_text
                            print(f"✅ Extraction alternative réussie pour la page {i+1}")
                            replaced_pages[i+1] = "vision_api"  # Garder une trace des pages remplacées
                        else:
                            print(f"⚠️ Extraction alternative insuffisante pour la page {i+1}")
                    except Exception as alt_err:
                        print(f"⚠️ Erreur lors de l'extraction alternative pour la page {i+1}: {str(alt_err)}")
                
                markdown_content += page_markdown + "\n\n"
            
            # Sauvegarder le Markdown
            pdf_stem = Path(pdf_path).stem
            output_dir = self.outputs_dir / pdf_stem
            output_dir.mkdir(exist_ok=True)
            
            markdown_path = output_dir / "content.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # Sauvegarder aussi les informations sur les pages remplacées
            replaced_info_path = output_dir / "replaced_pages.json"
            with open(replaced_info_path, "w", encoding="utf-8") as f:
                json.dump(replaced_pages, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Markdown sauvegardé: {markdown_path}")
            return str(markdown_path)
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion en Markdown: {str(e)}")
            return None

    def extract_text_from_image_with_vision(self, image_path: str) -> str:
        """
        Extrait le texte d'une image en utilisant l'API Mistral avec capacités de vision.
        Cette méthode est utilisée comme alternative quand l'OCR standard échoue.
        
        Args:
            image_path (str): Chemin vers l'image à analyser
            
        Returns:
            str: Le texte extrait de l'image
        """
        try:
            print(f"🔍 Tentative d'extraction de texte depuis l'image {image_path} avec l'API vision...")
            
            # Encoder l'image en base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            
            # Construire les messages pour l'API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Tu es un expert en extraction de texte à partir d'images de QCM. 
                            
Extrais TOUT le texte visible dans cette image, en particulier:
- Titres et en-têtes
- Questions numérotées (par ex. "Question 16", "Q.17", etc.)
- Propositions de réponses (A, B, C, D, E)
- Tout texte explicatif ou instructions

Maintiens le formatage exact avec les numéros des questions et les lettres des propositions.
Conserve les paragraphes et la structure du texte.
Formate ta réponse en markdown simple.
                            
Si tu vois des formules mathématiques, essaie de les représenter correctement avec la notation LaTex."""
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]
            
            # Appeler l'API vision
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-large-latest",  # Utiliser le modèle large qui a de meilleures capacités de vision
                messages=messages,
                temperature=0.0,
                max_tokens=4000
            )
            
            if response is None:
                print("❌ Échec de l'appel API vision")
                return ""
            
            extracted_text = response.choices[0].message.content.strip()
            
            # Résumer les résultats
            text_length = len(extracted_text)
            num_questions = len(re.findall(r'(?:[Qq](?:uestion)?\s*\d+|^\d+\s*[\.\)])', extracted_text))
            print(f"✅ Extraction par vision réussie: {text_length} caractères, ~{num_questions} questions détectées")
            
            return extracted_text
            
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction par vision: {str(e)}")
            return ""
    
    def save_to_supabase(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sauvegarde les métadonnées dans Supabase"""
        try:
            print("💾 Sauvegarde dans Supabase...")
            
            # Vérifier si un QCM avec ce type et année existe déjà
            # Comme il n'y a pas de colonne metadata, nous vérifions par type et année
            if metadata.get("type") and metadata.get("ue") and metadata.get("annee"):
                try:
                    type_qcm = metadata.get("type")
                    annee = metadata.get("annee")
                    
                    existing_qcms = self.supabase.table("qcm").select("id", "type", "annee", "uuid").eq("type", type_qcm).eq("annee", annee).execute()
                    
                    if existing_qcms.data:
                        # Le QCM existe déjà si type et année correspondent
                        print(f"ℹ️ QCM de type '{type_qcm}' pour l'année '{annee}' existe déjà. ID: {existing_qcms.data[0]['id']}")
                        return existing_qcms.data[0]
                except Exception as check_err:
                    print(f"⚠️ Erreur lors de la vérification des QCM existants: {str(check_err)}")
            
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
            
            # Préparer les données pour Supabase en fonction du schéma réel
            supabase_data = {
                "ue_id": ue_id,
                "type": metadata["type"],
                "annee": metadata["annee"],
                "uuid": str(uuid.uuid4())  # Générer un UUID unique
            }
            
            # Ajouter date_examen si disponible
            if "date_examen" in metadata:
                supabase_data["date_examen"] = metadata["date_examen"]
            
            # Insérer dans Supabase dans la table 'qcm'
            result = self.supabase.table("qcm").insert(supabase_data).execute()
            
            if result.data:
                print(f"✅ QCM sauvegardé dans Supabase (ID: {result.data[0]['id']})")
                # Stocker le chemin du fichier Markdown dans une variable d'instance
                self._last_markdown_path = metadata.get('markdown_path')
                return result.data[0]
            else:
                print("⚠️ Aucune donnée retournée lors de l'insertion du QCM")
                return None
            
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
            
            # Vérifier si l'appel API a échoué
            if response is None:
                print("❌ Échec de l'appel API pour l'extraction des métadonnées")
                return None
            
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
                        
                        # SUPPRESSION DE LA PAUSE SIGNIFICATIVE ICI - Cause racine identifiée ailleurs
                        # delay_before_propositions = 10 # secondes
                        # print(f"⏸️ Pause de {delay_before_propositions} secondes avant la Phase 2 (Propositions) pour assurer la visibilité des données...")
                        # time.sleep(delay_before_propositions)
                        
                        print("▶️ Lancement de la Phase 2: Extraction des propositions...")
                        # La pause originale de 10s pour l'API peut être rétablie si nécessaire, mais le problème principal est ailleurs.
                        # print("⏸️ Pause de 10 secondes avant l'extraction des propositions...")
                        # time.sleep(10) 
                        
                        # Obtenir le nombre initial de propositions pour cette question
                        prop_count_before = 0
                        try:
                            # Récupérer les IDs des questions de ce QCM
                            question_ids_result = self.supabase.table("questions").select("id").eq("qcm_id", qcm_id_for_processing).execute()
                            
                            if question_ids_result.data:
                                question_ids = [q["id"] for q in question_ids_result.data]
                                
                                # On peut faire une requête générale pour compter toutes les propositions
                                if question_ids:
                                    # Convertir la liste d'IDs en format pour la requête "in"
                                    # Comme on ne peut pas utiliser "in" directement avec Supabase Python,
                                    # on va faire plusieurs requêtes et additionner les résultats
                                    for q_id in question_ids:
                                        count_result = self.supabase.table("reponses").select("id").eq("question_id", q_id).execute()
                                        if count_result.data:
                                            prop_count_before += len(count_result.data)
                        except Exception as e:
                            print(f"⚠️ Erreur lors du comptage initial des propositions: {str(e)}")
                        
                        # Extraire les propositions
                        self._extract_and_save_propositions(markdown_content_for_processing, qcm_id_for_processing, saved_questions_details)
                        print("🏁 Phase 2 terminée.")
                        
                        # Nettoyer les questions et propositions dupliquées
                        print("🧹 Nettoyage des questions et propositions dupliquées...")
                        self._clean_duplicate_questions_and_propositions(qcm_id_for_processing)
                        
                        # Compter les propositions après insertion pour les statistiques
                        prop_count_after = 0
                        try:
                            # Récupérer les IDs des questions de ce QCM
                            question_ids_result = self.supabase.table("questions").select("id").eq("qcm_id", qcm_id_for_processing).execute()
                            
                            if question_ids_result.data:
                                question_ids = [q["id"] for q in question_ids_result.data]
                                
                                # On peut faire une requête générale pour compter toutes les propositions
                                if question_ids:
                                    for q_id in question_ids:
                                        count_result = self.supabase.table("reponses").select("id").eq("question_id", q_id).execute()
                                        if count_result.data:
                                            prop_count_after += len(count_result.data)
                        except Exception as e:
                            print(f"⚠️ Erreur lors du comptage final des propositions: {str(e)}")
                        
                        # Calculer le nombre de propositions insérées
                        propositions_inserted = prop_count_after - prop_count_before
                        
                        # Ajouter les statistiques aux métadonnées
                        metadata["questions_count"] = len(saved_questions_details)
                        metadata["propositions_count"] = propositions_inserted
                        
                        # Vérifier si toutes les questions ont des propositions
                        if propositions_inserted > 0:
                            avg_props_per_question = propositions_inserted / len(saved_questions_details)
                            metadata["avg_propositions_per_question"] = avg_props_per_question
                            
                            # Estimer la complétude (idéalement on devrait avoir 5 propositions par question)
                            expected_total = len(saved_questions_details) * 5
                            completeness = (propositions_inserted / expected_total) * 100 if expected_total > 0 else 0
                            metadata["extraction_completeness"] = completeness
                            
                            print(f"📊 Statistiques d'extraction: {propositions_inserted} propositions pour {len(saved_questions_details)} questions")
                            print(f"📊 Moyenne de {avg_props_per_question:.1f} propositions par question (complétude: {completeness:.1f}%)")
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

    def _clean_duplicate_questions_and_propositions(self, qcm_id: int) -> None:
        """
        Nettoie les questions dupliquées et les propositions dupliquées pour un QCM.
        Cette méthode est appelée après l'extraction pour s'assurer que chaque question
        a exactement 5 propositions (A, B, C, D, E).
        
        Args:
            qcm_id (int): ID du QCM à nettoyer
        """
        print(f"🔍 Vérification des questions pour le QCM ID: {qcm_id}")
        
        # Détection des questions dupliquées
        questions = self.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute()
        
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
        
        if duplicate_questions:
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
                        delete_props = self.supabase.table('reponses').delete().eq('question_id', q_to_delete['id']).execute()
                        print(f"  🗑️ Suppression de {len(delete_props.data) if delete_props.data else 0} propositions pour la question {num} (ID: {q_to_delete['id']})")
                        
                        # Ensuite, supprimer la question elle-même
                        delete_q = self.supabase.table('questions').delete().eq('id', q_to_delete['id']).execute()
                        print(f"  🗑️ Question {num} en double (ID: {q_to_delete['id']}) supprimée")
                        
                        # Pause pour éviter de surcharger l'API
                        time.sleep(0.2)
                    except Exception as e:
                        print(f"  ❌ Erreur lors de la suppression de la question {num} (ID: {q_to_delete['id']}): {str(e)}")
        
        # Maintenant obtenir une liste à jour des questions
        questions = self.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute()
        
        questions_to_fix = []
        
        # Vérifier combien de propositions a chaque question
        for question in questions.data:
            q_id = question['id']
            q_num = question['numero']
            
            # Récupérer les propositions pour cette question
            props = self.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
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
                        result = self.supabase.table('reponses').delete().eq('id', delete_id).execute()
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
        for question in self.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute().data:
            q_id = question['id']
            q_num = question['numero']
            
            # Récupérer les propositions pour cette question
            props = self.supabase.table('reponses').select('*').eq('question_id', q_id).execute()
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

            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-small-latest",
                messages=messages,
                temperature=0.0,
                max_tokens=1000
            )

            # Vérifier si l'appel API a échoué
            if response is None:
                print(f"❌ Échec de l'appel API pour l'extraction de texte de l'image {image_path}")
                return ""

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
        """Phase 1: Extrait les questions uniquement d'un document Markdown"""
        print(f"📝 Phase 1: Extraction des questions uniquement pour QCM ID: {qcm_id}...")
        
        # Charger les informations sur les pages remplacées si elles existent
        pdf_stem = None
        replaced_questions = []
        
        # Déterminer le répertoire de sortie
        match = re.search(r'qcm_extraction/temp/outputs/([^/]+)/content\.md', markdown_text)
        if match:
            pdf_stem = match.group(1)
            replaced_info_path = Path(f"qcm_extraction/temp/outputs/{pdf_stem}/replaced_pages.json")
            
            if replaced_info_path.exists():
                try:
                    with open(replaced_info_path, "r", encoding="utf-8") as f:
                        replaced_pages = json.load(f)
                        
                        # Extraire toutes les questions remplacées
                        for page_num, questions in replaced_pages.items():
                            replaced_questions.extend(questions)
                            
                        print(f"ℹ️ Questions remplacées détectées: {replaced_questions}")
                except Exception as e:
                    print(f"⚠️ Erreur lors du chargement des informations sur les pages remplacées: {str(e)}")
        
        # Diviser le document en sections par page
        page_sections = []
        header_matches = list(re.finditer(r'^# Page \d+', markdown_text, flags=re.MULTILINE))
        
        if not header_matches:
            if markdown_text.strip():
                page_sections.append({"index": 1, "content": markdown_text.strip()})
        else:
            for i, match in enumerate(header_matches):
                start_content = match.end()
                end_content = header_matches[i+1].start() if (i + 1) < len(header_matches) else len(markdown_text)
                page_content = markdown_text[start_content:end_content].strip()
                
                # Extraire le numéro de page
                page_header = match.group(0)
                page_num = re.search(r'Page (\d+)', page_header)
                page_num = int(page_num.group(1)) if page_num else i + 1
                
                print(f"    📄 Section de page {i+1} correspond à la Page {page_num} du PDF")
                
                if page_content:
                    page_sections.append({"index": i+1, "content": page_content, "page_num": page_num})
        
        print(f"📄 Traitement page par page ({len(page_sections)} sections)...")
        
        # Collections de questions et tracking des numéros de questions
        all_questions_data = []
        unique_question_numbers = set()
        question_numbers_sequence = []
        
        # Pour chaque section de page, extraire les questions
        for index, section in enumerate(page_sections):
            print(f"📄 Traitement section {index+1}/{len(page_sections)} pour questions...")
            
            # Vérifier si cette section contient du contenu remplacé
            has_replaced_content = False
            if "<!-- REPLACED_CONTENT:START -->" in section["content"] and "<!-- REPLACED_CONTENT:END -->" in section["content"]:
                has_replaced_content = True
                print(f"    ⚠️ Cette section contient du contenu remplacé (page {section.get('page_num', index+1)})")
            
            # Structure pour l'appel API
            prompt_data = {
                "content": section["content"],
                "section_num": index + 1,
                "qcm_id": qcm_id,
                "has_replaced_content": has_replaced_content
            }
            
            # Appel à l'API pour extraction des questions
            try:
                max_questions_in_section = 15  # Limite raisonnable par section
                
                # Détecter les questions avec un regex de base d'abord
                potential_questions = re.findall(r'(?:Q(?:uestion)?\s*(\d+)|^(\d+)\s*[\.\)])', section["content"], re.MULTILINE)
                flattened_matches = [int(num) for match in potential_questions for num in match if num]
                unique_detected_nums = set(flattened_matches)
                
                detected_count = len(unique_detected_nums)
                
                if detected_count > max_questions_in_section:
                    print(f"    ⚠️ Détecté {detected_count} numéros de questions potentielles, ce qui semble élevé. Limitation aux {max_questions_in_section} premiers.")
                    prompt_data["max_questions"] = max_questions_in_section
                
                questions_api_result = self._call_api_with_retry(
                    self._extract_questions_api,
                    content=prompt_data["content"],
                    section_index=index
                )
                
                # Valider et nettoyer les résultats
                if questions_api_result:
                    # Filtrer et normaliser les données
                    for q in questions_api_result:
                        # Si la question n'a pas de numéro, la sauter
                        if "numero_question" not in q or not q["numero_question"]:
                            continue
                        
                        try:
                            numero = int(q["numero_question"])
                            
                            # Vérifier si cette question est dans une page remplacée et déjà extraite d'ailleurs
                            if has_replaced_content and numero in replaced_questions and numero in unique_question_numbers:
                                print(f"    🔍 Question {numero} déjà extraite, ignorée car doublon dans contenu remplacé")
                                continue
                            
                            # Ajouter la question
                            question_data = {
                                "numero": numero,
                                "contenu": {"text": q.get("texte_question", "")},
                                "qcm_id": qcm_id,
                                "section_index": index,
                                "page_num": section.get("page_num", index+1)
                            }
                            
                            all_questions_data.append(question_data)
                            unique_question_numbers.add(numero)
                            question_numbers_sequence.append(numero)
                        except (ValueError, TypeError) as e:
                            print(f"    ⚠️ Erreur de traitement pour la question: {str(e)}")
                
                print(f"    ✅ {len(questions_api_result) if questions_api_result else 0} questions trouvées dans la section {index+1}")
                
            except Exception as e:
                print(f"    ⚠️ Erreur lors de l'extraction des questions de la section {index+1}: {str(e)}")
        
        # Supprimer les doublons basés sur le numero de question
        questions_deduplicated = {}
        for q in all_questions_data:
            q_num = q["numero"]
            if q_num not in questions_deduplicated:
                questions_deduplicated[q_num] = q
        
        # Tri par numéro de question
        sorted_questions = [questions_deduplicated[num] for num in sorted(questions_deduplicated.keys())]
        
        # Vérifier s'il manque des questions dans la séquence
        if sorted_questions:
            questions_sequence = sorted([q["numero"] for q in sorted_questions])
            expected_seq = list(range(min(questions_sequence), max(questions_sequence) + 1))
            missing_questions = [q for q in expected_seq if q not in questions_sequence]
            
            if missing_questions:
                print(f"⚠️ ATTENTION: Questions manquantes détectées: {missing_questions}")
                print(f"   Vérifiez le PDF source pour ces questions.")
        
        print(f"📊 Total de {len(all_questions_data)} questions collectées (brutes API).")
        # Avertissement des questions manquantes
        if sorted_questions:
            questions_nums = [q["numero"] for q in sorted_questions]
            expected_range = list(range(min(questions_nums), max(questions_nums) + 1))
            missing = [n for n in expected_range if n not in questions_nums]
            if missing:
                print(f"⚠️ Questions manquantes dans la séquence: {missing}")
        
        # Sauvegarder les questions dans Supabase
        saved_questions_details = []
        
        if sorted_questions:
            # Étape 1: Récupérer les questions existantes pour ce qcm_id
            existing_questions_db = {}
            try:
                print(f"    🔍 Vérification des questions existantes pour QCM ID: {qcm_id}...")
                result = self.supabase.table("questions").select("id, numero, uuid").eq("qcm_id", qcm_id).execute()
                if result.data:
                    for q_db in result.data:
                        existing_questions_db[q_db["numero"]] = {"id": q_db["id"], "uuid": q_db["uuid"]}
                    print(f"    ℹ️ {len(existing_questions_db)} questions existantes trouvées pour ce QCM.")
                    # Log des UUIDs existants
                    # for numero, details in existing_questions_db.items():
                    #    print(f"        [EXISTING Q] Numero: {numero}, UUID: {details['uuid']}")
            except Exception as e_fetch_existing_q:
                print(f"    🔥 Erreur lors de la vérification des questions existantes: {str(e_fetch_existing_q)}")
            
            questions_to_insert_api = []
            
            for q_extracted in sorted_questions:
                numero = q_extracted.get("numero")
                if numero in existing_questions_db:
                    # Question existante, ajouter ses détails (y compris l'UUID de la BD)
                    saved_questions_details.append({
                        "db_uuid": existing_questions_db[numero]["uuid"], # Important: UUID de la BD
                        "db_id": existing_questions_db[numero]["id"],     # ID entier de la BD
                        "qcm_id": qcm_id,
                        "numero": numero,
                        "texte": q_extracted.get("texte_question"),
                        "page_document": q_extracted.get("page_document")
                    })
                    print(f"        [LOG saved_details - Existant] Q {numero} -> UUID: {existing_questions_db[numero]['uuid']}")

                else:
                    # Nouvelle question
                    q_extracted["uuid"] = str(uuid.uuid4()) # Attribuer un nouvel UUID seulement si nouvelle
                    questions_to_insert_api.append({
                        "qcm_id": q_extracted["qcm_id"],
                        "numero": q_extracted["numero"],
                        "uuid": q_extracted["uuid"],
                        "contenu": q_extracted["contenu"]
                    })
            
            if questions_to_insert_api:
                print(f"    💾 Sauvegarde de {len(questions_to_insert_api)} NOUVELLES questions dans Supabase...")
                # Diviser en batches pour l'insertion
                batch_size = 50 # Peut être ajusté
                
                for i in range(0, len(questions_to_insert_api), batch_size):
                    chunk = questions_to_insert_api[i:i+batch_size]
                    try:
                        insert_result = self.supabase.table("questions").insert(chunk).execute()
                        if insert_result.data:
                            for q_inserted in insert_result.data:
                                saved_questions_details.append({
                                    "db_uuid": q_inserted.get("uuid"),
                                    "db_id": q_inserted.get("id"),
                                    "qcm_id": q_inserted.get("qcm_id"),
                                    "numero": q_inserted.get("numero"),
                                    "texte": q_inserted.get("texte"), # Assumant que l'API insert retourne le texte
                                    "page_document": q_inserted.get("page_document") # Idem
                                })
                                print(f"        [LOG saved_details - Nouveau] Q {q_inserted.get('numero')} -> UUID: {q_inserted.get('uuid')}")
                        else:
                            print(f"    ⚠️ Aucune donnée retournée par Supabase pour un lot de {len(chunk)} nouvelles questions.")
                    except Exception as e_insert_q_new:
                        print(f"    🔥 Erreur lors de l\'insertion de NOUVELLES questions: {str(e_insert_q_new)}")
            else:
                print("    ℹ️ Aucune nouvelle question à insérer. Toutes les questions extraites existaient déjà.")
        else:
            print("    ℹ️ Aucune question extraite de l'API à traiter.")
        
        # Filtrer les entrées incomplètes ou celles où db_id/db_uuid pourrait être None
        saved_questions_details = [
            q for q in saved_questions_details 
            if q.get("db_uuid") and q.get("qcm_id") is not None and q.get("numero") is not None
        ]
        
        print(f"📊 Total de {len(saved_questions_details)} questions disponibles pour la suite du traitement.")
        return saved_questions_details

    def _extract_and_save_propositions(self, markdown_text: str, qcm_id: int, saved_questions_details: List[Dict[str, Any]]):
        """Phase 2: Extrait les propositions pour des questions déjà sauvegardées et les insère dans Supabase."""
        if not saved_questions_details:
            print("ℹ️ Phase 2 Propositions: Aucune question sauvegardée fournie, donc pas de propositions à extraire.")
            return

        import datetime
        start_time = datetime.datetime.now()
        question_count = len(saved_questions_details)
        print(f"📝 Phase 2: Extraction des propositions pour {question_count} questions du QCM ID: {qcm_id}...")

        # Utiliser saved_questions_details COMME SOURCE PRINCIPALE pour le mappage UUID
        question_uuid_map_by_numero = {}
        if not saved_questions_details:
            print("⚠️ saved_questions_details est vide. Impossible de mapper les numéros de question aux UUIDs.")
            print("   Cela peut se produire si la phase d'extraction des questions n'a rien retourné ou a échoué.")
            return # Arrêt si aucune information de question n'est disponible

        for q_detail in saved_questions_details:
            numero = q_detail.get("numero")
            # CORRECTION CRUCIALE ICI: Utiliser "db_id" qui contient la PK UUID de la table 'questions'
            # au lieu de "db_uuid" qui contenait l'autre colonne UUID.
            question_pk_uuid = q_detail.get("db_id") 
            if numero is not None and question_pk_uuid is not None:
                question_uuid_map_by_numero[numero] = question_pk_uuid
            else:
                print(f"⚠️ Détail de question incomplet dans saved_questions_details: {q_detail}. PK UUID (db_id) ou numéro manquant.")

        if not question_uuid_map_by_numero:
            print("❌ Impossible de construire le mappage Numéro de Question -> PK UUID à partir de saved_questions_details.")
            print("   Assurez-vous que _extract_and_save_questions_only retourne des détails valides avec 'numero' et 'db_id'.")
            return
                
        print(f"📌 {len(question_uuid_map_by_numero)} questions mappées (numéro -> PK UUID) en utilisant saved_questions_details.")
        # Log détaillé du mapping
        # for num, uid in question_uuid_map_by_numero.items():
        #    print(f"        [MAP] Q {num} -> UUID {uid}")

        # Diviser le document en sections
        page_sections = []
        header_matches = list(re.finditer(r'^# Page \d+', markdown_text, flags=re.MULTILINE))
        
        if not header_matches:
            if markdown_text.strip(): 
                page_sections.append({"index": 1, "content": markdown_text.strip(), "page_num": 1})
        else:
            for i, match in enumerate(header_matches):
                start_content = match.end()
                end_content = header_matches[i+1].start() if (i + 1) < len(header_matches) else len(markdown_text)
                page_content = markdown_text[start_content:end_content].strip()
                
                # Extraire le numéro de page
                page_header = match.group(0)
                page_num = re.search(r'Page (\d+)', page_header)
                page_num = int(page_num.group(1)) if page_num else i + 1
                
                if page_content:
                    page_sections.append({"index": i+1, "content": page_content, "page_num": page_num})

        if not page_sections:
            print("ℹ️ Aucun contenu de page trouvé pour l'extraction des propositions.")
            return
            
        # Structure pour stocker toutes les propositions extraites
        all_propositions = []
        
        # Liste des numéros de questions pour lesquelles on recherche des propositions
        # Utiliser les numéros des questions pour lesquelles on a un UUID
        missing_questions = set(question_uuid_map_by_numero.keys())
        
        # OPTIMISATION: Traiter les sections par groupes pour réduire les appels API
        # Regrouper les sections en batch de 2-3 pour réduire le nombre d'appels API tout en gardant un contexte pertinent
        batched_sections = []
        current_batch = []
        current_batch_size = 0
        target_batch_size = 10000  # Viser ~10K caractères par batch pour un bon équilibre
        
        for section in page_sections:
            if current_batch_size + len(section["content"]) > target_batch_size and current_batch:
                batched_sections.append(current_batch)
                current_batch = [section]
                current_batch_size = len(section["content"])
            else:
                current_batch.append(section)
                current_batch_size += len(section["content"])
        
        if current_batch:  # Ajouter le dernier batch
            batched_sections.append(current_batch)
            
        print(f"📊 Optimisation: {len(page_sections)} sections regroupées en {len(batched_sections)} batchs pour réduire les appels API")
        
        # Barre de progression simple dans le terminal
        total_batches = len(batched_sections)
        
        # Pour le suivi de progression
        print(f"⏱️  Démarrage de l'extraction des propositions à {start_time.strftime('%H:%M:%S')}")
        print(f"⌛ [{'·' * total_batches}] 0% - 0/{total_batches} batchs traités")
        
        # Traiter les batchs de sections
        for batch_index, batch in enumerate(batched_sections):
            # Construire un contenu combiné avec des séparateurs clairs pour ce batch
            batch_content = "\n\n==== NOUVELLE SECTION ====\n\n".join([section["content"] for section in batch])
            batch_indexes = [section["index"] for section in batch]
            
            # Afficher la progression
            progress = int((batch_index / total_batches) * 100)
            progress_bar = '█' * (batch_index) + '·' * (total_batches - batch_index)
            print(f"\r⌛ [{progress_bar}] {progress}% - {batch_index}/{total_batches} batchs traités", end="")
            
            # Si toutes les questions sont couvertes, on peut arrêter le traitement
            if not missing_questions:
                print(f"\n✅ Toutes les questions ont des propositions! Arrêt anticipé du traitement.")
                break
            
            # Extraire les propositions avec un seul appel API pour tout le batch
            extracted_props = self._extract_propositions_with_api(
                batch_content, 
                prompt_type="optimized",
                section_index=f"batch_{batch_index+1}"
            )
            
            if extracted_props:
                all_propositions.extend(extracted_props)
                
                # Mettre à jour les questions trouvées
                question_nums = [item["numero_question"] for item in extracted_props]
                missing_questions -= set(question_nums)
                if batch_index < total_batches - 1:  # Ne pas afficher pour le dernier batch
                    print(f" | ✓ {len(question_nums)} question(s) traitées")
            else:
                # Fallback - essayer avec le prompt simplifié seulement si on a moins de 50% des questions
                if len(missing_questions) > len(question_uuid_map_by_numero) / 2:
                    extracted_props_fallback = self._extract_propositions_with_api(
                        batch_content, 
                        prompt_type="simplified",
                        section_index=f"batch_{batch_index+1}"
                    )
                    
                    if extracted_props_fallback:
                        all_propositions.extend(extracted_props_fallback)
                        question_nums = [item["numero_question"] for item in extracted_props_fallback]
                        missing_questions -= set(question_nums)
                        if batch_index < total_batches - 1:  # Ne pas afficher pour le dernier batch
                            print(f" | ✓ {len(question_nums)} question(s) traitées avec fallback")
                    else:
                        if batch_index < total_batches - 1:  # Ne pas afficher pour le dernier batch
                            print(f" | ⚠️ Aucune proposition extraite pour ce batch")
                else:
                    if batch_index < total_batches - 1:  # Ne pas afficher pour le dernier batch
                        print(f" | ⚠️ Aucune proposition extraite pour ce batch")
            
            # Pause légère pour éviter le rate limiting (réduite de 5s à 2s)
            if batch_index < len(batched_sections) - 1:
                time.sleep(2)
        
        # Terminer la barre de progression
        print("\n✅ Extraction des propositions terminée")
        
        # Si après les passes précédentes il reste des questions sans propositions, utiliser des regex
        if missing_questions:
            print(f"⚠️ Après l'extraction par API, il reste {len(missing_questions)} questions sans propositions.")
            print("🔍 Tentative d'extraction par regex patterns...")
            
            # Définir des patterns courants pour les propositions A, B, C, D, E
            proposition_patterns = [
                r'([A-E])\.\s+(.*?)(?=(?:[A-E]\.|\n\n|$))',  # A. Texte
                r'([A-E])\s*[:]\s+(.*?)(?=(?:[A-E]\s*:|\n\n|$))',  # A : Texte
                r'([A-E])\)\s+(.*?)(?=(?:[A-E]\)|\n\n|$))',  # A) Texte
                r'([A-E])\s+-\s+(.*?)(?=(?:[A-E]\s+-|\n\n|$))',  # A - Texte
                r'(?<!\w)([A-E])(?!\w)\s+(.*?)(?=(?:(?<!\w)[A-E](?!\w)|\n\n|$))'  # A Texte (sans ponctuation)
            ]
            
            # Parcourir TOUTES les sections pour les questions manquantes
            regex_propositions = []
            
            # Rechercher les questions manquantes dans toutes les sections
            for missing_num in missing_questions:
                # Construire un pattern pour détecter la question
                question_pattern = fr"(?:{missing_num}\s*[\.:)]|[Qq]uestion\s*{missing_num}|{missing_num}\s*[^\d])"
                
                # Chercher dans toutes les sections
                for section in page_sections:
                    section_content = section["content"]
                    
                    # Tenter de trouver la question dans cette section
                    question_match = re.search(question_pattern, section_content)
                    if question_match:
                        # Définir la zone de recherche pour les propositions
                        start_pos = question_match.start()
                        # Chercher dans un intervalle de 2000 caractères après la question
                        search_zone = section_content[start_pos:start_pos + 2000]
                        
                        # Rechercher les propositions dans cette zone
                        found_props = {}
                        for pattern in proposition_patterns:
                            for match in re.finditer(pattern, search_zone, re.DOTALL):
                                lettre, texte = match.groups()
                                texte = texte.strip()
                                if texte and lettre in "ABCDE" and lettre not in found_props:
                                    found_props[lettre] = texte
                        
                        if found_props:
                            regex_propositions.append({
                                "numero_question": missing_num,
                                "propositions": found_props
                            })
                            # Ne plus chercher cette question
                            break
                        
            if regex_propositions:
                print(f"✅ Extraction par regex réussie pour {len(regex_propositions)} questions")
                all_propositions.extend(regex_propositions)
                
                # Mettre à jour les questions trouvées
                question_nums = [item["numero_question"] for item in regex_propositions]
                missing_questions -= set(question_nums)

        # Préparation des données pour Supabase
        all_reponses_to_insert = []
        
        for prop_set in all_propositions:
            question_num = prop_set.get("numero_question")
            # Utiliser le mappage numero -> uuid
            if question_num not in question_uuid_map_by_numero:
                print(f"⚠️  Proposition pour Q{question_num} ignorée car UUID de question non trouvé dans le mappage.")
                continue
                
            question_uuid_for_reponse = question_uuid_map_by_numero[question_num] # UUID de la question
            propositions = prop_set.get("propositions", {})
            
            for lettre, texte in propositions.items():
                if lettre in "ABCDE" and texte:
                    texte_clean = str(texte).strip()
                    if texte_clean:
                        all_reponses_to_insert.append({
                            "question_id": question_uuid_for_reponse,  # UTILISER L'UUID ICI
                            "lettre": lettre,
                            "contenu": json.dumps({"text": texte_clean}),
                            "uuid": str(uuid.uuid4()),
                            "est_correcte": False, # Sera mis à jour plus tard
                            "latex": None # Ou extraire si disponible
                        })

        # Insertion des propositions dans Supabase
        print(f"📊 Statistiques finales d'extraction:")
        print(f"  - {len(all_propositions)} ensembles de propositions trouvés")
        print(f"  - {len(all_reponses_to_insert)} propositions individuelles à insérer")
        
        if missing_questions:
            print(f"⚠️ {len(missing_questions)} questions restent sans propositions: {sorted(missing_questions)}")
        else:
            print("✅ Toutes les questions ont des propositions!")

        if all_reponses_to_insert:
            # ÉTAPE DE DÉDUPLICATION AVANT INSERTION
            print(f"🔍 Vérification des propositions existantes avant insertion pour éviter les doublons...")
            final_propositions_to_insert = []
            existing_props_cache = {} # Cache pour question_id -> set de lettres existantes

            for prop_to_check in tqdm(all_reponses_to_insert, desc="Déduplication des propositions", unit="prop"):
                q_uuid = prop_to_check["question_id"]
                lettre = prop_to_check["lettre"]

                if q_uuid not in existing_props_cache:
                    try:
                        result = self.supabase.table("reponses").select("lettre").eq("question_id", q_uuid).execute()
                        existing_props_cache[q_uuid] = {p["lettre"] for p in result.data} if result.data else set()
                    except Exception as e_fetch_props:
                        print(f"\n    🔥 Erreur lors de la récupération des propositions existantes pour Q_UUID {q_uuid}: {e_fetch_props}")
                        existing_props_cache[q_uuid] = set() # Supposer qu'il n'y en a pas pour continuer
                
                if lettre not in existing_props_cache[q_uuid]:
                    final_propositions_to_insert.append(prop_to_check)
                    existing_props_cache[q_uuid].add(lettre) # Ajouter au cache pour ce batch
                # else:
                    # print(f"    [DEDUPLICATION] Proposition {lettre} pour Q_UUID {q_uuid} existe déjà. Ignorée.")
            
            if not final_propositions_to_insert:
                print("ℹ️ Aucune nouvelle proposition à insérer après déduplication.")
            else:
                print(f"💾 Sauvegarde de {len(final_propositions_to_insert)} NOUVELLES propositions dans Supabase (après déduplication)...")
                
                chunk_size = 100
                total_inserted = 0
                num_chunks = (len(final_propositions_to_insert) + chunk_size - 1) // chunk_size

                with tqdm(total=num_chunks, desc="Insertion des nouvelles propositions", unit="chunk") as pbar_chunks:
                    for i in range(0, len(final_propositions_to_insert), chunk_size):
                        chunk = final_propositions_to_insert[i:i + chunk_size]
                        try:
                            result = self.supabase.table("reponses").insert(chunk).execute()
                            if result.data:
                                total_inserted += len(result.data)
                        except Exception as e:
                            print(f"\n    🔥 Erreur lors de l'insertion d'un chunk de nouvelles propositions: {str(e)}")
                            problematic_question_uuids_in_chunk = list(set([p.get('question_id') for p in chunk]))
                            print(f"        UUIDs des questions dans le chunk problématique: {problematic_question_uuids_in_chunk}")
                        pbar_chunks.update(1)
                
                if total_inserted > 0:
                    print(f"\n✅ {total_inserted} NOUVELLES propositions sauvegardées dans Supabase.")
                else:
                    print("\n⚠️ Aucune nouvelle proposition n'a été sauvegardée avec succès.")
            
            # Ajouter des statistiques sur les performances
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            print(f"⏱️  Temps total d'extraction et d'insertion: {duration.total_seconds():.1f} secondes")
            props_per_sec = len(all_reponses_to_insert) / duration.total_seconds() if duration.total_seconds() > 0 else 0
            print(f"🚀 Performance: {props_per_sec:.1f} propositions traitées par seconde")
        else:
            print("ℹ️ Aucune proposition à sauvegarder")
        
        print("🏁 Phase 2 terminée.")
    
    def _extract_propositions_with_api(self, content: str, prompt_type: str = "standard", section_index: int = 0) -> List[Dict]:
        """Extrait les propositions d'un texte en utilisant l'API LLM."""
        
        # Vérifier si cette section contient du contenu remplacé
        has_replaced_content = "<!-- REPLACED_CONTENT:START -->" in content and "<!-- REPLACED_CONTENT:END -->" in content
        
        # Si c'est un contenu remplacé, indiquer cela dans le prompt
        instruction_remplace = ""
        if has_replaced_content:
            instruction_remplace = "\n\nATTENTION: Ce contenu contient des questions qui ont été remplacées manuellement (entre les balises REPLACED_CONTENT). Traite-les avec soin et vérifie de bien extraire les bonnes propositions pour ces questions."
        
        prompt = ""
        if prompt_type == "standard" or prompt_type == "optimized":
            # Prompt optimisé avec plus de contexte et d'exemples
            prompt = f"""Tu es un analyseur expert de QCM médicaux. Ton rôle est d'extraire les propositions de réponses pour chaque question d'un examen médical.{instruction_remplace}

INSTRUCTIONS ESSENTIELLES:
1. Pour CHAQUE question, identifie TOUTES les propositions de réponses (généralement marquées par A, B, C, D, E)
2. Assure-toi d'associer correctement les propositions à leur numéro de question
3. Extrais UNIQUEMENT le texte des propositions, pas les réponses correctes ni les explications

Pour chaque question, je veux:
- Le numéro de la question
- Les propositions sous forme de dictionnaire avec lettre => texte

===== EXEMPLE DE RÉSULTAT ATTENDU =====
[
  {{
    "numero_question": 1,
    "propositions": {{
      "A": "Texte proposition A",
      "B": "Texte proposition B",
      "C": "Texte proposition C",
      "D": "Texte proposition D",
      "E": "Texte proposition E"
    }}
  }},
  {{
    "numero_question": 2,
    "propositions": {{
      "A": "Texte proposition A pour Q2",
      ...et ainsi de suite...
    }}
  }}
]

===== CONTENU À ANALYSER =====
{content}
"""
        elif prompt_type == "simplified":
            # Prompt simplifié pour les cas difficiles
            prompt = f"""Extrais simplement les propositions de réponses (A, B, C, D, E) pour chaque question numérotée dans ce document.{instruction_remplace}

Format de résultat attendu:
[
  {{
    "numero_question": 1,
    "propositions": {{
      "A": "Texte A",
      "B": "Texte B",
      ...
    }}
  }},
  ...
]

Contenu:
{content}
"""
            
        # Tronquer si trop long
        max_tokens = 25000
        if len(prompt) > max_tokens:
            prompt = prompt[:max_tokens]
        
        try:
            # Utiliser un modèle adapté à la longueur et complexité
            model = "mistral-small-latest"
            if len(prompt) > 15000:
                model = "mistral-medium-latest"  # Plus robuste pour les contenus longs
                
            messages = [UserMessage(content=prompt)]
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model=model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # Vérifier si l'appel API a échoué
            if response is None:
                print(f"    ❌ Échec de l'appel API pour extraire les propositions (section {section_index})")
                return []
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                extracted_data_str = response.choices[0].message.content
                try:
                    print(f"    🔍 [DEBUG] Réponse API section {section_index}: {extracted_data_str[:500]}...")
                    
                    # Extraire les données JSON
                    extracted_data = json.loads(extracted_data_str)
                    
                    # Normaliser les données (gérer différents formats de réponse)
                    normalized_data = []
                    
                    if isinstance(extracted_data, list):
                        normalized_data = extracted_data
                    elif isinstance(extracted_data, dict):
                        if "questions" in extracted_data:
                            normalized_data = extracted_data["questions"]
                        elif "propositions" in extracted_data:
                            normalized_data = extracted_data["propositions"]
                        else:
                            # Essayer d'extraire une liste à partir des clés
                            for key, value in extracted_data.items():
                                if isinstance(value, dict) and "propositions" in value:
                                    try:
                                        q_num = int(key.replace("question_", "").replace("q", ""))
                                        normalized_data.append({
                                            "numero_question": q_num,
                                            "propositions": value["propositions"]
                                        })
                                    except ValueError:
                                        pass
                    
                    # Vérifier si le tableau est encore vide malgré tout
                    if not normalized_data and isinstance(extracted_data, dict):
                        # Dernier recours - reconstruction complète
                        for key in extracted_data:
                            if "question" in key.lower() and isinstance(extracted_data[key], dict):
                                try:
                                    q_num = int(key.replace("question_", "").replace("q", "").strip())
                                    props_dict = extracted_data[key]
                                    # Vérifier si l'objet props_dict est utilisable
                                    if any(k in "ABCDE" for k in props_dict.keys()):
                                        normalized_data.append({
                                            "numero_question": q_num,
                                            "propositions": props_dict
                                        })
                                except ValueError:
                                    pass
                    
                    # Filtrer les questions avec des propositions complètes (A-E)
                    valid_data = []
                    for item in normalized_data:
                        # S'assurer que item est un dict et contient les clés requises
                        if not isinstance(item, dict):
                            continue
                        
                        # Récupérer le numéro de question et les propositions
                        numero = item.get("numero_question") or item.get("numero") or item.get("question")
                        propositions = item.get("propositions", {})
                        
                        # Si le numéro n'est pas présent ou n'est pas un entier, sauter
                        if not numero:
                            continue
                        
                        # Convertir en entier si nécessaire
                        try:
                            if not isinstance(numero, int):
                                numero = int(str(numero).strip())
                        except ValueError:
                            continue
                        
                        # Si les propositions sont une liste, les convertir en dictionnaire
                        if isinstance(propositions, list):
                            prop_dict = {}
                            for i, prop in enumerate(propositions):
                                if isinstance(prop, dict) and "lettre" in prop and "texte" in prop:
                                    prop_dict[prop["lettre"]] = prop["texte"]
                                elif i < 5:  # Limiter à 5 propositions
                                    lettre = chr(65 + i)  # A, B, C, D, E
                                    prop_dict[lettre] = str(prop)
                            propositions = prop_dict
                        
                        # S'assurer que propositions est un dictionnaire
                        if not isinstance(propositions, dict):
                            continue
                        
                        # Ajouter à la liste valide
                        valid_data.append({
                            "numero_question": numero,
                            "propositions": propositions
                        })
                    
                    # Gérer les doublons en vérifiant les remplacements
                    if has_replaced_content:
                        # Extraire les numéros de questions qui sont dans la partie remplacée
                        replaced_matches = re.findall(r'## Q(\d+)\.', content)
                        replaced_question_nums = [int(m) for m in replaced_matches if m.isdigit()]
                        
                        if replaced_question_nums:
                            print(f"    ℹ️ Questions détectées dans le contenu remplacé: {replaced_question_nums}")
                            
                            # Dédupliquer en conservant les données du contenu remplacé en priorité
                            # Pour chaque numéro de question, on garde une seule entrée en privilégiant 
                            # celles qui sont dans la liste des questions remplacées
                            questions_by_number = {}
                            
                            # D'abord ajouter toutes les questions
                            for item in valid_data:
                                q_num = item["numero_question"]
                                questions_by_number[q_num] = item
                            
                            # Filtrer pour ne garder que les entrées uniques
                            valid_data = list(questions_by_number.values())
                    
                    return valid_data

                except json.JSONDecodeError as e:
                    print(f"    ⚠️ Erreur JSON dans l'extraction des propositions (section {section_index}): {str(e)}")
                    return []
                except Exception as e:
                    print(f"    ⚠️ Erreur dans le traitement des propositions (section {section_index}): {str(e)}")
                    return []
        except Exception as e:
            print(f"    ⚠️ Exception lors de l'appel API pour les propositions (section {section_index}): {str(e)}")
            return []
        
        return []
    
    def extract_correct_answers(self, markdown_text: str, qcm_id: int):
        """Identifie les réponses correctes à partir du contenu Markdown et met à jour la base de données."""
        print(f"🔍 Extraction des réponses correctes pour le QCM ID: {qcm_id}...")
        
        # Initialisation du compteur de mises à jour - IMPORTANT: Doit être initialisé ici
        updates_counter = 0
        
        # Récupérer les questions et leurs options depuis la base de données
        try:
            # D'abord, récupérer les questions pour ce QCM
            questions_result = self.supabase.table("questions").select("id", "uuid", "numero").eq("qcm_id", qcm_id).execute()
            
            if not questions_result.data:
                print(f"⚠️ Aucune question trouvée dans Supabase pour le QCM ID: {qcm_id}")
                return
                
            # Créer un mappage numéro de question -> ID de question
            question_map = {q["numero"]: q["id"] for q in questions_result.data if "numero" in q and "id" in q}
            
            if not question_map:
                print("⚠️ Aucune question n'a pu être mappée par numéro depuis Supabase.")
                return
                
            print(f"📌 {len(question_map)} questions mappées depuis Supabase.")
            
            # Créer un dictionnaire pour stocker toutes les lettres correctes par question
            corrections_data = {}
            questions_ambigues = set()  # Pour suivre les questions qui nécessitent une vérification
            
            # ÉTAPE 1: Méthode PRINCIPALE: Recherche "Réponses justes : X, Y, Z"
            # Stratégie modifiée: trouver "Réponses justes" PUIS remonter pour trouver le QXX précédent.
            print("🔍 Recherche directe des réponses justes explicites (stratégie améliorée)...")
            
            # Motifs pour trouver la ligne "Réponses justes : LETTRES"
            answer_line_patterns = [
                r'^[#\s]*[Rr](?:é|e)ponses?\s+(?:justes?|correctes?|exactes?)\s*:?\s*([A-E][,\sA-E]*[A-E])\.?',
                r'^[#\s]*[Bb]onne(?:s)?\s+[Rr](?:é|e)ponses?\s*:?\s*([A-E][,\sA-E]*[A-E])\.?',
                r'^[#\s]*[Rr]éponse\s+juste\s*:?\s*([A-E])\.?' # Pour le cas singulier "Réponse juste : A"
            ]
            
            # Motif pour trouver le numéro de la question QXX avant la ligne de réponse
            # Cherche Q<num>, <num>., <num>), ## Q<num> etc.
            question_number_pattern = r'(?:^|\n)[#\s]*Q(?:uestion)?\s*(\d+)[\s\.:\)]|\n(\d+)[\s\.:\)]'

            # Parcourir le texte ligne par ligne ou par blocs pour trouver les correspondances
            # Ici, on va chercher toutes les lignes de réponses d'abord
            found_answer_lines_with_positions = []
            for p_idx, ans_pattern in enumerate(answer_line_patterns):
                for match_ans_line in re.finditer(ans_pattern, markdown_text, re.MULTILINE):
                    found_answer_lines_with_positions.append({
                        "match_obj": match_ans_line,
                        "letters_group_index": 1, # Toutes les regex capturent les lettres dans le groupe 1
                        "pattern_index": p_idx # Pour le débogage
                    })
            
            # Trier les lignes de réponse trouvées par leur position pour traiter dans l'ordre d'apparition
            found_answer_lines_with_positions.sort(key=lambda x: x["match_obj"].start())

            last_q_num_found_overall = None # Garder une trace du dernier Qnum global

            for item in found_answer_lines_with_positions:
                match_ans_line = item["match_obj"]
                answer_text_start_pos = match_ans_line.start()
                letters_str = match_ans_line.group(item["letters_group_index"])
                
                # Chercher en arrière pour le numéro de question le plus proche
                # La zone de recherche arrière sera limitée (par exemple, les 1000 caractères précédents)
                search_before_text = markdown_text[max(0, answer_text_start_pos - 1000):answer_text_start_pos]
                
                # Trouver TOUS les numéros de question dans cette zone arrière
                question_num_matches_before = list(re.finditer(question_number_pattern, search_before_text, re.MULTILINE))
                
                current_q_num = None
                if question_num_matches_before:
                    # Prendre le DERNIER match (le plus proche de la ligne de réponse)
                    last_q_match_before = question_num_matches_before[-1]
                    # Extraire le numéro du bon groupe (celui qui n'est pas None)
                    num_group1 = last_q_match_before.group(1)
                    num_group2 = last_q_match_before.group(2)
                    if num_group1:
                        current_q_num = int(num_group1)
                    elif num_group2:
                        current_q_num = int(num_group2)
                
                if current_q_num is None and last_q_num_found_overall is not None:
                    # Heuristique: si on ne trouve pas de Q avant mais qu'on en a un global, on peut l'utiliser
                    # Cela peut être risqué si le format est très variable
                    # print(f"    ⚠️  Pour la ligne de réponse 'R: {letters_str}', aucun Qnum trouvé avant. Utilisation du dernier global: {last_q_num_found_overall}")
                    # current_q_num = last_q_num_found_overall # Décider si on active cette heuristique
                    pass # Pour l'instant, on n'active pas cette heuristique par défaut pour éviter les faux positifs

                if current_q_num is not None:
                    last_q_num_found_overall = current_q_num # Mettre à jour le dernier Qnum global
                    letters = re.findall(r'[A-E]', letters_str)
                    if letters:
                        unique_letters = sorted(list(set(letters)))
                        if 1 <= len(unique_letters) <= 5:
                            if current_q_num not in corrections_data:
                                corrections_data[current_q_num] = unique_letters
                                print(f"✅ Trouvé (Réponses Justes Explicites): Q {current_q_num}, réponses: {', '.join(unique_letters)}")
                            # else: # Si on veut logguer les écrasements ou les doublons par cette méthode
                                # print(f"    ℹ️ (Réponses Justes Explicites) pour Q {current_q_num} déjà trouvé: {corrections_data[current_q_num]}. Nouveau: {unique_letters}. Pattern index: {item['pattern_index']}")
                        else:
                            if current_q_num not in questions_ambigues and current_q_num not in corrections_data:
                                questions_ambigues.add(current_q_num)
                                print(f"⚠️ Réponse ambiguë (Réponses Justes Explicites) pour Q {current_q_num}: {', '.join(unique_letters)}. Texte: '{letters_str}'")
                # else:
                    # print(f"    ⚠️ Ligne de réponse '{match_ans_line.group(0).strip()}' trouvée mais aucun numéro de question associé trouvé avant.")

            # ÉTAPE 2: Analyse directe du texte pour les formats "A. Vrai" / "A. Faux"
            # S'applique seulement si la question n'a pas encore de réponse
            print("🔍 Recherche (Vrai/Faux)...")
            vrai_faux_pattern = r'(?:Question\\s+)?(\\d+)[\\.:\\)]\\s*(?:[^\\n]+\\n+)?([A-E])\\.?\\s+([Vv]rai|[Ff]aux|[Jj]uste|[Cc]orrect|[Ee]xact)'
            all_vrai_faux_matches = list(re.finditer(vrai_faux_pattern, markdown_text))
            
            if all_vrai_faux_matches:
                vrai_faux_by_question = {}
                for match in all_vrai_faux_matches:
                    try:
                        question_num = int(match.group(1))
                        if question_num not in corrections_data: # Ne traiter que si pas déjà résolu
                            lettre = match.group(2).upper()
                            vf_status = match.group(3).lower()
                            if question_num not in vrai_faux_by_question:
                                vrai_faux_by_question[question_num] = []
                            if vf_status in ['vrai', 'juste', 'correct', 'exact']:
                                vrai_faux_by_question[question_num].append(lettre)
                    except (ValueError, IndexError):
                        continue
                
                for question_num, lettres_vf in vrai_faux_by_question.items():
                    if lettres_vf and question_num not in corrections_data: # Double vérification
                        corrections_data[question_num] = sorted(list(set(lettres_vf)))
                        print(f"✅ Trouvé (Vrai/Faux): Q {question_num}, réponses: {', '.join(corrections_data[question_num])}")
            
            # ÉTAPE 3: Extraction directe des réponses avec pattern plus inclusif "1:A,B"
            # S'applique seulement si la question n'a pas encore de réponse
            print("🔍 Recherche (Format X:A,B)...")
            multi_answer_pattern = r'(?:Question\\s+)?(\\d+)\\s*[\\.:\\)]\\s*([A-E][,\\s]*(?:[A-E][,\\s]*)*)'
            multi_answers_matches = list(re.finditer(multi_answer_pattern, markdown_text))
            
            for match in multi_answers_matches:
                try:
                    question_num = int(match.group(1))
                    if question_num not in corrections_data: # Ne traiter que si pas déjà résolu
                        answers_str = match.group(2)
                        letters_multi = re.findall(r'[A-E]', answers_str)
                        if letters_multi:
                            unique_letters_multi = sorted(list(set(letters_multi)))
                            corrections_data[question_num] = unique_letters_multi
                            print(f"✅ Trouvé (Format X:A,B): Q {question_num}, réponses: {', '.join(unique_letters_multi)}")
                except (ValueError, IndexError):
                    continue

            # ÉTAPE 4: Déduction à partir des formulations 'A. Faux.'
            # S'applique seulement si la question n'a pas encore de réponse
            print("🔍 Recherche (Déduction par Faux)...")
            # CORRECTION: Échapper correctement la parenthèse fermante
            question_pattern_deduction = r'(?:Question|Q\\.?)?\\s*(\\d+)(?:\\s*:|\\.|\\\))' # Correction ici: \\\) 
            proposition_pattern_deduction = r'([A-E])\\.?\\s+([Ff]aux)' # Cherche explicitement "Faux"
            
            faux_propositions_by_question = {}
            current_question_deduction = None

            for line in markdown_text.split('\\n'):
                q_match = re.search(question_pattern_deduction, line)
                if q_match:
                    try:
                        current_question_deduction = int(q_match.group(1))
                        if current_question_deduction not in faux_propositions_by_question and current_question_deduction not in corrections_data:
                            faux_propositions_by_question[current_question_deduction] = []
                    except (ValueError, IndexError):
                        pass
                
                if current_question_deduction is not None and current_question_deduction not in corrections_data:
                    # S'assurer que la clé existe avant d'y accéder
                    if current_question_deduction in faux_propositions_by_question:
                        prop_matches = re.finditer(proposition_pattern_deduction, line)
                        for prop_match in prop_matches:
                            lettre = prop_match.group(1).upper()
                            faux_propositions_by_question[current_question_deduction].append(lettre)
            
            for question_num, faux_lettres in faux_propositions_by_question.items():
                if question_num not in corrections_data: # Vérifier à nouveau
                    if 0 < len(faux_lettres) < 5: # Doit y avoir des faux, mais pas tous faux
                        all_prop_letters = ['A', 'B', 'C', 'D', 'E']
                        correct_letters_deduced = sorted([l for l in all_prop_letters if l not in faux_lettres])
                        if correct_letters_deduced:
                            corrections_data[question_num] = correct_letters_deduced
                            print(f"✅ Trouvé (Déduction): Q {question_num}, réponses: {', '.join(correct_letters_deduced)}")
            
            # ÉTAPE 5: Interrogation de l'API Chat Mistral pour les questions restantes
            questions_needing_api_chat = sorted([
                q_num for q_num in question_map.keys() if q_num not in corrections_data
            ])

            if questions_needing_api_chat:
                print(f"\\n🤖 Tentative API Chat pour {len(questions_needing_api_chat)} questions restantes: {questions_needing_api_chat}")
                for question_num in questions_needing_api_chat:
                    # ... (récupération question_text et propositions_for_api comme avant)
                    # Assurez-vous que cette partie est correcte pour récupérer les détails de la question
                    question_id_db_api = question_map.get(question_num)
                    if not question_id_db_api: continue
                    q_details_result_api = self.supabase.table("questions").select("contenu, uuid").eq("id", question_id_db_api).single().execute()
                    if not q_details_result_api.data or not q_details_result_api.data.get("contenu"): continue
                    question_text_from_db_api = q_details_result_api.data["contenu"].get("text", "") if isinstance(q_details_result_api.data["contenu"], dict) else str(q_details_result_api.data["contenu"])
                    question_uuid_api = q_details_result_api.data.get("uuid")
                    if not question_uuid_api: continue
                    props_result_api = self.supabase.table("reponses").select("lettre, contenu").eq("question_id", question_uuid_api).order("lettre", desc=False).execute()
                    if not props_result_api.data: continue
                    propositions_for_api = [{"lettre": p["lettre"], "texte": (p["contenu"].get("text", "N/A") if isinstance(p["contenu"], dict) else str(p["contenu"]))} for p in props_result_api.data]
                    if not question_text_from_db_api or not propositions_for_api: continue
                    
                    api_chat_letters = self._get_correct_answers_with_chat_api(question_num, question_text_from_db_api, propositions_for_api)
                    
                    if api_chat_letters and question_num not in corrections_data: # Vérifier à nouveau avant d'écrire
                        corrections_data[question_num] = api_chat_letters
                        if question_num in questions_ambigues: questions_ambigues.remove(question_num)
                        print(f"  ✅ API Chat: Q {question_num}, réponses: {', '.join(api_chat_letters)}")
                    elif api_chat_letters:
                        print(f"  ℹ️ API Chat pour Q {question_num} a trouvé {api_chat_letters}, mais réponse existait déjà: {corrections_data[question_num]}")
                    else:
                        print(f"  ℹ️ API Chat: Aucune réponse trouvée pour Q {question_num}.")
                    time.sleep(0.5) 
            
            # ÉTAPE 6: API Vision pour les questions toujours manquantes OU ambiguës
            questions_for_vision_check = sorted(list(
                (set(question_map.keys()) - set(corrections_data.keys())).union(questions_ambigues.intersection(set(question_map.keys())))
            ))

            if questions_for_vision_check:
                print(f"\\n🖼️ Vérification API Vision pour {len(questions_for_vision_check)} questions: {questions_for_vision_check}...")
                # ... (logique pour pdf_stem et images_dir_path comme avant) ...
                pdf_stem_match_vision = None
                if isinstance(markdown_text, str):
                     match_path_vision = re.search(r'qcm_extraction/temp/outputs/([^/]+)/content\\.md', markdown_text)
                     if match_path_vision: pdf_stem_match_vision = match_path_vision.group(1)

                current_pdf_stem_vision = getattr(self, '_current_pdf_stem', None) # Si vous l'avez stocké
                
                pdf_stem_for_vision = current_pdf_stem_vision or pdf_stem_match_vision
                
                if not pdf_stem_for_vision:
                    qcm_info_vision = self.supabase.table("qcm").select("uuid").eq("id", qcm_id).single().execute()
                    if qcm_info_vision.data and qcm_info_vision.data.get("uuid"):
                         # Fallback très spéculatif: pdf_stem_for_vision = str(qcm_info_vision.data["uuid"])
                         # Il est préférable de s'assurer que pdf_stem est disponible plus tôt.
                         print("⚠️ pdf_stem non déterminé de manière fiable pour Vision, tentative avec UUID du QCM comme nom de dossier (spéculatif)...")
                         # Pour l'instant, on va juste afficher un avertissement si non trouvé.
                         pass


                if pdf_stem_for_vision:
                    images_dir_path_vision = self.images_dir / pdf_stem_for_vision
                    if not images_dir_path_vision.exists():
                        print(f"⚠️ Dossier d'images {images_dir_path_vision} non trouvé pour API Vision.")
                    else:
                        for question_num_vision in questions_for_vision_check:
                            # Si une réponse a été trouvée par l'API Chat entre-temps pour une question ambiguë
                            if question_num_vision in corrections_data and question_num_vision not in questions_ambigues:
                                continue

                            print(f"  🖼️ Vérification Vision pour Q {question_num_vision}...")
                            estimated_page_vision = (question_num_vision // 5) + 1 
                            
                            found_by_vision = False
                            for page_offset_vision in range(-1, 2): 
                                page_to_check = max(1, estimated_page_vision + page_offset_vision)
                                image_path_vision_file = images_dir_path_vision / f"page_{page_to_check}.jpg"

                                if image_path_vision_file.exists():
                                    response_vision = self._verify_correct_answers_with_vision(str(image_path_vision_file), question_num_vision)
                                    if response_vision and response_vision.get("correct_answers"):
                                        fetched_letters_vision = response_vision.get("correct_answers", [])
                                        if fetched_letters_vision:
                                            # Appliquer si la question n'a pas de réponse OU si elle était ambiguë et Vision la confirme/clarifie
                                            if question_num_vision not in corrections_data or question_num_vision in questions_ambigues:
                                                print(f"    ✅ Vision API: Q {question_num_vision}, réponses: {', '.join(fetched_letters_vision)}. Précédent: {corrections_data.get(question_num_vision)}")
                                                corrections_data[question_num_vision] = fetched_letters_vision
                                                if question_num_vision in questions_ambigues: questions_ambigues.remove(question_num_vision)
                                                found_by_vision = True
                                                break 
                                            # else: # Déjà résolue par une méthode plus prioritaire et non ambiguë
                                                # print(f"    ℹ️ Vision API pour Q {question_num_vision} a trouvé {fetched_letters_vision}, mais réponse fiable existait: {corrections_data[question_num_vision]}")
                                    time.sleep(0.5) 
                            if not found_by_vision:
                                 print(f"    ℹ️ Vision API n'a pas trouvé/confirmé de réponse pour Q{question_num_vision}")
                else:
                    print("⚠️ pdf_stem non trouvé pour l'API Vision. Vérification Vision sautée.")

            # Mise à jour finale en base de données
            final_resolved_questions = set(corrections_data.keys())
            print(f"\\n🔄 Mise à jour de la base de données avec {len(final_resolved_questions)} ensembles de réponses correctes trouvées...")
            updated_propositions_count = 0
            
            for question_num, correct_letters in corrections_data.items():
                if question_num not in question_map:
                    print(f"⚠️ Tentative de mise à jour pour question_num {question_num} non trouvé dans question_map.")
                    continue

                # question_map[question_num] CONTIENT DÉJÀ L'UUID PK de la table 'questions'
                question_pk_uuid_for_reponses = question_map[question_num]
                
                # L'ancienne logique récupérait la colonne 'uuid' (non-PK) ce qui était incorrect ici.
                # question_details_result = self.supabase.table("questions").select("uuid").eq("id", question_pk_uuid_for_reponses).single().execute()
                # if not question_details_result.data or "uuid" not in question_details_result.data:
                #     print(f"⚠️ Impossible de récupérer l'UUID (colonne uuid) pour la question PK UUID {question_pk_uuid_for_reponses} (Numéro {question_num}).")
                #     continue
                # question_secondary_uuid = question_details_result.data["uuid"] # Ceci était l'UUID de la colonne 'uuid', pas la PK

                # Récupérer les propositions pour cette question_id (qui est la PK UUID de la question)
                propositions_result = self.supabase.table("reponses").select("id, lettre").eq("question_id", question_pk_uuid_for_reponses).execute()
                
                if propositions_result.data:
                    for prop in propositions_result.data:
                        is_correct = prop["lettre"] in correct_letters
                        try:
                            update_response = self.supabase.table("reponses").update({"est_correcte": is_correct}).eq("id", prop["id"]).execute()
                            updates_counter += 1 # Compter chaque tentative de mise à jour
                            # Vérifier si des lignes ont été affectées (Supabase peut ne pas retourner cela directement dans .data pour update)
                            # La vérification de l'erreur se fait via l'exception potentielle.
                            # print(f"   Mise à jour Proposition ID {prop['id']} ({prop['lettre']}) pour Question {question_num}: est_correcte = {is_correct}")
                        except Exception as e:
                            print(f"❌ Erreur lors de la mise à jour de la proposition ID {prop['id']} pour Question {question_num}: {e}")
                else:
                    print(f"⚠️ Aucune proposition trouvée pour la question UUID {question_uuid} (Numéro {question_num}) lors de la mise à jour.")

            print(f"✨ {updates_counter} propositions mises à jour dans la base de données.")
            # CORRECTION: Utiliser final_resolved_questions au lieu de questions_with_answers (qui n'existe plus)
            print(f"✅ Processus d'extraction des réponses correctes terminé. {len(final_resolved_questions)} questions traitées.")
            
            # Afficher les questions qui n'ont toujours pas de réponses après toutes les étapes
            # CORRECTION: Utiliser corrections_data.keys() (ou final_resolved_questions) au lieu de questions_with_answers
            final_missing_questions = set(question_map.keys()) - final_resolved_questions 
            if final_missing_questions:
                print(f"⚠️ Attention: {len(final_missing_questions)} questions n'ont toujours pas de réponses correctes identifiées: {sorted(list(final_missing_questions))}")
            else:
                print("🎉 Toutes les questions ont des réponses correctes identifiées!")

        except Exception as e:
            print(f"❌ Erreur majeure dans extract_correct_answers: {str(e)}")
            import traceback
            traceback.print_exc() # Imprime la trace complète de l'erreur

    def _get_correct_answers_with_chat_api(self, question_num: int, question_text: str, propositions: List[Dict[str, str]]) -> List[str]:
        """
        Utilise l'API de chat Mistral pour déterminer les réponses correctes d'une question.

        Args:
            question_num (int): Le numéro de la question.
            question_text (str): Le texte de la question.
            propositions (List[Dict[str, str]]): Liste des propositions, ex: [{"lettre": "A", "texte": "..."}]

        Returns:
            List[str]: Une liste des lettres des réponses jugées correctes par l'API.
        """
        if not question_text or not propositions:
            return []

        print(f"🤖 Appel API Chat pour Q{question_num}: Détermination des réponses correctes...")

        # Construction du prompt plus robuste
        prompt_lines = []
        prompt_lines.append(f"Question {question_num}: {question_text}")
        prompt_lines.append("") # Ligne vide
        for prop in propositions:
            prompt_lines.append(f"{prop['lettre']}. {prop.get('texte', 'N/A')}")
        prompt_lines.append("") # Ligne vide
        prompt_lines.append("Quelles sont la ou les lettres des réponses correctes (A, B, C, D, E) à cette question ? Répondez uniquement avec les lettres correctes, séparées par des virgules si plusieurs. Par exemple: A ou A,C ou B,D,E.")
        
        prompt_content = "\n".join(prompt_lines)
        messages = [UserMessage(content=prompt_content)]

        try:
            response = self._call_api_with_retry(
                self.client.chat.create,
                model="mistral-small-latest",
                messages=messages,
                temperature=0.0,
                max_tokens=20
            )

            if response and response.choices:
                content = response.choices[0].message.content.strip().upper()
                correct_letters = re.findall(r'[A-E]', content)
                
                if correct_letters:
                    print(f"🤖 API Chat pour Q{question_num}: Réponses suggérées: {', '.join(correct_letters)}")
                    return sorted(list(set(correct_letters)))
                else:
                    print(f"⚠️ API Chat pour Q{question_num}: Aucune lettre correcte identifiée dans la réponse: '{content}'")
            else:
                print(f"⚠️ API Chat pour Q{question_num}: Réponse invalide ou vide de l'API.")

        except Exception as e:
            print(f"❌ Erreur lors de l'appel API Chat pour Q{question_num}: {e}")

        return []

    def _verify_correct_answers_with_vision(self, image_path: str, question_num: int) -> dict:
        """
        Utilise l'API vision pour vérifier les réponses correctes à une question spécifique.
        
        Args:
            image_path (str): Chemin vers l'image de la page à analyser
            question_num (int): Numéro de la question à vérifier
            
        Returns:
            dict: Dictionnaire contenant les informations extraites
        """
        try:
            print(f"    🔍 Analyse de l'image {image_path} pour la question {question_num}...")
            
            # Encoder l'image en base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            
            # Construire les messages pour l'API vision
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": f"""Analyse cette image d'un QCM médical et identifie les RÉPONSES CORRECTES pour la Question {question_num} uniquement.

CONSIGNES PRÉCISES:
1. Cherche UNIQUEMENT la Question {question_num} et ses réponses correctes
2. Cherche des indications comme "Réponses justes", "Réponses correctes", "Bonnes réponses", etc.
3. Tu peux aussi repérer les réponses marquées individuellement comme "Vrai" ou "Faux" 
4. Si plusieurs réponses sont correctes, liste-les toutes (A, B, C, D, E)

RÉPONDS UNIQUEMENT AU FORMAT JSON:
{{
  "question_num": {question_num},
  "correct_answers": ["A", "C", "E"],  // Liste des lettres correctes uniquement (A, B, C, D, E)
  "confidence": 0.95,  // Ta confiance dans ta réponse de 0 à 1
  "explanation": "J'ai trouvé ces réponses car..."  // Brève explication
}}

N'ajoute AUCUN texte avant ou après ce JSON."""
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]
            
            # Appeler l'API vision
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-large-latest",  # Utiliser le modèle large qui a de meilleures capacités de vision
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            if response is None:
                print(f"    ❌ Échec de l'appel API vision pour la question {question_num}")
                return None
            
            try:
                # Extraire le JSON de la réponse
                content = response.choices[0].message.content.strip()
                result = json.loads(content)
                
                # Vérifier que la structure du résultat est correcte
                if "question_num" in result and "correct_answers" in result:
                    verified_num = result["question_num"]
                    
                    # Vérifier que la réponse concerne bien la question demandée
                    if verified_num == question_num:
                        correct_answers = result["correct_answers"]
                        confidence = result.get("confidence", 0)
                        explanation = result.get("explanation", "")
                        
                        print(f"    ✅ Réponses identifiées par vision pour Q{question_num}: {', '.join(correct_answers)} (confiance: {confidence:.2f})")
                        print(f"    ℹ️ Explication: {explanation}")
                        
                        return result
                    else:
                        print(f"    ⚠️ La réponse concerne la question {verified_num}, mais nous cherchions la question {question_num}")
                else:
                    print(f"    ⚠️ Réponse API mal formatée pour la question {question_num}")
                    
            except json.JSONDecodeError:
                print(f"    ⚠️ Impossible de décoder la réponse JSON pour la question {question_num}")
                
            return None
                
        except Exception as e:
            print(f"    ❌ Erreur lors de la vérification des réponses avec vision: {str(e)}")
            return None

    def _extract_questions_api(self, content: str, section_index: int = 0) -> List[Dict]:
        """Extrait les questions d'un texte en utilisant l'API LLM."""
        
        # Vérifier si cette section contient du contenu remplacé
        has_replaced_content = "<!-- REPLACED_CONTENT:START -->" in content and "<!-- REPLACED_CONTENT:END -->" in content
        
        # Si c'est un contenu remplacé, indiquer cela dans le prompt
        instruction_remplace = ""
        if has_replaced_content:
            instruction_remplace = "\n\nATTENTION: Ce contenu contient des questions qui ont été remplacées manuellement (entre les balises REPLACED_CONTENT). Traite-les avec soin et assure-toi de bien extraire toutes les questions remplacées."
        
        # Extraire les numéros de questions potentielles via regex
        potential_questions = re.findall(r'(?:Q(?:uestion)?\s*(\d+)|^(\d+)\s*[\.\)])', content, re.MULTILINE)
        flattened_matches = [num for match in potential_questions for num in match if num]
        
        # Créer un prompt ciblé et adapté au contenu
        prompt = f"""Tu es un expert en analyse de QCM médicaux. Ta mission est d'extraire uniquement les questions (sans les propositions) d'un document de QCM.{instruction_remplace}

INSTRUCTIONS ESSENTIELLES:
1. Pour chaque question, je veux son numéro et son texte complet
2. N'inclus PAS les propositions (A,B,C,D,E) dans le texte de la question
3. Ignore les explications et les corrections
4. Assure-toi d'extraire TOUTES les questions, même celles qui pourraient être mal formatées

J'ai détecté ces numéros potentiels de questions dans le texte: {', '.join(flattened_matches) if flattened_matches else "aucun numéro détecté automatiquement"}

===== EXEMPLE DE RÉSULTAT ATTENDU =====
[
  {{
    "numero_question": 1,
    "texte_question": "Le texte complet de la question 1"
  }},
  {{
    "numero_question": 2,
    "texte_question": "Le texte complet de la question 2"
  }}
]

===== CONTENU À ANALYSER =====
{content}
"""
        
        # Tronquer si trop long
        max_tokens = 20000
        if len(prompt) > max_tokens:
            prompt = prompt[:max_tokens]
        
        try:
            # Utiliser un modèle adapté à la longueur et complexité
            model = "mistral-small-latest"
            if len(prompt) > 15000:
                model = "mistral-medium-latest"  # Plus robuste pour les contenus longs
                
            messages = [UserMessage(content=prompt)]
            response = self._call_api_with_retry(
                self.client.chat.complete,
                model=model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            # Vérifier si l'appel API a échoué
            if response is None:
                print(f"    ❌ Échec de l'appel API pour extraire les questions (section {section_index})")
                return []
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                extracted_data_str = response.choices[0].message.content
                try:
                    # Extraire les données JSON
                    extracted_data = json.loads(extracted_data_str)
                    
                    # Normaliser les données (gérer différents formats de réponse)
                    normalized_data = []
                    
                    if isinstance(extracted_data, list):
                        normalized_data = extracted_data
                    elif isinstance(extracted_data, dict):
                        if "questions" in extracted_data:
                            normalized_data = extracted_data["questions"]
                        elif "resultats" in extracted_data:
                            normalized_data = extracted_data["resultats"]
                        
                    # Filtrer et normaliser les résultats
                    valid_questions = []
                    for item in normalized_data:
                        if not isinstance(item, dict):
                            continue
                            
                        numero = item.get("numero_question") or item.get("numero") or item.get("question")
                        texte = item.get("texte_question") or item.get("texte") or item.get("contenu")
                        
                        if not numero or not texte:
                            continue
                            
                        try:
                            if not isinstance(numero, int):
                                numero = int(str(numero).strip())
                                
                            valid_questions.append({
                                "numero_question": numero,
                                "texte_question": str(texte).strip()
                            })
                        except (ValueError, TypeError):
                            continue
                    
                    return valid_questions
                    
                except json.JSONDecodeError as e:
                    print(f"    ⚠️ Erreur JSON dans l'extraction des questions (section {section_index}): {str(e)}")
                    return []
                except Exception as e:
                    print(f"    ⚠️ Erreur dans le traitement des questions (section {section_index}): {str(e)}")
                    return []
        except Exception as e:
            print(f"    ⚠️ Exception lors de l'appel API pour les questions (section {section_index}): {str(e)}")
            return []
        
        return []

    def _save_propositions(self, qcm_id: int, propositions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sauvegarde les propositions dans Supabase."""
        # Récupérer les IDs des questions depuis Supabase
        print(f"🔍 Récupération des IDs des questions depuis Supabase pour le QCM ID: {qcm_id}...")
        questions_data = self.supabase.table('questions').select('id,numero').eq('qcm_id', qcm_id).execute()
        questions_by_numero = {q['numero']: q['id'] for q in questions_data.data}
        
        print(f"📌 {len(questions_by_numero)} questions mappées par numéro depuis Supabase.")
        
        # Nettoyer les propositions existantes pour éviter les doublons
        self._clean_existing_propositions(qcm_id)
        
        # Créer la liste des propositions à sauvegarder
        propositions_to_save = []
        
        all_questions_have_propositions = True
        
        for prop_set in propositions_data:
            numero_question = prop_set.get('numero_question')
            propositions = prop_set.get('propositions', {})
            
            # Vérifier si la question existe
            if numero_question not in questions_by_numero:
                print(f"⚠️ Question {numero_question} non trouvée dans Supabase, ses propositions ne seront pas sauvegardées.")
                continue
            
            question_id = questions_by_numero[numero_question]
            
            # Vérifier que les propositions sont au bon format
            if not isinstance(propositions, dict) or not propositions:
                print(f"⚠️ Format de proposition invalide pour la question {numero_question}, ignorée.")
                all_questions_have_propositions = False
                continue
            
            # Ajouter chaque proposition à la liste
            for lettre, contenu in propositions.items():
                # Ne pas ajouter si la lettre n'est pas valide
                if lettre not in ['A', 'B', 'C', 'D', 'E']:
                    print(f"⚠️ Lettre invalide '{lettre}' pour la question {numero_question}, ignorée.")
                    continue
                
                propositions_to_save.append({
                    'question_id': question_id,
                    'lettre': lettre,
                    'contenu': contenu,
                    'est_correcte': False  # Par défaut, sera mis à jour plus tard
                })
        
        # Sauvegarder les propositions en batch
        total_propositions = len(propositions_to_save)
        if total_propositions > 0:
            print(f"💾 Sauvegarde de {total_propositions} propositions dans Supabase...")
            
            # Sauvegarder par batches de 100 propositions max
            batch_size = 100
            for i in range(0, total_propositions, batch_size):
                batch = propositions_to_save[i:i+batch_size]
                progress = i / total_propositions * 100
                print(f"⌛ [{self._progress_bar(progress)}] {progress:.0f}% - Insertion des propositions")
                result = self.supabase.table('reponses').insert(batch).execute()
            
            print(f"✅ {total_propositions} propositions sauvegardées dans Supabase")
        else:
            print("⚠️ Aucune proposition à sauvegarder.")
            all_questions_have_propositions = False
        
        return propositions_to_save, all_questions_have_propositions
    
    def _clean_existing_propositions(self, qcm_id: int) -> None:
        """Nettoie les propositions existantes pour les questions d'un QCM donné."""
        print(f"🧹 Nettoyage des propositions existantes pour le QCM ID: {qcm_id}...")
        
        # Récupérer toutes les questions pour le QCM
        questions_data = self.supabase.table('questions').select('id').eq('qcm_id', qcm_id).execute()
        
        if not questions_data.data:
            print(f"⚠️ Aucune question trouvée pour le QCM ID: {qcm_id}, rien à nettoyer.")
            return
        
        question_ids = [q['id'] for q in questions_data.data]
        
        # Supprimer toutes les propositions pour ces questions
        props_to_delete = []
        for question_id in question_ids:
            # Récupérer les propositions pour cette question
            props = self.supabase.table('reponses').select('id').eq('question_id', question_id).execute()
            if props.data:
                props_to_delete.extend([p['id'] for p in props.data])
        
        if not props_to_delete:
            print(f"✅ Aucune proposition existante à supprimer.")
            return
        
        print(f"🗑️ Suppression de {len(props_to_delete)} propositions existantes...")
        
        # Supprimer par batches de 100 propositions max
        batch_size = 100
        total_props = len(props_to_delete)
        
        for i in range(0, total_props, batch_size):
            batch = props_to_delete[i:i+batch_size]
            progress = i / total_props * 100
            print(f"⌛ [{self._progress_bar(progress)}] {progress:.0f}% - Suppression des propositions existantes")
            
            # Supprimer chaque proposition individuellement
            for prop_id in batch:
                try:
                    self.supabase.table('reponses').delete().eq('id', prop_id).execute()
                except Exception as e:
                    print(f"⚠️ Erreur lors de la suppression de la proposition ID {prop_id}: {str(e)}")
                    continue
        
        print(f"✅ {total_props} propositions existantes supprimées.")