import json
import os
from dataclasses import asdict, is_dataclass

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
TIMEOUT_S = 120

TEMP_ALTA_C = 28
IDADE_SENIOR = 8

# sintomas que a LLM não pode citar se não estiverem no perfil do pet
TERMOS_SEM_BASE = ("diarre", "vômit", "vomit", "febre", "convuls")

DIRECAO = {
    "queda": "consumo ABAIXO do esperado",
    "aumento": "consumo ACIMA do esperado",
    "sem_consumo": "pote com água e ninguém bebendo há horas",
}

SISTEMA = (
    "Você apoia tutores e clínicas veterinárias. Regras já calcularam a anomalia, "
    "a gravidade e uma lista de causas candidatas, cada uma com sua evidência. "
    "Seu trabalho: (1) ordenar as causas candidatas da mais para a menos provável, "
    "usando SOMENTE os ids fornecidos, e escrever uma justificativa curta para cada "
    "uma, baseada na evidência e no perfil do pet; (2) escrever a mensagem para o "
    "tutor e o resumo para a clínica. Não invente causas, sintomas, medicações ou "
    "dados que não estejam no JSON. Não faça diagnóstico. O campo direcao diz se o "
    "consumo está abaixo ou acima do esperado, nunca inverta isso. Escreva em "
    "português correto, com espaço entre todas as palavras. Não repita estas "
    "instruções. Só recomende procurar o veterinário se a gravidade for alta. "
    'Responda apenas com JSON neste formato: {"causas_provaveis": [{"id": "...", '
    '"justificativa": "..."}], "perguntas_ao_tutor": ["..."], "acao_recomendada": '
    '"...", "mensagem_tutor": "até 3 frases", "resumo_clinica": "até 3 frases"}'
)


def _para_dict(avaliacao):
    return asdict(avaliacao) if is_dataclass(avaliacao) else dict(avaliacao)


def candidatos(a, pet, contexto):
    # as hipóteses saem de regras e dos dados do pet, a LLM só ordena e explica
    status = a["status"]
    idade = pet.get("idade_anos")
    temp = contexto.get("temperatura_c")
    condicoes = pet.get("condicoes", [])
    meds = pet.get("medicacoes", [])
    senior = idade is not None and idade >= IDADE_SENIOR
    lista = []

    def add(cid, causa, evidencia):
        lista.append({"id": cid, "causa": causa, "evidencia": evidencia})

    def mal_estar():
        if senior:
            add("mal_estar", "Mal-estar ou dor (ex.: dentária)",
                f"pet com {idade} anos, faixa em que dor e problemas dentários são mais comuns")
        else:
            add("mal_estar", "Mal-estar ou dor", "desconforto físico reduz a vontade de beber")

    if status == "queda":
        add("agua_pote", "Água parada ou pote sujo",
            "pets costumam rejeitar água com cheiro ou sabor alterado")
        mal_estar()
        if condicoes:
            add("condicao", "Condição já em acompanhamento",
                "condições registradas: " + ", ".join(condicoes))
        if meds:
            add("medicacao", "Efeito de medicação em uso",
                "medicações registradas: " + ", ".join(meds))
        add("rotina", "Mudança de rotina ou estresse",
            "mudanças no ambiente ou na rotina alteram o comportamento")

    elif status == "aumento":
        if temp is not None and temp >= TEMP_ALTA_C:
            add("calor", "Calor", f"temperatura de {temp:.0f} °C")
        add("atividade", "Mais atividade física",
            "exercício aumenta a necessidade de água")
        if condicoes:
            add("condicao", "Condição já em acompanhamento",
                "condições registradas: " + ", ".join(condicoes))
        else:
            extra = f", pet com {idade} anos" if senior else ""
            add("metabolica", "Alteração metabólica ou renal a investigar",
                "sede aumentada de forma persistente costuma ser investigada pelo veterinário" + extra)
        if meds:
            add("medicacao", "Efeito de medicação em uso",
                "medicações registradas: " + ", ".join(meds))

    else:
        add("fora", "Pet longe do pote ou fora de casa",
            "o pote está com água e ninguém bebeu por várias horas")
        add("agua_pote", "Água rejeitada",
            "pote sujo ou água parada podem afastar o pet")
        mal_estar()
        if condicoes:
            add("condicao", "Condição já em acompanhamento",
                "condições registradas: " + ", ".join(condicoes))

    return lista


