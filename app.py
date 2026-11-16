from datetime import datetime
from io import BytesIO
import uuid
from google.oauth2.service_account import Credentials
import gspread
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gerador de PGRS Pro", page_icon="♻️", layout="wide"
)


# --- CONEXÃO COM GOOGLE SHEETS ---
@st.cache_resource
def conectar_planilha():
  scopes = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive",
  ]
  credentials = Credentials.from_service_account_info(
      st.secrets["gcp_service_account"], scopes=scopes
  )
  gc = gspread.authorize(credentials)
  return gc.open("Banco_Dados_PGRS")


def salvar_pgrs_no_sheets(dados):
  planilha = conectar_planilha()
  aba_empresas = planilha.worksheet("Empresas_PGRS")
  aba_residuos = planilha.worksheet("Inventario_Residuos")

  id_registro = str(uuid.uuid4())[:8].upper()
  data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

  # 1. Salva dados gerais na aba Empresas_PGRS
  linha_empresa = [
      id_registro,
      data_atual,
      dados["razao_social"],
      dados["nome_fantasia"],
      dados["cnpj"],
      dados["cnae"],
      dados["endereco"],
      dados["coordenadas"],
      dados["responsavel_legal"],
      dados["rt_nome"],
      dados["rt_formacao"],
      dados["rt_registro"],
      dados["rt_art"],
      dados["num_funcionarios"],
      dados["descricao_atividade"],
      dados["armazenamento_local"],
      dados["acoes_minimizacao"],
      dados["plano_emergencia"],
  ]
  aba_empresas.append_row(linha_empresa)

  # 2. Salva lista de resíduos na aba Inventario_Residuos
  linhas_residuos = []
  for r in dados["residuos"]:
    linhas_residuos.append([
        id_registro,
        dados["cnpj"],
        r["nome"],
        r["classe"],
        r["estado"],
        r["setor"],
        r["qtd"],
        r["acondicionamento"],
        r["destinacao"],
        r["transportador"],
        r["destinador"],
    ])

  if linhas_residuos:
    aba_residuos.append_rows(linhas_residuos)

  return id_registro


