# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image
# import io
# import os
# import argparse
# import sys

# # Configure Tesseract path for Windows
# # Configure Tesseract path for Windows (can be overridden via CLI)
# pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# def extract_text_from_pdf(pdf_path):
#     doc = fitz.open(pdf_path)
#     all_text = ""

#     for page in doc:
#         # Texte classique
#         all_text += page.get_text("text")

#         # OCR sur images
#         for img in page.get_images(full=True):
#             xref = img[0]
#             base_image = doc.extract_image(xref)
#             image_bytes = base_image["image"]
#             image = Image.open(io.BytesIO(image_bytes))
#             text_ocr = pytesseract.image_to_string(image, lang="fra+eng")  
#             all_text += "\n" + text_ocr

#     return all_text

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Extraire le texte (et OCR) d'un PDF.")
#     parser.add_argument("pdf", nargs="?", help="Chemin du fichier PDF à traiter")
#     parser.add_argument("-o", "--output", default=None, help="Chemin du fichier texte de sortie (par défaut: <nom_pdf>_extracted.txt dans le même dossier)")
#     parser.add_argument("-l", "--lang", default="fra+eng", help="Langues pour Tesseract (par défaut: fra+eng)")
#     parser.add_argument("--tesseract-path", default=None, help="Chemin vers tesseract.exe si différent de l'emplacement par défaut")

#     args = parser.parse_args()

#     if args.tesseract_path:
#         pytesseract.pytesseract.tesseract_cmd = args.tesseract_path

#     pdf_path = args.pdf
#     if not pdf_path:
#         try:
#             pdf_path = input("Entrez le chemin du PDF à traiter: ").strip()
#         except KeyboardInterrupt:
#             print("\nOpération annulée.")
#             sys.exit(1)

#     if not pdf_path:
#         print("Erreur: aucun chemin PDF fourni.")
#         sys.exit(1)

#     # Déterminer le chemin de sortie si non fourni
#     if args.output:
#         output_path = args.output
#     else:
#         pdf_dir = os.path.dirname(pdf_path) or "."
#         pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
#         output_path = os.path.join(pdf_dir, f"{pdf_stem}_extracted.txt")

#     # Override language dynamically inside OCR call by using a local function
#     def extract_with_lang(path, lang):
#         doc = fitz.open(path)
#         all_text = ""
#         for page in doc:
#             all_text += page.get_text("text")
#             for img in page.get_images(full=True):
#                 xref = img[0]
#                 base_image = doc.extract_image(xref)
#                 image_bytes = base_image["image"]
#                 image = Image.open(io.BytesIO(image_bytes))
#                 text_ocr = pytesseract.image_to_string(image, lang=lang)
#                 all_text += "\n" + text_ocr
#         return all_text

#     try:
#         text = extract_with_lang(pdf_path, args.lang)
#         with open(output_path, "w", encoding="utf-8") as f:
#             f.write(text)
#         print(f"Extraction réussie ! Enregistré dans '{output_path}'")
#         print(f"Nombre total de caractères extraits: {len(text)}")
#     except FileNotFoundError:
#         print(f"Erreur: fichier PDF introuvable à l'emplacement: {pdf_path}")
#         print("Vérifiez que le fichier existe et que le chemin est correct.")
#         sys.exit(1)
#     except Exception as e:
#         print(f"Erreur lors du traitement du PDF: {e}")
#         sys.exit(1)


"""
Extraction de texte depuis des fichiers PDF avec support OCR.

Ce module permet d'extraire le texte natif d'un PDF ainsi que le texte
des images intégrées via OCR (Tesseract).
"""

