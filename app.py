import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
import json
from io import BytesIO

st.set_page_config(page_title="Rádio Hub Premium", page_icon="📻", layout="wide")

TEMP_DIR = "temp_radio"
LISTA_SALVA = "fila_radio.json"

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

# --- INICIALIZAÇÃO DE MEMÓRIA (ESTADO) ---
if 'fila_nuvem' not in st.session_state:
    if os.path.exists(LISTA_SALVA):
        with open(LISTA_SALVA, "r") as f: st.session_state.fila_nuvem = json.load(f)
    else: st.session_state.fila_nuvem = []

# Mantém o texto do lote e busca salvos para não sumir ao clicar
if 'texto_lote' not in st.session_state: st.session_state.texto_lote = ""
if 'busca_termo' not in st.session_state: st.session_state.busca_termo = ""

def salvar_fila():
    with open(LISTA_SALVA, "w") as f: json.dump(st.session_state.fila_nuvem, f)

# --- MODAL MODO JOCA ---
@st.dialog("Configurar Música")
def modal_confirmacao(video_info):
    st.write(f"### 🎵 {video_info.get('title')}")
    st.audio(video_info.get('url'), format="audio/mp3")
    nome_f = st.text_input("Nome do arquivo:", value=video_info.get('title'))
    if st.button("✅ ADICIONAR", use_container_width=True, type="primary"):
        st.session_state.fila_nuvem.append({'titulo': nome_f, 'link': video_info.get('webpage_url') or video_info.get('url')})
        salvar_fila()
        st.rerun()

st.title("📻 Console Rádio Hub 24h")

tab_joca, tab_lote, tab_extrair = st.tabs(["⭐ MODO JOCA", "🚀 LOTE AVANÇADO", "📋 EXTRAIR NOMES"])

# --- ABA 1: MODO JOCA ---
with tab_joca:
    # Usamos o value do session_state para o texto não sumir
    busca = st.text_input("Buscar música:", value=st.session_state.busca_termo)
    st.session_state.busca_termo = busca
    
    if st.button("🔍 PESQUISAR", use_container_width=True):
        with st.spinner("Buscando..."):
            with yt_dlp.YoutubeDL({'format':'bestaudio','quiet':True,'default_search':'ytsearch1','noplaylist':True}) as ydl:
                info = ydl.extract_info(busca, download=False)
                modal_confirmacao(info['entries'][0] if 'entries' in info else info)

    if st.session_state.fila_nuvem:
        st.divider()
        c1, c2 = st.columns([3, 1])
        c1.subheader(f"📋 Fila ({len(st.session_state.fila_nuvem)})")
        if c2.button("🗑️ LIMPAR TUDO"):
            st.session_state.fila_nuvem = []; salvar_fila(); st.rerun()

        for idx, m in enumerate(st.session_state.fila_nuvem):
            with st.container(border=True):
                col_m, col_b = st.columns([5, 1])
                col_m.write(f"🎵 {m['titulo']}")
                if col_b.button("❌", key=f"del_{idx}"):
                    st.session_state.fila_nuvem.pop(idx); salvar_fila(); st.rerun()

        if st.button("🚀 GERAR ZIP DA FILA", type="primary", use_container_width=True):
            if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR)
            pb = st.progress(0)
            st_txt = st.empty()
            for i, m in enumerate(st.session_state.fila_nuvem):
                st_txt.write(f"📥 Convertendo: {m['titulo']}")
                opts = {'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'320'}],'outtmpl':f'{TEMP_DIR}/{m["titulo"]}.%(ext)s','quiet':True}
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([m['link']])
                except: pass
                pb.progress((i+1)/len(st.session_state.fila_nuvem))
            
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for arq in os.listdir(TEMP_DIR): z.write(os.path.join(TEMP_DIR, arq), arq)
            st_txt.success("✅ Pronto!")
            st.download_button("💾 BAIXAR ZIP", buf.getvalue(), file_name="radio_joca.zip", use_container_width=True)

# --- ABA 2: LOTE AVANÇADO ---
with tab_lote:
    st.subheader("Processamento em Massa")
    # Texto salvo no session_state para não sumir ao clicar em baixar
    txt_area = st.text_area("Cole sua lista:", value=st.session_state.texto_lote, height=200)
    st.session_state.texto_lote = txt_area
    
    if st.button("🔥 BAIXAR TUDO EM ZIP", use_container_width=True):
        musicas = [l.strip() for l in txt_area.split('\n') if l.strip()]
        if musicas:
            if os.path.exists(TEMP_DIR): shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR)
            pb_l = st.progress(0)
            st_l = st.empty()
            for i, m in enumerate(musicas):
                nome_limpo = m.split('. ', 1)[-1] if '. ' in m[:5] else m
                st_l.write(f"📥 Baixando: {nome_limpo}")
                opts_l = {'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'320'}],'outtmpl':f'{TEMP_DIR}/%(title)s.%(ext)s','default_search':'ytsearch1','quiet':True}
                try:
                    with yt_dlp.YoutubeDL(opts_l) as ydl: ydl.download([nome_limpo])
                except: pass
                pb_l.progress((i+1)/len(musicas))
            
            buf_l = BytesIO()
            with zipfile.ZipFile(buf_l, "w") as z:
                for arq in os.listdir(TEMP_DIR): z.write(os.path.join(TEMP_DIR, arq), arq)
            st_l.success("✅ Lote pronto!")
            st.download_button("💾 SALVAR ZIP DO LOTE", buf_l.getvalue(), file_name="lote_radio.zip", use_container_width=True)

# --- ABA 3: EXTRAIR NOMES ---
with tab_extrair:
    st.subheader("Extrair nomes de Playlist")
    url_p = st.text_input("Link da Playlist:")
    if st.button("GERAR LISTA"):
        with st.spinner("Lendo..."):
            with yt_dlp.YoutubeDL({'extract_flat':True,'quiet':True}) as ydl:
                res = ydl.extract_info(url_p, download=False)
                nomes = "\n".join([f"{e['title']}" for e in res['entries'] if e])
                st.session_state.texto_lote = nomes # Já joga pra aba de Lote automaticamente!
                st.success("Nomes extraídos e enviados para a aba LOTE!")
                st.text_area("Resultado:", nomes, height=200)
