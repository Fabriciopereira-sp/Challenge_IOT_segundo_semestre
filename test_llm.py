import json
import unittest
from unittest.mock import patch

import requests

import llm
from detector import avaliar

REX = {
    "nome": "Rex", "especie": "cachorro", "raca": "Labrador",
    "idade_anos": 9, "peso_kg": 30, "condicoes": [], "medicacoes": [],
}
MIMI = {
    "nome": "Mimi", "especie": "gato", "raca": "SRD", "idade_anos": 12, "peso_kg": 4.5,
    "condicoes": ["doença renal crônica em acompanhamento"],
    "medicacoes": ["benazepril (prescrição veterinária)"],
}
CONTEXTO = {"temperatura_c": 31, "reabastecimentos_24h": 3}


class RespostaFalsa:
    def __init__(self, conteudo):
        self._conteudo = conteudo

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._conteudo}}


def queda_rex():
    return avaliar(700, [1500] * 7, 30, 1.0, 500)


def resposta(causas=None, **extra):
    corpo = {
        "causas_provaveis": causas or [
            {"id": "agua_pote", "justificativa": "Água parada pode afastar o Rex do pote."},
            {"id": "mal_estar", "justificativa": "Aos 9 anos, dor dentária é mais comum."},
        ],
        "perguntas_ao_tutor": ["Ele está comendo normalmente?"],
        "acao_recomendada": "Trocar a água e observar.",
        "mensagem_tutor": "O Rex bebeu menos que o normal hoje.",
        "resumo_clinica": "Queda de consumo em cão de 9 anos.",
    }
    corpo.update(extra)
    return json.dumps(corpo)


class TestCandidatos(unittest.TestCase):
    def ids(self, av, pet, ctx=CONTEXTO):
        return [c["id"] for c in llm.candidatos(llm._para_dict(av), pet, ctx)]

    def test_perfil_sem_medicacao_nao_ganha_causa_de_medicacao(self):
        self.assertNotIn("medicacao", self.ids(queda_rex(), REX))

    def test_perfil_com_condicao_e_medicacao_ganha_as_duas(self):
        av = avaliar(100, [220] * 7, 4.5, 1.0, 500)
        ids = self.ids(av, MIMI)
        self.assertIn("condicao", ids)
        self.assertIn("medicacao", ids)

    def test_calor_so_aparece_quando_o_consumo_aumenta_e_faz_calor(self):
        av = avaliar(2600, [1500] * 7, 30, 1.0, 500)
        self.assertIn("calor", self.ids(av, REX))
        self.assertNotIn("calor", self.ids(av, REX, {"temperatura_c": 20}))
        self.assertNotIn("calor", self.ids(queda_rex(), REX))


class TestLLM(unittest.TestCase):
    @patch("llm.requests.post")
    def test_resposta_valida_usa_a_llm(self, post):
        post.return_value = RespostaFalsa(resposta())
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["origem"], "llm")
        self.assertEqual(r["causas_provaveis"][0]["causa"], "Água parada ou pote sujo")

    @patch("llm.requests.post")
    def test_llm_nao_consegue_mudar_a_gravidade(self, post):
        post.return_value = RespostaFalsa(resposta(gravidade="leve"))
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertNotIn("gravidade", r)

    @patch("llm.requests.post")
    def test_causa_inventada_e_descartada(self, post):
        causas = [
            {"id": "diarreia", "justificativa": "Pode ser diarreia."},
            {"id": "agua_pote", "justificativa": "Água parada afasta o pet."},
        ]
        post.return_value = RespostaFalsa(resposta(causas=causas))
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")
        self.assertEqual(r["motivo_padrao"], "causas_invalidas")

    @patch("llm.requests.post")
    def test_sintoma_sem_base_no_perfil_e_barrado(self, post):
        post.return_value = RespostaFalsa(
            resposta(mensagem_tutor="O Rex pode estar com diarreia.")
        )
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")
        self.assertEqual(r["motivo_padrao"], "termo_sem_base")

    @patch("llm.requests.post")
    def test_medicacao_inventada_para_pet_sem_medicacao_e_barrada(self, post):
        post.return_value = RespostaFalsa(
            resposta(resumo_clinica="O pet toma medicamentos que afetam a sede.")
        )
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["motivo_padrao"], "termo_sem_base")

    @patch("llm.requests.post")
    def test_medicacao_e_aceita_quando_esta_no_perfil(self, post):
        causas = [
            {"id": "medicacao", "justificativa": "O benazepril pode alterar a sede."},
            {"id": "condicao", "justificativa": "A doença renal já é acompanhada."},
        ]
        post.return_value = RespostaFalsa(
            resposta(causas=causas, resumo_clinica="Gata com DRC em uso de medicação.")
        )
        av = avaliar(100, [220] * 7, 4.5, 1.0, 500)
        r = llm.analisar(av, MIMI, CONTEXTO)
        self.assertEqual(r["origem"], "llm")

    @patch("llm.requests.post")
    def test_json_quebrado_cai_no_texto_padrao(self, post):
        post.return_value = RespostaFalsa("isso nao é json")
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["origem"], "padrao")
        self.assertEqual(r["motivo_padrao"], "json_invalido")

    @patch("llm.requests.post", side_effect=requests.ConnectionError())
    def test_ollama_fora_do_ar_cai_no_texto_padrao(self, post):
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        self.assertEqual(r["motivo_padrao"], "ollama_indisponivel")
        self.assertIn("Rex", r["mensagem_tutor"])

    @patch("llm.requests.post", side_effect=requests.ConnectionError())
    def test_texto_padrao_usa_so_fatos_do_perfil(self, post):
        r = llm.analisar(queda_rex(), REX, CONTEXTO)
        causas = [c["causa"] for c in r["causas_provaveis"]]
        self.assertFalse(any("medicação" in c.lower() for c in causas))

    @patch("llm.requests.post")
    def test_prompt_leva_direcao_e_nao_leva_reabastecimento(self, post):
        post.return_value = RespostaFalsa(resposta())
        llm.analisar(queda_rex(), REX, CONTEXTO)
        enviado = post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertIn("ABAIXO do esperado", enviado)
        self.assertNotIn("reabastecimentos", enviado)
        self.assertIn("Labrador", enviado)


if __name__ == "__main__":
    unittest.main(verbosity=2)