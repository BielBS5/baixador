import streamlit as st
import yt_dlp
import os
import re
import pandas as pd
import shutil
from pathlib import Path

# Configuração
st.set_page_config(page_title="Rádio Hub - Download em Massa", page_icon="📻", layout="wide")

# Pasta temporária para o ZIP
TMP_DOWNLOADS = "/tmp/radio_hub_batch"

def limpar_pasta():
    if os.path.exists(TMP_DOWNLOADS):
        shutil.rmtree(TMP_DOWNLOADS)
    os.makedirs(TMP_DOWNLOADS)

def sanitizar(nome):
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def baixar_musica_servidor(termo, nome_arquivo):
    nome_limpo = sanitizar(nome_arquivo)
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128', # 128kbps para o ZIP não ficar gigante e baixar rápido
        }],
        'outtmpl': f'{TMP_DOWNLOADS}/{nome_limpo}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        # Se não for link, busca no YouTube
        alvo = termo if termo.startswith('http') else f"ytsearch1:{termo}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([alvo])
        return True
    except:
        return False

# --- INTERFACE ---
st.title("📻 Rádio Hub - Batch Downloader")
st.info("💡 Perfeito para CSV do TuneMyMusic ou Exportify")

# Upload do Arquivo
arquivo = st.file_uploader("Suba seu arquivo CSV", type="csv")

if arquivo:
    try:
        df = pd.read_csv(arquivo)
        # Identifica as colunas do TuneMyMusic ou Exportify
        col_musica = next((c for c in df.columns if c.lower() in ['track', 'name', 'track name']), None)
        col_artista = next((c for c in df.columns if c.lower() in ['artist', 'artist name(s)', 'artist name']), None)
        col_url = next((c for c in df.columns if 'url' in c.lower()), None)

        if not col_musica:
            st.error("Não encontrei a coluna de nome da música no CSV.")
        else:
            st.success(f"Encontrei {len(df)} músicas!")
            
            if st.button(f"🚀 BAIXAR TODAS AS {len(df)} MÚSICAS E GERAR ZIP"):
                limpar_pasta()
                progresso = st.progress(0)
                status = st.empty()
                
                sucessos = 0
                for i, row in df.iterrows():
                    m_nome = str(row[col_musica])
                    m_art = str(row[col_artista]) if col_artista else ""
                    m_url = str(row[col_url]) if col_url and str(row[col_url]).startswith('http') else f"{m_art} {m_nome}"
                    
                    titulo_full = f"{m_art} - {m_nome}" if m_art else m_nome
                    status.write(f"⏳ Processando ({i+1}/{len(df)}): {titulo_full}")
                    
                    if baixar_musica_servidor(m_url, titulo_full):
                        sucessos += 1
                    
                    progresso.progress((i + 1) / len(df))
                
                # Criar o ZIP
                status.write("📦 Criando arquivo ZIP...")
                shutil.make_archive("/tmp/radio_hub_musicas", 'zip', TMP_DOWNLOADS)
                
                with open("/tmp/radio_hub_musicas.zip", "rb") as f:
                    st.download_button(
                        label="💾 BAIXAR TUDO AGORA (.ZIP)",
                        data=f,
                        file_name="minhas_musicas.zip",
                        mime="application/zip",
                        type="primary"
                    )
                st.balloons()
                st.success(f"Pronto! {sucessos} músicas foram incluídas no ZIP.")

    except Exception as e:
        st.error(f"Erro ao ler CSV: {e}")

st.markdown("---")
st.caption("Nota: O download em massa na nuvem pode demorar dependendo do tamanho da lista. Recomendado até 50-100 músicas por vez.")
