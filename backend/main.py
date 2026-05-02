from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import tempfile
import base64
import os
from .analysis import load_data, analyze_data, plot_curve, generate_pdf

app = FastAPI(title="Analyse de Compression API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

@app.post("/analyze")
async def analyze_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Veuillez uploader un fichier .csv")
    
    contents = await file.read()
    try:
        df = load_data(contents)
        results = analyze_data(df)
        
        img_buf = plot_curve(df, results)
        img_base64 = base64.b64encode(img_buf.getvalue()).decode('utf-8')
        
        fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        generate_pdf(results, img_buf, pdf_path)
        
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
            
        os.remove(pdf_path)
        
        return JSONResponse(content={
            "results": results,
            "plot_base64": img_base64,
            "pdf_base64": pdf_base64,
            "filename": file.filename
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
