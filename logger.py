import os
import re
import datetime

class Logger:
    def __init__(self, log_directory="logs"):
        """
        Inicializa o logger. Define o diretório e o caminho do arquivo de log.
        """
        self.log_directory = log_directory
        self.log_buffer = []
        self.log_file_path = self._get_next_log_filepath()
        
        # Log inicial
        self.log("--- Sessão de log iniciada ---")

    def _get_next_log_filepath(self):
        """
        Verifica a pasta de logs, encontra o último número de log e retorna
        o caminho para o próximo arquivo de log (ex: log5.txt).
        """
        # Garante que a pasta de logs exista
        os.makedirs(self.log_directory, exist_ok=True)
        
        # Lista os arquivos de log existentes
        existing_logs = [f for f in os.listdir(self.log_directory) if f.startswith('log') and f.endswith('.txt')]
        
        max_num = 0
        # Extrai o número de cada nome de arquivo para encontrar o maior
        for log_file in existing_logs:
            # Usamos expressão regular para extrair o número de forma segura
            match = re.search(r'log(\d+)\.txt', log_file)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        
        # O próximo log será o maior número encontrado + 1
        next_log_num = max_num + 1
        return os.path.join(self.log_directory, f'log{next_log_num}.txt')

    def log(self, message):
        """
        Adiciona uma mensagem de log formatada com timestamp ao buffer em memória.
        """
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # Imprime no console para feedback em tempo real
        print(log_entry)
        
        # Adiciona à lista (buffer)
        self.log_buffer.append(log_entry)

    def write_buffer_to_file(self):
        """
        Escreve o conteúdo do buffer para o arquivo .txt e limpa o buffer.
        """
        if not self.log_buffer:
            return  # Não faz nada se não houver logs para salvar

        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                for entry in self.log_buffer:
                    f.write(entry + '\n')
            
            # Limpa o buffer após salvar
            self.log_buffer = []
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Buffer de log salvo em {self.log_file_path}")
        except Exception as e:
            print(f"ERRO: Não foi possível salvar o log no arquivo. Erro: {e}")