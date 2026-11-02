import contextlib
import io
import unittest
from unittest import mock

import requests

import detector
import llm
import simulador
from agente import carregar_pet


class TestHistoricoZerado(unittest.TestCase):
    def test_historico_so_de_zeros_nao_quebra_e_usa_o_peso(self):
        av = detector.avaliar(0, [0, 0, 0, 0], 4.5, 3.0, 500)
        self.assertEqual(av.base, "peso")
        self.assertEqual(av.esperado_ml, 225.0)
        self.assertEqual(av.status, "queda")

    def test_mediana_zero_com_alguns_dias_de_consumo(self):
        av = detector.avaliar(100, [0, 0, 0, 300, 250], 4.5, 3.0, 500)
        self.assertEqual(av.base, "peso")

    def test_peso_zero_nao_divide_por_zero(self):
        av = detector.avaliar(10, [], 0, 3.0, 500)
        self.assertGreater(av.esperado_ml, 0)

    def test_historico_normal_continua_usando_o_historico(self):
        av = detector.avaliar(220, [210, 225, 218, 230], 4.5, 3.0, 500)
        self.assertEqual(av.base, "historico")
        self.assertEqual(av.status, "normal")


class TestMaxAlertas(unittest.TestCase):
    def rodar(self, **kwargs):
        saida = io.StringIO()
        with mock.patch.object(llm, "_chamar_ollama", side_effect=requests.ConnectionError()):
            with contextlib.redirect_stdout(saida):
                simulador.rodar_local("queda", carregar_pet("mimi"), **kwargs)
        return saida.getvalue()

    def test_sem_limite_gera_todos_os_alertas(self):
        self.assertEqual(self.rodar().count("[ALERTA"), 3)

    def test_max_alertas_para_depois_do_primeiro(self):
        self.assertEqual(self.rodar(max_alertas=1).count("[ALERTA"), 1)


if __name__ == "__main__":
    unittest.main()
