from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_FILE = "dbRFID.db"

def conectar_banco():
    return sqlite3.connect(DB_FILE)

def calcular_tempo_total(inicio, fim):
    delta = fim - datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
    total_segundos = int(delta.total_seconds())
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    segundos = total_segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

@app.route('/registro', methods=['POST'])
def registrar_rfid():
    data = request.get_json()
    rfid_tag = data.get("rfid")
    tarefa = data.get("tarefa")
    obra_id = data.get("obra_id")
    status = data.get("status")  # Pode ser None, "pausada" ou "finalizada"

    if not rfid_tag or not tarefa or obra_id is None:
        return jsonify({"erro": "RFID, tarefa ou obra_id não fornecidos"}), 400

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Usuarios WHERE rfid = ?", (rfid_tag,))
    usuario = cursor.fetchone()

    if not usuario:
        conn.close()
        return jsonify({"erro": "Usuário não encontrado"}), 404

    usuario_id = usuario[0]

    cursor.execute("SELECT id, inicio FROM Registros WHERE usuario_id = ? AND obra_id = ? AND tarefa = ? AND fim IS NULL", 
                   (usuario_id, obra_id, tarefa))
    registro = cursor.fetchone()

    if registro and status:  # Segunda passagem com escolha de pausar/finalizar
        registro_id, inicio = registro
        fim = datetime.now()
        tempo_total = calcular_tempo_total(inicio, fim)
        cursor.execute("UPDATE Registros SET fim = ?, tempo_total = ?, status = ? WHERE id = ?",
                       (fim.strftime("%Y-%m-%d %H:%M:%S"), tempo_total, status, registro_id))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Tarefa pausada/finalizada"})

    elif registro:  # Primeira passagem após iniciar, mas sem status definido ainda
        conn.close()
        return jsonify({"mensagem": "Tarefa pausada/finalizada"})

    else:  # Iniciar uma nova tarefa
        inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Registros (usuario_id, obra_id, tarefa, inicio, status) VALUES (?, ?, ?, ?, ?)", 
                       (usuario_id, obra_id, tarefa, inicio, "iniciada"))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Tarefa iniciada"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9050, debug=True)