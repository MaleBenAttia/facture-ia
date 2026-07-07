# main.py — Routeur FastAPI : recoit le fichier, lance le job en thread,
# sert le frontend build, gere le polling status et les telechargements.

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from gemini_extractor import extraire_facture
from excel_generator import json_vers_excel
from pdf_generator import json_vers_pdf
import cv2
from image_preprocessor import preparer_image_pour_llm
import shutil, os, uuid, asyncio, threading
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/tiff", "image/bmp", "application/pdf", "text/markdown", "text/x-markdown"]

# Stockage memoire des jobs en cours + annulation thread-safe
_jobs:        dict = {}
_job_cancel:  dict = {}  # job_id -> threading.Event (set = annuler)
_executor = ThreadPoolExecutor(max_workers=4)
jobs_lock = threading.Lock()
MAX_FILE_SIZE = 15 * 1024 * 1024


def _maj_progress(job_id: str, pct: int):
    """Met à jour la barre de progression (thread-safe, sous lock)."""
    with jobs_lock:
        job = _jobs.get(job_id)
        if job and job.get("status") == "processing":
            job["progress"] = pct

def _job_est_annule(job_id: str, cancel_event: threading.Event) -> bool:
    with jobs_lock:
        job = _jobs.get(job_id, {})
        if cancel_event.is_set() or job.get("status") == "cancelled":
            cancel_event.set()
            _jobs[job_id] = {"status": "cancelled"}
            return True
    return False


def _compter_pages(path: str, content_type: str) -> int:
    """Nombre de pages : 1 pour les images, n pour les PDF (via PyMuPDF)."""
    if content_type != "application/pdf":
        return 1
    try:
        import fitz
        doc = fitz.open(path)
        n = len(doc)
        doc.close()
        return max(n, 1)
    except Exception:
        return 1


def _run_job(job_id: str, path: str, content_type: str, cancel_event: threading.Event, nb_pages: int = 1):
    """Thread worker : Gemini → Excel → PDF, avec annulation et progression."""
    short = job_id[:8]
    print(f"\n[JOB {short}] Démarrage traitement ({nb_pages} page(s))...")
    try:
        _maj_progress(job_id, 5)

        # Vérifie l'annulation AVANT l'appel Gemini (long)
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] ⏹️  Annulé avant appel Gemini.")
            return

        _maj_progress(job_id, 10)
        result = extraire_facture(path, content_type, cancel_event)

        # Vérifie l'annulation après la réponse Gemini
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] ⏹️  Annulé après réponse Gemini — résultat ignoré.")
            return

        _maj_progress(job_id, 60)
        print(f"[JOB {short}] Gemini OK — génération Excel...")
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule avant generation Excel - resultat ignore.")
            return
        excel_filename = os.path.basename(json_vers_excel(result))
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule apres generation Excel - resultat ignore.")
            return
        _maj_progress(job_id, 85)
        print(f"[JOB {short}] Excel OK — génération PDF...")
        pdf_filename   = os.path.basename(json_vers_pdf(result))
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule apres generation PDF - resultat ignore.")
            return
        _maj_progress(job_id, 99)
        with jobs_lock:
            _jobs[job_id] = {
                "status": "done",
                "data": result,
                "excel": excel_filename,
                "pdf":   pdf_filename,
            }
        print(f"[JOB {short}] ✅ TERMINÉ — résultat disponible sur l'appareil")
    except Exception as exc:
        with jobs_lock:
            if cancel_event.is_set():
                _jobs[job_id] = {"status": "cancelled"}
            else:
                _jobs[job_id] = {"status": "error", "detail": str(exc)}
        if cancel_event.is_set():
            print(f"[JOB {short}] ⏹️  Annulé (exception interceptée après annulation).")
        else:
            print(f"[JOB {short}] ❌ ERREUR : {exc}")
    finally:
        if os.path.exists(path):
            os.remove(path)
        with jobs_lock:
            _job_cancel.pop(job_id, None)



