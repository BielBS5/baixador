import streamlit as st
import yt_dlp
import os
import re
import pandas as pd
import threading
from pathlib import Path

# ─────────────────────────────────────────
#  CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Rádio Hub",
    page_icon="📻",
    layout="wide",
)

# ─────────────────────────────────────────
#  CSS PERSONALIZADO (Visual Minimalista)
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
    .stApp { background: #f7f4f0; color: #1a1a1a; }
    .radio-header {
        background: linear-gradient(135deg, #fff8f2 0%, #ffe8d0 100%);
        border: 1.5px solid #e05a00;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
    }
    .radio-title { font-size: 2rem; font-weight: 800; color: #e05a00; margin: 0; }
    .stButton > button { font-family: 'Syne', sans-serif !important; font-weight: 700; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  CONSTANTES E SESSION STATE
# ─────────────────────────────────────────
DOWNLOAD_DIR = str(Path.home() / "Downloads")

if 'fila' not in st.session_state:
    st.session_state.fila = []

# ─────────────────────────────────────────
#  FUNÇÕES DE AUXÍLIO (HELPERS)
# ─────────────────────────────────────────
def sanitizar_nome(nome: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def baixar_musica(termo_ou_link, titulo, qualidade='320'):
    """Faz o download via link direto ou busca no YouTube."""
    nome_arquivo = sanitizar_nome(titulo)
    
    # Se não for um link HTTP, adiciona o prefixo de busca para evitar erros
    input_final = termo_ou_link.strip()
    if not input_final.startswith('http'):
        input_final = f"ytsearch1:{input_final}"

    opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': './ffmpeg.exe',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': qualidade
        }],
        'outtmpl': f'{DOWNLOAD_DIR}/{nome_arquivo}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([input_final])
        return True
    except Exception as e:
        print(f"Erro no download: {e}")
        return False

def buscar_info_video(entrada: str) -> dict | None:
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(entrada, download=False)
            if not info: return None
            return info['entries'][0] if 'entries' in info else info
    except:
        return None

# ─────────────────────────────────────────
#  INTERFACE PRINCIPAL
# ─────────────────────────────────────────
st.markdown("""
<div class="radio-header">
    <div class="radio-title">📻 RÁDIO HUB</div>
    <div style="color: #a0795a; font-family: 'Space Mono'; font-size: 0.8rem;">SISTEMA DE DOWNLOADS // CELERON OPTIMIZED</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["🔍 Buscar", "📋 Lista Manual", "🔗 Playlist YT", "📂 Arquivo CSV"])

# --- TAB 1: BUSCAR E BAIXAR ---
with tabs[0]:
    entrada = st.text_input("O que você quer ouvir?", placeholder="Nome da música ou Link do YouTube")
    if st.button("BUSCAR MÚSICA", type="primary"):
        if entrada:
            with st.spinner("Buscando..."):
                video = buscar_info_video(entrada)
                if video:
                    st.image(video.get('thumbnail'), width=200)
                    st.write(f"**Título:** {video.get('title')}")
                    if st.button("CONFIRMAR E BAIXAR"):
                        if baixar_musica(video.get('webpage_url'), video.get('title')):
                            st.success("Download Concluído!")
                else:
                    st.error("Não encontrei nada.")

# --- TAB 2: LISTA MANUAL ---
with tabs[1]:
    lista_texto = st.text_area("Cole aqui vários nomes ou links (um por linha):", height=150)
    if st.button("BAIXAR LISTA INTEIRA"):
        linhas = [l.strip() for l in lista_texto.split('\n') if l.strip()]
        prog = st.progress(0)
        for i, linha in enumerate(linhas):
            st.write(f"📥 Baixando: {linha}")
            baixar_musica(linha, linha)
            prog.progress((i + 1) / len(linhas))
        st.success("Toda a lista foi processada!")

# --- TAB 3: PLAYLIST ---
with tabs[2]:
    url_pl = st.text_input("Link da Playlist do YouTube:")
    if st.button("BAIXAR PLAYLIST COMPLETA"):
        if url_pl:
            with st.spinner("Isso pode demorar um pouco..."):
                opts_pl = {
                    'format': 'bestaudio/best',
                    'ffmpeg_location': './ffmpeg.exe',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
                    'outtmpl': f'{DOWNLOAD_DIR}/%(playlist_title)s/%(title)s.%(ext)s',
                }
                with yt_dlp.YoutubeDL(opts_pl) as ydl:
                    ydl.download([url_pl])
                st.success("Playlist salva na pasta Downloads!")

# --- TAB 4: ARQUIVO CSV (Exportify) ---
with tabs[3]:
    st.markdown("### 📂 Importar do Exportify / Spotify")
    arq_csv = st.file_uploader("Arraste seu arquivo .csv aqui", type=["csv"])
    
    if arq_csv:
        try:
            df = pd.read_csv(arq_csv)
            st.info(f"Encontrei {len(df)} músicas no arquivo.")
            
            if st.button("🚀 INICIAR DOWNLOAD DO CSV"):
                barra = st.progress(0)
                status = st.empty()
                
                for i, row in df.iterrows():
                    # Extração inteligente de colunas (Exportify usa Track URL e Track Name)
                    link = str(row.get('Track URL', '')).strip()
                    nome = str(row.get('Track Name', '')).strip()
                    artista = str(row.get('Artist Name(s)', '')).strip()
                    
                    # Define o que será usado para baixar
                    # Se tiver link, usa o link. Se não, busca por "Artista - Música"
                    if link.startswith('http'):
                        alvo = link
                    else:
                        alvo = f"{artista} {nome}"
                    
                    nome_limpo = f"{artista} - {nome}" if artista else nome
                    
                    status.caption(f"📥 Baixando ({i+1}/{len(df)}): {nome_limpo}")
                    baixar_musica(alvo, nome_limpo)
                    barra.progress((i + 1) / len(df))
                
                status.empty()
                st.success("✅ Arquivo CSV processado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")

st.divider()
st.caption(f"📁 Os arquivos serão salvos em: {DOWNLOAD_DIR}")
