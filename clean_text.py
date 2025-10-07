import requests
import re
import argparse
import os
import sys

def split_text_into_chunks(text, max_chars=2000):
    """Divise le texte en chunks plus petits pour éviter les erreurs d'API"""
    # Diviser par paragraphes d'abord
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # Si le paragraphe est trop long, le diviser par phrases
        if len(paragraph) > max_chars:
            sentences = re.split(r'[.!?]+\s+', paragraph)
            for sentence in sentences:
                if len(current_chunk + sentence) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        # Si une seule phrase est trop longue, la diviser
                        chunks.append(sentence[:max_chars])
                        current_chunk = sentence[max_chars:]
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
        else:
            if len(current_chunk + paragraph) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    chunks.append(paragraph)
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def correct_text_local(text):
    prompt = f"""Corrige et reformule légèrement ce texte OCR pour qu'il soit lisible, 
    sans fautes et sans caractères étranges, mais en gardant le sens original :

    {text}
    """

    try:
        response = requests.post(
            "http://192.168.1.22:1234/v1/chat/completions",  # LM Studio
            headers={"Content-Type": "application/json"},
            json={
                "model": "openai/gpt-oss-20b",  # ou le modèle que tu as chargé dans LM Studio
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2048
            },
            timeout=30
        )
        
        response.raise_for_status()  # Lève une exception si le statut HTTP n'est pas 200
        response_data = response.json()
        
        # Vérifier la structure de la réponse
        if "choices" not in response_data:
            print(f"Erreur: Structure de réponse inattendue: {response_data}")
            return text  # Retourner le texte original en cas d'erreur
        
        if not response_data["choices"] or len(response_data["choices"]) == 0:
            print("Erreur: Aucun choix dans la réponse")
            return text
            
        return response_data["choices"][0]["message"]["content"].strip()
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion à l'API: {e}")
        print("Retour du texte original sans correction.")
        return text
    except KeyError as e:
        print(f"Erreur de structure de réponse: {e}")
        print(f"Réponse reçue: {response_data}")
        return text
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corriger et nettoyer un texte extrait (OCR).")
    parser.add_argument("input", nargs="?", help="Chemin du fichier texte d'entrée (par défaut: 'extracted_text.txt' si présent)")
    parser.add_argument("-o", "--output", default=None, help="Chemin du fichier de sortie (par défaut: <nom_input>_corrected.txt dans le même dossier)")
    parser.add_argument("-m", "--max-chars", type=int, default=1500, help="Taille max des segments (par défaut: 1500)")
    args = parser.parse_args()

    input_path = args.input
    if not input_path:
        # Si non fourni, essayer 'extracted_text.txt' sinon demander
        default_candidate = "extracted_text.txt"
        if os.path.exists(default_candidate):
            input_path = default_candidate
        else:
            try:
                input_path = input("Entrez le chemin du fichier texte a corriger: ").strip()
            except KeyboardInterrupt:
                print("\nOpération annulée.")
                sys.exit(1)

    if not input_path:
        print("Erreur: aucun fichier d'entrée fourni.")
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        in_dir = os.path.dirname(input_path) or "."
        in_stem = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(in_dir, f"{in_stem}_corrected.txt")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        print(f"Texte original: {len(text)} caracteres")

        # Diviser le texte en chunks
        chunks = split_text_into_chunks(text, max_chars=args.max_chars)
        print(f"Texte divise en {len(chunks)} segments")

        corrected_chunks = []

        for i, chunk in enumerate(chunks, 1):
            print(f"\nTraitement du segment {i}/{len(chunks)} ({len(chunk)} caracteres)...")

            try:
                corrected_chunk = correct_text_local(chunk)
                corrected_chunks.append(corrected_chunk)
                print(f"[OK] Segment {i} corrige avec succes")
            except Exception as e:
                print(f"[ERREUR] Segment {i}: {str(e)}")
                print("Utilisation du texte original pour ce segment")
                corrected_chunks.append(chunk)

        # Recombiner tous les segments
        final_corrected_text = "\n\n".join(corrected_chunks)

        # Sauvegarder le texte corrigé
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_corrected_text)

        print(f"\n[SUCCES] Texte corrige sauvegarde dans '{output_path}'")
        print(f"Total caracteres: {len(final_corrected_text)}")
        print(f"Segments traites: {len(corrected_chunks)}")

        # Afficher un aperçu du texte corrigé
        print("\nApercu du texte corrige:")
        print("-" * 50)
        print(final_corrected_text[:500] + "..." if len(final_corrected_text) > 500 else final_corrected_text)

    except FileNotFoundError:
        print(f"Erreur: Le fichier '{input_path}' n'existe pas.")
        print("Veuillez d'abord executer 'extra_ocr_text.py' pour extraire le texte du PDF si besoin, ou fournir un chemin valide.")
    except Exception as e:
        print(f"Erreur inattendue: {e}")