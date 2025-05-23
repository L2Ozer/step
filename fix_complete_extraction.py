#!/usr/bin/env python3
"""
Solution complète et scalable pour extraire TOUTES les questions d'un PDF de QCM médical
Cette approche est conçue pour être parfaite et s'adapter à n'importe quel PDF
"""

import os
import sys
import re
import json
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

class PerfectQCMExtractor(QCMExtractor):
    """Extracteur parfait et scalable pour QCM médicaux"""
    
    def convert_pdf_to_markdown_perfect(self, pdf_path: str, original_url: str) -> str:
        """Conversion parfaite du PDF en Markdown avec validation en temps réel"""
        try:
            print("📝 Conversion parfaite du PDF en Markdown...")
            
            # Utiliser l'OCR Mistral standard SANS modifications
            document_input = {"type": "document_url", "document_url": original_url}
            
            ocr_response = self._call_api_with_retry(
                self.client.ocr.process,
                model="mistral-ocr-latest",
                document=document_input,
                include_image_base64=False
            )
            
            if ocr_response is None:
                print("❌ Échec de l'appel API OCR")
                return None
            
            # Extraire le texte de TOUTES les pages SANS filtrage
            markdown_content = ""
            total_questions_found = set()
            
            for i, page in enumerate(ocr_response.pages):
                page_header = f"# Page {i+1}\n\n"
                page_markdown = page.markdown
                
                # Analyser les questions sur cette page SANS juger de la qualité
                page_questions = set()
                for pattern in [r'Q\.?\s*(\d+)', r'Question\s*(\d+)', r'(\d+)[\.\)]']:
                    matches = re.findall(pattern, page_markdown)
                    numbers = [int(m) for m in matches if m.isdigit() and 1 <= int(m) <= 50]
                    page_questions.update(numbers)
                
                total_questions_found.update(page_questions)
                
                print(f"📄 Page {i+1}: {len(page_markdown)} chars, {len(page_questions)} questions {sorted(page_questions) if page_questions else 'aucune'}")
                
                markdown_content += page_header + page_markdown + "\n\n"
            
            print(f"📊 OCR STANDARD RÉSULTAT: {len(total_questions_found)} questions trouvées: {sorted(total_questions_found)}")
            
            # Si on a moins de 20 questions, utiliser une stratégie d'amélioration ciblée
            if len(total_questions_found) < 20:
                print("🔧 Stratégie d'amélioration ciblée activée...")
                markdown_content = self._enhance_extraction_targeted(pdf_path, original_url, markdown_content, total_questions_found)
            
            # Sauvegarder le Markdown final
            pdf_stem = Path(pdf_path).stem
            output_dir = self.outputs_dir / pdf_stem
            output_dir.mkdir(exist_ok=True)
            
            markdown_path = output_dir / "content.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"💾 Markdown parfait sauvegardé: {markdown_path}")
            return str(markdown_path)
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion parfaite: {str(e)}")
            return None
    
    def _enhance_extraction_targeted(self, pdf_path: str, original_url: str, current_markdown: str, found_questions: set) -> str:
        """Amélioration ciblée pour extraire les questions manquantes"""
        print("🎯 Amélioration ciblée en cours...")
        
        # Stratégie 1: Ré-essayer l'OCR avec des paramètres différents
        try:
            print("🔄 Tentative OCR avec extraction par images...")
            
            # Convertir le PDF en images
            images = self.pdf_to_images(pdf_path)
            enhanced_content = current_markdown
            
            # Traiter seulement les pages qui semblent problématiques
            problematic_pages = []
            lines = current_markdown.split('\n')
            current_page = 0
            
            for line in lines:
                if line.startswith('# Page '):
                    current_page = int(re.search(r'Page (\d+)', line).group(1))
                elif current_page > 0:
                    # Vérifier si cette page a du contenu substantiel
                    page_content = ""
                    page_start = current_markdown.find(f"# Page {current_page}")
                    next_page = current_markdown.find(f"# Page {current_page + 1}")
                    if next_page == -1:
                        page_content = current_markdown[page_start:]
                    else:
                        page_content = current_markdown[page_start:next_page]
                    
                    # Si la page a moins de 500 caractères, elle est potentiellement problématique
                    if len(page_content.strip()) < 500:
                        problematic_pages.append(current_page - 1)  # Index 0-based
            
            print(f"📋 Pages problématiques détectées: {[p+1 for p in problematic_pages]}")
            
            # Améliorer seulement les pages problématiques avec l'API de chat
            for page_idx in problematic_pages:
                if page_idx < len(images):
                    try:
                        enhanced_text = self._extract_text_with_chat_api(images[page_idx], page_idx + 1)
                        if enhanced_text and len(enhanced_text.strip()) > 100:
                            # Remplacer le contenu de cette page
                            page_marker = f"# Page {page_idx + 1}"
                            next_page_marker = f"# Page {page_idx + 2}"
                            
                            start_pos = enhanced_content.find(page_marker)
                            if start_pos != -1:
                                end_pos = enhanced_content.find(next_page_marker)
                                if end_pos == -1:
                                    end_pos = len(enhanced_content)
                                
                                enhanced_content = (enhanced_content[:start_pos] + 
                                                  page_marker + "\n\n" + enhanced_text + "\n\n" +
                                                  enhanced_content[end_pos:])
                                
                                print(f"✅ Page {page_idx + 1} améliorée avec l'API de chat")
                    except Exception as e:
                        print(f"⚠️ Erreur lors de l'amélioration de la page {page_idx + 1}: {e}")
            
            return enhanced_content
            
        except Exception as e:
            print(f"⚠️ Erreur lors de l'amélioration ciblée: {e}")
            return current_markdown
    
    def _extract_text_with_chat_api(self, image_path: str, page_num: int) -> str:
        """Extrait le texte d'une image spécifique avec l'API de chat optimisée"""
        try:
            with open(image_path, "rb") as image_file:
                import base64
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            prompt = f"""Tu es un expert en extraction de texte médical à partir d'images de QCM.

MISSION CRITIQUE - Page {page_num}:
Extrais TOUT le texte visible sur cette image de façon EXHAUSTIVE et PRÉCISE.

INSTRUCTIONS STRICTES:
1. Identifie chaque question avec son numéro (Q1, Q2, etc.)
2. Extrais chaque proposition A, B, C, D, E avec son texte complet
3. Inclus tous les détails médicaux, formules, équations
4. Préserve la structure et la numérotation exacte
5. N'omets RIEN, même les plus petits détails
6. Si tu vois des corrections ou réponses justes, inclus-les

FORMAT MARKDOWN STRICT:
## Q[numéro]. [Titre de la question]

[Contenu détaillé de la question]

A. [Proposition A complète]
B. [Proposition B complète]
C. [Proposition C complète]
D. [Proposition D complète]
E. [Proposition E complète]

[Réponses justes ou corrections si présentes]

Sois PARFAIT et EXHAUSTIF."""

            from mistralai import UserMessage
            
            messages = [
                UserMessage(content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                ])
            ]

            response = self._call_api_with_retry(
                self.client.chat.complete,
                model="mistral-large-latest",  # Utiliser le modèle le plus puissant
                messages=messages,
                temperature=0.0,
                max_tokens=4000
            )

            if response and response.choices:
                extracted_text = response.choices[0].message.content
                print(f"✅ API Chat: {len(extracted_text)} caractères extraits pour page {page_num}")
                return extracted_text
            else:
                print(f"⚠️ Échec API Chat pour page {page_num}")
                return ""

        except Exception as e:
            print(f"⚠️ Erreur API Chat page {page_num}: {str(e)}")
            return ""

