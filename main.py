from pathlib import Path
from dotenv import load_dotenv

# Charge le .env depuis le répertoire du projet (avant tout autre import)
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
ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/tiff", "image/bmp", "application/pdf"]

# Stockage en mémoire des jobs en cours et terminés
_jobs:        dict = {}
_job_cancel:  dict = {}  # job_id -> threading.Event (set = annuler)
_executor = ThreadPoolExecutor(max_workers=4)
jobs_lock = threading.Lock()
MAX_FILE_SIZE = 15 * 1024 * 1024


def _job_est_annule(job_id: str, cancel_event: threading.Event) -> bool:
    with jobs_lock:
        job = _jobs.get(job_id, {})
        if cancel_event.is_set() or job.get("status") == "cancelled":
            cancel_event.set()
            _jobs[job_id] = {"status": "cancelled"}
            return True
    return False


def _run_job(job_id: str, path: str, content_type: str, cancel_event: threading.Event):
    """Exécuté dans un thread séparé : extraction Gemini + Excel + PDF."""
    short = job_id[:8]
    print(f"\n[JOB {short}] Démarrage traitement...")
    try:
        # Vérifie l'annulation AVANT l'appel Gemini (long)
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] ⏹️  Annulé avant appel Gemini.")
            return

        result = extraire_facture(path, content_type, cancel_event)

        # Vérifie l'annulation après la réponse Gemini
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] ⏹️  Annulé après réponse Gemini — résultat ignoré.")
            return

        print(f"[JOB {short}] Gemini OK — génération Excel...")
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule avant generation Excel - resultat ignore.")
            return
        excel_filename = os.path.basename(json_vers_excel(result))
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule apres generation Excel - resultat ignore.")
            return
        print(f"[JOB {short}] Excel OK — génération PDF...")
        pdf_filename   = os.path.basename(json_vers_pdf(result))
        if _job_est_annule(job_id, cancel_event):
            print(f"[JOB {short}] Annule apres generation PDF - resultat ignore.")
            return
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
    return {"status": "ok"}


@app.post("/preview")
async def preview(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 15 Mo)")
    img_bgr = preparer_image_pour_llm(contents, file.content_type)
    _, buffer = cv2.imencode(".png", img_bgr)
    return Response(content=buffer.tobytes(), media_type="image/png")


@app.post("/process")
async def process(file: UploadFile = File(...)):
    """Démarre le traitement et retourne immédiatement un job_id."""
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

    cancel_event = threading.Event()
    with jobs_lock:
        _job_cancel[job_id] = cancel_event
        _jobs[job_id] = {"status": "processing"}

    # Lancer le traitement dans un thread sans bloquer le serveur
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_job, job_id, path, file.content_type, cancel_event)

    return JSONResponse({"job_id": job_id})

@app.delete("/cancel/{job_id}")
def cancel(job_id: str):
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
    with jobs_lock:
        job = _jobs.get(job_id)
    if job is None or job.get("status") == "not_found":
        return {"status": "not_found"}
    if job["status"] == "done":
        return {"status": "done", "excel": job["excel"], "pdf": job["pdf"]}
    return {k: v for k, v in job.items() if k != "data"}


@app.get("/result/{job_id}")
def result(job_id: str):
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
    if not _fichier_appartient_a_un_job(filename):
        raise HTTPException(status_code=404, detail="Fichier non disponible")
    path = f"outputs/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF non trouve")
    return FileResponse(path, filename=filename, media_type="application/pdf")


# TOUJOURS EN DERNIER
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")