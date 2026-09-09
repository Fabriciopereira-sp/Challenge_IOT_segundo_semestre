import json
import time
import sys
import requests
import paho.mqtt.client as mqtt

# broker MQTT (mesmo usado no firmware do ESP32)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_NIVEL = "clyvo/vet/bebedouro/nivel"
TOPIC_TEMP = "clyvo/vet/bebedouro/temp"
TOPIC_UMID = "clyvo/vet/bebedouro/umid"
TOPIC_ALERTA = "clyvo/vet/bebedouro/alerta"
TOPIC_IA_ALERTA = "clyvo/vet/bebedouro/ia_alerta"

# config do Ollama (roda local, sem custo)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# % de queda no consumo para considerar anomalia
LIMITE_ANOMALIA_PERCENTUAL = 30

DATASET_PATH = "dataset_historico.json"


def carregar_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_media_historica(historico):
    valores = [dia["consumo_ml"] for dia in historico]
    return sum(valores) / len(valores)


def detectar_anomalia(consumo_hoje_ml, media_historica_ml):
    # calcula quanto o consumo de hoje caiu em relação à média
    diferenca_percentual = ((media_historica_ml - consumo_hoje_ml) / media_historica_ml) * 100
    anomalo = diferenca_percentual >= LIMITE_ANOMALIA_PERCENTUAL
    return anomalo, round(diferenca_percentual, 1)


def gerar_mensagem_ia(pet_nome, percentual_queda, temp_hoje_c, media_historica_ml, consumo_hoje_ml):
    # monta o prompt e manda pro modelo local via Ollama
    prompt = f"""Você é um assistente veterinário virtual do app CLYVO VET.
Gere uma mensagem curta (máximo 3 frases), clara e empática para o tutor de um pet,
alertando sobre baixo consumo de água, explicando o risco (desidratação e problemas renais)
e sugerindo uma ação simples. Não use saudação nem assinatura, vá direto ao ponto.

Dados:
- Nome do pet: {pet_nome}
- Consumo de água hoje: {consumo_hoje_ml}ml
- Média histórica de consumo: {media_historica_ml:.0f}ml
- Queda no consumo: {percentual_queda}%
- Temperatura de hoje: {temp_hoje_c}C
"""

    try:
        resposta = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        resposta.raise_for_status()
        return resposta.json()["response"].strip()

    except requests.exceptions.ConnectionError:
        return (
            "[ERRO] Não foi possível conectar ao Ollama. "
            "Verifique se ele está rodando (comando: ollama serve) "
            "e se o modelo foi baixado (comando: ollama pull " + OLLAMA_MODEL + ")."
        )
    except Exception as erro:
        return f"[ERRO ao gerar mensagem com IA]: {erro}"


def publicar_alerta_ia(client, mensagem, anomalo, percentual):
    payload = json.dumps({
        "anomalo": anomalo,
        "queda_percentual": percentual,
        "mensagem": mensagem,
    }, ensure_ascii=False)

    client.publish(TOPIC_IA_ALERTA, payload)
    print(f"\n[MQTT] Mensagem publicada em '{TOPIC_IA_ALERTA}':")
    print(payload)


def executar_ciclo_do_agente(client=None):
    # fluxo principal: le os dados, verifica anomalia, chama a IA e publica
    dados = carregar_dataset()
    pet_nome = dados["pet"]["nome"]
    historico = dados["historico_consumo_diario_ml"]
    consumo_hoje = dados["consumo_hoje_ml"]
    temp_hoje = dados["temp_hoje_c"]

    media_historica = calcular_media_historica(historico)

    print(f"--- Ciclo do agente | Pet: {pet_nome} ---")
    print(f"Média histórica de consumo: {media_historica:.0f}ml")
    print(f"Consumo de hoje: {consumo_hoje}ml")

    anomalo, percentual = detectar_anomalia(consumo_hoje, media_historica)

    if not anomalo:
        print(f"[OK] Consumo dentro do esperado (queda de {percentual}%). Nenhuma ação necessária.")
        return

    print(f"[ANOMALIA DETECTADA] Queda de {percentual}% em relação à média. Acionando IA generativa...")

    mensagem = gerar_mensagem_ia(
        pet_nome=pet_nome,
        percentual_queda=percentual,
        temp_hoje_c=temp_hoje,
        media_historica_ml=media_historica,
        consumo_hoje_ml=consumo_hoje,
    )

    print(f"\n[IA] Mensagem gerada para o tutor:\n{mensagem}")

    if client is not None:
        publicar_alerta_ia(client, mensagem, anomalo, percentual)


def modo_simulado():
    # roda com os dados do dataset, sem precisar do hardware ligado
    print("=== MODO SIMULADO (usando dataset_historico.json) ===\n")
    executar_ciclo_do_agente(client=None)


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Conectado ao broker {MQTT_BROKER} (código: {rc})")
    client.subscribe(TOPIC_ALERTA)
    print(f"[MQTT] Escutando o tópico '{TOPIC_ALERTA}'...")


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"\n[MQTT] Mensagem recebida em '{msg.topic}': {payload}")

    try:
        dados = json.loads(payload)
    except json.JSONDecodeError:
        return

    # quando o firmware manda "vazio", roda a análise de consumo
    if dados.get("msg") == "vazio":
        print("[AGENTE] Nível crítico detectado pelo sensor. Rodando análise de consumo...")
        executar_ciclo_do_agente(client=client)


def modo_tempo_real():
    # conecta de verdade no broker e fica escutando o ESP32
    print("=== MODO TEMPO REAL (conectado ao MQTT) ===\n")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "simulado"

    if modo == "simulado":
        modo_simulado()
    elif modo == "mqtt":
        modo_tempo_real()
    else:
        print("Uso: python agente_bebedouro.py [simulado|mqtt]")