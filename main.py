from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from gemini_extractor import extraire_facture
from excel_generator import json_vers_excel
from pdf_generator import json_vers_pdf
import shutil, os, uuid, asyncio
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
_jobs: dict = {}
_executor = ThreadPoolExecutor(max_workers=4)


def _run_job(job_id: str, path: str):
    """Exécuté dans un thread séparé : extraction Gemini + Excel + PDF."""
    short = job_id[:8]
    print(f"\n[JOB {short}] Démarrage traitement...")
    try:
        result = extraire_facture(path)
        print(f"[JOB {short}] Gemini OK — génération Excel...")
        excel_filename = os.path.basename(json_vers_excel(result))
        print(f"[JOB {short}] Excel OK — génération PDF...")
        pdf_filename   = os.path.basename(json_vers_pdf(result))
        _jobs[job_id] = {
            "status": "done",
            "data": result,
            "excel": excel_filename,
            "pdf":   pdf_filename,
        }
        print(f"[JOB {short}] ✅ TERMINÉ — résultat disponible sur l'appareil")
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "detail": str(exc)}
        print(f"[JOB {short}] ❌ ERREUR : {exc}")
    finally:
        if os.path.exists(path):
            os.remove(path)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
async def process(file: UploadFile = File(...)):
    """Démarre le traitement et retourne immédiatement un job_id."""
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")

    job_id = str(uuid.uuid4())
    path   = f"{UPLOAD_DIR}/{job_id}_{file.filename}"

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    _jobs[job_id] = {"status": "processing"}

    # Lancer le traitement dans un thread sans bloquer le serveur
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_job, job_id, path)

    return JSONResponse({"job_id": job_id})


@app.get("/status/{job_id}")
def status(job_id: str):
    """Poll léger : retourne uniquement le statut + noms de fichiers (pas les données complètes)."""
    job = _jobs.get(job_id)
    if job is None or job.get("status") == "not_found":
        return {"status": "not_found"}
    if job["status"] == "done":
        # Réponse légère : pas les données, juste les noms de fichiers
        return {"status": "done", "excel": job["excel"], "pdf": job["pdf"]}
    # processing ou error
    return {k: v for k, v in job.items() if k != "data"}


@app.get("/result/{job_id}")
def result(job_id: str):
    """Retourne les données complètes d'un job terminé."""
    job = _jobs.get(job_id)
    if job is None or job.get("status") != "done":
        raise HTTPException(status_code=404, detail="Résultat non disponible")
    return {"data": job["data"]}


@app.get("/excel/{filename}")
def download_excel(filename: str):
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
    path = f"outputs/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF non trouve")
    return FileResponse(path, filename=filename, media_type="application/pdf")


# TOUJOURS EN DERNIER
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")