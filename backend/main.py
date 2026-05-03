from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import tempfile
import base64
import os
import io
import zipfile
import pandas as pd
from typing import List, Optional
from datetime import timedelta
from .analysis import load_data, analyze_data, plot_curve, generate_pdf
from .database import SessionLocal, TestRecord, Project, User, Base, engine
from .auth import get_current_user, get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Analyse de Compression API V2 - Expert")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(password)
    db_user = User(email=email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}

@app.post("/projects")
def create_project(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(name=name, description=description, owner=current_user)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@app.get("/projects")
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    return projects

def save_to_db(db: Session, res: dict, meta: dict, filename: str, current_user: User):
    project_id = meta.get("project_id")
    record = TestRecord(
        project_id=project_id,
        user_id=current_user.id,
        project_name=meta.get("project_name", ""),
        operator=meta.get("operator", ""),
        specimen_id=meta.get("specimen", ""),
        filename=filename,
        fc=res["fc"],
        e_modulus=res["E"],
        eps0=res["eps0"],
        eps_u=res["eps_u"],
        toughness=res.get("toughness"),
        age_days=meta.get("age_days"),
        fc_28_pred=res.get("fc_28_pred"),
        compliance_status=res.get("compliance_status"),
        anomaly_flag=res.get("anomaly_flag", False)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.post("/analyze")
async def analyze_csv(
    file: UploadFile = File(...),
    project_id: int = Form(None),
    project_name: str = Form(""),
    operator: str = Form(""),
    specimen: str = Form(""),
    apply_smoothing: str = Form("false"),
    e_start: int = Form(10),
    e_end: int = Form(40),
    age_days: int = Form(None),
    target_fc: float = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Veuillez uploader un fichier .csv")
    
    contents = await file.read()
    smoothing = True if apply_smoothing.lower() == "true" else False
    try:
        df = load_data(contents)
        results = analyze_data(df, smoothing, e_start, e_end, age_days, target_fc)
        
        metadata = {
            "project_id": project_id,
            "project_name": project_name,
            "operator": operator,
            "specimen": specimen,
            "age_days": age_days
        }
        
        save_to_db(db, results, metadata, file.filename, current_user)
        
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
    project_id: int = Form(None),
    project_name: str = Form(""),
    operator: str = Form(""),
    apply_smoothing: str = Form("false"),
    e_start: int = Form(10),
    e_end: int = Form(40),
    age_days: int = Form(None),
    target_fc: float = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
                    results = analyze_data(df, smoothing, e_start, e_end, age_days, target_fc)
                    
                    specimen_name = os.path.splitext(file.filename)[0]
                    metadata = {
                        "project_id": project_id,
                        "project_name": project_name, 
                        "operator": operator, 
                        "specimen": specimen_name,
                        "age_days": age_days
                    }
                    
                    save_to_db(db, results, metadata, file.filename, current_user)
                    
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
                        "Ténacité": results.get("toughness"),
                        "Anomalie": "Oui" if results.get("anomaly_flag") else "Non",
                        "Conformité": results.get("compliance_status") or "-"
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
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = db.query(TestRecord).filter(TestRecord.user_id == current_user.id).order_by(TestRecord.id.desc()).limit(50).all()
    return records
