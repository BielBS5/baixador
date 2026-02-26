import streamlit as st
import yt_dlp
import os
import re
import pandas as pd
from pathlib import Path

# Configuração da página
st.set_page_config(page_title="Rádio Hub Cloud", page_icon="📻", layout="wide")

# CSS para ficar bonito
st.markdown("""
<style>
    .stApp { background: #f7f4f0; }
    .radio-header { background: linear-gradient(135deg, #fff8f2 0%, #ffe8d0 100%); border: 1.5px solid #e05a00; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .radio-title { font-size: 2rem; font-weight: 800; color: #e05a00; }
</style>
""", unsafe_allow_html=True)

# Na nuvem, usamos a pasta temporária do servidor
TMP_DIR = "/tmp/downloads"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

def sanitizar(nome):
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def baixar_na_nuvem(termo, titulo):
    nome_limpo = sanitizar(titulo)
    caminho_final = os.path.join(TMP_DIR, f"{nome_limpo}.mp3")
    
    # Se não for link, vira busca
    alvo = termo if termo.startswith('http') else f"ytsearch1:{termo}"

    opts = {
        'format': 'bestaudio/best',
        # 'ffmpeg_location' NÃO é necessário no Streamlit Cloud se tiver o packages.txt
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(TMP_DIR, f"{nome_limpo}.%(ext)s"),
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([alvo])
        return caminho_final
    except Exception as e:
        st.error(f"Erro no servidor: {e}")
        return None

# Interface
st.markdown('<div class="radio-header"><div class="radio-title">📻 RÁDIO HUB CLOUD</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["🔍 Busca Única", "📂 Arquivo CSV (Exportify)"])

with tabs[0]:
    nome_musica = st.text_input("Nome da música ou Link:")
    if st.button("PREPARAR DOWNLOAD"):
        with st.spinner("Processando no servidor..."):
            caminho = baixar_na_nuvem(nome_musica, nome_musica)
            if caminho and os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    st.download_button(f"💾 BAIXAR MP3 AGORA", f, file_name=os.path.basename(caminho))
                st.success("Pronto! Clique no botão acima.")

with tabs[1]:
    st.write("Suba o CSV do Exportify e baixe um por um (para não travar a nuvem).")
    arq = st.file_uploader("Arquivo CSV", type="csv")
    if arq:
        df = pd.read_csv(arq)
        for i, row in df.iterrows():
            nome = row.get('Track Name', 'Musica')
            artista = row.get('Artist Name(s)', '')
            link = row.get('Track URL', f"{artista} {nome}")
            
            col1, col2 = st.columns([3, 1])
            col1.write(f"🎵 {artista} - {nome}")
            if col2.button("Preparar", key=f"btn_{i}"):
                with st.spinner("..."):
                    caminho = baixar_na_nuvem(link, f"{artista} - {nome}")
                    if caminho:
                        with open(caminho, "rb") as f:
                            st.download_button("✅ Download", f, file_name=os.path.basename(caminho), key=f"dl_{i}")
