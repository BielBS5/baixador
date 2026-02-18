import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
import json
from io import BytesIO

st.set_page_config(page_title="Rádio Hub Console", page_icon="📻", layout="wide")

TEMP_DIR = "temp_radio"
LISTA_SALVA = "fila_radio.json"

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- FUNÇÕES DE MEMÓRIA ---
def carregar_fila():
    if os.path.exists(LISTA_SALVA):
        try:
            with open(LISTA_SALVA, "r") as f: return json.load(f)
        except: return []
    return []

def salvar_fila(fila):
    with open(LISTA_SALVA, "w") as f:
        json.dump(fila, f)

if 'fila_nuvem' not in st.session_state:
    st.session_state.fila_nuvem = carregar_fila()

# --- MODAL MODO JOCA ---
@st.dialog("Configurar Música")
def modal_confirmacao(video_info):
    st.write(f"### 🎵 {video_info.get('title')}")
    st.audio(video_info.get('url'), format="audio/mp3")
    nome_final = st.text_input("Nome do arquivo:", value=video_info.get('title'))
    if st.button("✅ SALVAR NA FILA", use_container_width=True, type="primary"):
        st.session_state.fila_nuvem.append({'titulo': nome_final, 'link': video_info.get('webpage_url') or video_info.get('url')})
        salvar_fila(st.session_state.fila_nuvem)
        st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title("📻 Console Rádio Hub 24h")

tab_joca, tab_lote, tab_extrair = st.tabs(["⭐ MODO JOCA", "🚀 LOTE AVANÇADO", "📋 EXTRAIR NOMES"])

# --- ABA 1: MODO JOCA ---
with tab_joca:
    with st.form("busca_joca", clear_on_submit=True):
        entrada = st.text_input("Buscar música ou link:")
        btn_busca = st.form_submit_button("🔍 PESQUISAR", use_container_width=True)

    if btn_busca and entrada:
        with st.spinner("Buscando..."):
            try:
                with yt_dlp.YoutubeDL({'format':'bestaudio','quiet':True,'default_search':'ytsearch1','noplaylist':True}) as ydl:
                    info = ydl.extract_info(entrada, download=False)
                    video = info['entries'][0] if 'entries' in info else info
                    modal_confirmacao(video)
            except: st.error("Erro ao buscar.")

    if st.session_state.fila_nuvem:
        st.divider()
        c_t, c_l = st.columns([3, 1])
        c_t.subheader(f"📋 Sua Lista ({len(st.session_state.fila_nuvem)})")
        if c_l.button("🗑️ LIMPAR TUDO"):
            st.session_state.fila_nuvem = []; salvar_fila([]); st.rerun()

        for idx, m in enumerate(st.session_state.fila_nuvem):
            with st.container(border=True):
                col_m, col_b = st.columns([5, 1])
                col_m.write(f"🎵 {m['titulo']}")
                if col_b.button("❌", key=f"del_{idx}"):
                    st.session_state.fila_nuvem.pop(idx); salvar_fila(st.session_state.fila_nuvem); st.rerun()

        if st.button("🚀 PREPARAR ZIP DA FILA", type="primary", use_container_width=True):
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
            st_txt.success("✅ Pacote pronto!")
            st.download_button("💾 BAIXAR ZIP DA FILA", buf.getvalue(), file_name="fila_joca.zip", mime="application/zip", use_container_width=True)

# --- ABA 2: LOTE AVANÇADO ---
with tab_lote:
    st.subheader("Processamento em Massa")
    lista_txt = st.text_area("Cole a lista (um por linha):", height=200, placeholder="Música 1\nMúsica 2\nLink do YT...")
    if st.button("🔥 PROCESSAR LOTE EM ZIP", use_container_width=True):
        musicas = [l.strip() for l in lista_txt.split('\n') if l.strip()]
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
            st.download_button("💾 BAIXAR ZIP DO LOTE", buf_l.getvalue(), file_name="lote_radio.zip", mime="application/zip", use_container_width=True)

# --- ABA 3: EXTRAIR NOMES ---
with tab_extrair:
    st.subheader("Extrair nomes de Playlist")
    url_p = st.text_input("Link da Playlist:")
    if st.button("GERAR LISTA .TXT"):
        with st.spinner("Lendo playlist..."):
            try:
                with yt_dlp.YoutubeDL({'extract_flat':True,'quiet':True}) as ydl:
                    res = ydl.extract_info(url_p, download=False)
                    txt = "\n".join([f"{e['title']}" for e in res['entries'] if e])
                    st.download_button("💾 BAIXAR NOMES.TXT", txt, file_name="lista_playlist.txt")
                    st.text_area("Prévia:", txt, height=200)
            except: st.error("Erro ao ler playlist.")