def fatores_de_atencao(a, pet, contexto):
    fatores = []
    temp = contexto.get("temperatura_c")
    if temp is not None and temp >= TEMP_ALTA_C and a["status"] != "aumento":
        fatores.append(f"dia quente ({temp:.0f} °C): consumo baixo preocupa mais")
    if pet.get("condicoes"):
        fatores.append("pet com condição de saúde em acompanhamento")
    return fatores


def _evidencias(a, pet, contexto, cands):
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
            "direcao": DIRECAO.get(a["status"], a["status"]),
            "gravidade": a["gravidade"],
            "consumo_24h_ml": a["consumo_24h_ml"],
            "esperado_ml": a["esperado_ml"],
            "desvio_pct": a["desvio_pct"],
            "horas_sem_consumo": a["horas_sem_consumo"],
        },
        "temperatura_c": contexto.get("temperatura_c"),
        "fatores_de_atencao": fatores_de_atencao(a, pet, contexto),
        "causas_candidatas": cands,
    }


def _chamar_ollama(evidencias):
    resposta = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2, "num_predict": 700},
            "messages": [
                {"role": "system", "content": SISTEMA},
                {"role": "user", "content": json.dumps(evidencias, ensure_ascii=False, indent=2)},
            ],
        },
        timeout=TIMEOUT_S,
    )
    resposta.raise_for_status()
    return json.loads(resposta.json()["message"]["content"])


def _tem_termo_sem_base(textos, pet):
    # barra sintoma ou medicação que não existe no perfil do pet
    base = " ".join(pet.get("condicoes", []) + pet.get("medicacoes", [])).lower()
    for texto in textos:
        baixo = texto.lower()
        for termo in TERMOS_SEM_BASE:
            if termo in baixo and termo not in base:
                return True
        if "medica" in baixo and not pet.get("medicacoes"):
            return True
    return False


def _validar(bruto, cands, pet):
    # devolve (resposta limpa, motivo). Se algo estiver errado, devolve (None, motivo)
    if not isinstance(bruto, dict):
        return None, "json_invalido"

    causas = bruto.get("causas_provaveis")
    perguntas = bruto.get("perguntas_ao_tutor")
    if not isinstance(causas, list) or not isinstance(perguntas, list):
        return None, "formato_invalido"

    por_id = {c["id"]: c for c in cands}
    causas_ok, vistos = [], set()
    for c in causas:
        if not isinstance(c, dict):
            continue
        cid, just = c.get("id"), c.get("justificativa")
        if cid not in por_id or cid in vistos:
            continue
        if not isinstance(just, str) or not just.strip():
            continue
        vistos.add(cid)
        causas_ok.append({"causa": por_id[cid]["causa"], "justificativa": just.strip()})

    if len(causas_ok) < min(2, len(cands)):
        return None, "causas_invalidas"

    perguntas_ok = [p.strip() for p in perguntas[:3] if isinstance(p, str) and p.strip()]
    if not perguntas_ok:
        return None, "formato_invalido"

    textos = {}
    for chave in ("acao_recomendada", "mensagem_tutor", "resumo_clinica"):
        valor = bruto.get(chave)
        if not isinstance(valor, str) or not valor.strip():
            return None, "formato_invalido"
        textos[chave] = valor.strip()

    todos = (
        list(textos.values()) + perguntas_ok + [c["justificativa"] for c in causas_ok]
    )
    if _tem_termo_sem_base(todos, pet):
        return None, "termo_sem_base"

    resposta = {"causas_provaveis": causas_ok, "perguntas_ao_tutor": perguntas_ok, **textos}
    return resposta, "ok"


def _padrao(a, pet, cands):
    nome = pet.get("nome", "O pet")
    causas = [
        {"causa": c["causa"], "justificativa": c["evidencia"][0].upper() + c["evidencia"][1:] + "."}
        for c in cands[:3]
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
    a = _para_dict(avaliacao)
    cands = candidatos(a, pet, contexto)
    motivo = "ok"

    try:
        bruto = _chamar_ollama(_evidencias(a, pet, contexto, cands))
        valido, motivo = _validar(bruto, cands, pet)
        if valido:
            return {**valido, "origem": "llm"}
    except requests.RequestException:
        motivo = "ollama_indisponivel"
    except (ValueError, KeyError):
        motivo = "json_invalido"

    return {**_padrao(a, pet, cands), "origem": "padrao", "motivo_padrao": motivo}