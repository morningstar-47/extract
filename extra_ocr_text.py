import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import argparse
import sys

# Configure Tesseract path for Windows
# Configure Tesseract path for Windows (can be overridden via CLI)
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = ""

    for page in doc:
        # Texte classique
        all_text += page.get_text("text")

        # OCR sur images
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            text_ocr = pytesseract.image_to_string(image, lang="fra+eng")  
            all_text += "\n" + text_ocr

    return all_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraire le texte (et OCR) d'un PDF.")
    parser.add_argument("pdf", nargs="?", help="Chemin du fichier PDF à traiter")
    parser.add_argument("-o", "--output", default=None, help="Chemin du fichier texte de sortie (par défaut: <nom_pdf>_extracted.txt dans le même dossier)")
    parser.add_argument("-l", "--lang", default="fra+eng", help="Langues pour Tesseract (par défaut: fra+eng)")
    parser.add_argument("--tesseract-path", default=None, help="Chemin vers tesseract.exe si différent de l'emplacement par défaut")

    args = parser.parse_args()

    if args.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_path

    pdf_path = args.pdf
    if not pdf_path:
        try:
            pdf_path = input("Entrez le chemin du PDF à traiter: ").strip()
        except KeyboardInterrupt:
            print("\nOpération annulée.")
            sys.exit(1)

    if not pdf_path:
        print("Erreur: aucun chemin PDF fourni.")
        sys.exit(1)

    # Déterminer le chemin de sortie si non fourni
    if args.output:
        output_path = args.output
    else:
        pdf_dir = os.path.dirname(pdf_path) or "."
        pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(pdf_dir, f"{pdf_stem}_extracted.txt")

    # Override language dynamically inside OCR call by using a local function
    def extract_with_lang(path, lang):
        doc = fitz.open(path)
        all_text = ""
        for page in doc:
            all_text += page.get_text("text")
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                text_ocr = pytesseract.image_to_string(image, lang=lang)
                all_text += "\n" + text_ocr
        return all_text

    try:
        text = extract_with_lang(pdf_path, args.lang)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Extraction réussie ! Enregistré dans '{output_path}'")
        print(f"Nombre total de caractères extraits: {len(text)}")
    except FileNotFoundError:
        print(f"Erreur: fichier PDF introuvable à l'emplacement: {pdf_path}")
        print("Vérifiez que le fichier existe et que le chemin est correct.")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lors du traitement du PDF: {e}")
        sys.exit(1)
