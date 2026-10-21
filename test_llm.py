import json
import unittest
from unittest.mock import patch

import requests

import llm
from detector import avaliar

PET = {
    "nome": "Rex", "especie": "cachorro", "raca": "Labrador",
    "idade_anos": 9, "peso_kg": 30, "condicoes": [], "medicacoes": [],
}
CONTEXTO = {"temperatura_c": 31, "reabastecimentos_24h": 1}


class RespostaFalsa:
    def __init__(self, conteudo):
        self._conteudo = conteudo

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._conteudo}}


def avaliacao_queda():
    return avaliar(700, [1500] * 7, 30, 1.0, 500)


RESPOSTA_VALIDA = json.dumps({
    "causas_provaveis": [
        {"causa": "Calor", "justificativa": "31 graus aumenta a necessidade de água."},
        {"causa": "Dor", "justificativa": "Cães de 9 anos podem ter dor de dente."},
    ],
    "perguntas_ao_tutor": ["Ele está comendo normalmente?"],
    "acao_recomendada": "Trocar a água e observar.",
    "mensagem_tutor": "O Rex bebeu menos que o normal.",
    "resumo_clinica": "Queda de consumo em cão de 9 anos.",
    "gravidade": "leve",
})


class TestLLM(unittest.TestCase):
    @patch("llm.requests.post")
    def test_resposta_valida_usa_a_llm(self, post):
        post.return_value = RespostaFalsa(RESPOSTA_VALIDA)
        r = llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        self.assertEqual(r["origem"], "llm")
        self.assertGreaterEqual(len(r["causas_provaveis"]), 2)

    @patch("llm.requests.post")
    def test_llm_nao_consegue_mudar_a_gravidade(self, post):
        # a LLM tentou devolver "gravidade": "leve", mas isso é ignorado
        post.return_value = RespostaFalsa(RESPOSTA_VALIDA)
        r = llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        self.assertNotIn("gravidade", r)

    @patch("llm.requests.post")
    def test_json_quebrado_cai_no_texto_padrao(self, post):
        post.return_value = RespostaFalsa("isso nao é json")
        r = llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")

    @patch("llm.requests.post")
    def test_formato_incompleto_cai_no_texto_padrao(self, post):
        post.return_value = RespostaFalsa(json.dumps({"mensagem_tutor": "oi"}))
        r = llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")

    @patch("llm.requests.post", side_effect=requests.ConnectionError())
    def test_ollama_fora_do_ar_cai_no_texto_padrao(self, post):
        r = llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")
        self.assertIn("Rex", r["mensagem_tutor"])

    @patch("llm.requests.post")
    def test_prompt_leva_perfil_e_contexto(self, post):
        post.return_value = RespostaFalsa(RESPOSTA_VALIDA)
        llm.analisar(avaliacao_queda(), PET, CONTEXTO)
        enviado = post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("Labrador", enviado)
        self.assertIn("31", enviado)


if __name__ == "__main__":
    unittest.main(verbosity=2)