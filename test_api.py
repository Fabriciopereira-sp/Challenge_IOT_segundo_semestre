import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from api import criar_app
from test_db import rodar_com_banco
from db import Repositorio


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = os.path.join(self.pasta.name, "teste.db")
        self.client = TestClient(criar_app(self.caminho))

    def tearDown(self):
        self.pasta.cleanup()

    def popular(self, cenario="queda"):
        repo = Repositorio(self.caminho)
        rodar_com_banco(repo, cenario)
        repo.fechar()

    def test_saude(self):
        r = self.client.get("/saude")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_lista_os_pets(self):
        r = self.client.get("/pets")
        self.assertEqual([p["id"] for p in r.json()], ["mimi", "rex"])

    def test_pet_inexistente_da_404(self):
        self.assertEqual(self.client.get("/pets/naoexiste").status_code, 404)
        self.assertEqual(self.client.get("/pets/naoexiste/alertas").status_code, 404)

    def test_estado_da_404_antes_de_haver_leituras(self):
        self.assertEqual(self.client.get("/pets/rex/estado").status_code, 404)

    def test_clinica_atualiza_o_perfil(self):
        r = self.client.put("/pets/rex/perfil", json={"peso_kg": 31, "medicacoes": ["prednisona"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["medicacoes"], ["prednisona"])
        self.assertEqual(self.client.get("/pets/rex").json()["peso_kg"], 31)

    def test_perfil_invalido_e_recusado(self):
        r = self.client.put("/pets/rex/perfil", json={"peso_kg": -5})
        self.assertEqual(r.status_code, 422)

    def test_endpoints_refletem_o_que_o_agente_gravou(self):
        self.popular("queda")
        self.assertEqual(self.client.get("/pets/rex/estado").status_code, 200)

        alertas = self.client.get("/pets/rex/alertas").json()
        self.assertTrue(alertas)
        self.assertIn("queda", {a["status"] for a in alertas})

        self.assertTrue(self.client.get("/pets/rex/eventos").json())
        self.assertGreater(len(self.client.get("/pets/rex/consumo").json()["historico_dias_ml"]), 6)

    def test_resumo_da_clinica(self):
        self.popular("queda")
        resumo = self.client.get("/pets/rex/resumo-clinica").json()
        self.assertEqual(resumo["perfil"]["nome"], "Rex")
        self.assertGreaterEqual(resumo["total_alertas"], 1)
        self.assertIn("resumo_clinica", resumo["ultimo_alerta"]["analise"])

    def test_limite_de_alertas_e_validado(self):
        self.assertEqual(self.client.get("/pets/rex/alertas?limite=0").status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