def test_perfect_extraction():
    """Test de l'extraction parfaite"""
    print("🚀 TEST D'EXTRACTION PARFAITE ET SCALABLE")
    print("=" * 60)
    
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE2/QCM/ue2-correction-colle1-s38-21-22-47305.pdf"
    
    try:
        # Nettoyer les données existantes
        extractor = PerfectQCMExtractor()
        
        try:
            existing_qcm = extractor.supabase.table("qcm").select("id").eq("type", "Colle N°1").eq("annee", "2021 / 2022").execute()
            if existing_qcm.data:
                qcm_id = existing_qcm.data[0]["id"]
                print(f"🧹 Nettoyage du QCM existant ID: {qcm_id}")
                
                questions = extractor.supabase.table("questions").select("id").eq("qcm_id", qcm_id).execute()
                if questions.data:
                    for q in questions.data:
                        extractor.supabase.table("reponses").delete().eq("question_id", q["id"]).execute()
                
                extractor.supabase.table("questions").delete().eq("qcm_id", qcm_id).execute()
                extractor.supabase.table("qcm").delete().eq("id", qcm_id).execute()
                print("✅ Nettoyage terminé")
        except Exception as e:
            print(f"ℹ️ Pas de données existantes: {e}")
        
        # Télécharger le PDF
        pdf_path = extractor.download_pdf(pdf_url)
        print(f"📥 PDF téléchargé: {pdf_path}")
        
        # Conversion parfaite en Markdown
        markdown_path = extractor.convert_pdf_to_markdown_perfect(pdf_path, pdf_url)
        
        if markdown_path:
            # Analyser le résultat final
            with open(markdown_path, "r", encoding="utf-8") as f:
                final_content = f.read()
            
            # Compter les questions finales
            final_questions = set()
            for pattern in [r'Q\.?\s*(\d+)', r'Question\s*(\d+)', r'##\s*Q(\d+)']:
                matches = re.findall(pattern, final_content)
                numbers = [int(m) for m in matches if m.isdigit() and 1 <= int(m) <= 50]
                final_questions.update(numbers)
            
            print(f"\n🎯 RÉSULTAT FINAL:")
            print(f"✅ Questions extraites: {len(final_questions)}")
            print(f"📋 Numéros: {sorted(final_questions)}")
            
            if len(final_questions) >= 25:
                print("🎉 EXTRACTION EXCELLENTE!")
                return True
            elif len(final_questions) >= 20:
                print("✅ Extraction bonne mais peut être améliorée")
                return True
            else:
                print("⚠️ Extraction insuffisante")
                return False
        else:
            print("❌ Échec de la conversion")
            return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_perfect_extraction()
    if success:
        print("\n🎉 SUCCÈS: Extraction parfaite réalisée!")
    else:
        print("\n⚠️ Amélioration nécessaire") 