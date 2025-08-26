import os
import json
import random
import string
from PIL import Image, ImageOps

def gerar_codigo():
    """Gera um código aleatório de 6 dígitos."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def carregar_presets(data_file, default_preset_data, DEFAULT_PRESET):
    """Carrega os presets de um arquivo JSON."""
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
        # Garante compatibilidade retroativa
        for preset in data.values():
            if "mostrar_fundo" not in preset:
                preset["mostrar_fundo"] = False
            if "opacidade" not in preset:
                preset["opacidade"] = 0
            if "no_color" not in preset:
                preset["no_color"] = False
        return data
    
    # Adiciona as chaves também ao preset padrão inicial
    default_preset_data[DEFAULT_PRESET]["opacidade"] = 0
    default_preset_data[DEFAULT_PRESET]["no_color"] = False
    return default_preset_data

def salvar_presets(presets_data, data_file):
    """Salva os presets em um arquivo JSON."""
    with open(data_file, "w") as f:
        json.dump(presets_data, f, indent=4)

def carregar_imagens(preset_code, base_dir):
    """
    Carrega os caminhos das imagens de um preset, garantindo que g1.png seja o primeiro
    e que black.png seja ignorado.
    """
    pasta = os.path.join(base_dir, preset_code)
    if not os.path.exists(pasta):
        return []
    
    imagens = []
    
    # Adiciona g1.png primeiro, se existir
    caminho_g1 = os.path.join(pasta, "g1.png")
    if os.path.exists(caminho_g1):
        imagens.append(("g1.png", caminho_g1))
    
    # Adiciona as outras imagens, ignorando g1.png e black.png
    for arquivo in sorted(os.listdir(pasta)):
        # --- CONDIÇÃO ADICIONADA AQUI ---
        # Converte para minúsculas para a checagem não falhar
        nome_arquivo_lower = arquivo.lower()
        if nome_arquivo_lower == "g1.png" or nome_arquivo_lower == "black.png":
            continue
        
        if nome_arquivo_lower.endswith((".png", ".jpg", ".jpeg")):
            caminho = os.path.join(pasta, arquivo)
            imagens.append((arquivo, caminho))
            
    return imagens

def carregar_g1_colorido(preset_code, cor, opacidade, no_color, base_dir):
    """Carrega a imagem g1.png, a colore (ou não), aplica opacidade e redimensiona."""
    pasta = os.path.join(base_dir, preset_code)
    caminho_g1 = os.path.join(pasta, "g1.png")
    caminho_black = os.path.join(pasta, "black.png")

    if not os.path.exists(caminho_g1):
        return None
    
    try:
        # --- LÓGICA ATUALIZADA ---
        if no_color:
            # Se a opção "no color" estiver ativa, carrega a imagem em modo RGBA diretamente.
            colorida = Image.open(caminho_g1).convert("RGBA")
        else:
            # Caso contrário, aplica o efeito de cor como antes.
            img = Image.open(caminho_g1).convert("L")
            colorida = ImageOps.colorize(img, black="black", white=cor).convert("RGBA")

        # A lógica de opacidade continua a mesma
        if opacidade > 0:
            if os.path.exists(caminho_black):
                img_black = Image.open(caminho_black).convert("RGBA")
                if img_black.size != colorida.size:
                    img_black = img_black.resize(colorida.size, Image.Resampling.LANCZOS)
            else:
                img_black = Image.new("RGBA", colorida.size, (0, 0, 0, 255))
            
            alpha = opacidade / 100.0
            final = Image.blend(colorida, img_black, alpha)
        else:
            final = colorida
            
        return final.resize((146, 96))

    except Exception as e:
        print(f"Erro ao carregar g1.png colorido: {e}")
        return None