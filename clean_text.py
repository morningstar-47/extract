"""
Correction et nettoyage de texte OCR via LLM local.

Ce module permet de corriger et reformuler du texte extrait par OCR
en utilisant un modèle de langage local (LM Studio).
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

import requests
from requests.exceptions import RequestException, Timeout

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextCorrector:
    """Correcteur de texte OCR utilisant un LLM local."""

    def __init__(
        self,
        api_url: str = "http://192.168.1.22:1234/v1/chat/completions",
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: int = 60
    ):
        """
        Initialise le correcteur de texte.

        Args:
            api_url: URL de l'API LM Studio
            model: Nom du modèle à utiliser
            temperature: Température de génération (0.0-1.0)
            max_tokens: Nombre maximum de tokens à générer
            timeout: Timeout des requêtes en secondes
        """
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Vérifier la connexion à l'API
        self._check_api_connection()

    def _check_api_connection(self) -> None:
        """Vérifie que l'API LM Studio est accessible."""
        try:
            response = requests.get(
                self.api_url.replace("/v1/chat/completions", "/v1/models"),
                timeout=5
            )
            if response.ok:
                logger.info("✓ Connexion à l'API LM Studio établie")
            else:
                logger.warning(f"API accessible mais retourne le code {response.status_code}")
        except RequestException:
            logger.warning("⚠ Impossible de se connecter à l'API LM Studio")
            logger.warning(f"   Vérifiez que LM Studio est lancé sur {self.api_url}")

    def split_text_into_chunks(self, text: str, max_chars: int = 2000) -> List[str]:
        """
        Divise le texte en segments pour éviter les erreurs d'API.

        Args:
            text: Texte à diviser
            max_chars: Taille maximale de chaque segment

        Returns:
            Liste des segments de texte
        """
        # Diviser par paragraphes
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si le paragraphe est trop long, le diviser par phrases
            if len(paragraph) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                        
                    # Si une phrase est trop longue, la découper
                    if len(sentence) > max_chars:
                        for i in range(0, len(sentence), max_chars):
                            chunk_part = sentence[i:i + max_chars]
                            if current_chunk and len(current_chunk + chunk_part) > max_chars:
                                chunks.append(current_chunk.strip())
                                current_chunk = chunk_part
                            else:
                                current_chunk += " " + chunk_part if current_chunk else chunk_part
                    else:
                        if current_chunk and len(current_chunk + sentence) > max_chars:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk and len(current_chunk + paragraph) > max_chars:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def correct_text(self, text: str) -> str:
        """
        Corrige un segment de texte via l'API LLM.

        Args:
            text: Texte à corriger

        Returns:
            Texte corrigé (ou texte original en cas d'erreur)
        """
        prompt = f"""Corrige et reformule légèrement ce texte OCR pour qu'il soit lisible, 
sans fautes et sans caractères étranges, mais en gardant le sens original.
Ne change pas la structure ni le contenu, corrige uniquement les erreurs OCR.

{text}
"""

        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Validation de la structure de réponse
            if "choices" not in data or not data["choices"]:
                logger.error(f"Structure de réponse invalide: {data}")
                return text
            
            corrected = data["choices"][0]["message"]["content"].strip()
            return corrected
            
        except Timeout:
            logger.error(f"Timeout après {self.timeout}s - texte trop long ou serveur occupé")
            return text
        except RequestException as e:
            logger.error(f"Erreur de connexion à l'API: {e}")
            return text
        except (KeyError, IndexError) as e:
            logger.error(f"Erreur de structure de réponse: {e}")
            return text
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            return text

    def correct_full_text(
        self,
        text: str,
        max_chars: int = 1500,
        show_preview: bool = True
    ) -> str:
        """
        Corrige un texte complet en le divisant en segments.

        Args:
            text: Texte complet à corriger
            max_chars: Taille maximale des segments
            show_preview: Afficher un aperçu de chaque segment

        Returns:
            Texte complet corrigé
        """
        logger.info(f"Texte original: {len(text):,} caractères")
        
        # Diviser en segments
        chunks = self.split_text_into_chunks(text, max_chars=max_chars)
        logger.info(f"Divisé en {len(chunks)} segment(s)")
        
        corrected_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Segment {i}/{len(chunks)} ({len(chunk):,} caractères)")
            logger.info(f"{'='*60}")
            
            if show_preview:
                preview = chunk[:150] + "..." if len(chunk) > 150 else chunk
                logger.info(f"Aperçu: {preview}")
            
            try:
                corrected_chunk = self.correct_text(chunk)
                corrected_chunks.append(corrected_chunk)
                
                # Vérifier si la correction a fonctionné
                if corrected_chunk != chunk:
                    logger.info(f"✓ Segment {i} corrigé avec succès")
                else:
                    logger.warning(f"⚠ Segment {i} inchangé (erreur possible)")
                    
            except Exception as e:
                logger.error(f"✗ Erreur segment {i}: {str(e)}")
                logger.warning("  → Utilisation du texte original")
                corrected_chunks.append(chunk)
        
        # Recombiner
        final_text = "\n\n".join(corrected_chunks)
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Traitement terminé")
        logger.info(f"  - Total: {len(final_text):,} caractères")
        logger.info(f"  - Segments: {len(corrected_chunks)}")
        logger.info(f"{'='*60}")
        
        return final_text


