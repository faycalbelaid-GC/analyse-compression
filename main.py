from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import tempfile
import base64
import os
import io
import zipfile
import pandas as pd
from typing import List, Optional
from .analysis import load_data, analyze_data, plot_curve, generate_pdf
from .database import SessionLocal, TestRecord, Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Analyse de Compression API V2")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_to_db(db: Session, res: dict, meta: dict, filename: str):
    record = TestRecord(
        project_name=meta.get("project", ""),
        operator=meta.get("operator", ""),
        specimen_id=meta.get("specimen", ""),
        filename=filename,
        fc=res["fc"],
        e_modulus=res["E"],
        eps0=res["eps0"],
        eps_u=res["eps_u"]
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.post("/analyze")
async def analyze_csv(
    file: UploadFile = File(...),
    project: str = Form(""),
    operator: str = Form(""),
    specimen: str = Form(""),
    apply_smoothing: str = Form("false"),
    e_start: int = Form(10),
    e_end: int = Form(40),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Veuillez uploader un fichier .csv")
    
    contents = await file.read()
    smoothing = True if apply_smoothing.lower() == "true" else False
    try:
        df = load_data(contents)
        results = analyze_data(df, smoothing, e_start, e_end)
        
        metadata = {"project": project, "operator": operator, "specimen": specimen}
        save_to_db(db, results, metadata, file.filename)
        
        img_buf = plot_curve(results)
        fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        generate_pdf(results, img_buf, pdf_path, metadata)
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
        os.remove(pdf_path)
        
        return JSONResponse(content={
            "results": results,
            "pdf_base64": pdf_base64,
            "filename": file.filename
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-batch")
async def analyze_batch(
    files: List[UploadFile] = File(...),
    project: str = Form(""),
    operator: str = Form(""),
    apply_smoothing: str = Form("false"),
    e_start: int = Form(10),
    e_end: int = Form(40),
    db: Session = Depends(get_db)
):
    try:
        smoothing = True if apply_smoothing.lower() == "true" else False
        zip_buffer = io.BytesIO()
        summary_data = []
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in files:
                if not file.filename.endswith('.csv'): continue
                contents = await file.read()
                try:
                    df = load_data(contents)
                    results = analyze_data(df, smoothing, e_start, e_end)
                    
                    specimen_name = os.path.splitext(file.filename)[0]
                    metadata = {"project": project, "operator": operator, "specimen": specimen_name}
                    
                    save_to_db(db, results, metadata, file.filename)
                    
                    img_buf = plot_curve(results)
                    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)
                    generate_pdf(results, img_buf, pdf_path, metadata)
                    
                    zip_file.write(pdf_path, arcname=f"{specimen_name}_rapport.pdf")
                    os.remove(pdf_path)
                    
                    zip_file.writestr(f"{specimen_name}_graphique.png", img_buf.getvalue())
                    
                    summary_data.append({
                        "Fichier": file.filename,
                        "Résistance (MPa)": results["fc"],
                        "Module Young (MPa)": results["E"],
                        "Déformation (fc)": results["eps0"],
                        "Déformation ultime": results["eps_u"]
                    })
                except Exception as e:
                    print(f"Erreur batch sur {file.filename}: {e}")
            
            if summary_data:
                df_summary = pd.DataFrame(summary_data)
                excel_buf = io.BytesIO()
                df_summary.to_excel(excel_buf, index=False)
                zip_file.writestr("synthese_essais.xlsx", excel_buf.getvalue())
                
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=resultats_batch.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    records = db.query(TestRecord).order_by(TestRecord.id.desc()).limit(50).all()
    return records
