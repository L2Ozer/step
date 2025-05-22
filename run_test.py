from dotenv import load_dotenv
import time
import os

# S'assurer que le chemin d'importation pour qcm_extraction est correct
# Si run_test.py est à la racine du projet, et qcm_extraction est un dossier à la racine
try:
    from qcm_extraction.extractor import QCMExtractor
except ImportError:
    # Alternative si le script est exécuté depuis un autre endroit ou si PYTHONPATH n'est pas configuré
    import sys
    # Ajouter le répertoire parent au chemin (si qcm_extraction est un module frère)
    # Ou ajuster selon la structure de votre projet
    sys.path.append(os.path.dirname(os.path.abspath(__file__))) # Ajoute le répertoire courant
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')) # Ajoute le répertoire parent

    from qcm_extraction.extractor import QCMExtractor


if __name__ == "__main__":
    load_dotenv() # Charger les variables d'environnement depuis .env

    # Récupérer les variables d'environnement
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not all([mistral_api_key, supabase_url, supabase_key]):
        print("Erreur: Les variables d'environnement MISTRAL_API_KEY, SUPABASE_URL, et SUPABASE_KEY doivent être définies.")
        print("Veuillez créer un fichier .env à la racine du projet avec ces variables ou les définir dans votre environnement.")
        exit(1)

    # Initialiser l'extracteur avec les clés chargées
    # Note: QCMExtractor peut aussi charger depuis os.getenv par défaut si les args sont None
    extractor = QCMExtractor(api_key=mistral_api_key, supabase_url=supabase_url, supabase_key=supabase_key)
    
    # URL du PDF à traiter
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE1/QCM/ue1-correction-colle-2-s42-2021-49647.pdf"
    
    print(f"🚀 Lancement du traitement complet pour: {pdf_url}")
    
    # Étape 1 & 2: Extraction des métadonnées, questions et propositions
    extracted_metadata = extractor.extract_metadata_from_path(pdf_url)
    
    if extracted_metadata and extracted_metadata.get("qcm_db_id") and extracted_metadata.get("markdown_path"):
        qcm_id = extracted_metadata["qcm_db_id"]
        markdown_path = extracted_metadata["markdown_path"]
        
        print(f"\n✅ Métadonnées, questions et propositions extraites pour QCM ID: {qcm_id}")
        print(f"📄 Fichier Markdown généré: {markdown_path}")
        
        # Lire le contenu Markdown pour l'étape suivante
        try:
            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
            
            # Étape 3: Extraction des réponses correctes
            print("\n▶️ Lancement de la Phase 3: Extraction des réponses correctes...")
            print("⏸️ Pause de 5 secondes avant l'extraction des réponses correctes...")
            time.sleep(5)
            
            extractor.extract_correct_answers(markdown_content, qcm_id)
            
            print("\n🎉 Traitement complet terminé.")
            
        except FileNotFoundError:
            print(f"❌ Erreur: Le fichier Markdown {markdown_path} n'a pas été trouvé pour l'extraction des réponses correctes.")
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction des réponses correctes: {str(e)}")
            import traceback
            traceback.print_exc()
            
    elif extracted_metadata:
        print("⚠️ Le traitement s'est arrêté après l'extraction des métadonnées car qcm_db_id ou markdown_path est manquant.")
        print(f"   Détails des métadonnées: {extracted_metadata}")
    else:
        print("❌ Échec de l'extraction des métadonnées. Le traitement ne peut pas continuer.") 