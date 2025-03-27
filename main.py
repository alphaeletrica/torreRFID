import serial
import sqlite3
import time
from datetime import datetime
import requests
import json

# Configurações
SERIAL_PORT = "COM5"  # Ajuste para sua porta
BAUD_RATE = 9600
DB_FILE = "dbRFID.db"
FLASK_URL = "http://localhost:9050/registro"

# Lista de tarefas
TAREFAS = [
    "RETIRAR PORTAS, TAMPAS, FLANGES E TETO",
    "UNIR OS MODULOS",
    "MONTAR OS CHASSIS",
    "IDENTIFICAR OS COMPONENTES",
    "CORTAR DOBRAR E MONTAR OS BARRAMENTOS GERAL E BANCO DE CAPACITORES",
    "DISTRIBUIR OS CIRCUITOS DE POTENCIA (FORCA)",
    "DISTRIBUIR CIRCUITOS DE COMANDO",
    "BIPAR BANCO DE CAPACITORES COM MULTIMETRO",
    "ANILHAR CIRCUITOS DE COMANDO",
    "ORGANIZAR E AMARRAR CABOS, FIOS",
    "ORGANIZAR CABOS COM ESPIRAL TUBE",
    "LIMPAR QUADRO DE COMANDO",
    "TESTE DE REQUISITOS"
]

def conectar_banco():
    return sqlite3.connect(DB_FILE)

