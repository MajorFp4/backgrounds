import os
import json
import random
import string
from PIL import Image, ImageOps

def gerar_codigo():
    """Gera um código aleatório de 6 dígitos."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def carregar_presets(data_file, default_preset_data):
    """Carrega os presets de um arquivo JSON."""
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
        # Garante compatibilidade com versões antigas sem a chave "mostrar_fundo"
        for preset in data.values():
            if "mostrar_fundo" not in preset:
                preset["mostrar_fundo"] = False
        return data
    return default_preset_data

def salvar_presets(presets_data, data_file):
    """Salva os presets em um arquivo JSON."""
    with open(data_file, "w") as f:
        json.dump(presets_data, f, indent=4)

def carregar_imagens(preset_code, base_dir):
    """
    Carrega os caminhos das imagens de um preset, garantindo que g1.png seja o primeiro item da lista.
    """
    pasta = os.path.join(base_dir, preset_code)
    if not os.path.exists(pasta):
        return []
    
    imagens = []
    
    # --- NOVA LÓGICA ---
    # 1. Procura por g1.png primeiro e o adiciona à lista se existir.
    # Isso garante que ele será sempre o primeiro.
    caminho_g1 = os.path.join(pasta, "g1.png")
    if os.path.exists(caminho_g1):
        imagens.append(("g1.png", caminho_g1))
    
    # 2. Varre o diretório para adicionar as outras imagens, em ordem alfabética.
    #    Usar sorted() garante uma ordem consistente para as outras imagens.
    for arquivo in sorted(os.listdir(pasta)):
        # Garante que não vamos adicionar g1.png novamente (a checagem é case-insensitive)
        if arquivo.lower() == "g1.png":
            continue
        
        # Adiciona os outros arquivos de imagem válidos
        if arquivo.lower().endswith((".png", ".jpg", ".jpeg")):
            caminho = os.path.join(pasta, arquivo)
            imagens.append((arquivo, caminho))
            
    return imagens

def carregar_g1_colorido(preset_code, cor, base_dir):
    """Carrega a imagem g1.png, a colore e a redimensiona."""
    pasta = os.path.join(base_dir, preset_code)
    caminho_g1 = os.path.join(pasta, "g1.png")
    if not os.path.exists(caminho_g1):
        return None
    
    try:
        img = Image.open(caminho_g1).convert("L")
        colorida = ImageOps.colorize(img, black="black", white=cor).resize((146, 96))
        return colorida.convert("RGBA")
    except Exception as e:
        print(f"Erro ao carregar g1.png: {e}")
        return None