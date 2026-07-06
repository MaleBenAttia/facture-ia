"""
image_preprocessor.py — Pipeline adaptatif : upscale, CLAHE, sharpening,
puis envoi au LLM. Gere images, PDF scannes et PDF natifs (avec ou sans logo).
"""

import fitz  # PyMuPDF
import cv2
import numpy as np


MIN_DIMENSION = 1000  # pixels minimum sur le plus court cote

# ---------- Extraction depuis PDF (3 cas) ou image ----------
def pdf_vers_images(pdf_bytes: bytes, dpi: int = 300) -> list:
    """Rend chaque page PDF en image bitmap 300 DPI (page entiere, pas d'extraction d'images embarquees)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        zoom_f = dpi / 72
        mat = fitz.Matrix(zoom_f, zoom_f)
        pix = page.get_pixmap(matrix=mat)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        elif pix.n == 1:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        images.append(img_bgr)
    doc.close()
    return images


def extraire_image_de_lentree(file_bytes: bytes, content_type: str):
    """Detecte le type (image / PDF / markdown), appelle pdf_vers_images ou decode directement."""
    if content_type in ("text/markdown", "text/x-markdown"):
        return None, "markdown"

    if content_type == "application/pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texte_total = sum(len(page.get_text().strip()) for page in doc)
        nb_images_embarquees = sum(len(page.get_images()) for page in doc)
        doc.close()

        if texte_total < 50:
            return pdf_vers_images(file_bytes, dpi=300), "scan"
        elif nb_images_embarquees > 0:
            return pdf_vers_images(file_bytes, dpi=300), "scan"
        else:
            return pdf_vers_images(file_bytes, dpi=300), "natif"
    else:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError(f"Impossible de decoder l'image (format: {content_type}). Fichier corrompu ou format non supporte.")
        return [img_bgr], "scan"


# ---------- Corrections ----------


def upscale_smooth(img_bgr, facteur: float = 2):
    h, w = img_bgr.shape[:2]
    img = cv2.resize(img_bgr, (int(w * facteur), int(h * facteur)), interpolation=cv2.INTER_CUBIC)
    return unsharp_mask(img, sigma=0.8, force=0.6)


def unsharp_mask(img_bgr, sigma: float = 1.0, force: float = 1.2):
    flou = cv2.GaussianBlur(img_bgr, (0, 0), sigma)
    return cv2.addWeighted(img_bgr, 1 + force, flou, -force, 0)


def ameliorer_texte(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.merge([l, a, b])
    img = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
    img = cv2.bilateralFilter(img, 9, 75, 75)
    return unsharp_mask(img, sigma=0.5, force=0.5)


# ---------- Pipeline complet adaptatif (résolution réelle) ----------
def pipeline_adaptatif_complet(img_bgr, verbose: bool = True):
    """Upscale si petite image, puis CLAHE + bilateral + sharpening. S'adapte a la resolution."""
    h, w = img_bgr.shape[:2]
    taille_px = h * w
    if verbose:
        print(f"[preprocessing] Résolution: {w}x{h} ({taille_px / 1e6:.1f} MP)")

    img = img_bgr

    if taille_px < 0.5e6:
        img = upscale_smooth(img, facteur=4)
        img = ameliorer_texte(img)
        if verbose: print("[preprocessing] → Petite image: upscale x4 + text enhancement")
    elif taille_px < 2e6:
        img = upscale_smooth(img, facteur=2)
        img = ameliorer_texte(img)
        if verbose: print("[preprocessing] → Image moyenne: upscale x2 + text enhancement")
    elif taille_px < 8e6:
        img = ameliorer_texte(img)
        img = unsharp_mask(img, force=0.8)
        if verbose: print("[preprocessing] → Résolution suffisante: sharpening + contrast")
    else:
        facteur_reduction = (4e6 / taille_px) ** 0.5
        nouvelle_taille = (int(w * facteur_reduction), int(h * facteur_reduction))
        img = cv2.resize(img, nouvelle_taille, interpolation=cv2.INTER_AREA)
        img = ameliorer_texte(img)
        if verbose: print(f"[preprocessing] -> Grande image: reduite a {nouvelle_taille} + sharpening")

    return img


# ---------- Point d'entrée public ----------
def preparer_image_pour_llm(file_bytes: bytes, content_type: str, verbose: bool = True):
    """Point d'entree unique : detecte image/PDF/markdown, applique le pipeline, retourne images ou texte."""
    images_bgr, type_contenu = extraire_image_de_lentree(file_bytes, content_type)

    if type_contenu == "markdown":
        return file_bytes.decode("utf-8")

    # Pipeline complet sur TOUTES les images (Upscale + CLAHE + Bilateral + Sharpening)
    # Le filtre d'ombre est desactive (abime le logo)
    images_bgr = [pipeline_adaptatif_complet(img, verbose=verbose) for img in images_bgr]

    return images_bgr