# --- MOTOR DE GERAÇÃO DO PDF (REPORTLAB) ---
def gerar_pdf_pgrs(dados, protocolo):
  buffer = BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=A4,
      rightMargin=45,
      leftMargin=45,
      topMargin=50,
      bottomMargin=50,
  )

  story = []
  styles = getSampleStyleSheet()

  # Estilos personalizados
  titulo_style = ParagraphStyle(
      "TituloDoc",
      parent=styles["Heading1"],
      fontName="Helvetica-Bold",
      fontSize=16,
      leading=20,
      textColor=colors.HexColor("#1b4332"),
      alignment=1,
      spaceAfter=10,
  )
  subtitulo_capa = ParagraphStyle(
      "SubCapa",
      parent=styles["Normal"],
      fontName="Helvetica",
      fontSize=10,
      leading=14,
      textColor=colors.HexColor("#495057"),
      alignment=1,
      spaceAfter=20,
  )
  h2_style = ParagraphStyle(
      "SecaoH2",
      parent=styles["Heading2"],
      fontName="Helvetica-Bold",
      fontSize=12,
      leading=16,
      textColor=colors.HexColor("#2d6a4f"),
      spaceBefore=14,
      spaceAfter=6,
  )
  body_style = ParagraphStyle(
      "CorpoTexto",
      parent=styles["Normal"],
      fontName="Helvetica",
      fontSize=9.5,
      leading=13,
      textColor=colors.HexColor("#212529"),
      spaceAfter=6,
  )
  th_style = ParagraphStyle(
      "CabecalhoTabela",
      parent=styles["Normal"],
      fontName="Helvetica-Bold",
      fontSize=8.5,
      leading=11,
      textColor=colors.white,
  )

  # Cabeçalho do Documento
  story.append(
      Paragraph(
          "PLANO DE GERENCIAMENTO DE RESÍDUOS SÓLIDOS (PGRS)", titulo_style
      )
  )
  story.append(
      Paragraph(
          f"Elaborado em conformidade com a Lei Federal nº 12.305/2010 e ABNT NBR 10.004<br/>Protocolo de Registro: <b>{protocolo}</b> | Data: {datetime.now().strftime('%d/%m/%Y')}",
          subtitulo_capa,
      )
  )

  # 1. IDENTIFICAÇÃO DO GERADOR
  story.append(Paragraph("1. IDENTIFICAÇÃO DO EMPREENDIMENTO", h2_style))
  dados_emp = [
      [
          Paragraph("<b>Razão Social:</b>", body_style),
          Paragraph(dados["razao_social"], body_style),
      ],
      [
          Paragraph("<b>Nome Fantasia:</b>", body_style),
          Paragraph(dados["nome_fantasia"], body_style),
      ],
      [
          Paragraph("<b>CNPJ:</b>", body_style),
          Paragraph(dados["cnpj"], body_style),
      ],
      [
          Paragraph("<b>CNAE Principal:</b>", body_style),
          Paragraph(dados["cnae"], body_style),
      ],
      [
          Paragraph("<b>Endereço:</b>", body_style),
          Paragraph(dados["endereco"], body_style),
      ],
      [
          Paragraph("<b>Coordenadas / Bacia:</b>", body_style),
          Paragraph(dados["coordenadas"], body_style),
      ],
      [
          Paragraph("<b>Responsável Legal:</b>", body_style),
          Paragraph(dados["responsavel_legal"], body_style),
      ],
  ]
  t_emp = Table(dados_emp, colWidths=[140, 365])
  t_emp.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ])
  )
  story.append(t_emp)

  # 2. CARACTERIZAÇÃO DA ATIVIDADE
  story.append(
      Paragraph("2. CARACTERIZAÇÃO DA ATIVIDADE E PROCESSOS", h2_style)
  )
  story.append(
      Paragraph(
          f"<b>População Fixa / Flutuante:</b> {dados['num_funcionarios']}",
          body_style,
      )
  )
  story.append(
      Paragraph(
          f"<b>Descrição Operacional e Fluxograma:</b><br/>{dados['descricao_atividade'].replace(chr(10), '<br/>')}",
          body_style,
      )
  )

  # 3. INVENTÁRIO E CLASSIFICAÇÃO DE RESÍDUOS
  story.append(
      Paragraph("3. INVENTÁRIO E CLASSIFICAÇÃO DE RESÍDUOS", h2_style)
  )
  tabela_res = [[
      Paragraph("Resíduo", th_style),
      Paragraph("Classe NBR 10.004", th_style),
      Paragraph("Estado / Setor", th_style),
      Paragraph("Qtd/Mês", th_style),
      Paragraph("Acondicionamento", th_style),
  ]]
  for r in dados["residuos"]:
    tabela_res.append([
        Paragraph(r["nome"], body_style),
        Paragraph(r["classe"], body_style),
        Paragraph(f"{r['estado']} ({r['setor']})", body_style),
        Paragraph(r["qtd"], body_style),
        Paragraph(r["acondicionamento"], body_style),
    ])

  t_res = Table(tabela_res, colWidths=[110, 115, 100, 70, 110])
  t_res.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ])
  )
  story.append(t_res)

  # 4. ARMAZENAMENTO TEMPORÁRIO
  story.append(
      Paragraph("4. ACONDICIONAMENTO E ARMAZENAMENTO TEMPORÁRIO", h2_style)
  )
  story.append(
      Paragraph(
          dados["armazenamento_local"].replace(chr(10), "<br/>"), body_style
      )
  )

  # 5. MINIMIZAÇÃO E EDUCAÇÃO AMBIENTAL
  story.append(
      Paragraph("5. AÇÕES DE MINIMIZAÇÃO, METAS E EDUCAÇÃO AMBIENTAL", h2_style)
  )
  story.append(
      Paragraph(
          dados["acoes_minimizacao"].replace(chr(10), "<br/>"), body_style
      )
  )

  # 6. DESTINAÇÃO FINAL E LOGÍSTICA (MTR / CDF)
  story.append(
      Paragraph(
          "6. TRATAMENTO, DESTINAÇÃO FINAL E CONTROLE (MTR/CDF)", h2_style
      )
  )
  tabela_dest = [[
      Paragraph("Resíduo", th_style),
      Paragraph("Forma de Destinação", th_style),
      Paragraph("Transportador (Licença)", th_style),
      Paragraph("Destinador Final (Licença)", th_style),
  ]]
  for r in dados["residuos"]:
    tabela_dest.append([
        Paragraph(r["nome"], body_style),
        Paragraph(r["destinacao"], body_style),
        Paragraph(r["transportador"], body_style),
        Paragraph(r["destinador"], body_style),
    ])

  t_dest = Table(tabela_dest, colWidths=[110, 115, 140, 140])
  t_dest.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ])
  )
  story.append(t_dest)
  story.append(Spacer(1, 6))
  story.append(
      Paragraph(
          "<i>Nota de Rastreabilidade: Todas as movimentações de resíduos são acompanhadas por Manifesto de Transporte de Resíduos (MTR) via sistema SINIR/SIGOR e comprovadas mediante Certificado de Destinação Final (CDF).</i>",
          body_style,
      )
  )

  # 7. EMERGÊNCIA E CONTINGÊNCIA
  story.append(
      Paragraph(
          "7. PROCEDIMENTOS DE EMERGÊNCIA, CONTINGÊNCIA E EPIs", h2_style
      )
  )
  story.append(
      Paragraph(dados["plano_emergencia"].replace(chr(10), "<br/>"), body_style)
  )

  # 8. RESPONSABILIDADE TÉCNICA E ASSINATURAS
  story.append(
      Paragraph("8. RESPONSABILIDADE TÉCNICA E ASSINATURAS", h2_style)
  )
  dados_rt = [
      [
          Paragraph("<b>Responsável Técnico:</b>", body_style),
          Paragraph(dados["rt_nome"], body_style),
      ],
      [
          Paragraph("<b>Formação / Conselho:</b>", body_style),
          Paragraph(
              f"{dados['rt_formacao']} - {dados['rt_registro']}", body_style
          ),
      ],
      [
          Paragraph("<b>Número da ART:</b>", body_style),
          Paragraph(dados["rt_art"], body_style),
      ],
  ]
  t_rt = Table(dados_rt, colWidths=[140, 365])
  t_rt.setStyle(
      TableStyle([
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ])
  )
  story.append(t_rt)
  story.append(Spacer(1, 35))

  # Campos de assinatura
  assinaturas = [[
      Paragraph(
          f"________________________________________<br/><b>{dados['responsavel_legal']}</b><br/>Responsável Legal",
          body_style,
      ),
      Paragraph(
          f"________________________________________<br/><b>{dados['rt_nome']}</b><br/>Responsável Técnico ({dados['rt_registro']})",
          body_style,
      ),
  ]]
  t_ass = Table(assinaturas, colWidths=[250, 250])
  story.append(t_ass)

  doc.build(story)
  buffer.seek(0)
  return buffer


