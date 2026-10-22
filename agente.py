import argparse
import json
import time

import paho.mqtt.client as mqtt

import llm
from consumo import RastreadorConsumo
from detector import Gatilho, alerta_pote_vazio, avaliar

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

# prefixo próprio para não misturar com outros grupos no broker público
PREFIXO = "clyvo/vet/s4-rm563237/bebedouro"

HORAS_AQUECIMENTO = 24    # antes disso a janela de 24h ainda está incompleta
MAX_DIAS_HISTORICO = 14


def topico(nome):
    return f"{PREFIXO}/{nome}"


def carregar_pet(nome="rex", caminho="pets.json"):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)[nome]


class Agente:
    def __init__(self, pet, analisar=llm.analisar, gatilho=None):
        self.pet = pet
        self.historico = list(pet.get("historico_dias_ml", []))
        self.rastreador = RastreadorConsumo()
        self.gatilho = gatilho or Gatilho()
        self.analisar = analisar
        self.temperatura = None
        self.dia_atual = None

    def receber_temperatura(self, valor):
        self.temperatura = valor

    def receber_nivel(self, ts, dist_cm):
        # cada leitura atualiza o consumo, mas a avaliação é por tempo
        # e não depende do nível estar vazio
        self.rastreador.leitura(ts, dist_cm)
        self._fechar_dia(ts)

        if not self.gatilho.deve_avaliar(ts):
            return []
        return self._avaliar(ts)

    def _horas_observadas(self, ts):
        return (ts - self.rastreador.primeiro_ts) / 3600

    def _fechar_dia(self, ts):
        # na virada do dia o consumo das últimas 24h entra no histórico
        dia = int(ts // 86400)
        if self.dia_atual is None:
            self.dia_atual = dia
            return

        if dia != self.dia_atual:
            if self._horas_observadas(ts) >= HORAS_AQUECIMENTO:
                self.historico.append(self.rastreador.consumo_janela(ts))
                self.historico = self.historico[-MAX_DIAS_HISTORICO:]
            self.dia_atual = dia

    def _reabastecimentos_24h(self, ts):
        inicio = ts - 24 * 3600
        return sum(
            1 for e in self.rastreador.eventos
            if e.tipo == "reabastecimento" and e.ts >= inicio
        )

    def _avaliar(self, ts):
        r = self.rastreador
        av = avaliar(
            r.consumo_janela(ts), self.historico, self.pet["peso_kg"],
            r.horas_sem_consumo(ts), r.nivel_ml,
        )

        # com menos de 24h de dados, comparar com um dia inteiro daria falso alarme
        coletando = (
            self._horas_observadas(ts) < HORAS_AQUECIMENTO
            and av.status in ("queda", "aumento")
        )
        if coletando:
            self.gatilho.ultima_avaliacao = ts
            return [("ia_estado", self._estado(ts, av, "coletando_dados"))]

        saidas = [("ia_estado", self._estado(ts, av, av.status))]

        if self.gatilho.deve_alertar(ts, av):
            contexto = {
                "temperatura_c": self.temperatura,
                "reabastecimentos_24h": self._reabastecimentos_24h(ts),
                "horas_observadas": round(self._horas_observadas(ts), 1),
            }
            analise = self.analisar(av, self.pet, contexto)
            saidas.append(("ia_alerta", self._alerta(ts, av, analise)))

        return saidas

    def _estado(self, ts, av, status):
        return {
            "pet": self.pet["nome"],
            "ts": ts,
            "status": status,
            "gravidade": av.gravidade,
            "consumo_24h_ml": av.consumo_24h_ml,
            "esperado_ml": av.esperado_ml,
            "desvio_pct": av.desvio_pct,
            "nivel_ml": round(self.rastreador.nivel_ml),
            "pote_vazio": alerta_pote_vazio(self.rastreador.nivel_ml),
            "temperatura_c": self.temperatura,
        }

    def _alerta(self, ts, av, analise):
        return {
            "pet": self.pet["nome"],
            "ts": ts,
            "status": av.status,
            "gravidade": av.gravidade,
            "motivo": av.motivo,
            "metricas": {
                "consumo_24h_ml": av.consumo_24h_ml,
                "esperado_ml": av.esperado_ml,
                "desvio_pct": av.desvio_pct,
                "horas_sem_consumo": av.horas_sem_consumo,
                "base": av.base,
            },
            "analise": analise,
        }


def ler_valor(payload):
    # aceita {"valor": 12.3, "ts": ...} (firmware e simulador) ou só o número
    try:
        dados = json.loads(payload)
        if isinstance(dados, dict):
            return float(dados["valor"]), dados.get("ts")
        return float(dados), None
    except (ValueError, KeyError, TypeError):
        return None, None


def rodar_mqtt(pet):
    agente = Agente(pet)

    def on_connect(client, userdata, flags, rc):
        print(f"[MQTT] conectado ao {MQTT_BROKER} (codigo {rc})")
        client.subscribe(topico("nivel"))
        client.subscribe(topico("temp"))
        print(f"[AGENTE] acompanhando o pet {pet['nome']} em {PREFIXO}")

    def on_message(client, userdata, msg):
        valor, ts = ler_valor(msg.payload.decode())
        if valor is None:
            return
        ts = ts if ts is not None else time.time()

        if msg.topic.endswith("/temp"):
            agente.receber_temperatura(valor)
            return

        if msg.topic.endswith("/nivel"):
            for nome, payload in agente.receber_nivel(ts, valor):
                client.publish(topico(nome), json.dumps(payload, ensure_ascii=False), retain=True)
                if nome == "ia_alerta":
                    print(f"[ALERTA] {payload['status']} ({payload['gravidade']}): {payload['motivo']}")
                    print(f"         {payload['analise']['mensagem_tutor']}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pet", default="rex", help="chave do pet no pets.json")
    args = parser.parse_args()
    rodar_mqtt(carregar_pet(args.pet))