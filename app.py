from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import status
import pandas as pd
from io import StringIO
import re
from pypdf import PdfReader

# Importar todas as funções do "cérebro" aqui
from sped_core import parse_efd, resumo_bloco_c, resumo_bloco_g, resumo_bloco_e, processar_livro_fiscal_pdf, comparar_com_livro

app = FastAPI(title="API de Processamento SPED")

#  CONFIGURAÇÃO DE CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Simplificado para desenvolvimento
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#  ROTAS DE PÁGINA 

@app.get("/", response_class=FileResponse)
async def read_login_page():
    return "login.html"

@app.post("/login")
async def handle_login(username: str = Form(), password: str = Form()):
    # Login provisório: isso virará de um banco de dados seguro.
    if username == "admin" and password == "admin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/dashboard", response_class=FileResponse)
async def read_dashboard_page():
    return "dashboard.html"


#  ROTAS DA API (para os dados) 

@app.post("/processar_sped/")
async def processar_sped(file: UploadFile = File(...)):
    content = await file.read()
    decoded = content.decode("latin-1")
    file_like = StringIO(decoded)
    blocos = parse_efd(file_like)
    resumo_c = resumo_bloco_c(blocos["C"])
    resumo_g = resumo_bloco_g(blocos["G"])
    resumo_e = resumo_bloco_e(blocos["E"])
    return {
        "resumo_c": resumo_c,
        "resumo_g": resumo_g.to_dict(orient="records"),
        "resumo_e": {
            "periodos": resumo_e["periodos"].to_dict(orient="records"),
            "apuracoes": resumo_e["apuracoes"].to_dict(orient="records"),
            "obrigacoes": resumo_e["obrigacoes"].to_dict(orient="records"),
        }
    }

@app.post("/comparar/")
async def comparar(sped_file: UploadFile = File(...), livro_file: UploadFile = File(...)):
    sped_content = await sped_file.read()
    decoded = sped_content.decode("latin-1")
    blocos = parse_efd(StringIO(decoded))
    resumo_c = resumo_bloco_c(blocos["C"])
    path_livro = f"temp_{livro_file.filename}"
    with open(path_livro, "wb") as f:
        f.write(await livro_file.read())
    df_livro = processar_livro_fiscal_pdf(path_livro)
    df_livro.set_index("operacao", inplace=True)
    comparacao, divergencias = comparar_com_livro(resumo_c, df_livro)
    return {"comparacao": comparacao, "divergencias": divergencias}
