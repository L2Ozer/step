#!/usr/bin/env python3
"""
QCM Medical Extraction System - Commande Principale
Interface unifiée pour extraire n'importe quel PDF QCM
"""

import sys
import time
import argparse
from pathlib import Path

# Ajouter le chemin du module
sys.path.append(str(Path(__file__).parent / "qcm_extraction"))

from extractor import QCMExtractor

def print_banner():
    """Affiche la bannière du système"""
    print("🏥 QCM MEDICAL EXTRACTION SYSTEM")
    print("=" * 50)
    print("Système d'extraction automatisé et scalable")
    print("Support: UE1-UE7, tous formats QCM médicaux")
    print()

def extract_qcm(pdf_url, verbose=False):
    """
    Extrait un QCM depuis une URL PDF
    
    Args:
        pdf_url (str): URL du PDF à traiter
        verbose (bool): Affichage détaillé
        
    Returns:
        dict: Métadonnées d'extraction
    """
    
    if verbose:
        print(f"📄 PDF: {pdf_url.split('/')[-1]}")
        print(f"🔗 URL: {pdf_url}")
        print()

    # Initialisation
    print("🔧 Initialisation de l'extracteur...")
    try:
        extractor = QCMExtractor()
        if verbose:
            print("✅ Extracteur initialisé")
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        return None

    # Extraction complète (3 phases automatiques)
    print("🚀 Lancement de l'extraction complète...")
    if verbose:
        print("   Phase 1: Extraction des questions")
        print("   Phase 2: Extraction des propositions") 
        print("   Phase 3: Identification des réponses correctes")
        print()

    start_time = time.time()

    try:
        # Le système fait tout automatiquement
        metadata = extractor.extract_metadata_from_path(pdf_url)
        
        execution_time = time.time() - start_time
        
        # Affichage des résultats
        print("\n🎉 EXTRACTION TERMINÉE AVEC SUCCÈS!")
        print("=" * 40)
        
        # Métriques essentielles
        questions_count = metadata.get('questions_count', 0)
        propositions_count = metadata.get('propositions_count', 0)
        correct_answers = metadata.get('correct_answers_updated', 0)
        qcm_id = metadata.get('qcm_db_id', 'N/A')
        
        print(f"⏱️  Temps: {execution_time:.1f}s")
        print(f"📊 Questions: {questions_count}")
        print(f"📝 Propositions: {propositions_count}")
        print(f"✅ Réponses correctes: {correct_answers}")
        print(f"🆔 QCM ID: {qcm_id}")
        
        # Validation automatique
        if questions_count > 0:
            expected_props = questions_count * 5
            precision = (propositions_count / expected_props * 100) if expected_props > 0 else 0
            correct_rate = (correct_answers / propositions_count * 100) if propositions_count > 0 else 0
            
            print(f"🎯 Précision: {precision:.1f}%")
            print(f"📈 Taux de réponses: {correct_rate:.1f}%")
            
            # Validation qualité
            if propositions_count == expected_props:
                print("✅ PRÉCISION MATHÉMATIQUE PARFAITE")
            else:
                print(f"⚠️  Écart: {abs(propositions_count - expected_props)} propositions")
                
            if correct_answers > 0:
                print("✅ RÉPONSES CORRECTES IDENTIFIÉES")
            else:
                print("⚠️  Aucune réponse correcte trouvée")
        
        print("\n🎯 EXTRACTION RÉUSSIE - QCM PRÊT POUR UTILISATION")
        return metadata
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"\n❌ ERREUR après {execution_time:.1f}s: {e}")
        
        if verbose:
            import traceback
            traceback.print_exc()
        
        return None

def main():
    """Interface en ligne de commande"""
    parser = argparse.ArgumentParser(
        description="QCM Medical Extraction System - Extraction universelle de PDF QCM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  # Extraction simple
  python extract_qcm.py https://example.com/qcm.pdf
  
  # Extraction avec détails
  python extract_qcm.py https://example.com/qcm.pdf --verbose
  
  # Extraction UE3 Nancy
  python extract_qcm.py https://ityugjyhrtvlvhbyohyi.supabase.co/storage/v1/object/public/qcm_pdfs/Nancy/UE3/QCM/ue3-correction-cb1-s40-21-22-48479.pdf
        """
    )
    
    parser.add_argument(
        'pdf_url',
        help='URL du PDF QCM à extraire'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Affichage détaillé du processus'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='QCM Medical Extraction System v2.0.0'
    )

    args = parser.parse_args()

    # Validation URL
    if not args.pdf_url.startswith(('http://', 'https://')):
        print("❌ Erreur: URL invalide (doit commencer par http:// ou https://)")
        sys.exit(1)

    # Affichage bannière
    print_banner()
    
    # Extraction
    result = extract_qcm(args.pdf_url, args.verbose)
    
    if result:
        print(f"\n📊 QCM sauvegardé avec l'ID: {result.get('qcm_db_id', 'N/A')}")
        print("🚀 Le QCM est maintenant disponible dans votre base de données")
        sys.exit(0)
    else:
        print("\n❌ Échec de l'extraction")
        print("📋 Vérifiez l'URL et vos configurations (clés API)")
        sys.exit(1)

if __name__ == "__main__":
    main() 