# --- INTERFACE DO USUÁRIO (STREAMLIT) ---
st.title("♻️ Sistema Elaborador de PGRS")
st.markdown(
    "Preencha todas as etapas abaixo. Ao final, clique em **Gerar PGRS** para registrar os dados na planilha e baixar o documento oficial em PDF."
)

abas = st.tabs([
    "1. Empresa & RT",
    "2. Atividades",
    "3. Inventário & Destinação",
    "4. Armazenamento & Emergência",
])

with abas[0]:
  st.subheader("Dados Cadastrais do Gerador")
  c1, c2 = st.columns(2)
  with c1:
    razao_social = st.text_input("Razão Social *")
    nome_fantasia = st.text_input("Nome Fantasia")
    cnpj = st.text_input("CNPJ *", placeholder="00.000.000/0001-00")
    cnae = st.text_input("CNAE Principal *")
  with c2:
    endereco = st.text_input("Endereço Completo *")
    coordenadas = st.text_input(
        "Coordenadas Geográficas / Bacia Hidrográfica",
        placeholder="Ex: -23.9931, -46.2564 | Bacia Baixada Santista",
    )
    responsavel_legal = st.text_input("Nome e Cargo do Responsável Legal *")

  st.markdown("---")
  st.subheader("Responsável Técnico pela Elaboração")
  c3, c4 = st.columns(2)
  with c3:
    rt_nome = st.text_input("Nome Completo do RT *")
    rt_formacao = st.text_input(
        "Formação Profissional", placeholder="Ex: Engenheiro Ambiental"
    )
  with c4:
    rt_registro = st.text_input(
        "Conselho de Classe e Registro *", placeholder="Ex: CREA-SP 50600000/D"
    )
    rt_art = st.text_input("Número da ART *")

