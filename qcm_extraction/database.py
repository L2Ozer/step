import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

class Database:
    def __init__(self):
        load_dotenv()
        
        # Configuration Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Les variables d'environnement SUPABASE_URL et SUPABASE_KEY sont requises")
        
        # Connexion à Supabase
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Configuration du bucket de stockage pour les images
        self.bucket_name = "qcm_images"
        
        # Cache pour les IDs fréquemment utilisés
        self._cache: Dict[str, Dict[str, str]] = {
            "universites": {},
            "ue": {},
            "qcm": {}
        }
    
    def get_universite_id(self, nom: str) -> Optional[str]:
        """Récupère l'ID d'une université existante"""
        result = self.client.table("universites").select("id").eq("nom", nom).execute()
        return result.data[0]["id"] if result.data else None
    
    def get_ue_id(self, ue_name: str) -> str:
        """Récupère l'ID d'une UE à partir de son numéro (UE1, UE2, etc.)"""
        try:
            # Afficher toutes les UEs existantes
            response = self.client.table('ue').select('*').execute()
            print("UEs existantes dans la base de données:")
            for ue in response.data:
                print(f"- {ue['numero']} (ID: {ue['id']})")
            
            # Rechercher l'UE spécifique
            response = self.client.table('ue').select('id').eq('numero', ue_name).execute()
            
            if response.data:
                return response.data[0]['id']
            else:
                print(f"⚠️ UE '{ue_name}' non trouvée dans la base de données")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la recherche de l'UE: {str(e)}")
            return None
    
    def create_qcm(self, metadata: Dict[str, Any]) -> Optional[int]:
        """Crée un QCM dans la base de données"""
        try:
            # Récupérer l'ID de l'UE
            ue_id = self.get_ue_id(metadata['ue'])
            if not ue_id:
                print(f"❌ UE '{metadata['ue']}' non trouvée dans la base de données")
                return None
            
            # Créer le QCM
            qcm_data = {
                'ue_id': ue_id,
                'type': metadata['type'],
                'annee': metadata['annee']
            }
            
            response = self.client.table('qcm').insert(qcm_data).execute()
            
            if response.data:
                qcm_id = response.data[0]['id']
                print(f"✅ QCM créé avec l'ID: {qcm_id}")
                return qcm_id
            else:
                print("❌ Erreur lors de la création du QCM")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lors de la création du QCM: {str(e)}")
            return None
    
    def create_question(self, qcm_id: str, numero: int, texte: str, explication: Optional[str] = None) -> str:
        """Crée une nouvelle question"""
        question_data = {
            "qcm_id": qcm_id,
            "numero": numero,
            "texte": texte,
            "explication": explication
        }
        
        result = self.client.table("questions").insert(question_data).execute()
        return result.data[0]["id"]
    
    def create_option(self, question_id: str, lettre: str, texte: str, est_correcte: bool = False) -> str:
        """Crée une nouvelle option de réponse"""
        option_data = {
            "question_id": question_id,
            "lettre": lettre,
            "texte": texte,
            "est_correcte": est_correcte
        }
        
        result = self.client.table("options").insert(option_data).execute()
        return result.data[0]["id"]
    
    def create_image(self, question_id: str, url: str, alt: str = "Image de la question") -> str:
        """Crée une nouvelle image"""
        image_data = {
            "question_id": question_id,
            "url": url,
            "alt": alt
        }
        
        result = self.client.table("images").insert(image_data).execute()
        return result.data[0]["id"]
    
    def upload_image(self, file_path: str, qcm_id: str, question_num: int) -> str:
        """Upload une image vers le stockage Supabase"""
        import mimetypes
        from pathlib import Path
        
        # Déterminer le type MIME
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'image/jpeg'  # Par défaut
            
        # Construire le chemin de stockage
        filename = Path(file_path).name
        storage_path = f"{qcm_id}/q{question_num}_{filename}"
        
        # Upload du fichier
        with open(file_path, 'rb') as f:
            self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=f,
                file_options={"content-type": content_type}
            )
        
        # Construire l'URL publique
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{storage_path}" 