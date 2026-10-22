import argparse
import json
import math
import statistics
import time

import paho.mqtt.client as mqtt

from agente import Agente, MQTT_BROKER, MQTT_PORT, carregar_pet, topico
from consumo import ML_POR_CM, PROFUNDIDADE_CM

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


def rodar_local(cenario, pet):
    agente = Agente(pet)
    alertas = 0
    print(f"=== cenario '{cenario}' | pet {pet['nome']} (simulacao local) ===")

    for ts, dist, temp in gerar(cenario, pet):
        agente.receber_temperatura(temp)