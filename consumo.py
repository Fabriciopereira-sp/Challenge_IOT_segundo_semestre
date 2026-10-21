from dataclasses import dataclass

# calibração do pote (ajustar conforme o pote real)
PROFUNDIDADE_CM = 20.0   # acima disso o firmware já considera o pote vazio
ML_POR_CM = 40.0         # quantos ml cabem em 1 cm de altura de água

REABASTECIMENTO_MIN_ML = 80.0   # subida maior que isso = tutor encheu o pote
CONSUMO_MIN_ML = 5.0            # queda menor que isso é ruído do sensor


def distancia_para_ml(dist_cm):
    # o sensor mede a distância até a água, então quanto maior, menos água
    nivel_cm = PROFUNDIDADE_CM - dist_cm
    nivel_cm = max(0.0, min(PROFUNDIDADE_CM, nivel_cm))
    return nivel_cm * ML_POR_CM


@dataclass
class Evento:
    tipo: str   # "consumo" ou "reabastecimento"
    ts: float
    ml: float


class RastreadorConsumo:
    def __init__(self):
        self.primeiro_ts = None
        self.ultimo_ml = None
        self.ultimo_ts = None
        self.episodio_ml = 0.0
        self.eventos = []

    @property
    def nivel_ml(self):
        return self.ultimo_ml or 0.0

    def _fechar_episodio(self, ts):
        # um episodio é uma sequencia de leituras caindo (o pet bebendo)
        if self.episodio_ml >= CONSUMO_MIN_ML:
            self.eventos.append(Evento("consumo", ts, self.episodio_ml))
        self.episodio_ml = 0.0

    def leitura(self, ts, dist_cm):
        ml = distancia_para_ml(dist_cm)

        if self.ultimo_ml is None:
            self.primeiro_ts = ts
            self.ultimo_ml, self.ultimo_ts = ml, ts
            return

        delta = ml - self.ultimo_ml

        if delta >= REABASTECIMENTO_MIN_ML:
            # nível subiu: foi o tutor, não conta como consumo
            self._fechar_episodio(self.ultimo_ts)
            self.eventos.append(Evento("reabastecimento", ts, delta))
        elif delta < 0:
            self.episodio_ml += -delta
        else:
            self._fechar_episodio(self.ultimo_ts)

        self.ultimo_ml, self.ultimo_ts = ml, ts

    def consumo_janela(self, agora, horas=24):
        inicio = agora - horas * 3600
        total = sum(
            e.ml for e in self.eventos
            if e.tipo == "consumo" and inicio <= e.ts <= agora
        )
        if self.episodio_ml >= CONSUMO_MIN_ML:
            total += self.episodio_ml
        return total

    def horas_sem_consumo(self, agora):
        if self.primeiro_ts is None:
            return None
        consumos = [e.ts for e in self.eventos if e.tipo == "consumo"]
        referencia = max(consumos) if consumos else self.primeiro_ts
        return (agora - referencia) / 3600