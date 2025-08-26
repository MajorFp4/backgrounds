import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, colorchooser, IntVar, simpledialog, messagebox, filedialog
from PIL import Image, ImageTk, ImageOps
from logger import Logger
from functions import (
    gerar_codigo,
    carregar_presets,
    salvar_presets,
    carregar_imagens,
    carregar_g1_colorido,
    gerar_imagem_final
)

# --- CONFIGURAÇÕES GLOBAIS E CONSTANTES ---
BASE_DIR = os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, "presets.json")
DEFAULT_PRESET = "standard"
DEFAULT_PRESET_DATA = {DEFAULT_PRESET: {"code": "standard", "color": "#FFFFFF", "mostrar_fundo": False}}

# --- INICIALIZAÇÃO DO LOGGER ---
logger = Logger()

# Função para salvar os logs periodicamente
def periodic_save():
    logger.write_buffer_to_file()
    # Agenda a próxima execução para daqui a 5 minutos (300000 ms)
    janela.after(300000, periodic_save)

# Função para ser chamada ao fechar a janela
def on_closing():
    logger.log("--- Sessão encerrada pelo usuário. Salvando logs finais. ---")
    logger.write_buffer_to_file()
    janela.destroy()

# Variáveis de estado da aplicação
cor_selecionada = "#FFFFFF"
imagens_atuais = []

# --- FUNÇÕES DA INTERFACE GRÁFICA (GUI) ---

