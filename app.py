import streamlit as st
import yt_dlp
import os
import re
import pandas as pd
from pathlib import Path

# Configuração para rodar leve no Celeron do utilizador (via Nuvem)
st.set_page_config(page_title="Rádio Hub - TuneMyMusic", page_icon="📻", layout="wide")

# Pasta temporária no servidor do Streamlit Cloud
TMP_DIR = "/tmp/downloads"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# CSS Minimalista
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&display=swap');
    .stApp { background: #f7f4f0; }
    .radio-header { 
        background: linear-gradient(135deg, #fff8f2 0%, #ffe8d0 100%); 
        border: 1.5px solid #e05a00; 
        border-radius: 12px; padding: 20px; margin-bottom: 20px; 
    }
    .radio-title { font-size: 2rem; font-weight: 800; color: #e05a00; margin: 0; }
</style>
""", unsafe_allow_html=True)

def sanitizar(nome):
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def baixar_na_nuvem(termo_busca, nome_arquivo):
    nome_limpo = sanitizar(nome_arquivo)
    caminho_mp3 = os.path.join(TMP_DIR, f"{nome_limpo}.mp3")
    
    # Se não for link direto, força a busca no YouTube
    alvo = termo_busca.strip()
    if not alvo.startswith('http'):
        alvo = f"ytsearch1:{alvo}"

    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(TMP_DIR, f"{nome_limpo}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([alvo])
        return caminho_mp3
    except Exception as e:
        st.error(f"Erro ao processar {nome_arquivo}: {e}")
        return None

# --- INTERFACE ---
st.markdown('<div class="radio-header"><div class="radio-title">📻 RÁDIO HUB (TUNE MY MUSIC)</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["🔍 Busca Simples", "📂 CSV do TuneMyMusic"])

with tabs[0]:
    txt_busca = st.text_input("Nome da música ou Link:")
    if st.button("PREPARAR MP3", type="primary"):
        with st.spinner("A gerar ficheiro..."):
            path = baixar_na_nuvem(txt_busca, txt_busca)
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    st.download_button("💾 DESCARREGAR AGORA", f, file_name=os.path.basename(path))

with tabs[1]:
    st.markdown("### Importar Lista CSV")
    st.caption("Compatível com TuneMyMusic (Colunas: Artist, Track)")
    
    ficheiro = st.file_uploader("Sobe o teu CSV aqui", type="csv")
    
    if ficheiro:
        try:
            df = pd.read_csv(ficheiro)
            st.success(f"Encontrei {len(df)} músicas!")
            
            # O TuneMyMusic costuma usar 'Artist' e 'Track'
            # Criamos uma lista para o utilizador escolher o que baixar
            for i, row in df.iterrows():
                # Tenta colunas do TuneMyMusic ou nomes genéricos
                artista = row.get('Artist') or row.get('artist') or ""
                musica = row.get('Track') or row.get('track') or row.get('Name') or "Musica"
                url = row.get('URL') or row.get('url') or f"{artista} {musica}"
                
                label_exibicao = f"{artista} - {musica}" if artista else musica
                
                col_nome, col_btn = st.columns([4, 1])
                col_nome.write(f"🎵 {label_exibicao}")
                
                # Botão único para cada música (melhor para a RAM do teu Celeron)
                if col_btn.button("Preparar", key=f"btn_{i}"):
                    with st.spinner("A processar..."):
                        path = baixar_na_nuvem(url, label_exibicao)
                        if path:
                            with open(path, "rb") as f:
                                st.download_button("✅ Download", f, file_name=os.path.basename(path), key=f"dl_{i}")
        
        except Exception as e:
            st.error(f"Erro ao ler o CSV: {e}")

st.divider()
st.info("Dica: No Streamlit Cloud, é melhor baixar uma de cada vez para não estourar o limite de memória do servidor gratuito.")
