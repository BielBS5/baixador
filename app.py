import streamlit as st
import yt_dlp
import os
import re
import json
import pandas as pd  # Adicionado para suportar CSV
from datetime import datetime
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
#  CSS PERSONALIZADO (Mantido original)
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Syne', sans-serif;
    }
    .stApp {
        background: #f7f4f0;
        color: #1a1a1a;
    }
    h1, h2, h3 {
        font-family: 'Syne', sans-serif !important;
        letter-spacing: -0.5px;
        color: #1a1a1a;
    }
    .radio-header {
        background: linear-gradient(135deg, #fff8f2 0%, #ffe8d0 100%);
        border: 1.5px solid #e05a00;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .radio-title {
        font-size: 2rem;
        font-weight: 800;
        color: #e05a00;
        margin: 0;
        line-height: 1;
    }
    .radio-subtitle {
        font-family: 'Space Mono', monospace;
        color: #a0795a;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }
    .queue-item {
        background: #ffffff;
        border: 1px solid #e8e0d8;
        border-left: 3px solid #e05a00;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        color: #1a1a1a;
    }
    .badge {
        background: #e05a00;
        color: #fff;
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 20px;
    }
    .hist-item {
        background: #ffffff;
        border: 1px solid #e8e0d8;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.35rem;
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        color: #888;
    }
    .hist-item span { color: #1a1a1a; }
    .stButton > button {
        font-family: 'Syne', sans-serif !important;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        color: #888;
    }
    .stTabs [aria-selected="true"] {
        color: #e05a00 !important;
        border-bottom-color: #e05a00 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
if 'fila' not in st.session_state:
    st.session_state.fila = []
if 'downloads_ativos' not in st.session_state:
    st.session_state.downloads_ativos = []

# ─────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────
DOWNLOAD_DIR = str(Path.home() / "Downloads")

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def sanitizar_nome(nome: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()

def extrair_url_stream(video: dict) -> str | None:
    url_direta = video.get('url')
    if url_direta:
        return url_direta
    formats = video.get('formats', [])
    audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
    if audio_formats:
        audio_formats.sort(key=lambda f: f.get('abr') or 0, reverse=True)
        return audio_formats[0].get('url')
    return None

def buscar_info_video(entrada: str) -> dict | None:
    opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True, 'default_search': 'ytsearch1', 'noplaylist': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(entrada, download=False)
        return info['entries'][0] if info and 'entries' in info else info

def baixar_musica(link: str, titulo: str, qualidade: str) -> bool:
    nome_arquivo = sanitizar_nome(titulo)
    opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': './ffmpeg.exe',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': qualidade}],
        'outtmpl': f'{DOWNLOAD_DIR}/{nome_arquivo}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])
        return True
    except Exception:
        return False

def adivinhar_artista_titulo(video: dict) -> tuple[str, str]:
    artista = video.get('artist') or video.get('creator') or ''
    titulo  = video.get('track') or ''
    if artista and titulo: return artista.strip(), titulo.strip()
    titulo_bruto = video.get('title', '')
    if ' - ' in titulo_bruto:
        partes = titulo_bruto.split(' - ', 1)
        return partes[0].strip(), partes[1].strip()
    return '', titulo_bruto.strip()

@st.dialog("🎵 Confirmar música", width="large")
def modal_confirmacao(video: dict):
    thumb = video.get('thumbnail')
    duracao = video.get('duration', 0)
    mins, secs = divmod(int(duracao or 0), 60)
    artista_inicial, titulo_inicial = adivinhar_artista_titulo(video)

    col_img, col_audio = st.columns([1, 2])
    with col_img:
        if thumb: st.image(thumb, width='stretch')
    with col_audio:
        st.markdown(f"### {video.get('title', '')}")
        st.caption(f"⏱ {mins}:{secs:02d}")
        stream_url = extrair_url_stream(video)
        if stream_url: st.audio(stream_url, format="audio/webm")

    st.divider()
    valor_padrao = f"{artista_inicial} - {titulo_inicial}" if artista_inicial else titulo_inicial
    nome_final = st.text_input("✏️ Nome do arquivo:", value=valor_padrao)
    
    col_fila, col_baixar, col_cancel = st.columns([2, 2, 1])
    if col_fila.button("➕ Adicionar na fila", width='stretch'):
        st.session_state.fila.append({'titulo': nome_final.strip(), 'link': video.get('webpage_url', ''), 'qualidade': '320'})
        st.rerun()
    if col_baixar.button("⬇️ Baixar agora", width='stretch', type="primary"):
        with st.spinner("Baixando..."):
            if baixar_musica(video.get('webpage_url', ''), nome_final.strip(), '320'):
                st.success("✅ Salvo!")
                st.rerun()
    if col_cancel.button("✖", width='stretch'): st.rerun()

# ─────────────────────────────────────────
#  THREADS & CABEÇALHO
# ─────────────────────────────────────────
_downloads_global = {}
_downloads_lock = threading.Lock()

st.markdown("""<div class="radio-header"><div><div class="radio-title">📻 RÁDIO HUB</div><div class="radio-subtitle">CONSOLE DE TRANSMISSÃO // DOWNLOAD MANAGER v2.0</div></div></div>""", unsafe_allow_html=True)

col_m1, _ = st.columns([1, 3])
col_m1.metric("🎵 Na fila", len(st.session_state.fila))

def _worker_download(dl_id, link, titulo, qualidade):
    with _downloads_lock: _downloads_global[dl_id] = {'titulo': titulo, 'status': 'baixando', 'pct': 0}
    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            with _downloads_lock: _downloads_global[dl_id]['pct'] = int((d.get('downloaded_bytes', 0) / total) * 100)
    
    opts = {'format': 'bestaudio/best', 'ffmpeg_location': './ffmpeg.exe', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': qualidade}], 'outtmpl': f'{DOWNLOAD_DIR}/{sanitizar_nome(titulo)}.%(ext)s', 'quiet': True, 'progress_hooks': [hook]}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([link])
        with _downloads_lock: _downloads_global[dl_id]['status'] = 'ok'
    except:
        with _downloads_lock: _downloads_global[dl_id]['status'] = 'erro'

def iniciar_download_paralelo(link, titulo, qualidade):
    import uuid
    dl_id = str(uuid.uuid4())[:8]
    threading.Thread(target=_worker_download, args=(dl_id, link, titulo, qualidade), daemon=True).start()
    return dl_id

# ─────────────────────────────────────────
#  TABS (Com a nova aba CSV)
# ─────────────────────────────────────────
tab_joca, tab_solo, tab_lote, tab_playlist, tab_csv = st.tabs([
    "🎵 Buscar e Baixar", "⚡ Baixar Vários", "📋 Lista Manual", "🔗 Playlist YT", "📂 Arquivo CSV"
])

# ABA 1: Buscar e Baixar
with tab_joca:
    st.markdown("### 🎵 Qual música você quer baixar?")
    entrada = st.text_input("Buscar música:", placeholder="Ex: Legião Urbana Tempo Perdido", key="in_joca", label_visibility="collapsed")
    if st.button("🔍 BUSCAR", type="primary", width='stretch'):
        video = buscar_info_video(entrada)
        if video: modal_confirmacao(video)

    if st.session_state.fila:
        st.divider()
        if st.button("🚀 BAIXAR TODA A FILA", type="primary", width='stretch'):
            for m in st.session_state.fila: baixar_musica(m['link'], m['titulo'], m['qualidade'])
            st.session_state.fila = []; st.rerun()

# ABA 2: Vários ao mesmo tempo
with tab_solo:
    st.markdown("### ⚡ Multi-Download")
    ent_s = st.text_input("Música:", key="in_solo")
    if st.button("⚡ INICIAR", type="primary"):
        v = buscar_info_video(ent_s)
        if v:
            art, tit = adivinhar_artista_titulo(v)
            dl_id = iniciar_download_paralelo(v['webpage_url'], f"{art} - {tit}" if art else tit, '320')
            if 'solo_ids' not in st.session_state: st.session_state.solo_ids = []
            st.session_state.solo_ids.append(dl_id)

    for did in st.session_state.get('solo_ids', []):
        with _downloads_lock: info = _downloads_global.get(did)
        if info:
            st.write(f"**{info['titulo']}** - {info['status']} ({info.get('pct', 0)}%)")
            st.progress(info.get('pct', 0) / 100)

# ABA 3: Lista Manual
with tab_lote:
    lista_texto = st.text_area("Uma música por linha:", height=150)
    if st.button("⬇️ BAIXAR TUDO", type="primary"):
        for l in lista_texto.split('\n'):
            if l.strip(): baixar_musica(l.strip(), l.strip(), '320')

# ABA 4: Playlist
with tab_playlist:
    url_pl = st.text_input("Link da Playlist:")
    if st.button("⬇️ BAIXAR PLAYLIST", type="primary"):
        opts = {'format': 'bestaudio/best', 'ffmpeg_location': './ffmpeg.exe', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}], 'outtmpl': f'{DOWNLOAD_DIR}/%(playlist_title)s/%(title)s.%(ext)s'}
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url_pl])

# ══════════════════════════════════════════
#  ABA 5 — ARQUIVO CSV (EXPORTIFY)
# ══════════════════════════════════════════
with tab_csv:
    st.markdown("### 📂 Importar do Exportify (CSV)")
    st.caption("Arraste o arquivo CSV aqui para baixar a lista completa.")
    arq_csv = st.file_uploader("Arquivo CSV", type=["csv"], label_visibility="collapsed")
    
    if arq_csv:
        df = pd.read_csv(arq_csv)
        st.write(f"📊 Encontrei **{len(df)}** músicas.")
        if st.button("🚀 BAIXAR LISTA CSV", type="primary", width='stretch'):
            prog = st.progress(0)
            for i, row in df.iterrows():
                # Tenta pegar URL, se não tiver, monta o nome para busca
                link = row.get('Track URL') or row.get('URL')
                nome = row.get('Track Name') or row.get('name') or "Musica"
                art = row.get('Artist Name(s)') or row.get('artists') or ""
                termo = link if link else f"{art} {nome}"
                
                st.caption(f"Baixando: {art} - {nome}")
                baixar_musica(termo, f"{art} - {nome}", '320')
                prog.progress((i+1)/len(df))
            st.success("✅ Concluído!")
