from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # ← ajouter
from gemini_extractor import extraire_facture
from excel_generator import json_vers_excel
from pdf_generator import json_vers_pdf
import shutil, os

app = FastAPI()

# ← ajouter ce bloc CORS juste après app = FastAPI()
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")
    path = f"{UPLOAD_DIR}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename, "type": file.content_type}

@app.post("/process")
async def process(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Format non supporte")
    path = f"{UPLOAD_DIR}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        result = extraire_facture(path)
        excel_filename = os.path.basename(json_vers_excel(result))
        pdf_filename = os.path.basename(json_vers_pdf(result))
        return {"data": result, "excel": excel_filename, "pdf": pdf_filename}
    finally:
        # Suppression automatique de l'image stockée temporairement après traitement
        if os.path.exists(path):
            os.remove(path)

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