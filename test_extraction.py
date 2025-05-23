#!/usr/bin/env python3
from qcm_extraction.extractor import QCMExtractor
import time

def main():
    # URL du PDF à tester
    pdf_url = "https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE1/QCM/ue1-correction-colle-2-s42-2021-49647.pdf"
    
    # Initialiser l'extracteur avec les clés API définies dans les variables d'environnement
    extractor = QCMExtractor()
    
    print("=== Test d'extraction sur PDF ===")
    print(f"URL du PDF: {pdf_url}")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Extraire les métadonnées et les questions
    metadata = extractor.extract_metadata_from_path(pdf_url)
        
    # Afficher les résultats
    end_time = time.time()
    duration = end_time - start_time
    
    if metadata:
        print("\n=== Résultats d'extraction ===")
        print(f"Temps d'exécution: {duration:.2f} secondes")
        print(f"UE: {metadata.get('ue', 'Non détecté')}")
        print(f"Type: {metadata.get('type', 'Non détecté')}")
        print(f"Année: {metadata.get('annee', 'Non détectée')}")
        print(f"Nombre de questions extraites: {metadata.get('questions_count', 'Non disponible')}")
        print(f"Nombre de propositions extraites: {metadata.get('propositions_count', 'Non disponible')}")
            
        # Vérifier si on a des statistiques de complétude
        if 'extraction_completeness' in metadata:
            print(f"Complétude de l'extraction: {metadata['extraction_completeness']:.1f}%")
            else:
        print("❌ L'extraction a échoué")

if __name__ == "__main__":
    main() 