def criar_tabelas():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        rfid TEXT UNIQUE NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Obras (
        id INTEGER NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        data_inicio TEXT,
        data_fim TEXT,
        status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        obra_id INTEGER,
        tarefa TEXT,
        inicio TEXT,
        fim TEXT,
        status TEXT,
        tempo_total TEXT,
        FOREIGN KEY (usuario_id) REFERENCES Usuarios(id),
        FOREIGN KEY (obra_id) REFERENCES Obras(id))''')
    conn.commit()
    conn.close()

def cadastrar_usuario(nome, rfid):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE rfid = ?", (rfid,))
    rfid_existe = cursor.fetchone()[0] > 0
    cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE nome = ?", (nome,))
    nome_existe = cursor.fetchone()[0] > 0
    
    if rfid_existe:
        conn.close()
        return "ID já cadastrado"
    if nome_existe:
        conn.close()
        return "Usuário já cadastrado"
    
    try:
        cursor.execute("INSERT INTO Usuarios (nome, rfid) VALUES (?, ?)", (nome, rfid))
        conn.commit()
        conn.close()
        return "Usuário cadastrado com sucesso"
    except sqlite3.IntegrityError:
        conn.close()
        return "Erro ao cadastrar usuário"

def cadastrar_obra(id_obra, nome):
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Obras (id, nome, status) VALUES (?, ?, 'em andamento')", (id_obra, nome))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        print("Erro: ID da obra já existe. Escolha um ID único.")
        conn.close()
        return False

def atualizar_status_obra(obra_id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT inicio FROM Registros WHERE obra_id = ? ORDER BY inicio ASC LIMIT 1", (obra_id,))
    inicio = cursor.fetchone()
    cursor.execute("SELECT fim FROM Registros WHERE obra_id = ? AND tarefa = ? AND status = 'finalizada' ORDER BY fim DESC LIMIT 1", 
                   (obra_id, TAREFAS[-1]))
    fim = cursor.fetchone()
    
    if inicio:
        cursor.execute("UPDATE Obras SET data_inicio = ? WHERE id = ?", (inicio[0], obra_id))
    if fim:
        cursor.execute("UPDATE Obras SET data_fim = ?, status = 'finalizada' WHERE id = ?", (fim[0], obra_id))
    else:
        cursor.execute("UPDATE Obras SET status = 'em andamento' WHERE id = ?", (obra_id,))
    conn.commit()
    conn.close()

def get_usuario_by_rfid(rfid):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM Usuarios WHERE rfid = ?", (rfid,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def get_obras():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM Obras")
    obras = cursor.fetchall()
    conn.close()
    return obras

def todas_obras_finalizadas():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Obras")
    obras = cursor.fetchall()
    if not obras:
        conn.close()
        return False
    ultima_tarefa = TAREFAS[-1]
    for obra in obras:
        obra_id = obra[0]
        cursor.execute("SELECT COUNT(*) FROM Registros WHERE obra_id = ? AND tarefa = ? AND fim IS NOT NULL AND status = 'finalizada'", 
                       (obra_id, ultima_tarefa))
        finalizada = cursor.fetchone()[0]
        if finalizada == 0:
            conn.close()
            return False
    conn.close()
    return True

def tarefa_ja_finalizada(usuario_id, obra_id, tarefa):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Registros WHERE usuario_id = ? AND obra_id = ? AND tarefa = ? AND fim IS NOT NULL AND status = 'finalizada'", 
                   (usuario_id, obra_id, tarefa))
    finalizada = cursor.fetchone()[0] > 0
    conn.close()
    return finalizada

def tarefa_ja_iniciada(obra_id, tarefa):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT usuario_id FROM Registros WHERE obra_id = ? AND tarefa = ? AND fim IS NULL", 
                   (obra_id, tarefa))
    resultado = cursor.fetchone()
    conn.close()
    return resultado  # Retorna None se não iniciada, ou (usuario_id,) se iniciada

def ler_rfid():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        ser.write(b"LER_RFID\n")
        start_time = time.time()
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("UID: "):
                    rfid = line.replace("UID: ", "")
                    ser.close()
                    return rfid
            time.sleep(0.1)
        ser.close()
        print("Timeout ao ler RFID")
        return None
    except serial.SerialException as e:
        print(f"Erro na conexão serial: {e}")
        return None

def verificar_tarefa_anterior(usuario_id, obra_id, tarefa_index):
    conn = conectar_banco()
    cursor = conn.cursor()
    if tarefa_index > 0:
        anterior = TAREFAS[tarefa_index - 1]
        cursor.execute("SELECT fim, status FROM Registros WHERE usuario_id = ? AND obra_id = ? AND tarefa = ? AND fim IS NOT NULL AND status = 'finalizada'", 
                       (usuario_id, obra_id, anterior))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None
    conn.close()
    return True

def menu_principal():
    criar_tabelas()
    while True:
        print("\nMenu Principal:")
        print("1. Tarefa")
        print("2. Cadastrar usuário")
        print("3. Cadastrar obra")
        print("0. Sair")
        opcao = input("Selecione uma opção: ")
        if opcao == "1":
            gerenciar_tarefa()
        elif opcao == "2":
            cadastrar_usuario_menu()
        elif opcao == "3":
            cadastrar_obra_menu()
        elif opcao == "0":
            print("Saindo...")
            break
        else:
            print("Opção inválida.")

def cadastrar_usuario_menu():
    nome = input("Digite o nome do usuário: ")
    print("Aproxime o cartão RFID...")
    rfid = ler_rfid()
    if rfid:
        resultado = cadastrar_usuario(nome, rfid)
        print(resultado)
    else:
        print("Falha ao ler o RFID.")

def cadastrar_obra_menu():
    while True:
        try:
            id_obra = int(input("Digite o ID da obra: "))
            break
        except ValueError:
            print("ID deve ser um número inteiro.")
    nome = input("Digite o nome da obra: ")
    if cadastrar_obra(id_obra, nome):
        print(f"Obra cadastrada, ID: {id_obra}, OBRA: {nome}")

def gerenciar_tarefa():
    if todas_obras_finalizadas():
        print("Não há obras a serem executadas. Todas as obras estão finalizadas.")
        return

    obras = get_obras()
    if not obras:
        print("Nenhuma obra cadastrada. Cadastre uma obra primeiro.")
        return
    print("\nSelecione uma obra:")
    for i, obra in enumerate(obras, start=1):
        print(f"{i}. {obra[0]} {obra[1]}")
    while True:
        try:
            escolha_obra = int(input("Digite o número da obra: "))
            if 1 <= escolha_obra <= len(obras):
                obra_id = obras[escolha_obra - 1][0]
                break
            else:
                print("Número inválido.")
        except ValueError:
            print("Entrada inválida.")
    
    print("\nSelecione uma tarefa:")
    for i, tarefa in enumerate(TAREFAS, start=1):
        print(f"{i}. {tarefa}")
    while True:
        try:
            escolha = int(input("Digite o número da tarefa: "))
            if 1 <= escolha <= len(TAREFAS):
                tarefa = TAREFAS[escolha - 1]
                tarefa_index = escolha - 1
                break
            else:
                print("Número inválido.")
        except ValueError:
            print("Entrada inválida.")
    
    print("Aproxime o cartão RFID...")
    rfid = ler_rfid()
    if rfid:
        usuario = get_usuario_by_rfid(rfid)
        if usuario:
            usuario_id, nome = usuario
            # Verifica se a tarefa já foi finalizada pelo usuário
            if tarefa_ja_finalizada(usuario_id, obra_id, tarefa):
                print(f"A tarefa '{tarefa}' já foi finalizada para esta obra.")
                return
            # Verifica se a tarefa está iniciada por alguém
            tarefa_iniciada = tarefa_ja_iniciada(obra_id, tarefa)
            if tarefa_iniciada and tarefa_iniciada[0] != usuario_id:
                print(f"A tarefa '{tarefa}' já foi iniciada por outro usuário e não pode ser iniciada novamente.")
                return
            # Verifica se a tarefa anterior foi finalizada
            if not verificar_tarefa_anterior(usuario_id, obra_id, tarefa_index):
                print(f"A tarefa anterior ({TAREFAS[tarefa_index - 1]}) deve ser finalizada primeiro para esta obra.")
                return
            
            payload = {"rfid": rfid, "tarefa": tarefa, "obra_id": obra_id}
            headers = {"Content-Type": "application/json"}
            try:
                response = requests.post(FLASK_URL, data=json.dumps(payload), headers=headers)
                mensagem = response.json().get("mensagem")
                if mensagem == "Tarefa iniciada":
                    print("Tarefa iniciada")
                    atualizar_status_obra(obra_id)
                elif mensagem == "Tarefa pausada/finalizada":
                    conn = conectar_banco()
                    cursor = conn.cursor()
                    cursor.execute("SELECT usuario_id FROM Registros WHERE obra_id = ? AND tarefa = ? AND fim IS NULL", 
                                   (obra_id, tarefa))
                    registro = cursor.fetchone()
                    conn.close()
                    if registro:
                        if registro[0] != usuario_id:
                            print(f"Apenas o usuário que iniciou a tarefa '{tarefa}' pode pausá-la ou finalizá-la.")
                            return
                        print("Opções:")
                        print("1. Pausar")
                        print("2. Finalizar")
                        opcao = input("Digite a opção: ")
                        if opcao == "1":
                            mensagem = "Tarefa pausada"
                            payload["status"] = "pausada"
                        elif opcao == "2":
                            mensagem = "Tarefa finalizada"
                            payload["status"] = "finalizada"
                        else:
                            print("Opção inválida, assumindo pausada")
                            mensagem = "Tarefa pausada"
                            payload["status"] = "pausada"
                        requests.post(FLASK_URL, data=json.dumps(payload), headers=headers)
                        print(mensagem)
                        atualizar_status_obra(obra_id)
            except requests.exceptions.RequestException as e:
                print(f"Erro ao enviar para o Flask: {e}")
        else:
            print("Usuário não encontrado.")
    else:
        print("Falha ao ler o RFID.")

if __name__ == "__main__":
    menu_principal()