with abas[1]:
  st.subheader("Caracterização Operacional")
  num_funcionarios = st.text_input(
      "Efetivo de Pessoal (Fixos e Flutuantes)",
      placeholder="Ex: 120 colaboradores fixos e média de 300 visitantes/dia",
  )
  descricao_atividade = st.text_area(
      "Descrição Detalhada das Atividades e Fluxograma de Processos *",
      height=180,
      placeholder="Descreva os setores (ex: manutenção, oficinas, restaurante, administração) e como os insumos entram e geram resíduos...",
  )

with abas[2]:
  st.subheader("Inventário de Resíduos e Destinação Final")
  st.info(
      "Cadastre cada tipo de resíduo gerado, sua classificação NBR 10.004 e os dados do transportador e destinador final."
  )

  qtd_itens = st.number_input(
      "Quantidade de tipos de resíduos a cadastrar:",
      min_value=1,
      max_value=25,
      value=2,
  )
  lista_residuos = []

  for i in range(int(qtd_itens)):
    with st.expander(f"Resíduo #{i+1}", expanded=True):
      col_a, col_b, col_c = st.columns(3)
      with col_a:
        r_nome = st.text_input(
            "Nome / Descrição do Resíduo *",
            key=f"r_nome_{i}",
            placeholder="Ex: Óleo lubrificante usado (OLUC)",
        )
        r_classe = st.selectbox(
            "Classificação (NBR 10.004)",
            [
                "Classe I - Perigoso",
                "Classe II A - Não Inerte",
                "Classe II B - Inerte",
            ],
            key=f"r_classe_{i}",
        )
      with col_b:
        r_estado = st.selectbox(
            "Estado Físico",
            ["Sólido", "Líquido", "Pastoso", "Gasoso"],
            key=f"r_estado_{i}",
        )
        r_setor = st.text_input(
            "Setor Gerador",
            key=f"r_setor_{i}",
            placeholder="Ex: Oficina Mecânica",
        )
      with col_c:
        r_qtd = st.text_input(
            "Geração Média Mensal", key=f"r_qtd_{i}", placeholder="Ex: 50 litros/mês"
        )
        r_acond = st.text_input(
            "Acondicionamento",
            key=f"r_acond_{i}",
            placeholder="Ex: Tambor metálico 200L com contenção",
        )

      col_d, col_e, col_f = st.columns(3)
      with col_d:
        r_dest = st.selectbox(
            "Tratamento / Destinação Final",
            [
                "Reciclagem",
                "Rerrefino",
                "Compostagem",
                "Coprocessamento",
                "Incineração",
                "Aterro Industrial (Classe I)",
                "Aterro Sanitário (Classe II)",
            ],
            key=f"r_dest_{i}",
        )
      with col_e:
        r_transp = st.text_input(
            "Empresa Transportadora + Licença",
            key=f"r_transp_{i}",
            placeholder="Ex: TransResíduos Ltda (LO CETESB 1234)",
        )
      with col_f:
        r_destinador = st.text_input(
            "Empresa Destinadora Final + Licença",
            key=f"r_destinador_{i}",
            placeholder="Ex: EcoDestino S/A (LO 5678)",
        )

      lista_residuos.append({
          "nome": r_nome,
          "classe": r_classe,
          "estado": r_estado,
          "setor": r_setor,
          "qtd": r_qtd,
          "acondicionamento": r_acond,
          "destinacao": r_dest,
          "transportador": r_transp,
          "destinador": r_destinador,
      })