def main():
    """Point d'entrée principal du script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Corriger et nettoyer un texte extrait par OCR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s extracted_text.txt
  %(prog)s extracted_text.txt -o texte_propre.txt
  %(prog)s extracted_text.txt -m 2000
  %(prog)s extracted_text.txt --api-url http://localhost:1234/v1/chat/completions
        """
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Chemin du fichier texte d'entrée"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Chemin du fichier de sortie (défaut: <nom_input>_corrected.txt)"
    )
    parser.add_argument(
        "-m", "--max-chars",
        type=int,
        default=1500,
        help="Taille max des segments (défaut: 1500)"
    )
    parser.add_argument(
        "--api-url",
        default="http://192.168.1.22:1234/v1/chat/completions",
        help="URL de l'API LM Studio"
    )
    parser.add_argument(
        "--model",
        default="openai/gpt-oss-20b",
        help="Nom du modèle à utiliser"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Température de génération (0.0-1.0, défaut: 0.2)"
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Ne pas afficher l'aperçu des segments"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Afficher les messages de débogage détaillés"
    )

    args = parser.parse_args()

    # Configuration du niveau de log
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Gestion du fichier d'entrée
    input_path = args.input
    if not input_path:
        default_candidate = Path("extracted_text.txt")
        if default_candidate.exists():
            input_path = default_candidate
            logger.info(f"Utilisation du fichier par défaut: {input_path}")
        else:
            try:
                user_input = input("Entrez le chemin du fichier texte à corriger: ").strip()
                if not user_input:
                    logger.error("Aucun fichier d'entrée fourni.")
                    sys.exit(1)
                input_path = Path(user_input)
            except KeyboardInterrupt:
                print("\nOpération annulée.")
                sys.exit(1)

    # Vérification de l'existence du fichier
    if not input_path.exists():
        logger.error(f"Le fichier '{input_path}' n'existe pas.")
        logger.info("Veuillez d'abord extraire le texte avec 'extra_ocr_text.py'")
        sys.exit(1)

    # Déterminer le chemin de sortie
    if args.output:
        output_path = args.output
    else:
        output_path = input_path.parent / f"{input_path.stem}_corrected.txt"

    try:
        # Lire le texte d'entrée
        text = input_path.read_text(encoding="utf-8")
        
        # Créer le correcteur et traiter le texte
        corrector = TextCorrector(
            api_url=args.api_url,
            model=args.model,
            temperature=args.temperature
        )
        
        corrected_text = corrector.correct_full_text(
            text,
            max_chars=args.max_chars,
            show_preview=not args.no_preview
        )
        
        # Sauvegarder le résultat
        output_path.write_text(corrected_text, encoding="utf-8")
        
        logger.info(f"\n✓ Texte corrigé sauvegardé: {output_path}")
        
        # Afficher un aperçu
        logger.info("\nAperçu du résultat:")
        logger.info("-" * 60)
        preview = corrected_text[:500] + "..." if len(corrected_text) > 500 else corrected_text
        print(preview)
        
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()