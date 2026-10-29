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

    def test_frases_inocentes_sobre_medicacao_passam(self):
        for frase in ("Converse com o veterinário sobre a medicação.",
                      "A medicação pode alterar o apetite.",
                      "Houve alterações na medicação?",
                      "O benazepril é usado para a doença renal."):
            r, motivo = llm._validar(bruto(tutor=frase), self.cands, PET)
            self.assertEqual(motivo, "ok", frase)

    def test_texto_bom_passa(self):
        r, motivo = llm._validar(bruto(), self.cands, PET)
        self.assertEqual(motivo, "ok")

    def test_orientacao_de_medicacao_marca_tutor_inseguro(self):
        r, motivo = llm._validar(
            bruto(tutor="É importante revisar a medicação e ajustá-la."), self.cands, PET)
        self.assertEqual(motivo, "ok")
        self.assertTrue(r["_tutor_inseguro"])

    def test_tutor_inseguro_troca_so_o_texto_do_tutor(self):
        ruim = bruto(tutor="É importante revisar a medicação e ajustá-la.", just="Idade avançada.")
        with mock.patch.object(llm, "_chamar_ollama", return_value=ruim):
            r = llm.analisar(AV, PET, {})
        self.assertEqual(r["origem"], "llm")
        self.assertTrue(r["tutor_texto_seguro"])
        self.assertNotIn("medica", r["mensagem_tutor"].lower())
        self.assertEqual(r["causas_provaveis"][0]["justificativa"], "Idade avançada.")
        self.assertNotIn("_tutor_inseguro", r)

    def test_conserta_cola_com_maiuscula(self):
        r, motivo = llm._validar(bruto(just="afeta o consumo emMimi."), self.cands, PET)
        self.assertEqual(motivo, "ok")
        self.assertIn("em Mimi", r["causas_provaveis"][0]["justificativa"])

    def test_conserta_cola_com_prefixo(self):
        r, motivo = llm._validar(bruto(just="Adoença renal e amedicação atual"), self.cands, PET)
        self.assertEqual(motivo, "ok")
        self.assertEqual(r["causas_provaveis"][0]["justificativa"], "A doença renal e a medicação atual")

    def test_conserta_cola_com_gerundio(self):
        r, motivo = llm._validar(bruto(just="pode estar contribuindopara a queda"), self.cands, PET)
        self.assertEqual(motivo, "ok")
        self.assertIn("contribuindo para", r["causas_provaveis"][0]["justificativa"])

    def test_texto_correto_nao_e_alterado(self):
        frase = "Mimi tem doença renal e usa medicação; segundo o perfil, o consumo caiu."
        r, motivo = llm._validar(bruto(just=frase), self.cands, PET)
        self.assertEqual(r["causas_provaveis"][0]["justificativa"], frase)

    def test_palavra_gigante_sem_conserto_e_recusada(self):
        r, motivo = llm._validar(bruto(just="causa efeitoscolateraisgraves aqui"), self.cands, PET)
        self.assertTrue(motivo.startswith("palavras_coladas"))

    def test_conserta_cola_de_pontuacao_e_substantivo(self):
        r, motivo = llm._validar(
            bruto(just="afeta o consumo de águade Mimi, oque pode ser dor.É importante"),
            self.cands, PET)
        self.assertEqual(motivo, "ok")
        self.assertEqual(r["causas_provaveis"][0]["justificativa"],
                         "afeta o consumo de água de Mimi, o que pode ser dor. É importante")

    def test_decimais_e_abreviacoes_nao_quebram(self):
        frase = "Consumo de 2.6 dias; ex.: dentária (cerca de 12.5 ml)."
        r, motivo = llm._validar(bruto(just=frase), self.cands, PET)
        self.assertEqual(r["causas_provaveis"][0]["justificativa"], frase)

    def test_tutor_em_primeira_pessoa_e_trocado(self):
        ruim = bruto(tutor="Obrigado por sua atenção. Estou preocupado e gostaria de ajudar.")
        with mock.patch.object(llm, "_chamar_ollama", return_value=ruim):
            r = llm.analisar(AV, PET, {})
        self.assertTrue(r["tutor_texto_seguro"])
        self.assertNotIn("Obrigado", r["mensagem_tutor"])

    def test_tutor_falando_de_remedio_e_trocado(self):
        ruim = bruto(tutor="Os efeitos da medicação benazepril podem reduzir o consumo.")
        with mock.patch.object(llm, "_chamar_ollama", return_value=ruim):
            r = llm.analisar(AV, PET, {})
        self.assertTrue(r["tutor_texto_seguro"])

    def test_tutor_bom_e_mantido(self):
        r = None
        with mock.patch.object(llm, "_chamar_ollama", return_value=bruto()):
            r = llm.analisar(AV, PET, {})
        self.assertNotIn("tutor_texto_seguro", r)
        self.assertEqual(r["mensagem_tutor"], "Mimi está bebendo menos água. Observe o comportamento dela.")

    def test_segunda_tentativa_recupera(self):
        ruim = bruto(just="causa efeitoscolateraisgraves aqui")
        with mock.patch.object(llm, "_chamar_ollama", side_effect=[ruim, bruto()]) as m:
            r = llm.analisar(AV, PET, {})
        self.assertEqual(r["origem"], "llm")
        self.assertEqual(m.call_count, 2)

    def test_duas_falhas_caem_no_padrao(self):
        ruim = bruto(just="causa efeitoscolateraisgraves aqui")
        with mock.patch.object(llm, "_chamar_ollama", side_effect=[ruim, ruim]):
            r = llm.analisar(AV, PET, {})
        self.assertEqual(r["origem"], "padrao")
        self.assertTrue(r["motivo_padrao"].startswith("palavras_coladas"))


if __name__ == "__main__":
    unittest.main()
