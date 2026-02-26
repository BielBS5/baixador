import streamlit as st
import yt_dlp
import os
import re
import pandas as pd
import shutil
from pathlib import Path

# Configuração para o seu X515MA (Celeron N4020) rodando via Nuvem
st.set_page_config(page_title="Rádio Hub - Spotify Library", page_icon="📻", layout="wide")

# Pasta temporária no servidor Linux da nuvem
TMP_DIR = "/tmp/downloads_radio"

def limpar_pasta():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

def sanitizar(nome):
    return re.sub(r'[\\/*?:"<>|]', "", str(nome)).strip()

def baixar_musica_cloud(termo_busca, nome_arquivo):
    nome_limpo = sanitizar(nome_arquivo)
    
    # OPÇÕES ANTI-BLOQUEIO (Para evitar o Erro 403)
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320', # 128kbps é mais rápido para o seu Celeron processar depois
        }],
        'outtmpl': f"{TMP_DIR}/{nome_limpo}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # O segredo para evitar o 403 é fingir que é um navegador real:
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        # Se não for link, faz a busca
        alvo = termo_busca if termo_busca.startswith('http') else f"ytsearch1:{termo_busca}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([alvo])
        return True
    except Exception as e:
        print(f"Erro no download: {e}")
        return False

# --- INTERFACE ---
st.title("📻 Rádio Hub - My Spotify Library")
st.markdown(f"Focado no arquivo: `{os.path.basename('My Spotify Library.csv')}`")

arquivo_csv = st.file_uploader("Suba o seu arquivo CSV do Spotify", type=["csv"])

if arquivo_csv:
    try:
        # Lendo o CSV com as colunas do seu arquivo
        df = pd.read_csv(arquivo_csv)
        
        # Mapeamento exato das colunas do seu arquivo
        # 'Track name' e 'Artist name'
        if 'Track name' in df.columns and 'Artist name' in df.columns:
            st.success(f"✅ Arquivo lido! {len(df)} músicas encontradas.")
            
            if st.button(f"🚀 BAIXAR TUDO E GERAR ZIP"):
                limpar_pasta()
                progresso = st.progress(0)
                status = st.empty()
                
                sucessos = 0
                for i, row in df.iterrows():
                    musica = str(row['Track name'])
                    artista = str(row['Artist name'])
                    nome_completo = f"{artista} - {musica}"
                    
                    status.write(f"📥 Processando ({i+1}/{len(df)}): **{nome_completo}**")
                    
                    # Tenta baixar
                    if baixar_musica_cloud(nome_completo, nome_completo):
                        sucessos += 1
                    
                    progresso.progress((i + 1) / len(df))
                
                # Criar o ZIP para o usuário baixar de uma vez
                if sucessos > 0:
                    status.write("📦 Criando pacote ZIP...")
                    shutil.make_archive("/tmp/musicas_radio", 'zip', TMP_DIR)
                    
                    with open("/tmp/musicas_radio.zip", "rb") as f:
                        st.download_button(
                            label="💾 DESCARREGAR TODAS AS MÚSICAS (.ZIP)",
                            data=f,
                            file_name="minha_biblioteca_mp3.zip",
                            mime="application/zip",
                            type="primary"
                        )
                    st.balloons()
                else:
                    st.error("Nenhuma música pôde ser baixada. O YouTube bloqueou o servidor (Erro 403).")
        else:
            st.error("O CSV subido não tem as colunas 'Track name' e 'Artist name'.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")

st.divider()
st.caption("Dica: Se der erro 403, tente baixar em horários diferentes ou com menos músicas no CSV.")
