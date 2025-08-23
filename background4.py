import os
import re
import json
import shutil
import tkinter as tk
from tkinter import ttk, colorchooser, IntVar, simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
from logger import Logger
from functions import (
    gerar_codigo,
    carregar_presets,
    salvar_presets,
    carregar_imagens,
    carregar_g1_colorido
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
    Abre uma janela personalizada para editar a cor da imagem de fundo g1.png.
    VERSÃO CORRIGIDA.
    """
    preset_atual = preset_var.get()
    if preset_atual not in PRESETS:
        return

    editor_g1_window = tk.Toplevel(janela)
    editor_g1_window.title(f"Editando Cor de Fundo - {preset_atual}")
    editor_g1_window.geometry("800x800")
    editor_g1_window.transient(janela)
    editor_g1_window.grab_set()

    # Variável para guardar o ID do item de imagem no canvas
    canvas_image_id = None

    def validar_e_salvar_cor_hex(cor_hex):
        if re.match(r'^#[0-9a-fA-F]{6}$', cor_hex):
            PRESETS[preset_atual]["color"] = cor_hex
            salvar_presets(PRESETS, DATA_FILE)
            logger.log(f"Cor do preset '{preset_atual}' atualizada para {cor_hex} via entrada de texto.")
            return True
        return False

    def atualizar_controles_cor(nova_cor):
        nonlocal canvas_image_id
        
        cor_preview_local.config(bg=nova_cor)
        
        hex_var.trace_remove("write", hex_trace_id)
        hex_entry.delete(0, tk.END)
        hex_entry.insert(0, nova_cor)
        hex_var.trace_add("write", validar_hex_entry)
        
        preview_g1_colorido = carregar_g1_colorido(
            PRESETS[preset_atual]["code"],
            nova_cor,
            BASE_DIR
        )
        if preview_g1_colorido:
            img_tk = ImageTk.PhotoImage(preview_g1_colorido.resize((400, 263)))
            
            # --- MELHORIA APLICADA AQUI ---
            # Se já existir uma imagem no canvas, apague-a antes de desenhar a nova.
            if canvas_image_id:
                canvas_preview.delete(canvas_image_id)
            
            canvas_image_id = canvas_preview.create_image(200, 131, image=img_tk, anchor="center") # Centralizado
            canvas_preview.image = img_tk

    def escolher_nova_cor_dialogo():
        cor_rgb, cor_hex = colorchooser.askcolor(title="Escolha uma cor")
        if cor_hex:
            if validar_e_salvar_cor_hex(cor_hex):
                atualizar_controles_cor(cor_hex)

    def validar_hex_entry(*args):
        """Função chamada toda vez que o texto na caixa de entrada muda."""
        cor_inserida = hex_var.get()
        # --- CORREÇÃO PRINCIPAL APLICADA AQUI ---
        # Agora, se a cor for válida, chamamos a função principal de atualização
        # que atualiza TUDO (quadrado, texto e o preview grande).
        if validar_e_salvar_cor_hex(cor_inserida):
            atualizar_controles_cor(cor_inserida)
    
    def aplicar_e_fechar():
        cor_final = hex_var.get()
        if validar_e_salvar_cor_hex(cor_final):
            logger.log(f"Edição de cor para '{preset_atual}' finalizada.")
            editor_g1_window.destroy()
            mudar_preset()
        else:
            messagebox.showwarning("Cor Inválida", "A cor inserida não é um código hexadecimal válido (ex: #1A2B3C).")

    # --- Widgets da Janela de Edição (sem alteração) ---
    
    top_frame = tk.Frame(editor_g1_window)
    top_frame.pack(side="top", fill="x", padx=10, pady=10)

    btn_escolher_cor = tk.Button(top_frame, text="Escolher cor", command=escolher_nova_cor_dialogo)
    btn_escolher_cor.pack(side="left")

    cor_atual = PRESETS[preset_atual]["color"]
    cor_preview_local = tk.Label(top_frame, bg=cor_atual, relief="solid", bd=1, width=4)
    cor_preview_local.pack(side="left", padx=5)

    hex_var = tk.StringVar(value=cor_atual)
    hex_entry = tk.Entry(top_frame, textvariable=hex_var, width=10)
    hex_entry.pack(side="left")
    hex_trace_id = hex_var.trace_add("write", validar_hex_entry)

    preview_frame = tk.Frame(editor_g1_window, relief="sunken", bd=2)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
    canvas_preview = tk.Canvas(preview_frame, bg="gray")
    # Bind para recalcular o centro da imagem se a janela for redimensionada
    canvas_preview.bind("<Configure>", lambda e: atualizar_controles_cor(hex_var.get()))
    canvas_preview.pack(fill="both", expand=True)

    btn_aplicar = tk.Button(editor_g1_window, text="Aplicar e Fechar", command=aplicar_e_fechar)
    btn_aplicar.pack(side="right", padx=10, pady=10)
    
    atualizar_controles_cor(cor_atual)

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
    A nova imagem será convertida para .png e renomeada para o nome da original.
    """
    
    # --- Criação da Janela de Edição ---
    editor_window = tk.Toplevel(janela)
    editor_window.title("Substituir Imagem")
    editor_window.geometry("800x800")
    editor_window.transient(janela) # Mantém a janela de edição na frente da principal
    editor_window.grab_set() # Foca a interação nesta janela até que ela seja fechada

    # --- Função interna para processar a substituição ---
    def procurar_e_substituir():
        # Abre o diálogo para o usuário escolher um novo arquivo
        novo_caminho = filedialog.askopenfilename(
            title="Escolha a nova imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos os arquivos", "*.*")]
        )

        # Se o usuário não escolheu nada, encerra a função
        if not novo_caminho:
            logger.log(f"Substituição de '{os.path.basename(caminho_original)}' cancelada.")
            return

        try:
            # Pega o diretório e o nome do arquivo original (sem extensão)
            diretorio_preset = os.path.dirname(caminho_original)
            nome_original_sem_ext = os.path.splitext(os.path.basename(caminho_original))[0]
            
            # Define o caminho final para o novo arquivo. Ele terá o nome do antigo e a extensão .png
            caminho_final = os.path.join(diretorio_preset, f"{nome_original_sem_ext}.png")

            # Abre a nova imagem com o Pillow
            nova_imagem = Image.open(novo_caminho)
            
            # Remove o arquivo antigo
            os.remove(caminho_original)
            logger.log(f"Arquivo original '{os.path.basename(caminho_original)}' removido para substituição.")

            # Salva a nova imagem no formato PNG no caminho final
            # Se a imagem tiver um canal alfa (transparência), ele será preservado
            nova_imagem.save(caminho_final, "PNG")
            logger.log(f"Nova imagem salva como '{os.path.basename(caminho_final)}'.")

            messagebox.showinfo("Sucesso", "Imagem substituída com sucesso!")
            
            # Fecha a janela de edição e atualiza a galeria principal
            editor_window.destroy()
            mudar_preset()

        except Exception as e:
            messagebox.showerror("Erro na Substituição", f"Ocorreu um erro: {e}")
            logger.log(f"ERRO ao substituir imagem: {e}")
            editor_window.destroy()

    # --- Widgets da Janela de Edição ---
    
    # Espaço para visualização da imagem (atualmente vazio, como solicitado)
    preview_frame = tk.Frame(editor_window, bg="black", height=600)
    preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
    tk.Label(preview_frame, text="Área de preview (a ser implementada)", bg="black", fg="white").pack(pady=20)

    # Barra inferior com o botão
    bottom_bar = tk.Frame(editor_window, height=50)
    bottom_bar.pack(fill="x", padx=10, pady=10)

    btn_procurar = tk.Button(bottom_bar, text="Procurar Novo Arquivo...", command=procurar_e_substituir)
    btn_procurar.pack(pady=10)

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
    preset = preset_var.get()
    
    if preset not in PRESETS: return

    g1_base = carregar_g1_colorido(
        PRESETS[preset]["code"], 
        PRESETS[preset]["color"], 
        BASE_DIR
    ) if mostrar_fundo_var.get() else None

    for nome, caminho in imagens:
        frame = tk.Frame(galeria_inner, width=150, height=100, bd=2, relief="solid")
        frame.grid(row=row, column=col, padx=5, pady=5)
        frame.grid_propagate(False)

        imagem_principal_pil = Image.open(caminho).resize((146, 96)).convert("RGBA")
        
        final_pil = imagem_principal_pil
        if g1_base:
            fundo = g1_base.copy()
            fundo.paste(imagem_principal_pil, (0, 0), imagem_principal_pil)
            final_pil = fundo

        img_tk = ImageTk.PhotoImage(final_pil)
        canvas = tk.Canvas(frame, width=146, height=96, highlightthickness=0)
        canvas.create_image(0, 0, image=img_tk, anchor="nw")
        canvas.image = img_tk
        canvas.place(x=0, y=0)

        # --- NOVA LÓGICA DE RECORTE PARA FUNDO DOS ÍCONES ---
        
        # Posições e tamanho dos botões
        btn_size = 15
        pos_delete = (5, 5)
        pos_edit = (25, 5)

        # Recorta o pedaço da imagem final que ficará atrás do botão de excluir
        bg_delete_pil = final_pil.crop((pos_delete[0], pos_delete[1], pos_delete[0] + btn_size, pos_delete[1] + btn_size))
        bg_delete_tk = ImageTk.PhotoImage(bg_delete_pil)
        
        # Recorta o pedaço da imagem final que ficará atrás do botão de editar
        bg_edit_pil = final_pil.crop((pos_edit[0], pos_edit[1], pos_edit[0] + btn_size, pos_edit[1] + btn_size))
        bg_edit_tk = ImageTk.PhotoImage(bg_edit_pil)
        
        # Guarda uma referência para as imagens de fundo para evitar que o Python as apague
        canvas.bg_delete = bg_delete_tk
        canvas.bg_edit = bg_edit_tk

        # --- CRIAÇÃO DOS BOTÕES COM FUNDO PERSONALIZADO ---

        # Botão para EXCLUIR a imagem
        comando_excluir = lambda c=caminho: acao_excluir_imagem(c)
        botao_excluir = criar_botao_com_icone(
            frame, 
            background_image_tk=bg_delete_tk, 
            icon_image_tk=icon_delete_tk, 
            command=comando_excluir, 
            size=btn_size
        )
        botao_excluir.place(x=pos_delete[0], y=pos_delete[1])

        # --- LÓGICA DIFERENCIADA PARA O BOTÃO DE EDITAR ---
        if nome == "g1.png":
            # Se a imagem for a g1.png, chama a nova janela de edição de cor
            comando_editar = lambda: abrir_janela_edicao_g1()
        else:
            # Para todas as outras imagens, chama a janela de substituição
            comando_editar = lambda c=caminho: acao_editar_imagem(c)

        # Botão para EDITAR a imagem (a criação é a mesma, só o comando muda)
        botao_editar = criar_botao_com_icone(
            frame, 
            background_image_tk=bg_edit_tk, 
            icon_image_tk=icon_edit_tk, 
            command=comando_editar, 
            size=btn_size
        )
        botao_editar.place(x=pos_edit[0], y=pos_edit[1])   

        col += 1
        if col >= 5:
            col, row = 0, row + 1

     # --- Frame para adicionar nova imagem ---
    frame_add = tk.Frame(galeria_inner, width=150, height=100, bd=2, relief="solid", bg="#E5E5E5")
    frame_add.grid(row=row, column=col, padx=5, pady=5)
    frame_add.grid_propagate(False) # Impede que o frame mude de tamanho

    # Cria o ícone de "+" usando a função aprimorada
    icon_add = criar_botao_com_icone(
        frame_add,
        icon_image_tk=icon_add_tk,
        background_color="#E5E5E5", # Cor de fundo da janela
        size=50 # Tamanho do ícone
    )
    # Posiciona o ícone no centro do frame
    icon_add.place(relx=0.5, rely=0.4, anchor="center")

    # Cria o label de texto
    label_add = tk.Label(frame_add, text="Adicionar nova\nimagem", bg="#E5E5E5", fg="black")
    label_add.place(relx=0.5, rely=0.8, anchor="center")
    
    # --- Adiciona a função de clique a TODOS os elementos ---
    # Isso garante que clicar em qualquer lugar (no fundo, no ícone ou no texto) funcione.
    comando_clique = lambda e: abrir_janela_adicionar_imagem()
    frame_add.bind("<Button-1>", comando_clique)
    icon_add.bind("<Button-1>", comando_clique)
    # Precisamos iterar sobre os filhos do canvas (o ícone em si) para adicionar o bind
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
    logger.log("Botão 'Gerar' foi clicado.")
    print("Função gerar chamada.")

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
PRESETS = carregar_presets(DATA_FILE, DEFAULT_PRESET_DATA) # <--- CHAMADA DA FUNÇÃO IMPORTADA

# Interface principal
janela = tk.Tk()
janela.title("Editor de Presets")
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