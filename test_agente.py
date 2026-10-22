import unittest

from agente import Agente, carregar_pet
from simulador import gerar


def analise_falsa(avaliacao, pet, contexto):
    return {
        "causas_provaveis": [], "perguntas_ao_tutor": [], "acao_recomendada": "",
        "mensagem_tutor": "teste", "resumo_clinica": "teste", "origem": "teste",
    }


def rodar(cenario, nome_pet="rex"):
    pet = carregar_pet(nome_pet)
    agente = Agente(pet, analisar=analise_falsa)
    alertas = []
    for ts, dist, temp in gerar(cenario, pet):
        agente.receber_temperatura(temp)
        for nome, payload in agente.receber_nivel(ts, dist):
            if nome == "ia_alerta":
                alertas.append(payload)
    return agente, alertas


class TestCenarios(unittest.TestCase):
    def test_dia_normal_nao_gera_alerta(self):
        for pet in ("rex", "mimi"):
            _, alertas = rodar("normal", pet)
            self.assertEqual(alertas, [], pet)

    def test_queda_de_consumo_gera_alerta(self):
        _, alertas = rodar("queda")
        self.assertTrue(alertas)
        self.assertEqual(alertas[0]["status"], "queda")

    def test_aumento_de_consumo_gera_alerta(self):
        _, alertas = rodar("aumento")
        self.assertTrue(alertas)
        self.assertEqual(alertas[0]["status"], "aumento")

    def test_reabastecimentos_nao_geram_falso_alerta(self):
        agente, alertas = rodar("refil")
        refils = sum(1 for e in agente.rastreador.eventos if e.tipo == "reabastecimento")
        self.assertGreaterEqual(refils, 10)
        self.assertEqual(alertas, [])

    def test_pote_cheio_sem_consumo_gera_alerta(self):
        _, alertas = rodar("sem_consumo")
        self.assertTrue(alertas)
        self.assertEqual(alertas[0]["status"], "sem_consumo")

    def test_nao_alerta_queda_antes_de_24h_de_dados(self):
        _, alertas = rodar("queda")
        self.assertTrue(all(a["ts"] >= 24 * 3600 for a in alertas))

    def test_cooldown_evita_spam_de_alertas(self):
        _, alertas = rodar("queda")
        for anterior, atual in zip(alertas, alertas[1:]):
            mesmo = (anterior["status"], anterior["gravidade"]) == (atual["status"], atual["gravidade"])
            if mesmo:
                self.assertGreaterEqual(atual["ts"] - anterior["ts"], 6 * 3600)


if __name__ == "__main__":
    unittest.main(verbosity=2)