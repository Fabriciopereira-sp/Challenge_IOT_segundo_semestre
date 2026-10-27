import argparse
import json
import math
import statistics
import time

import paho.mqtt.client as mqtt

from agente import Agente, MQTT_BROKER, MQTT_PORT, carregar_pet, topico
from consumo import ML_POR_CM, PROFUNDIDADE_CM
from db import Repositorio

CAPACIDADE_ML = PROFUNDIDADE_CM * ML_POR_CM
PASSO_S = 600                                   # uma leitura a cada 10 min simulados
HORAS_GOLES = [6.5, 8, 10, 12, 14.5, 17, 19, 21.5]
HORAS_TUTOR = [6, 9, 11, 13, 16, 18, 20, 22]

# multiplicador do consumo de cada dia e até que nível o tutor deixa o pote chegar
CENARIOS = {
    "normal":      {"mult": [1, 1, 1],   "limite_refil": 400},
    "queda":       {"mult": [1, 1, 0.5], "limite_refil": 400},
    "aumento":     {"mult": [1, 1, 1.9], "limite_refil": 400},
    "refil":       {"mult": [1, 1, 1],   "limite_refil": 700},
    "sem_consumo": {"mult": [1, 1, 0],   "limite_refil": 400},
}


def dist_de_ml(ml):
    return PROFUNDIDADE_CM - ml / ML_POR_CM


def temperatura_em(hora):
    return 22 + 8 * max(0.0, math.sin(math.pi * (hora - 6) / 12))


def na_janela(t, hora_do_dia, dia):
    # o evento cai entre a leitura anterior e a atual
    alvo = dia * 86400 + hora_do_dia * 3600
    return t - PASSO_S < alvo <= t


def gerar(cenario, pet):
    cfg = CENARIOS[cenario]
    alvo_dia = statistics.median(pet["historico_dias_ml"])
    nivel = CAPACIDADE_ML

    for t in range(0, len(cfg["mult"]) * 86400, PASSO_S):
        dia = t // 86400
        hora = (t % 86400) / 3600
        gole = alvo_dia * cfg["mult"][dia] / len(HORAS_GOLES)

        if any(na_janela(t, h, dia) for h in HORAS_GOLES):
            nivel -= min(gole, nivel)

        if any(na_janela(t, h, dia) for h in HORAS_TUTOR) and nivel < cfg["limite_refil"]:
            nivel = CAPACIDADE_ML

        yield t, dist_de_ml(nivel), temperatura_em(hora)


def rodar_local(cenario, pet, repo=None, atraso=0.0):
    if repo is not None:
        repo.reiniciar(pet["id"])

    agente = Agente(pet, repo=repo)
    alertas = 0
    print(f"=== cenario '{cenario}' | pet {pet['nome']} (simulacao local) ===")

    for ts, dist, temp in gerar(cenario, pet):
        agente.receber_temperatura(temp)
        for nome, payload in agente.receber_nivel(ts, dist):
            if nome != "ia_alerta":
                continue
            alertas += 1
            dia = payload["ts"] / 86400
            print(f"\n[ALERTA no dia {dia:.1f}] {payload['status']} - gravidade {payload['gravidade']}")
            print(f"  motivo: {payload['motivo']}")
            analise = payload["analise"]
            print(f"  origem da analise: {analise['origem']}")
            if analise["origem"] != "llm":
                print(f"  motivo do texto padrao: {analise['motivo_padrao']}")
            print(f"  tutor:   {analise['mensagem_tutor']}")
            print(f"  clinica: {analise['resumo_clinica']}")
            for causa in analise["causas_provaveis"]:
                print(f"  - {causa['causa']}: {causa['justificativa']}")
        if atraso:
            time.sleep(atraso)

    refils = sum(1 for e in agente.rastreador.eventos if e.tipo == "reabastecimento")
    print(f"\nresumo: {alertas} alerta(s), {refils} reabastecimento(s) do tutor ignorados no consumo")
    if repo is not None:
        print("tudo foi gravado no banco (clyvo.db) e pode ser consultado pela API")


def rodar_mqtt(cenario, pet, atraso):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print(f"publicando o cenario '{cenario}' ({pet['nome']}) no broker...")

    for ts, dist, temp in gerar(cenario, pet):
        client.publish(topico("temp"), json.dumps({"valor": round(temp, 1), "ts": ts}))
        status = "vazio" if dist > 20 else "ok"
        client.publish(topico("nivel"), json.dumps({"valor": round(dist, 2), "status": status, "ts": ts}))
        time.sleep(atraso)

    time.sleep(1)
    client.loop_stop()
    print("fim do cenario")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cenario", choices=CENARIOS.keys())
    parser.add_argument("--pet", default="rex")
    parser.add_argument("--mqtt", action="store_true", help="publica no broker em vez de rodar local")
    parser.add_argument("--db", action="store_true", help="grava no banco SQLite (para a API e o dashboard)")
    parser.add_argument("--atraso", type=float, default=None,
                        help="segundos entre leituras (deixa a demonstração mais lenta)")
    args = parser.parse_args()

    pet = carregar_pet(args.pet)
    if args.mqtt:
        rodar_mqtt(args.cenario, pet, 0.05 if args.atraso is None else args.atraso)
    else:
        repo = None
        if args.db:
            repo = Repositorio()
            repo.semear_pets()
        rodar_local(args.cenario, pet, repo, args.atraso or 0.0)
