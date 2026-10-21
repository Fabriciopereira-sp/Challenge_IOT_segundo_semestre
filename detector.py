import statistics
from dataclasses import dataclass

MIN_DIAS_HISTORICO = 3      # menos que isso, usa o peso do pet como referência
ML_POR_KG_DIA = 50.0        # referência geral de consumo diário (ajustar com o vet)

QUEDA_PCT = 30
AUMENTO_PCT = 50
Z_MIN = 2.0
HORAS_SEM_CONSUMO = 8
NIVEL_COM_AGUA_ML = 100     # abaixo disso o pote está praticamente vazio


@dataclass
class Avaliacao:
    status: str              # normal, queda, aumento ou sem_consumo
    gravidade: str           # nenhuma, leve, moderada ou alta
    consumo_24h_ml: float
    esperado_ml: float
    desvio_pct: float
    z_robusto: float
    base: str                # "historico" ou "peso"
    dias_historico: int
    horas_sem_consumo: float
    motivo: str


def baseline(historico_ml, peso_kg):
    # mediana e MAD aguentam um dia fora da curva, a média não
    if len(historico_ml) >= MIN_DIAS_HISTORICO:
        mediana = statistics.median(historico_ml)
        mad = statistics.median(abs(x - mediana) for x in historico_ml)
        escala = max(1.4826 * mad, 0.10 * mediana)
        return mediana, escala, "historico"

    esperado = peso_kg * ML_POR_KG_DIA
    return esperado, 0.20 * esperado, "peso"


def gravidade_por_desvio(desvio_pct):
    d = abs(desvio_pct)
    if d >= 60:
        return "alta"
    if d >= 45:
        return "moderada"
    return "leve"


def avaliar(consumo_24h_ml, historico_ml, peso_kg, horas_sem_consumo, nivel_ml):
    esperado, escala, base = baseline(historico_ml, peso_kg)
    desvio_pct = (consumo_24h_ml - esperado) / esperado * 100
    z = (consumo_24h_ml - esperado) / escala
    horas = horas_sem_consumo or 0.0

    def montar(status, gravidade, motivo):
        return Avaliacao(
            status, gravidade, round(consumo_24h_ml, 1), round(esperado, 1),
            round(desvio_pct, 1), round(z, 2), base, len(historico_ml),
            round(horas, 1), motivo,
        )

    # pote com agua e ninguem bebendo: é o caso que o gatilho "vazio" nunca pegava
    if horas >= HORAS_SEM_CONSUMO and nivel_ml >= NIVEL_COM_AGUA_ML:
        gravidade = "alta" if horas >= 2 * HORAS_SEM_CONSUMO else "moderada"
        return montar(
            "sem_consumo", gravidade,
            f"{horas:.1f}h sem consumo com o pote ainda com água",
        )

    if desvio_pct <= -QUEDA_PCT and z <= -Z_MIN:
        return montar(
            "queda", gravidade_por_desvio(desvio_pct),
            f"consumo {abs(desvio_pct):.0f}% abaixo do esperado",
        )

    if desvio_pct >= AUMENTO_PCT and z >= Z_MIN:
        return montar(
            "aumento", gravidade_por_desvio(desvio_pct),
            f"consumo {desvio_pct:.0f}% acima do esperado",
        )

    return montar("normal", "nenhuma", "consumo dentro do esperado")


def alerta_pote_vazio(nivel_ml):
    # lembrete simples de reabastecimento, não tem nada de IA aqui
    return nivel_ml < NIVEL_COM_AGUA_ML


class Gatilho:
    # decide quando avaliar (por tempo) e quando vale alertar (sem spam)

    def __init__(self, intervalo_s=300, cooldown_s=6 * 3600):
        self.intervalo_s = intervalo_s
        self.cooldown_s = cooldown_s
        self.ultima_avaliacao = None
        self.ultimo_alerta = None
        self.ultimo_status = "normal"

    def deve_avaliar(self, agora):
        if self.ultima_avaliacao is None:
            return True
        return agora - self.ultima_avaliacao >= self.intervalo_s

    def deve_alertar(self, agora, avaliacao):
        self.ultima_avaliacao = agora

        if avaliacao.status == "normal":
            self.ultimo_status = "normal"
            return False

        mudou = avaliacao.status != self.ultimo_status
        fora_do_cooldown = (
            self.ultimo_alerta is None
            or agora - self.ultimo_alerta >= self.cooldown_s
        )
        self.ultimo_status = avaliacao.status

        if mudou or fora_do_cooldown:
            self.ultimo_alerta = agora
            return True
        return False