@app.get("/health")
def health():
    """Verification rapide que le serveur repond."""
    return {"status": "ok"}


@app.post("/preview")
async def preview(file: UploadFile = File(...)):
    """Previsualisation : preprocess l'image et la renvoie en PNG sans appeler Gemini."""
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 15 Mo)")
    prepared = preparer_image_pour_llm(contents, file.content_type)
    if isinstance(prepared, str):
        return Response(content=prepared.encode("utf-8"), media_type="text/plain; charset=utf-8")
    if not prepared:
        raise HTTPException(status_code=400, detail="Aucune image extraite du fichier")
    _, buffer = cv2.imencode(".jpg", prepared[0], [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.post("/process")
async def process(file: UploadFile = File(...)):
    """Demarre le traitement et retourne un job_id (asynchrone, ne bloque pas)."""
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 15 Mo)")

    job_id = str(uuid.uuid4())
    path   = f"{UPLOAD_DIR}/{job_id}_{file.filename}"

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    nb_pages = _compter_pages(path, file.content_type)
    cancel_event = threading.Event()
    with jobs_lock:
        _job_cancel[job_id] = cancel_event
        _jobs[job_id] = {"status": "processing", "nb_pages": nb_pages}

    # Lancer le traitement dans un thread sans bloquer le serveur
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_job, job_id, path, file.content_type, cancel_event, nb_pages)

    return JSONResponse({"job_id": job_id, "nb_pages": nb_pages})

@app.delete("/cancel/{job_id}")
def cancel(job_id: str):
    """Annule un job en cours (flag le threading.Event, le thread le verra au prochain point de controle)."""
    with jobs_lock:
        event = _job_cancel.get(job_id)
        if event:
            event.set()
            _jobs[job_id] = {"status": "cancelled"}
            print(f"[CANCEL] Job {job_id[:8]} — signal d'annulation envoyé.")
            return {"cancelled": True}
        job = _jobs.get(job_id)
        return {"cancelled": False, "status": job.get("status") if job else "not_found"}



@app.get("/status/{job_id}")
def status(job_id: str):
    """Polling : retourne 'processing' (avec progress), 'done', 'error' ou 'cancelled'."""
    with jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job.get("status") == "not_found":
        return {"status": "not_found"}
    if job["status"] == "done":
        return {"status": "done", "excel": job["excel"], "pdf": job["pdf"],
                "nb_pages": job.get("nb_pages", 1)}
    resp = {k: v for k, v in job.items() if k != "data"}
    return resp


@app.get("/result/{job_id}")
def result(job_id: str):
    """Recupere le resultat complet d'un job termine (YAML+TSV parse + produits)."""
    with jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job.get("status") != "done":
        raise HTTPException(status_code=404, detail="Résultat non disponible")
    return {"data": job["data"]}


def _fichier_appartient_a_un_job(filename: str) -> bool:
    with jobs_lock:
        return any(
            job.get("status") == "done" and (job.get("excel") == filename or job.get("pdf") == filename)
            for job in _jobs.values()
        )


@app.get("/excel/{filename}")
def download_excel(filename: str):
    """Telecharge un fichier Excel genere (verifie qu'il appartient a un job done)."""
    if not _fichier_appartient_a_un_job(filename):
        raise HTTPException(status_code=404, detail="Fichier non disponible")
    path = f"outputs/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Fichier Excel non trouve")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/pdf/{filename}")
def download_pdf(filename: str):
    """Telecharge un PDF genere (verifie qu'il appartient a un job done)."""
    if not _fichier_appartient_a_un_job(filename):
        raise HTTPException(status_code=404, detail="Fichier non disponible")
    path = f"outputs/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF non trouve")
    return FileResponse(path, filename=filename, media_type="application/pdf")


# TOUJOURS EN DERNIER
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")