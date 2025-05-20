#!/usr/bin/env python3
# Script pour ajouter manuellement les questions 16-18 dans le contenu Markdown généré

import os
import sys
import re
from pathlib import Path

# Texte correct de la page 7 contenant les questions manquantes 16-18
PAGE_7_CONTENT = """# Page 7

# Stansanté 

formoup
Tél : 03 83 40 70 02
contact@stan-sante.com
UE 1 – Biologie Cellulaire Fondamentale

## Q16. A propos de la technique d'ombrage et cryofracture :

A. Une congélation précède la cassure.
B. Elle permet l'observation des surfaces internes des membranes.  
C. La cassure de l'échantillon se fait à l'aide d'un couteau.
D. L'ombrage se fait grâce à la vaporisation de sels de métaux lourds.
E. C'est une technique réalisée pour des observations en microscope électronique.

Réponses justes : A, B, C, D, E.


## Q17. A propos du noyau :

A. Sa forme varie en fonction de l'âge.
B. Les ostéoclastes sont des cellules plurinucléées.
C. Les polynucléaires ont un unique noyau.
D. Au microscope électronique, l'hétérochromatine apparait dense aux électrons.
E. Il occupe une position centrale dans les fibres musculaires squelettique.

Réponses justes : A, B, C, D.
E. Faux. Il occupe une position périphérique dans les fibres musculaires squelettiques.


## Q18. A propos de l'ADN dans le noyau :

A. Un nucléosome est composé d'ADN et d'histones H1, H2, H3 et H4.
B. Une chromatide mesure environ 700 nm de large.
C. Un chromatosome ne contient pas de protéine.
D. Une chromatine dont les histones sont acétylées et l'ADN méthylé est sous forme compactée.  
E. Il est associé aux lamines.

Réponses justes : B, E.
A. Faux. Un nucléosome est composé d'ADN et d'histones H2A, H2B, H3 et H4.
C. Faux. Un chromatosome = nucléosome + H1, et les histones sont des protéines.
D. Faux. Une chromatine dont les histones sont acétylées et l'ADN non méthylé est sous forme décompactée.
"""

def fix_markdown_file(markdown_path):
    """Corrige le contenu Markdown en ajoutant les questions manquantes 16-18 à la page 7."""
    if not os.path.exists(markdown_path):
        print(f"Erreur: Le fichier {markdown_path} n'existe pas!")
        return False

    # Lire le contenu actuel
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Chercher le pattern problématique à la page 7
    page7_pattern = r'# Page 7\s+# Stang[^\n]*\s+form0*'
    
    # Remplacer la page 7 problématique par notre contenu corrigé
    if re.search(page7_pattern, content):
        content = re.sub(page7_pattern, PAGE_7_CONTENT, content)
        
        # Sauvegarder le fichier corrigé
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fichier {markdown_path} corrigé avec succès! Les questions 16-18 ont été ajoutées.")
        return True
    else:
        print(f"⚠️ Pattern de page 7 problématique non trouvé dans {markdown_path}")
        return False

def find_and_fix_qcm_markdown(qcm_id=None, base_dir="qcm_extraction/temp/outputs"):
    """Recherche tous les fichiers Markdown dans le répertoire de sortie et les corrige."""
    base_path = Path(base_dir)
    
    # Si qcm_id est spécifié, corriger uniquement ce QCM
    if qcm_id:
        qcm_dir = base_path / qcm_id
        if qcm_dir.exists():
            markdown_path = qcm_dir / "content.md"
            if markdown_path.exists():
                fix_markdown_file(str(markdown_path))
            else:
                print(f"⚠️ Fichier Markdown non trouvé pour le QCM {qcm_id}")
        else:
            print(f"⚠️ Répertoire non trouvé pour le QCM {qcm_id}")
        return
    
    # Sinon, parcourir tous les répertoires et corriger les fichiers Markdown
    count_fixed = 0
    count_processed = 0
    
    for qcm_dir in base_path.iterdir():
        if qcm_dir.is_dir():
            markdown_path = qcm_dir / "content.md"
            if markdown_path.exists():
                count_processed += 1
                if fix_markdown_file(str(markdown_path)):
                    count_fixed += 1
    
    print(f"📊 Résumé: {count_fixed} fichiers corrigés sur {count_processed} fichiers traités.")

if __name__ == "__main__":
    # Si un argument est passé, considérez-le comme l'ID du QCM
    if len(sys.argv) > 1:
        qcm_id = sys.argv[1]
        find_and_fix_qcm_markdown(qcm_id)
    else:
        find_and_fix_qcm_markdown() 