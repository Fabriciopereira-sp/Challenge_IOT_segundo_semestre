import unittest

from agente import Agente, carregar_pet
from db import Repositorio
from simulador import gerar


def analise_falsa(avaliacao, pet, contexto):
    return {
        "causas_provaveis": [], "perguntas_ao_tutor": [], "acao_recomendada": "",
        "mensagem_tutor": "teste", "resumo_clinica": "teste", "origem": "teste",
    }


def rodar_com_banco(repo, cenario, analisar=analise_falsa, nome_pet="rex"):
    pet = carregar_pet(nome_pet)
    agente = Agente(pet, analisar=analisar, repo=repo)
    for ts, dist, temp in gerar(cenario, pet):
        agente.receber_temperatura(temp)
        agente.receber_nivel(ts, dist)
    return agente


class TestRepositorio(unittest.TestCase):
    def setUp(self):
        self.repo = Repositorio(":memory:")
        self.repo.semear_pets()

    def test_semear_e_idempotente(self):
        self.repo.semear_pets()
        self.assertEqual(len(self.repo.listar_pets()), 2)
        self.assertEqual(len(self.repo.historico("rex")), 7)

    def test_perfil_volta_com_listas(self):
        mimi = self.repo.perfil("mimi")
        self.assertEqual(mimi["especie"], "gato")
        self.assertEqual(mimi["medicacoes"], ["benazepril (prescrição veterinária)"])

    def test_idade_inteira_volta_sem_casa_decimal(self):
        rex = self.repo.perfil("rex")
        self.assertEqual(rex["idade_anos"], 9)
        self.assertIsInstance(rex["idade_anos"], int)
        self.assertEqual(self.repo.perfil("mimi")["peso_kg"], 4.5)

    def test_pet_inexistente_devolve_none(self):
        self.assertIsNone(self.repo.perfil("naoexiste"))

    def test_atualizar_perfil_persiste(self):
        self.repo.atualizar_perfil("rex", peso_kg=31.5, medicacoes=["prednisona"])
        rex = self.repo.perfil("rex")
        self.assertEqual(rex["peso_kg"], 31.5)
        self.assertEqual(rex["medicacoes"], ["prednisona"])

    def test_reiniciar_apaga_o_medido_e_mantem_a_semente(self):
        rodar_com_banco(self.repo, "queda")
        self.repo.reiniciar("rex")
        self.assertEqual(len(self.repo.historico("rex")), 7)
        self.assertEqual(self.repo.alertas("rex"), [])
        self.assertIsNone(self.repo.estado("rex"))


class TestAgenteComBanco(unittest.TestCase):
    def setUp(self):
        self.repo = Repositorio(":memory:")
        self.repo.semear_pets()

    def test_agente_grava_estado_eventos_e_alertas(self):
        rodar_com_banco(self.repo, "queda")
        self.assertIsNotNone(self.repo.estado("rex"))
        self.assertGreater(len(self.repo.eventos("rex", 500)), 0)
        self.assertGreaterEqual(self.repo.total_alertas("rex"), 1)
        self.assertEqual(self.repo.alertas("rex")[0]["analise"]["origem"], "teste")

    def test_reabastecimentos_ficam_registrados_no_banco(self):
        rodar_com_banco(self.repo, "refil")
        tipos = {e["tipo"] for e in self.repo.eventos("rex", 500)}
        self.assertEqual(tipos, {"consumo", "reabastecimento"})
        self.assertEqual(self.repo.total_alertas("rex"), 0)

    def test_dias_fechados_entram_no_historico_do_banco(self):
        rodar_com_banco(self.repo, "normal")
        self.assertGreater(len(self.repo.historico("rex")), 7)

    def test_mudanca_do_perfil_pela_clinica_chega_na_proxima_analise(self):
        vistos = []

        def espiao(avaliacao, pet, contexto):
            vistos.append(list(pet["medicacoes"]))
            return analise_falsa(avaliacao, pet, contexto)

        self.repo.atualizar_perfil("rex", medicacoes=["prednisona"])
        rodar_com_banco(self.repo, "queda", analisar=espiao)
        self.assertTrue(vistos)
        self.assertEqual(vistos[0], ["prednisona"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
