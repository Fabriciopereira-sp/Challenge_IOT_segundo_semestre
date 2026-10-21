import statistics
import unittest

from consumo import RastreadorConsumo, PROFUNDIDADE_CM, ML_POR_CM
from detector import avaliar, alerta_pote_vazio, Gatilho


def dist_de(ml):
    return PROFUNDIDADE_CM - ml / ML_POR_CM


def alimentar(rast, pontos):
    # pontos: lista de (ts, ml)
    for ts, ml in pontos:
        rast.leitura(ts, dist_de(ml))


class TestConsumo(unittest.TestCase):
    def test_reabastecimento_nao_conta_como_consumo(self):
        r = RastreadorConsumo()
        alimentar(r, [(0, 400), (3, 370), (6, 370), (9, 800), (12, 780), (15, 780)])
        self.assertEqual(sum(1 for e in r.eventos if e.tipo == "reabastecimento"), 1)
        self.assertAlmostEqual(r.consumo_janela(15), 50, places=1)

    def test_reabastecer_no_meio_do_dia_nao_distorce_o_consumo(self):
        # o pet bebe 40 + 40 + 40 + 60 = 180 ml e o tutor enche o pote uma vez
        r = RastreadorConsumo()
        alimentar(r, [(0, 800), (3, 760), (6, 760), (9, 720), (12, 720),
                      (15, 800), (18, 760), (21, 760), (24, 700)])
        self.assertAlmostEqual(r.consumo_janela(24), 180, places=1)
        # a conta ingênua (nível inicial - nível final) erraria por causa do refil
        ingenuo = 800 - 700
        self.assertNotEqual(round(r.consumo_janela(24)), ingenuo)

    def test_ruido_pequeno_e_ignorado(self):
        r = RastreadorConsumo()
        alimentar(r, [(0, 600), (3, 598), (6, 600), (9, 597), (12, 600)])
        self.assertEqual(r.consumo_janela(12), 0)


class TestDetector(unittest.TestCase):
    def test_dia_normal_nao_alerta(self):
        a = avaliar(780, [780, 810, 795, 820, 805, 790, 815], 12, 1.0, 500)
        self.assertEqual(a.status, "normal")

    def test_mediana_resiste_a_dia_atipico_e_media_nao(self):
        historico = [800, 810, 790, 200, 805, 795, 815]
        consumo = 540
        media = statistics.mean(historico)
        desvio_media = (consumo - media) / media * 100
        self.assertGreater(desvio_media, -30)  # pela média passaria batido
        a = avaliar(consumo, historico, 12, 1.0, 500)
        self.assertEqual(a.status, "queda")

    def test_partida_a_frio_usa_peso(self):
        a = avaliar(250, [], 12, 1.0, 500)
        self.assertEqual(a.base, "peso")
        self.assertEqual(a.status, "queda")
        self.assertEqual(a.gravidade, "moderada")

    def test_aumento_de_consumo(self):
        a = avaliar(1300, [800, 810, 790, 805, 795, 815, 800], 12, 1.0, 500)
        self.assertEqual(a.status, "aumento")

    def test_pote_cheio_sem_consumo_alerta_sem_nunca_ficar_vazio(self):
        r = RastreadorConsumo()
        pontos = [(h * 3600, 700) for h in range(0, 11)]
        alimentar(r, pontos)
        agora = 10 * 3600
        self.assertFalse(alerta_pote_vazio(r.nivel_ml))
        a = avaliar(r.consumo_janela(agora), [800] * 7, 12,
                    r.horas_sem_consumo(agora), r.nivel_ml)
        self.assertEqual(a.status, "sem_consumo")

    def test_pote_vazio_nao_e_tratado_como_sem_consumo(self):
        a = avaliar(300, [800] * 7, 12, 10.0, 20)
        self.assertNotEqual(a.status, "sem_consumo")


class TestGatilho(unittest.TestCase):
    def test_avalia_por_tempo_e_respeita_cooldown(self):
        g = Gatilho(intervalo_s=300, cooldown_s=3600)
        self.assertTrue(g.deve_avaliar(0))
        a = avaliar(250, [800] * 7, 12, 1.0, 500)
        self.assertTrue(g.deve_alertar(0, a))
        self.assertFalse(g.deve_avaliar(100))
        self.assertTrue(g.deve_avaliar(300))
        self.assertFalse(g.deve_alertar(300, a))     # mesmo status, dentro do cooldown
        self.assertTrue(g.deve_alertar(4000, a))     # passou o cooldown


if __name__ == "__main__":
    unittest.main(verbosity=2)