import unittest
from unittest import mock

import llm

PET = {"nome": "Mimi", "especie": "gato", "idade_anos": 12,
       "condicoes": ["doença renal crônica em acompanhamento"],
       "medicacoes": ["benazepril (prescrição veterinária)"]}
AV = {"status": "queda", "gravidade": "leve", "consumo_24h_ml": 150, "esperado_ml": 220,
      "desvio_pct": -31.0, "horas_sem_consumo": 3, "motivo": "consumo 31% abaixo do esperado"}


def bruto(tutor="Mimi está bebendo menos água. Observe o comportamento dela.",
          acao="Troque a água do pote.", just="Idade avançada."):
    return {
        "causas_provaveis": [{"id": "agua_pote", "justificativa": just},
                             {"id": "mal_estar", "justificativa": just}],
        "perguntas_ao_tutor": ["O apetite está normal?"],
        "acao_recomendada": acao,
        "mensagem_tutor": tutor,
        "resumo_clinica": "Queda de consumo em paciente renal.",
    }


class TestGuardas(unittest.TestCase):
    def setUp(self):
        self.cands = llm.candidatos(AV, PET, {})

    def test_texto_bom_passa(self):
        r, motivo = llm._validar(bruto(), self.cands, PET)
        self.assertEqual(motivo, "ok")

    def test_tutor_nao_ajusta_medicacao(self):
        r, motivo = llm._validar(
            bruto(tutor="É importante revisar a medicação e ajustá-la."), self.cands, PET)
        self.assertEqual(motivo, "orienta_medicacao")

    def test_palavra_colada_com_maiuscula(self):
        r, motivo = llm._validar(bruto(just="afeta o consumo emMimi."), self.cands, PET)
        self.assertEqual(motivo, "palavras_coladas")

    def test_palavra_colada_com_prefixo(self):
        r, motivo = llm._validar(bruto(just="ajustar amedicação ou a rotina"), self.cands, PET)
        self.assertEqual(motivo, "palavras_coladas")

    def test_palavra_gigante(self):
        r, motivo = llm._validar(bruto(just="causa efeitoscolateraisgraves aqui"), self.cands, PET)
        self.assertEqual(motivo, "palavras_coladas")

    def test_segunda_tentativa_recupera(self):
        ruim = bruto(just="afeta emMimi")
        with mock.patch.object(llm, "_chamar_ollama", side_effect=[ruim, bruto()]) as m:
            r = llm.analisar(AV, PET, {})
        self.assertEqual(r["origem"], "llm")
        self.assertEqual(m.call_count, 2)

    def test_duas_falhas_caem_no_padrao(self):
        ruim = bruto(just="afeta emMimi")
        with mock.patch.object(llm, "_chamar_ollama", side_effect=[ruim, ruim]):
            r = llm.analisar(AV, PET, {})
        self.assertEqual(r["origem"], "padrao")
        self.assertEqual(r["motivo_padrao"], "palavras_coladas")


if __name__ == "__main__":
    unittest.main()
