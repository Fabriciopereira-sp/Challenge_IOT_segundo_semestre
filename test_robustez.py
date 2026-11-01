import unittest

import detector


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


if __name__ == "__main__":
    unittest.main()
