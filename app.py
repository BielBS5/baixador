import streamlit as st
import yt_dlp
import os
import pandas as pd
import shutil
import time

# Configuração da página
st.set_page_config(page_title="Rádio Hub - Fix 403", page_icon="📻")

TMP_DIR = "/tmp/downloads_radio"

def preparar_pasta():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

def baixar_musica_safe(termo, nome_arquivo):
    caminho_final = os.path.join(TMP_DIR, f"{nome_arquivo}.mp3")
    
    # OPÇÕES PARA CONTORNAR O ERRO 403
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': f"{TMP_DIR}/{nome_arquivo}.%(ext)s",
        # Configurações Críticas para a Nuvem:
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'source_address': '0.0.0.0', # Força usar IPv4 (ajuda no 403)
        'default_search': 'ytsearch1',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Tenta baixar
            ydl.download([termo])
        return True
    except Exception as e:
        st.error(f"Erro no YouTube: {e}")
        return False

# --- UI ---
st.title("📻 Rádio Hub - Versão Anti-Bloqueio")
st.warning("⚠️ Se o erro 403 persistir, o YouTube bloqueou temporariamente o IP da nuvem. Tente novamente em alguns minutos.")

uploaded_file = st.file_uploader("Suba o seu 'My Spotify Library.csv'", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Verifica se as colunas batem com o seu arquivo
    if 'Track name' in df.columns:
        st.write(f"Músicas prontas: {len(df)}")
        
        # Como o seu notebook tem 4GB de RAM, vamos baixar em blocos menores
        tamanho_lista = st.slider("Quantas músicas baixar da lista?", 1, len(df), 20)
        
        if st.button(f"🚀 INICIAR DOWNLOAD DE {tamanho_lista} MÚSICAS"):
            preparar_pasta()
            prog = st.progress(0)
            status = st.empty()
            
            sucessos = 0
            # Processa apenas a quantidade selecionada no slider
            for i in range(tamanho_lista):
                row = df.iloc[i]
                nome_musica = str(row['Track name'])
                nome_artista = str(row['Artist name']) if 'Artist name' in row else ""
                busca = f"{nome_artista} {nome_musica}"
                
                status.write(f"📥 A baixar ({i+1}/{tamanho_lista}): {busca}")
                
                if baixar_musica_safe(busca, busca):
                    sucessos += 1
                
                # Pequena pausa para não ser banido pelo YouTube
                time.sleep(1) 
                prog.progress((i + 1) / tamanho_lista)
            
            # ZIP
            if sucessos > 0:
                status.write("📦 A criar ZIP...")
                shutil.make_archive("/tmp/musicas", 'zip', TMP_DIR)
                with open("/tmp/musicas.zip", "rb") as f:
                    st.download_button("💾 DESCARREGAR ZIP", f, file_name="minhas_musicas.zip")
                st.balloons()
            else:
                st.error("O YouTube bloqueou todas as tentativas. Tente trocar o nome do arquivo ou fazer Reboot no Streamlit Cloud.")