def abrir_janela_edicao_g1():
    """
    Abre uma janela personalizada para editar o fundo g1.png.
    VERSÃO com checkbox "no color" no lado direito.
    """
    preset_atual = preset_var.get()
    if preset_atual not in PRESETS:
        return

    caminho_g1_original = os.path.join(BASE_DIR, PRESETS[preset_atual]["code"], "g1.png")
    caminho_black_png = os.path.join(BASE_DIR, PRESETS[preset_atual]["code"], "black.png")

    try:
        imagem_g1_pil = Image.open(caminho_g1_original)
        img_w, img_h = imagem_g1_pil.size
        img_aspect_ratio = img_w / img_h
    except FileNotFoundError:
        messagebox.showerror("Erro", "Não foi possível encontrar o arquivo g1.png para este preset.")
        return

    editor_g1_window = tk.Toplevel(janela)
    editor_g1_window.title(f"Editando Fundo (g1.png) - {preset_atual}")
    
    # Lógica de dimensionamento da janela (mantida)
    screen_w = editor_g1_window.winfo_screenwidth()
    screen_h = editor_g1_window.winfo_screenheight()
    max_win_w = int(screen_w * 0.9)
    max_win_h = int(screen_h * 0.9)
    chrome_height = 150 
    window_h = min(img_h + chrome_height, max_win_h)
    preview_h = window_h - chrome_height
    preview_w = preview_h * img_aspect_ratio
    window_w = int(preview_w + 40)
    if window_w > max_win_w:
        window_w = max_win_w
        preview_w = window_w - 40
        preview_h = preview_w / img_aspect_ratio
        window_h = int(preview_h + chrome_height)
    editor_g1_window.minsize(500, 400)
    editor_g1_window.geometry(f"{window_w}x{window_h}")
    editor_g1_window.transient(janela)
    editor_g1_window.grab_set()

    # --- Variáveis de Estado e CACHE ---
    canvas_image_id = None
    novo_caminho_selecionado = None
    cached_g1_original = None
    cached_black_img = None

    # --- CRIAÇÃO DOS WIDGETS (com layout corrigido) ---
    top_frame = tk.Frame(editor_g1_window)
    top_frame.pack(side="top", fill="x", padx=10, pady=10)
    
    # Controles de Cor (continuam na esquerda)
    btn_escolher_cor = tk.Button(top_frame, text="Escolher cor", command=lambda: escolher_nova_cor_dialogo())
    btn_escolher_cor.pack(side="left")
    cor_atual = PRESETS[preset_atual]["color"]
    cor_preview_local = tk.Label(top_frame, bg=cor_atual, relief="solid", bd=1, width=4)
    cor_preview_local.pack(side="left", padx=5)
    hex_var = tk.StringVar(value=cor_atual)
    hex_entry = tk.Entry(top_frame, textvariable=hex_var, width=10)
    hex_entry.pack(side="left")
    
    # Controles de Opacidade (continuam na esquerda)
    opacidade_atual = PRESETS[preset_atual].get("opacidade", 0)
    opacidade_var = tk.IntVar(value=opacidade_atual)
    slider = tk.Scale(top_frame, from_=0, to=100, orient="horizontal", variable=opacidade_var, showvalue=0, length=150)
    slider.pack(side="left", padx=(20, 0))
    opacidade_entry = tk.Entry(top_frame, textvariable=opacidade_var, width=5)
    opacidade_entry.pack(side="left", padx=5)

    # --- Checkbox "no color" (MOVIDO PARA A DIREITA) ---
    no_color_var = tk.BooleanVar(value=PRESETS[preset_atual].get("no_color", False))
    # O checkbox é empacotado primeiro para a direita
    no_color_check = tk.Checkbutton(top_frame, variable=no_color_var, command=lambda: regenerate_caches())
    no_color_check.pack(side="right")
    # O texto é empacotado depois, ficando à esquerda do checkbox
    no_color_label = tk.Label(top_frame, text="no color")
    no_color_label.pack(side="right")

    # Frame do Preview
    preview_frame = tk.Frame(editor_g1_window, relief="sunken", bd=2)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
    canvas_preview = tk.Canvas(preview_frame, bg="gray")
    canvas_preview.pack(fill="both", expand=True)

    # Frame Inferior (Botões)
    bottom_frame = tk.Frame(editor_g1_window)
    bottom_frame.pack(fill="x", padx=10, pady=(0, 10))
    btn_aplicar = tk.Button(bottom_frame, text="Aplicar e Fechar", command=lambda: aplicar_e_fechar())
    btn_aplicar.pack(side="right", padx=10)
    center_frame = tk.Frame(bottom_frame)
    center_frame.pack(expand=True)
    btn_procurar = tk.Button(center_frame, text="Procurar Nova Imagem...", command=lambda: procurar_nova_imagem_g1())
    btn_procurar.pack()

    # --- FUNÇÕES INTERNAS (sem alterações) ---
    def regenerate_caches():
        nonlocal cached_g1_original, cached_black_img
        caminho_base = novo_caminho_selecionado if novo_caminho_selecionado else caminho_g1_original
        try:
            cached_g1_original = Image.open(caminho_base).convert("RGBA")
            if os.path.exists(caminho_black_png):
                cached_black_img = Image.open(caminho_black_png).convert("RGBA")
                if cached_black_img.size != cached_g1_original.size:
                    cached_black_img = cached_black_img.resize(cached_g1_original.size, Image.Resampling.LANCZOS)
            else:
                cached_black_img = Image.new("RGBA", cached_g1_original.size, (0, 0, 0, 255))
        except Exception as e:
            print(f"Erro ao regenerar cache de imagens: {e}")
        update_g1_preview()

    def update_g1_preview():
        nonlocal canvas_image_id
        if not cached_g1_original: return
        
        if no_color_var.get():
            img_colorida = cached_g1_original
        else:
            cor_valida = hex_var.get()
            img_base_l = cached_g1_original.convert("L")
            img_colorida = ImageOps.colorize(img_base_l, black="black", white=cor_valida).convert("RGBA")

        opacidade_percent = opacidade_var.get()
        if opacidade_percent > 0:
            alpha = opacidade_percent / 100.0
            img_final = Image.blend(img_colorida, cached_black_img, alpha)
        else:
            img_final = img_colorida

        canvas_w = canvas_preview.winfo_width()
        canvas_h = canvas_preview.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1: return
        
        final_w, final_h = img_final.size
        final_aspect_ratio = final_w / final_h
        if canvas_w / canvas_h > final_aspect_ratio:
            new_h = canvas_h
            new_w = int(new_h * final_aspect_ratio)
        else:
            new_w = canvas_w
            new_h = int(new_w / final_aspect_ratio)
            
        img_resized = img_final.resize((new_w, new_h), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_resized)
        if canvas_image_id:
            canvas_preview.delete(canvas_image_id)
        canvas_image_id = canvas_preview.create_image(canvas_w/2, canvas_h/2, image=img_tk, anchor="center")
        canvas_preview.image = img_tk

    def on_hex_var_change(*args):
        cor_inserida = hex_var.get()
        if re.match(r'^#[0-9a-fA-F]{6}$', cor_inserida):
            cor_preview_local.config(bg=cor_inserida)
            update_g1_preview()

    def on_opacity_change(*args):
        try:
            valor = opacidade_var.get()
            if valor < 0: opacidade_var.set(0)
            if valor > 100: opacidade_var.set(100)
            update_g1_preview()
        except tk.TclError:
            pass

    def escolher_nova_cor_dialogo():
        cor_rgb, cor_hex = colorchooser.askcolor(title="Escolha uma cor")
        if cor_hex:
            hex_var.set(cor_hex)

    def procurar_nova_imagem_g1():
        nonlocal novo_caminho_selecionado
        caminho = filedialog.askopenfilename(title="Escolha a nova imagem de fundo (g1)", filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos os arquivos", "*.*")])
        if caminho:
            novo_caminho_selecionado = caminho
            logger.log(f"Nova imagem '{os.path.basename(caminho)}' selecionada para substituir g1.png.")
            try:
                imagem_selecionada = Image.open(caminho)
                largura, altura = imagem_selecionada.size
                imagem_preta = Image.new('RGB', (largura, altura), color='black')
                pasta_preset = os.path.dirname(caminho_g1_original)
                caminho_black_png = os.path.join(pasta_preset, "black.png")
                imagem_preta.save(caminho_black_png, "PNG")
                logger.log(f"Imagem black.png criada/atualizada com sucesso no tamanho {largura}x{altura}.")
            except Exception as e:
                logger.log(f"ERRO ao criar black.png: {e}")
                messagebox.showerror("Erro", f"Não foi possível criar a imagem black.png: {e}")
            regenerate_caches()

    def aplicar_e_fechar():
        cor_final = hex_var.get()
        if not re.match(r'^#[0-9a-fA-F]{6}$', cor_final):
            messagebox.showwarning("Cor Inválida", "A cor final inserida não é um código hexadecimal válido (ex: #1A2B3C).")
            return
        if PRESETS[preset_atual]["color"] != cor_final:
            PRESETS[preset_atual]["color"] = cor_final
            salvar_presets(PRESETS, DATA_FILE)
            logger.log(f"Cor do preset '{preset_atual}' salva como {cor_final}.")
            
        opacidade_final = opacidade_var.get()
        if PRESETS[preset_atual].get("opacidade", 0) != opacidade_final:
            PRESETS[preset_atual]["opacidade"] = opacidade_final
            salvar_presets(PRESETS, DATA_FILE)
            logger.log(f"Opacidade do preset '{preset_atual}' salva como {opacidade_final}%.")

        no_color_final = no_color_var.get()
        if PRESETS[preset_atual].get("no_color", False) != no_color_final:
            PRESETS[preset_atual]["no_color"] = no_color_final
            salvar_presets(PRESETS, DATA_FILE)
            logger.log(f"Opção 'no color' do preset '{preset_atual}' salva como {no_color_final}.")

        if novo_caminho_selecionado:
            try:
                nova_imagem = Image.open(novo_caminho_selecionado)
                nova_imagem.save(caminho_g1_original, "PNG")
                logger.log(f"Imagem g1.png do preset '{preset_atual}' foi substituída.")
            except Exception as e:
                messagebox.showerror("Erro ao Salvar Imagem", f"Não foi possível salvar a nova imagem g1.png: {e}")
                return
        
        logger.log(f"Edição de g1 para '{preset_atual}' finalizada.")
        editor_g1_window.destroy()
        mudar_preset()

    def fechar_sem_salvar():
        logger.log(f"Edição de g1 do preset '{preset_atual}' cancelada.")
        editor_g1_window.destroy()

    # --- CHAMADAS FINAIS ---
    hex_var.trace_add("write", on_hex_var_change)
    opacidade_var.trace_add("write", on_opacity_change)
    canvas_preview.bind("<Configure>", lambda e: regenerate_caches())
    editor_g1_window.protocol("WM_DELETE_WINDOW", fechar_sem_salvar)
    editor_g1_window.after(100, regenerate_caches)
    logger.log(f"Janela de edição de cor aberta para o preset '{preset_atual}'.")

def excluir_preset_selecionado():
    """
    Exclui o preset atualmente selecionado no combobox, incluindo sua pasta de imagens.
    """
    preset_selecionado = preset_var.get()

    # 1. Verificação de segurança: não permitir excluir o preset padrão.
    if preset_selecionado == DEFAULT_PRESET:
        messagebox.showwarning("Ação Bloqueada", f"O preset padrão '{DEFAULT_PRESET}' não pode ser excluído.")
        return

    # 2. Pedir confirmação do usuário.
    if not messagebox.askyesno("Confirmar Exclusão", 
                               f"Você tem certeza que deseja excluir permanentemente o preset '{preset_selecionado}'?\n\n"
                               "Todos os arquivos de imagem associados a ele serão apagados."):
        logger.log(f"Exclusão do preset '{preset_selecionado}' cancelada pelo usuário.")
        return

    try:
        logger.log(f"Iniciando exclusão do preset '{preset_selecionado}'.")
        
        # 3. Encontrar o código da pasta para saber qual diretório apagar.
        codigo_pasta = PRESETS[preset_selecionado]["code"]
        caminho_pasta = os.path.join(BASE_DIR, codigo_pasta)

        # 4. Remover a entrada do preset do dicionário.
        del PRESETS[preset_selecionado]
        
        # 5. Apagar a pasta e todo o seu conteúdo.
        if os.path.exists(caminho_pasta):
            shutil.rmtree(caminho_pasta)
            logger.log(f"Pasta '{caminho_pasta}' excluída com sucesso.")

        # 6. Salvar as alterações no arquivo JSON.
        salvar_presets(PRESETS, DATA_FILE)
        
        # 7. Atualizar a interface gráfica.
        logger.log("Atualizando a interface após a exclusão.")
        atualizar_lista_presets()      # Remove o nome do preset do combobox
        preset_var.set(DEFAULT_PRESET) # Seleciona o preset padrão como fallback
        mudar_preset()                 # Recarrega a galeria com as imagens do preset padrão

        messagebox.showinfo("Sucesso", f"O preset '{preset_selecionado}' foi excluído com sucesso.")

    except Exception as e:
        messagebox.showerror("Erro na Exclusão", f"Ocorreu um erro ao excluir o preset: {e}")
        logger.log(f"ERRO ao excluir o preset '{preset_selecionado}': {e}")

def atualizar_mostrar_fundo():
    preset = preset_var.get()
    if preset in PRESETS:
        PRESETS[preset]["mostrar_fundo"] = bool(mostrar_fundo_var.get())
        salvar_presets(PRESETS, DATA_FILE) # <--- CHAMADA DA FUNÇÃO IMPORTADA
        atualizar_galeria(imagens_atuais)

def novo_preset():
    logger.log(f"Tentativa de criar novo preset.")
    nome = simpledialog.askstring("Novo Preset", "Digite o nome do novo preset:")
    if not nome:
        logger.log("Criação de preset cancelada pelo usuário.")
        return

    if nome in PRESETS:
        messagebox.showerror("Erro", "Este nome de preset já existe.")
        return

    codigo = gerar_codigo() # <--- CHAMADA DA FUNÇÃO IMPORTADA
    while codigo in [v["code"] for v in PRESETS.values()]:
        codigo = gerar_codigo() # <--- CHAMADA DA FUNÇÃO IMPORTADA

    pasta_preset = os.path.join(BASE_DIR, codigo)
    os.makedirs(pasta_preset, exist_ok=True)

    pasta_raws = os.path.join(BASE_DIR, "raws")
    if os.path.exists(pasta_raws):
        for arquivo in os.listdir(pasta_raws):
            origem = os.path.join(pasta_raws, arquivo)
            destino = os.path.join(pasta_preset, arquivo)
            if os.path.isfile(origem):
                shutil.copy2(origem, destino)

    PRESETS[nome] = {"code": codigo, "color": "#FFFFFF", "mostrar_fundo": False}
    logger.log(f"Preset '{nome}' criado com sucesso. Código: {codigo}.")
    salvar_presets(PRESETS, DATA_FILE) # <--- CHAMADA DA FUNÇÃO IMPORTADA
    
    atualizar_lista_presets()
    preset_var.set(nome)
    mudar_preset()

def escolher_cor():
    global cor_selecionada
    cor = colorchooser.askcolor(title="Escolha uma cor")[1]
    if cor:
        cor_selecionada = cor
        cor_preview.config(bg=cor)
        preset_selecionado = preset_var.get()
        if preset_selecionado in PRESETS:
            PRESETS[preset_selecionado]["color"] = cor
            logger.log(f"Cor do preset '{preset_selecionado}' alterada para {cor}.")
            salvar_presets(PRESETS, DATA_FILE) # <--- CHAMADA DA FUNÇÃO IMPORTADA
            atualizar_galeria(imagens_atuais)

def acao_excluir_imagem(caminho_da_imagem):
    """
    Pede confirmação, exclui o arquivo de imagem do disco e atualiza a galeria.
    """
    nome_arquivo = os.path.basename(caminho_da_imagem)
    
    # Pede confirmação antes de apagar, o que é uma boa prática
    if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir a imagem '{nome_arquivo}'?"):
        try:
            os.remove(caminho_da_imagem)
            logger.log(f"Imagem '{nome_arquivo}' foi excluída com sucesso.")
            
            # A forma mais fácil de atualizar a galeria é chamar a função que a carrega
            mudar_preset() 
            
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir a imagem: {e}")
            logger.log(f"ERRO ao tentar excluir a imagem '{nome_arquivo}': {e}")

def acao_editar_imagem(caminho_original):
    """
    Abre uma nova janela para substituir a imagem selecionada por uma nova.
    VERSÃO FINAL com preview, aplicação manual e dimensionamento dinâmico.
    """
    
    # --- LÓGICA DE DIMENSIONAMENTO DA JANELA ---
    try:
        imagem_pil = Image.open(caminho_original)
        img_w, img_h = imagem_pil.size
        img_aspect_ratio = img_w / img_h
    except Exception as e:
        messagebox.showerror("Erro ao Abrir", f"Não foi possível ler a imagem original: {e}")
        return

    editor_window = tk.Toplevel(janela)
    editor_window.title("Substituir Imagem")

    # Pega o tamanho da tela e define um limite (90%)
    screen_w = editor_window.winfo_screenwidth()
    screen_h = editor_window.winfo_screenheight()
    max_win_w = int(screen_w * 0.9)
    max_win_h = int(screen_h * 0.9)

    # Estima o espaço dos controles
    chrome_height = 120 
    
    # Calcula o tamanho inicial ideal, garantindo que não ultrapasse o limite da tela
    window_h = min(img_h + chrome_height, max_win_h)
    preview_h = window_h - chrome_height
    preview_w = preview_h * img_aspect_ratio
    window_w = int(preview_w + 40)

    if window_w > max_win_w:
        window_w = max_win_w
        preview_w = window_w - 40
        preview_h = preview_w / img_aspect_ratio
        window_h = int(preview_h + chrome_height)

    editor_window.minsize(500, 400)
    editor_window.geometry(f"{window_w}x{window_h}")
    editor_window.transient(janela)
    editor_window.grab_set()

    # --- O RESTANTE DA LÓGICA ---
    novo_caminho_selecionado = None
    canvas_image_id = None

    def atualizar_preview():
        nonlocal canvas_image_id
        caminho_para_mostrar = novo_caminho_selecionado if novo_caminho_selecionado else caminho_original
        try:
            imagem_pil_preview = Image.open(caminho_para_mostrar)
            canvas_w = preview_canvas.winfo_width()
            canvas_h = preview_canvas.winfo_height()
            if canvas_w <= 1 or canvas_h <= 1: return

            prev_w, prev_h = imagem_pil_preview.size
            prev_aspect_ratio = prev_w / prev_h
            if canvas_w / canvas_h > prev_aspect_ratio:
                new_h = canvas_h
                new_w = int(new_h * prev_aspect_ratio)
            else:
                new_w = canvas_w
                new_h = int(new_w / prev_aspect_ratio)
            
            img_resized = imagem_pil_preview.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img_resized)
            
            if canvas_image_id:
                preview_canvas.delete(canvas_image_id)
            
            canvas_image_id = preview_canvas.create_image(canvas_w/2, canvas_h/2, image=img_tk, anchor="center")
            preview_canvas.image = img_tk
        except Exception as e:
            print(f"Erro ao carregar preview: {e}")

    def procurar_nova_imagem():
        nonlocal novo_caminho_selecionado
        caminho = filedialog.askopenfilename(
            title="Escolha a nova imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            novo_caminho_selecionado = caminho
            logger.log(f"Nova imagem '{os.path.basename(caminho)}' selecionada para substituir '{os.path.basename(caminho_original)}'.")
            atualizar_preview()

    def salvar_e_fechar():
        if not novo_caminho_selecionado:
            editor_window.destroy()
            return
        try:
            diretorio_preset = os.path.dirname(caminho_original)
            nome_original_sem_ext = os.path.splitext(os.path.basename(caminho_original))[0]
            caminho_final = os.path.join(diretorio_preset, f"{nome_original_sem_ext}.png")
            nova_imagem = Image.open(novo_caminho_selecionado)
            
            if os.path.normpath(caminho_original) != os.path.normpath(caminho_final):
                os.remove(caminho_original)
                logger.log(f"Arquivo original '{os.path.basename(caminho_original)}' removido.")

            nova_imagem.save(caminho_final, "PNG")
            logger.log(f"Nova imagem salva como '{os.path.basename(caminho_final)}'.")
            
            # --- POPUP REMOVIDO ---
            
            editor_window.destroy()
            mudar_preset()
        except Exception as e:
            messagebox.showerror("Erro na Substituição", f"Ocorreu um erro: {e}")
            logger.log(f"ERRO ao substituir imagem: {e}")

    def fechar_sem_salvar():
        logger.log(f"Edição de '{os.path.basename(caminho_original)}' cancelada pelo usuário.")
        editor_window.destroy()

    # --- Widgets da Janela de Edição ---
    
    preview_frame = tk.Frame(editor_window, relief="sunken", bd=2)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
    preview_canvas = tk.Canvas(preview_frame, bg="gray")
    preview_canvas.pack(fill="both", expand=True)

    bottom_frame = tk.Frame(editor_window)
    bottom_frame.pack(fill="x", padx=10, pady=(0, 10))

    # --- POSICIONAMENTO DOS BOTÕES CORRIGIDO ---
    # Botão de aplicar vai para a direita
    btn_aplicar = tk.Button(bottom_frame, text="Aplicar e Fechar", command=salvar_e_fechar)
    btn_aplicar.pack(side="right", padx=10)
    
    # Botão de procurar fica no centro (usando expand=True em um frame pai)
    center_frame = tk.Frame(bottom_frame)
    center_frame.pack(expand=True)
    btn_procurar = tk.Button(center_frame, text="Procurar Novo Arquivo...", command=procurar_nova_imagem)
    btn_procurar.pack() # .pack() sem argumentos centraliza

    # --- Chamadas Iniciais e Binds ---
    editor_window.after(100, atualizar_preview) 
    preview_canvas.bind("<Configure>", lambda e: atualizar_preview())
    editor_window.protocol("WM_DELETE_WINDOW", fechar_sem_salvar)
    logger.log(f"Janela de edição aberta para o arquivo '{os.path.basename(caminho_original)}'.")

def criar_botao_com_icone(master, icon_image_tk, background_image_tk=None, background_color=None, command=None, size=15):
    """
    Cria um botão Canvas com um ícone.
    - Se 'background_image_tk' for fornecido, usa como fundo (para transparência).
    - Se 'background_color' for fornecido, usa como uma cor de fundo sólida.
    """
    btn = tk.Canvas(master, width=size, height=size, highlightthickness=0, bd=0)
    
    if background_image_tk:
        btn.create_image(0, 0, image=background_image_tk, anchor="nw")
    elif background_color:
        btn.config(bg=background_color)

    if icon_image_tk:
        btn.create_image(size/2, size/2, image=icon_image_tk)

    overlay = btn.create_rectangle(0, 0, size, size, fill='', outline='')

    def on_enter(event):
        # Aplica um preenchimento preto com um padrão de 50% de cinza
        btn.itemconfig(overlay, fill='black', stipple='gray50')
    
    # --- CORREÇÃO APLICADA AQUI ---
    def on_leave(event):
        # Simplesmente remove o preenchimento. O stipple é ignorado.
        btn.itemconfig(overlay, fill='')
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    if command:
        btn.bind("<Button-1>", lambda e: command())
        
    return btn

def abrir_janela_adicionar_imagem():
    """
    Abre uma janela para o usuário selecionar um novo arquivo de imagem
    e adicioná-lo ao preset atual.
    """
    preset_atual = preset_var.get()
    if not preset_atual or preset_atual == "Novo preset":
        messagebox.showwarning("Ação Inválida", "Selecione um preset válido antes de adicionar uma imagem.")
        return

    # Abre o diálogo para escolher um arquivo
    novo_caminho = filedialog.askopenfilename(
        title="Escolha a nova imagem para adicionar",
        filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos os arquivos", "*.*")]
    )

    if not novo_caminho:
        logger.log("Adição de nova imagem cancelada.")
        return

    try:
        # Define a pasta de destino
        codigo_preset = PRESETS[preset_atual]["code"]
        pasta_destino = os.path.join(BASE_DIR, codigo_preset)
        
        # Pega o nome do novo arquivo sem a extensão
        nome_novo_arquivo_sem_ext = os.path.splitext(os.path.basename(novo_caminho))[0]
        
        # Monta o caminho final, garantindo a extensão .png
        caminho_final = os.path.join(pasta_destino, f"{nome_novo_arquivo_sem_ext}.png")
        
        # Verifica se um arquivo com esse nome já existe
        if os.path.exists(caminho_final):
            if not messagebox.askyesno("Arquivo Existente", "Uma imagem com este nome já existe no preset. Deseja substituí-la?"):
                logger.log("Substituição de imagem existente cancelada.")
                return
        
        # Abre a imagem selecionada e a salva como PNG no destino
        imagem_para_adicionar = Image.open(novo_caminho)
        imagem_para_adicionar.save(caminho_final, "PNG")
        
        logger.log(f"Imagem '{os.path.basename(caminho_final)}' adicionada ao preset '{preset_atual}'.")
        messagebox.showinfo("Sucesso", "Nova imagem adicionada com sucesso!")
        
        # Atualiza a galeria para mostrar a nova imagem
        mudar_preset()

    except Exception as e:
        messagebox.showerror("Erro ao Adicionar Imagem", f"Ocorreu um erro: {e}")
        logger.log(f"ERRO ao adicionar nova imagem: {e}")

def atualizar_galeria(imagens):
    for widget in galeria_inner.winfo_children():
        widget.destroy()

    row, col = 0, 0
    preset_nome = preset_var.get()
    
    if preset_nome not in PRESETS: return

    preset_info = PRESETS[preset_nome]

    # Carrega a base do fundo uma vez, se a opção estiver marcada
    g1_base_para_fundo = None
    if mostrar_fundo_var.get():
        caminho_g1 = os.path.join(BASE_DIR, preset_info["code"], "g1.png")
        if os.path.exists(caminho_g1):
            # Processa a g1 em tamanho real para usar como fundo
            fundo_processado = gerar_imagem_final(preset_info, caminho_g1, BASE_DIR)
            if fundo_processado:
                # Redimensiona para o tamanho do thumbnail
                g1_base_para_fundo = fundo_processado.resize((146, 96), Image.Resampling.LANCZOS)


    for nome, caminho in imagens:
        frame = tk.Frame(galeria_inner, width=150, height=100, bd=2, relief="solid")
        frame.grid(row=row, column=col, padx=5, pady=5)
        frame.grid_propagate(False)

        # Se a imagem atual for a g1.png, o thumbnail dela é a própria base de fundo
        if nome == "g1.png" and g1_base_para_fundo:
            final_pil = g1_base_para_fundo
        else:
            # Para as outras imagens, carrega e as coloca sobre a base de fundo
            imagem_principal_pil = Image.open(caminho).resize((146, 96)).convert("RGBA")
            if g1_base_para_fundo:
                fundo = g1_base_para_fundo.copy()
                fundo.paste(imagem_principal_pil, (0, 0), imagem_principal_pil)
                final_pil = fundo
            else:
                final_pil = imagem_principal_pil

        img_tk = ImageTk.PhotoImage(final_pil)
        canvas = tk.Canvas(frame, width=146, height=96, highlightthickness=0)
        canvas.create_image(0, 0, image=img_tk, anchor="nw")
        canvas.image = img_tk
        canvas.place(x=0, y=0)

        # Lógica dos botões de editar/excluir
        btn_size = 15
        pos_delete = (5, 5)
        pos_edit = (25, 5)
        bg_delete_pil = final_pil.crop((pos_delete[0], pos_delete[1], pos_delete[0] + btn_size, pos_delete[1] + btn_size))
        bg_delete_tk = ImageTk.PhotoImage(bg_delete_pil)
        bg_edit_pil = final_pil.crop((pos_edit[0], pos_edit[1], pos_edit[0] + btn_size, pos_edit[1] + btn_size))
        bg_edit_tk = ImageTk.PhotoImage(bg_edit_pil)
        canvas.bg_delete = bg_delete_tk
        canvas.bg_edit = bg_edit_tk
        comando_excluir = lambda c=caminho: acao_excluir_imagem(c)
        botao_excluir = criar_botao_com_icone(frame, icon_image_tk=icon_delete_tk, background_image_tk=bg_delete_tk, command=comando_excluir, size=btn_size)
        botao_excluir.place(x=pos_delete[0], y=pos_delete[1])
        if nome == "g1.png":
            comando_editar = lambda: abrir_janela_edicao_g1()
        else:
            comando_editar = lambda c=caminho: acao_editar_imagem(c)
        botao_editar = criar_botao_com_icone(frame, icon_image_tk=icon_edit_tk, background_image_tk=bg_edit_tk, command=comando_editar, size=btn_size)
        botao_editar.place(x=pos_edit[0], y=pos_edit[1])

        col += 1
        if col >= 5:
            col, row = 0, row + 1

    # Frame de "Adicionar nova imagem"
    frame_add = tk.Frame(galeria_inner, width=150, height=100, bd=2, relief="solid", bg="#E5E5E5")
    frame_add.grid(row=row, column=col, padx=5, pady=5)
    frame_add.grid_propagate(False)
    icon_add = criar_botao_com_icone(frame_add, icon_image_tk=icon_add_tk, background_color="#E5E5E5", size=50)
    icon_add.place(relx=0.5, rely=0.4, anchor="center")
    label_add = tk.Label(frame_add, text="Adicionar nova\nimagem", bg="#E5E5E5", fg="black")
    label_add.place(relx=0.5, rely=0.8, anchor="center")
    comando_clique = lambda e: abrir_janela_adicionar_imagem()
    frame_add.bind("<Button-1>", comando_clique)
    icon_add.bind("<Button-1>", comando_clique)
    for child in icon_add.winfo_children():
        child.bind("<Button-1>", comando_clique)
    label_add.bind("<Button-1>", comando_clique)

def mudar_preset(event=None):
    global imagens_atuais, cor_selecionada
    preset = preset_var.get()

    if preset == "Novo preset":
        # Evita bugs se o usuário clicar em "Novo preset" sem ter criado um antes
        ultimo_preset = lista_presets[-2] if len(lista_presets) > 1 else DEFAULT_PRESET
        preset_var.set(ultimo_preset)
        novo_preset()
        return

    if preset not in PRESETS: return

    logger.log(f"Preset alterado para: '{preset}'.")

    # <--- CHAMADA DA FUNÇÃO IMPORTADA
    imagens_atuais = carregar_imagens(PRESETS[preset]["code"], BASE_DIR)
    
    cor_selecionada = PRESETS[preset]["color"]
    mostrar_fundo_var.set(1 if PRESETS[preset].get("mostrar_fundo", False) else 0)
    cor_preview.config(bg=cor_selecionada)
    atualizar_galeria(imagens_atuais)

def gerar():
    """
    Pega o preset atual, processa todas as suas imagens e as salva na pasta 'output'.
    """
    preset_selecionado = preset_var.get()
    if not preset_selecionado in PRESETS:
        messagebox.showerror("Erro", "Selecione um preset válido para gerar as imagens.")
        return

    logger.log(f"Iniciando processo de geração para o preset '{preset_selecionado}'.")

    # Garante que a pasta 'output' exista
    pasta_output = os.path.join(BASE_DIR, "output")
    os.makedirs(pasta_output, exist_ok=True)

    # Pega as informações do preset
    preset_info = PRESETS[preset_selecionado]
    codigo_preset = preset_info["code"]
    pasta_preset = os.path.join(BASE_DIR, codigo_preset)

    # Lista todas as imagens no preset, exceto black.png
    imagens_a_gerar = [f for f in os.listdir(pasta_preset) if f.lower().endswith((".png", ".jpg", ".jpeg")) and f.lower() != "black.png"]

    total_imagens = len(imagens_a_gerar)
    imagens_geradas = 0

    for i, nome_imagem in enumerate(imagens_a_gerar):
        print(f"Processando {i+1}/{total_imagens}: {nome_imagem}")
        caminho_imagem = os.path.join(pasta_preset, nome_imagem)
        
        # Usa a nova função para processar a imagem em tamanho real
        imagem_final = gerar_imagem_final(preset_info, caminho_imagem, BASE_DIR)

        if imagem_final:
            # Salva a imagem final na pasta 'output'
            caminho_saida = os.path.join(pasta_output, nome_imagem)
            try:
                imagem_final.save(caminho_saida, "PNG")
                imagens_geradas += 1
            except Exception as e:
                logger.log(f"ERRO ao salvar a imagem final '{nome_imagem}': {e}")
    
    logger.log(f"Geração concluída. {imagens_geradas}/{total_imagens} imagens salvas em '{pasta_output}'.")
    messagebox.showinfo("Processo Concluído", f"{imagens_geradas} de {total_imagens} imagens foram geradas com sucesso na pasta 'output'.")

def posicionar_direita(event=None):
    largura_janela = janela.winfo_width()
    x_botao = largura_janela - 180
    y1, y2, espacamento = 15, 55, 10

    btn_escolher_cor.place(x=x_botao, y=y1)
    cor_preview.place(x=x_botao + btn_escolher_cor.winfo_reqwidth() + espacamento, y=y1+2, width=20, height=20)
    label_mostrar.place(x=x_botao, y=y2)
    checkbox.place(x=x_botao + btn_escolher_cor.winfo_reqwidth() + espacamento, y=y2)
    btn_gerar.place(x=largura_janela - 90, y=janela.winfo_height() - 40, width=80, height=30)

def atualizar_lista_presets():
    global lista_presets
    lista_presets = list(PRESETS.keys())
    if "Novo preset" not in lista_presets:
        lista_presets.append("Novo preset")
    preset_menu['values'] = lista_presets

# --- INICIALIZAÇÃO DA APLICAÇÃO ---
# Carregamento inicial de presets
PRESETS = carregar_presets(DATA_FILE, DEFAULT_PRESET_DATA, DEFAULT_PRESET) # <--- CHAMADA DA FUNÇÃO IMPORTADA

# Interface principal
janela = tk.Tk()
janela.title("backgrounds")
janela.configure(bg="#E5E5E5")
janela.state('zoomed')

# --- CARREGAMENTO DOS ÍCONES ---
try:
    icon_delete_pil = Image.open("assets/delete_icon.png").resize((12, 12), Image.Resampling.LANCZOS)
    icon_delete_tk = ImageTk.PhotoImage(icon_delete_pil)

    icon_edit_pil = Image.open("assets/edit_icon.png").resize((12, 12), Image.Resampling.LANCZOS)
    icon_edit_tk = ImageTk.PhotoImage(icon_edit_pil)

    icon_grid_pil = Image.open("assets/grid_icon.png").resize((12, 12), Image.Resampling.LANCZOS)
    icon_grid_tk = ImageTk.PhotoImage(icon_grid_pil)

    icon_add_pil = Image.open("assets/add_icon.png").resize((36, 36), Image.Resampling.LANCZOS)
    icon_add_tk = ImageTk.PhotoImage(icon_add_pil)
    
    # Guarda uma referência para evitar que o garbage collector do Python apague as imagens
    janela.icon_delete_tk = icon_delete_tk
    janela.icon_edit_tk = icon_edit_tk
    janela.icon_grid_tk = icon_grid_tk
    janela.icon_add_tk = icon_add_tk

except FileNotFoundError:
    messagebox.showerror("Erro", "Arquivos de ícone não encontrados na pasta 'icons'. Crie os ícones 'delete_icon.png' e 'edit_icon.png'.")
    # Define como None para o programa não quebrar
    icon_delete_tk = None
    icon_edit_tk = None
    icon_grid_tk = None
    icon_add_tk = None

# Galeria com scroll
galeria_canvas = tk.Canvas(janela, bg="#E5E5E5", highlightthickness=0)
scrollbar = tk.Scrollbar(janela, orient="vertical", command=galeria_canvas.yview)
galeria_canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.place(relx=0.75, y=60, relheight=0.75, anchor="nw")
galeria_canvas.place(x=60, y=60, relwidth=0.7, relheight=0.75)
galeria_inner = tk.Frame(galeria_canvas, bg="#E5E5E5")
galeria_inner.bind("<Configure>", lambda e: galeria_canvas.configure(scrollregion=galeria_canvas.bbox("all")))
galeria_canvas.create_window((0, 0), window=galeria_inner, anchor="nw")

# Controles do topo
icone_topo = criar_botao_com_icone(
    janela, 
    icon_image_tk=icon_grid_tk, 
    background_color="yellow", 
    size=30
)
icone_topo.place(x=0, y=0)
preset_var = tk.StringVar()
preset_menu = ttk.Combobox(janela, textvariable=preset_var, state="readonly", width=20)
preset_menu.place(x=50, y=15)
preset_menu.bind("<<ComboboxSelected>>", mudar_preset)

# --- BOTÃO DE EXCLUIR PRESET ---
btn_excluir_preset = tk.Button(janela, text="Excluir Preset", command=excluir_preset_selecionado, 
                               bg="#FFFFFF", activebackground="#E5E5E5", relief="raised", borderwidth=2)

def alinhar_botoes_topo():
    x_pos = 200 + preset_menu.winfo_width() + 5
    btn_excluir_preset.place(x=x_pos, y=12, height=25)

janela.after(100, alinhar_botoes_topo)
janela.bind("<Configure>", lambda e: (posicionar_direita(e), alinhar_botoes_topo()), add='+')

atualizar_lista_presets()
preset_var.set(list(PRESETS.keys())[0])

# Controles da direita
btn_escolher_cor = tk.Button(janela, text="Escolher cor", command=escolher_cor)
cor_preview = tk.Label(janela, bg=cor_selecionada, relief="solid", bd=1)
mostrar_fundo_var = IntVar()
label_mostrar = tk.Label(janela, text="Mostrar fundo:", bg="#E5E5E5")
checkbox = tk.Checkbutton(janela, variable=mostrar_fundo_var, command=atualizar_mostrar_fundo)
btn_gerar = tk.Button(janela, text="Gerar", command=gerar)

# Binds e chamadas iniciais
janela.bind("<Configure>", posicionar_direita)
# Configura o que acontece ao clicar no "X" da janela
janela.protocol("WM_DELETE_WINDOW", on_closing)
mudar_preset()
posicionar_direita() # Chamada inicial para posicionar os botões corretamente
periodic_save()
janela.mainloop()