with abas[3]:
  st.subheader("Armazenamento, Minimização e Contingência")
  armazenamento_local = st.text_area(
      "Características do Abrigo Temporário de Resíduos *",
      height=100,
      value="Área coberta, piso impermeabilizado em concreto, ventilação natural, bacia de contenção para líquidos inflamáveis/perigosos, sinalização de segurança conforme NBR 7500 e acesso restrito a pessoal autorizado.",
  )
  acoes_minimizacao = st.text_area(
      "Ações de Redução na Fonte, Reutilização e Educação Ambiental *",
      height=100,
      value="1. Segregação na fonte com coletores identificados por padrão de cores (CONAMA 275/01).\n2. Treinamento semestral de integração e reciclagem para colaboradores.\n3. Priorização de compras com logística reversa de embalagens.",
  )
  plano_emergencia = st.text_area(
      "Procedimentos de Emergência, Contingência e EPIs *",
      height=100,
      value="Em caso de vazamento de resíduos perigosos: isolar a área, utilizar kit de mitigação ambiental (mantas absorventes e serragem), acionar brigada interna e destinar o material contaminado como resíduo Classe I. Uso obrigatório de luvas nitrílicas, óculos de proteção e calçado de segurança.",
  )

# --- BOTÃO FINAL DE GERAÇÃO ---
st.markdown("---")
if st.button("🚀 Gerar PGRS", type="primary", use_container_width=True):
  # Verifica individualmente o que está vazio (usando .strip() para evitar espaços)
  campos_faltantes = []
  if not razao_social.strip():
    campos_faltantes.append("Razão Social (Aba 1)")
  if not cnpj.strip():
    campos_faltantes.append("CNPJ (Aba 1)")
  if not rt_nome.strip():
    campos_faltantes.append("Nome do Responsável Técnico (Aba 1)")
  if not lista_residuos or not lista_residuos[0]["nome"].strip():
    campos_faltantes.append("Nome do Resíduo #1 (Aba 3)")

  if campos_faltantes:
    st.error(
        f"⚠️ O sistema identificou os seguintes campos obrigatórios vazios: **{', '.join(campos_faltantes)}**.\n\n*Dica: Após digitar no último campo de uma aba, clique fora da caixa de texto antes de mudar de aba ou clicar em Gerar.*"
    )
  else:
    dados_completos = {
        "razao_social": razao_social.strip(),
        "nome_fantasia": nome_fantasia.strip(),
        "cnpj": cnpj.strip(),
        "cnae": cnae.strip(),
        "endereco": endereco.strip(),
        "coordenadas": coordenadas.strip(),
        "responsavel_legal": responsavel_legal.strip(),
        "rt_nome": rt_nome.strip(),
        "rt_formacao": rt_formacao.strip(),
        "rt_registro": rt_registro.strip(),
        "rt_art": rt_art.strip(),
        "num_funcionarios": num_funcionarios.strip(),
        "descricao_atividade": descricao_atividade.strip(),
        "residuos": lista_residuos,
        "armazenamento_local": armazenamento_local.strip(),
        "acoes_minimizacao": acoes_minimizacao.strip(),
        "plano_emergencia": plano_emergencia.strip(),
    }

    try:
      with st.spinner(
          "Gravando dados no Google Sheets e gerando o PDF do PGRS..."
      ):
        protocolo_gerado = salvar_pgrs_no_sheets(dados_completos)
        pdf_final = gerar_pdf_pgrs(dados_completos, protocolo_gerado)

      st.success(
          f"✅ PGRS gerado e registrado com sucesso! Protocolo: **{protocolo_gerado}**"
      )

      nome_arquivo = f"PGRS_{razao_social.strip().replace(' ', '_')}_{protocolo_gerado}.pdf"
      st.download_button(
          label="📥 Baixar Documento PGRS (.PDF)",
          data=pdf_final,
          file_name=nome_arquivo,
          mime="application/pdf",
          use_container_width=True,
      )
    except Exception as e:
      st.error(f"Ocorreu um erro ao conectar com o Google Sheets: {e}")
