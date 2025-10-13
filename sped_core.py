import pandas as pd
import re
from pypdf import PdfReader

# --- CONSTANTES E REGRAS FISCAIS ---
C100_IND_OPER = 1; C100_NUM_DOC = 8; C100_CHV_NFE = 9; C100_DT_DOC = 10; C100_VL_DOC = 11
C190_CST_ICMS = 2; C190_CFOP = 3; C190_VL_OPR = 4; C190_VL_BC_ICMS = 5; C190_VL_ICMS = 6
G125_COD_IND_BEM = 2; G125_DT_MOV = 3; G125_VL_ICMS_OP = 5; G125_VL_ICMS_ST = 6; G125_VL_ICMS_FRT = 7
E100_DT_INI = 1; E100_DT_FIN = 2; E110_VL_TOT_DEBITOS = 2; E110_VL_TOT_CREDITOS = 4
E110_VL_SLD_APURADO = 7; E110_VL_ICMS_RECOLHER = 9; E116_COD_OR = 1; E116_VL_OR = 2
E116_DT_VCTO = 3; E116_COD_REC = 4
CFOPS_OUTRAS = {
    '1905','1908','1909','1910','1911','1912','1913','1914','1915','1916','1917','1918','1919','1920','1921','1922','1923','1924','1925','1926','1949','2905','2908','2909','2910','2911','2912','2913','2914','2915','2916','2917','2918','2919','2920','2921','2922','2923','2924','2925','2949','5905','5908','5909','5910','5911','5912','5913','5914','5915','5916','5917','5918','5919','5920','5921','5922','5923','5924','5925','5926','5949','6905','6908','6909','6910','6911','6912','6913','6914','6915','6916','6917','6918','6919','6920','6921','6922','6923','6924','6925','6949'
}
CSTS_TRIBUTADOS = {'00', '10', '20', '51', '70', '90'}
CSTS_ISENTOS_NT = {'40', '41', '50'}

def parse_efd(file_like):
    blocos = {"C": [], "G": [], "E": []}
    for line in file_like:
        line = line.strip()
        if not line: continue
        parts = [p for p in line.split("|") if p]
        if not parts: continue
        reg = parts[0]
        if reg.startswith("C"): blocos["C"].append(parts)
        elif reg.startswith("G"): blocos["G"].append(parts)
        elif reg.startswith("E"): blocos["E"].append(parts)
    return blocos

def resumo_bloco_c(registros):
    documentos = []
    c100_atual = None

    for r in registros:
        if r[0] == "C100":
            try:
                c100_atual = {
                    "operacao": "ENTRADA" if r[C100_IND_OPER] == '0' else "SAÍDA",
                    "ind_oper": r[C100_IND_OPER],
                    "doc": r[C100_NUM_DOC],
                    "chave_nfe": r[C100_CHV_NFE],
                    "data": r[C100_DT_DOC],
                    "valor_contabil": float(r[C100_VL_DOC].replace(",", ".")),
                    "base_icms": 0.0,
                    "valor_icms": 0.0,
                    "isentas_nt": 0.0,
                    "outras": 0.0,
                    "itens": []
                }
                documentos.append(c100_atual)
            except (ValueError, IndexError):
                c100_atual = None
                continue
        elif r[0] == "C190" and c100_atual:
            try:
                cfop = r[C190_CFOP]; cst = r[C190_CST_ICMS][-2:]
                vl_opr = float(r[C190_VL_OPR].replace(",", ".")) if len(r) > C190_VL_OPR and r[C190_VL_OPR] else 0
                vl_bc_icms = float(r[C190_VL_BC_ICMS].replace(",", ".")) if len(r) > C190_VL_BC_ICMS and r[C190_VL_BC_ICMS] else 0
                vl_icms = float(r[C190_VL_ICMS].replace(",", ".")) if len(r) > C190_VL_ICMS and r[C190_VL_ICMS] else 0
                
                item_detalhe = {"cfop": cfop, "cst": cst, "valor_operacao": vl_opr, "base_icms": vl_bc_icms, "valor_icms": vl_icms}
                c100_atual["itens"].append(item_detalhe)

                if cfop in CFOPS_OUTRAS: c100_atual["outras"] += vl_opr
                elif cst in CSTS_TRIBUTADOS:
                    c100_atual["base_icms"] += vl_bc_icms
                    c100_atual["valor_icms"] += vl_icms
                elif cst in CSTS_ISENTOS_NT: c100_atual["isentas_nt"] += vl_opr
                else: c100_atual["outras"] += vl_opr
            except (ValueError, IndexError): continue

    if not documentos:
        return {"resumo": None, "detalhes": []}

    for doc in documentos:
        soma_itens_opr = sum(item.get("valor_operacao", 0.0) for item in doc.get("itens", []))
        residual = round(doc.get("valor_contabil", 0.0) - soma_itens_opr, 2)
        doc["soma_itens"] = soma_itens_opr
        doc["ajustes"] = residual

    df_docs = pd.DataFrame(documentos)
    
    resumo = {}
    for tipo_op, nome_op in [("0", "Entradas"), ("1", "Saídas")]:
        if not df_docs.empty and "ind_oper" in df_docs.columns:
            df_filtro = df_docs[df_docs["ind_oper"] == tipo_op]
            resumo[nome_op] = {
                "qtd_docs": int(len(df_filtro)),
                "valor_contabil": float(df_filtro["valor_contabil"].sum()),
                "base_icms": float(df_filtro["base_icms"].sum()),
                "valor_icms": float(df_filtro["valor_icms"].sum()),
                "isentas_nt": float(df_filtro["isentas_nt"].sum()),
                "outras": float(df_filtro["outras"].sum())
            }
        else:
            resumo[nome_op] = {"qtd_docs": 0, "valor_contabil": 0.0, "base_icms": 0.0, "valor_icms": 0.0, "isentas_nt": 0.0, "outras": 0.0}

    return {"resumo": resumo, "detalhes": documentos}

