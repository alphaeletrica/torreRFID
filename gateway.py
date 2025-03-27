from time import sleep
import requests
import serial

# Configuração do LoRa (Gateway)
PORT = 'COM5'  # Porta serial (ex: /dev/ttyUSB0 para Linux)
BAUDRATE = 115200

# Configuração do servidor Flask
SERVER_URL = "http://192.168.55.130:5050/registro"

def send_to_server(rfid):
    try:
        response = requests.post(SERVER_URL, json={"rfid": rfid})
        print(f"Resposta do servidor ({rfid}):", response.text)
    except Exception as e:
        print("Erro na requisição:", e)

def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    print("Gateway LoRa iniciado...")

    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            if data:
                print("RFID Recebido:", data)
                send_to_server(data)
        sleep(0.1)

if __name__ == "__main__":
    main()