import io
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemin par défaut de Tesseract pour Windows
DEFAULT_TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class PDFTextExtractor:
    """Extracteur de texte pour fichiers PDF avec support OCR."""

    def __init__(self, tesseract_path: Optional[str] = None, languages: str = "fra+eng"):
        """
        Initialise l'extracteur de texte PDF.

        Args:
            tesseract_path: Chemin vers l'exécutable Tesseract (optionnel)
            languages: Langues pour l'OCR, séparées par '+' (défaut: "fra+eng")
        """
        self.languages = languages
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif sys.platform == 'win32':
            pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_PATH

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrait tout le texte d'un PDF (natif + OCR sur images).

        Args:
            pdf_path: Chemin vers le fichier PDF

        Returns:
            Texte extrait complet

        Raises:
            FileNotFoundError: Si le PDF n'existe pas
            fitz.FileDataError: Si le PDF est corrompu
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"Le fichier PDF n'existe pas: {pdf_path}")

        logger.info(f"Ouverture du PDF: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except fitz.FileDataError as e:
            logger.error(f"PDF corrompu ou invalide: {e}")
            raise

        all_text = []
        total_pages = len(doc)
        logger.info(f"Traitement de {total_pages} page(s)...")

        for page_num, page in enumerate(doc, start=1):
            logger.debug(f"Page {page_num}/{total_pages}")
            
            # Extraction du texte natif
            native_text = page.get_text("text")
            if native_text.strip():
                all_text.append(native_text)

            # OCR sur les images embarquées
            image_list = page.get_images(full=True)
            if image_list:
                logger.debug(f"  - {len(image_list)} image(s) détectée(s)")
                
            for img_index, img in enumerate(image_list, start=1):
                try:
                    ocr_text = self._extract_text_from_image(doc, img[0], page_num, img_index)
                    if ocr_text.strip():
                        all_text.append(ocr_text)
                except Exception as e:
                    logger.warning(f"  - Erreur OCR image {img_index}: {e}")
                    continue

        doc.close()
        
        result = "\n\n".join(all_text)
        logger.info(f"Extraction terminée: {len(result)} caractères")
        return result

    def _extract_text_from_image(self, doc: fitz.Document, xref: int, 
                                  page_num: int, img_index: int) -> str:
        """
        Effectue l'OCR sur une image embarquée dans le PDF.

        Args:
            doc: Document PDF ouvert
            xref: Référence de l'image dans le PDF
            page_num: Numéro de la page
            img_index: Index de l'image dans la page

        Returns:
            Texte extrait par OCR
        """
        try:
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            
            # OCR avec la langue configurée
            text_ocr = pytesseract.image_to_string(image, lang=self.languages)
            
            if text_ocr.strip():
                logger.debug(f"  - OCR image {img_index}: {len(text_ocr)} caractères extraits")
            
            return text_ocr
            
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract n'est pas installé ou non trouvé dans le PATH")
            raise
        except Exception as e:
            logger.warning(f"Erreur lors de l'OCR de l'image {img_index} (page {page_num}): {e}")
            return ""


def main():
    """Point d'entrée principal du script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extraire le texte (et OCR) d'un PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s document.pdf
  %(prog)s document.pdf -o texte_extrait.txt
  %(prog)s document.pdf -l fra
  %(prog)s document.pdf --tesseract-path "C:\\tesseract\\tesseract.exe"
        """
    )
    
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        help="Chemin du fichier PDF à traiter"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Chemin du fichier texte de sortie (défaut: <nom_pdf>_extracted.txt)"
    )
    parser.add_argument(
        "-l", "--lang",
        default="fra+eng",
        help="Langues pour Tesseract, séparées par '+' (défaut: fra+eng)"
    )
    parser.add_argument(
        "--tesseract-path",
        type=Path,
        default=None,
        help="Chemin vers tesseract.exe si différent de l'emplacement par défaut"
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

    # Demander le chemin du PDF si non fourni
    if not args.pdf:
        try:
            pdf_input = input("Entrez le chemin du PDF à traiter: ").strip()
            if not pdf_input:
                logger.error("Aucun chemin PDF fourni.")
                sys.exit(1)
            args.pdf = Path(pdf_input)
        except KeyboardInterrupt:
            print("\nOpération annulée.")
            sys.exit(1)

    # Déterminer le chemin de sortie
    if args.output:
        output_path = args.output
    else:
        output_path = args.pdf.parent / f"{args.pdf.stem}_extracted.txt"

    try:
        # Créer l'extracteur et traiter le PDF
        extractor = PDFTextExtractor(
            tesseract_path=str(args.tesseract_path) if args.tesseract_path else None,
            languages=args.lang
        )
        
        text = extractor.extract_text_from_pdf(args.pdf)
        
        # Sauvegarder le résultat
        output_path.write_text(text, encoding="utf-8")
        
        logger.info(f"✓ Extraction réussie !")
        logger.info(f"✓ Enregistré dans: {output_path}")
        logger.info(f"✓ Total: {len(text)} caractères extraits")
        
    except FileNotFoundError as e:
        logger.error(f"Fichier introuvable: {e}")
        sys.exit(1)
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract OCR n'est pas installé ou configuré correctement")
        logger.error("Installez Tesseract depuis: https://github.com/tesseract-ocr/tesseract")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur lors du traitement: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()