# --- OUTRAS FUNÇÕES (sem alterações) ---
def resumo_bloco_g(registros):
    df_g125 = []
    for r in registros:
        if r[0] == "G125":
            try: df_g125.append({ "COD_IND_BEM": r[G125_COD_IND_BEM], "DT_MOV": r[G125_DT_MOV], "VL_ICMS_OP": float(r[G125_VL_ICMS_OP].replace(",", ".")), "VL_ICMS_ST": float(r[G125_VL_ICMS_ST].replace(",", ".")), "VL_ICMS_FRT": float(r[G125_VL_ICMS_FRT].replace(",", ".")) })
            except: continue
    return pd.DataFrame(df_g125)

def resumo_bloco_e(registros):
    periodos, apuracoes, obrigacoes = [], [], []
    for r in registros:
        try:
            if r[0] == "E100": periodos.append({"DT_INI": r[E100_DT_INI], "DT_FIN": r[E100_DT_FIN]})
            elif r[0] == "E110": apuracoes.append({ "VL_TOT_DEBITOS": float(r[E110_VL_TOT_DEBITOS].replace(",", ".")), "VL_TOT_CREDITOS": float(r[E110_VL_TOT_CREDITOS].replace(",", ".")), "VL_SLD_APURADO": float(r[E110_VL_SLD_APURADO].replace(",", ".")), "VL_ICMS_RECOLHER": float(r[E110_VL_ICMS_RECOLHER].replace(",", ".")) })
            elif r[0] == "E116": obrigacoes.append({ "COD_OR": r[E116_COD_OR], "VL_OR": float(r[E116_VL_OR].replace(",", ".")), "DT_VCTO": r[E116_DT_VCTO], "COD_REC": r[E116_COD_REC] })
        except: continue
    return {"periodos": pd.DataFrame(periodos), "apuracoes": pd.DataFrame(apuracoes), "obrigacoes": pd.DataFrame(obrigacoes)}

def comparar_com_livro(res_c, df_livro):
    dados_comparacao = []
    divergencias_encontradas = False
    metricas_map = {"Valor Contábil": "valor_contabil", "Base ICMS (Trib.)": "base_icms", "Valor ICMS (Trib.)": "valor_icms", "Isentas/NT": "isentas_nt", "Outras": "outras"}
    for tipo_op in ["Entradas", "Saídas"]:
        for nome_metrica, chave_metrica in metricas_map.items():
            valor_sped = res_c.get('resumo',{}).get(tipo_op, {}).get(chave_metrica, 0)
            try: valor_livro = df_livro.loc[tipo_op, nome_metrica]
            except KeyError: valor_livro = 0
            diferenca = valor_sped - valor_livro
            dados_comparacao.append({"metrica": nome_metrica, "tipo": tipo_op, "sped": valor_sped, "livro": valor_livro, "diff": diferenca})
            if abs(diferenca) > 0.01: divergencias_encontradas = True
    return dados_comparacao, divergencias_encontradas

def parse_number(s): return float(s.replace('.', '').replace(',', '.'))

def processar_livro_fiscal_pdf(path: str) -> pd.DataFrame:
    reader = PdfReader(path)
    text_entradas, text_saidas = "", ""
    for page in reader.pages:
        text = page.extract_text()
        if "ENTRADAS" in text and "Subtotais Entradas" in text: text_entradas = text
        if "SAÍDAS" in text and "Subtotais Saídas" in text: text_saidas = text
    if not text_entradas or not text_saidas: raise ValueError("Não foi possível encontrar as tabelas de totais no PDF.")
    regex = r"Totais\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
    match_entradas = re.search(regex, text_entradas.replace('\n', ' '))
    match_saidas = re.search(regex, text_saidas.replace('\n', ' '))
    entradas_vals = [parse_number(v) for v in match_entradas.groups()]
    saidas_vals = [parse_number(v) for v in match_saidas.groups()]
    data = {'operacao': ['Entradas', 'Saídas'], 'valor_contabil': [entradas_vals[0], saidas_vals[0]], 'base_icms': [entradas_vals[1], saidas_vals[1]], 'valor_icms': [entradas_vals[2], saidas_vals[2]], 'isentas_nt': [entradas_vals[3], saidas_vals[3]], 'outras': [entradas_vals[4], saidas_vals[4]],}
    return pd.DataFrame(data)