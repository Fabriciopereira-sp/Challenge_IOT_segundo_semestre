import json
from dataclasses import asdict, is_dataclass

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"
TIMEOUT_S = 90

SISTEMA = (
    "Você apoia tutores e clínicas veterinárias interpretando o padrão de consumo "
    "de água de um pet. A detecção e a gravidade já foram calculadas por regras e "
    "você NÃO pode alterá-las. Seu trabalho é interpretar os dados junto com o "
    "perfil do pet. Regras: não faça diagnóstico, trate tudo como possibilidade a "
    "investigar; use somente informações presentes nos dados; relacione as causas "
    "ao perfil (espécie, raça, idade, condições, medicações) e à temperatura quando "
    "fizer sentido; se a gravidade for alta, recomende procurar o veterinário. "
    "Responda apenas com um JSON com as chaves: causas_provaveis (lista de 2 a 4 "
    "objetos com causa e justificativa), perguntas_ao_tutor (lista de 2 a 3 "
    "perguntas curtas), acao_recomendada (texto curto), mensagem_tutor (até 3 "
    "frases, tom acolhedor) e resumo_clinica (até 3 frases, tom técnico e objetivo)."
)

CAUSAS_PADRAO = {
    "queda": [
        ("Água parada ou pote sujo", "Pets podem rejeitar água com cheiro ou sabor alterado."),
        ("Mal-estar ou dor", "Dor de dente, enjoo ou outro desconforto reduzem a vontade de beber."),
        ("Mudança de rotina ou estresse", "Mudanças no ambiente podem alterar o comportamento."),
    ],
    "aumento": [
        ("Calor ou mais atividade", "Dias quentes e exercício aumentam a necessidade de água."),
        ("Alteração metabólica ou renal", "Sede aumentada de forma persistente é algo que o veterinário costuma investigar."),
        ("Efeito de medicação", "Alguns medicamentos aumentam a sede."),
    ],
    "sem_consumo": [
        ("Pet longe do pote", "Ele pode estar fora de casa ou evitando o local do pote."),
        ("Água rejeitada", "Pote sujo ou água parada podem afastar o pet."),
        ("Mal-estar", "Desconforto físico pode reduzir a vontade de beber."),
    ],
}


def _para_dict(avaliacao):
    return asdict(avaliacao) if is_dataclass(avaliacao) else dict(avaliacao)


def _evidencias(avaliacao, pet, contexto):
    a = _para_dict(avaliacao)
    return {
        "pet": {
            "nome": pet.get("nome"),
            "especie": pet.get("especie"),
            "raca": pet.get("raca"),
            "idade_anos": pet.get("idade_anos"),
            "peso_kg": pet.get("peso_kg"),
            "condicoes": pet.get("condicoes", []),
            "medicacoes": pet.get("medicacoes", []),
        },
        "avaliacao": {
            "status": a["status"],
            "gravidade": a["gravidade"],
            "consumo_24h_ml": a["consumo_24h_ml"],
            "esperado_ml": a["esperado_ml"],
            "desvio_pct": a["desvio_pct"],
            "horas_sem_consumo": a["horas_sem_consumo"],
            "dias_de_historico": a["dias_historico"],
        },
        "contexto": contexto,
    }


def _chamar_ollama(evidencias):
    resposta = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
            "messages": [
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": json.dumps(evidencias, ensure_ascii=False, indent=2)},
            ],
        },
        timeout=TIMEOUT_S,
    )
    resposta.raise_for_status()
    return json.loads(resposta.json()["message"]["content"])


def _validar(bruto):
    # só aceita a resposta se vier no formato esperado, senão usa o texto padrão
    if not isinstance(bruto, dict):
        return None

    causas = bruto.get("causas_provaveis")
    perguntas = bruto.get("perguntas_ao_tutor")
    if not isinstance(causas, list) or not isinstance(perguntas, list):
        return None

    causas_ok = []
    for c in causas[:4]:
        if isinstance(c, dict) and isinstance(c.get("causa"), str) and isinstance(c.get("justificativa"), str):
            causas_ok.append({"causa": c["causa"].strip(), "justificativa": c["justificativa"].strip()})
    perguntas_ok = [p.strip() for p in perguntas[:3] if isinstance(p, str) and p.strip()]

    textos = {}
    for chave in ("acao_recomendada", "mensagem_tutor", "resumo_clinica"):
        valor = bruto.get(chave)
        if not isinstance(valor, str) or not valor.strip():
            return None
        textos[chave] = valor.strip()

    if len(causas_ok) < 2 or not perguntas_ok:
        return None

    return {"causas_provaveis": causas_ok, "perguntas_ao_tutor": perguntas_ok, **textos}


def _padrao(avaliacao, pet):
    a = _para_dict(avaliacao)
    nome = pet.get("nome", "O pet")
    causas = [
        {"causa": causa, "justificativa": just}
        for causa, just in CAUSAS_PADRAO.get(a["status"], CAUSAS_PADRAO["queda"])
    ]

    if a["gravidade"] == "alta":
        acao = "Procure o veterinário o quanto antes e leve o registro de consumo."
    else:
        acao = "Observe o comportamento nas próximas horas e troque a água do pote."

    return {
        "causas_provaveis": causas,
        "perguntas_ao_tutor": [
            "O apetite e a disposição estão normais?",
            "Houve mudança de rotina, de ambiente ou de local do pote?",
        ],
        "acao_recomendada": acao,
        "mensagem_tutor": (
            f"{nome} está com o consumo de água fora do padrão ({a['motivo']}). {acao}"
        ),
        "resumo_clinica": (
            f"{nome}: consumo em 24h de {a['consumo_24h_ml']} ml contra {a['esperado_ml']} ml "
            f"esperados ({a['desvio_pct']:+.0f}%), {a['horas_sem_consumo']} h desde o último "
            f"consumo, gravidade {a['gravidade']}."
        ),
    }


def analisar(avaliacao, pet, contexto):
    # tenta a LLM e, se falhar por qualquer motivo, devolve o texto padrão
    try:
        bruto = _chamar_ollama(_evidencias(avaliacao, pet, contexto))
        valido = _validar(bruto)
        if valido:
            return {**valido, "origem": "llm"}
    except (requests.RequestException, ValueError, KeyError):
        pass

    return {**_padrao(avaliacao, pet), "origem": "padrao"}