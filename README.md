# CLYVO VET - Bebedouro Inteligente com IA

Componente de Inteligência Artificial da disciplina **Disruptive Architectures: IoT, IoB & Generative IA**, construído sobre o bebedouro inteligente da CLYVO VET.

O bebedouro mede a água do pet. A solução transforma essas medidas em **consumo diário**, compara com o **padrão do próprio pet** e, quando algo foge do normal, gera um alerta com **causas prováveis explicadas por uma IA generativa local**. O tutor vê a mensagem simples e a clínica vê o resumo técnico, e a clínica ainda pode atualizar o perfil do pet, que passa a ser usado na análise seguinte.

> Projeto original (Sprint 1 e 2, hardware): [IOT_challenge_2026](https://github.com/Fabriciopereira-sp/IOT_challenge_2026.git)

## Integrantes

| Nome | RM |
|---|---|
| Fabrício Henrique Pereira | 563237 |
| Henrique Sinkevicius Maran | 562977 |
| Leonardo José Pereira | 563065 |
| Miguel Henrique Oliveira Dias | 565492 |
| Pedro Henrique de Oliveira | 562312 |

## Entrega - Sprint 4

| Item | Link |
|---|---|
| Vídeo (YouTube, não listado) | **[colar aqui o link do vídeo da Sprint 4]** |
| Documentação técnica | [documentacao_bebedouro.md](./documentacao_bebedouro.md) |
| Diagrama de arquitetura | [diagrama_arquitetura.svg](./diagrama_arquitetura.svg) |
| Entrega anterior (Sprint 3) | [sprint3/](./sprint3/) |

## O que mudou da Sprint 3 para a Sprint 4

A avaliação da Sprint 3 trouxe quatro pontos. Cada um virou uma mudança concreta:

| Ponto levantado | O que foi feito |
|---|---|
| A LLM era subutilizada e técnicas mais baratas serviriam | A **detecção é feita por estatística** (barata e auditável). A LLM só faz o que as regras não fazem: ordenar causas candidatas, justificá-las com os dados do pet e escrever o texto para tutor e clínica. |
| Cálculo só pela média é frágil; e quando o tutor enche o pote? | Uso de **mediana e MAD**, que aguentam um dia fora da curva. O consumo vem das **leituras de nível** e uma subida brusca é tratada como **reabastecimento**, que não conta como consumo. |
| Gatilho incoerente: o cálculo só rodava com `msg == "vazio"` | A análise agora é **disparada por tempo** (a cada 5 minutos de dados), independente de o pote estar vazio. O "vazio" virou só um aviso à parte. |
| Projeto simples, mas atende a rubrica | Foram integrados **banco de dados SQLite, API REST e dashboard** com duas visões (tutor e clínica), e o perfil do pet passou a alimentar a IA. |

## Como funciona

1. O ESP32 publica nível de água e temperatura no broker MQTT.
2. O agente calcula o consumo, descarta ruído e reabastecimentos e mede o desvio contra o padrão do pet.
3. Se há anomalia (queda, aumento ou sem consumo), classifica a gravidade (leve, moderada ou alta).
4. As **regras** montam uma lista de causas candidatas, cada uma com a evidência dos dados. A **LLM só ordena e justifica** essas causas, sem poder inventar outras nem mudar a gravidade.
5. A resposta da LLM é **validada**. Se citar sintoma ou remédio que não está no perfil, mandar o tutor mexer em medicação ou vier com palavras coladas, ela é recusada, tenta-se uma segunda vez e, se falhar de novo, usa-se um texto padrão seguro.
6. Leituras, eventos e alertas são gravados no banco. A API serve esses dados para o dashboard.

## Como rodar

### 1. Instalar o Ollama e o modelo

Baixe em [ollama.com/download](https://ollama.com/download) e, com ele aberto:

```bash
ollama pull llama3.2
```

### 2. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 3. Gerar dados com o simulador (grava no banco)

Cenários: `normal`, `queda`, `aumento`, `refil`, `sem_consumo`. Pets: `rex` e `mimi`.

```bash
python simulador.py queda --db
python simulador.py queda --pet mimi --db
```

Sem `--db` o simulador só imprime o resultado na tela.

### 4. Subir a API e o dashboard

```bash
python api.py
```

Abra `http://127.0.0.1:8000` para o dashboard (abas **Tutor** e **Clínica**) e `http://127.0.0.1:8000/docs` para a documentação interativa da API.

### 5. Rodar os testes

```bash
python -m unittest
```

### 6. (Opcional) Tempo real com o ESP32

```bash
python agente.py --pet rex
```

O agente escuta o broker `broker.hivemq.com` no prefixo `clyvo/vet/s4-rm563237/bebedouro`.

### Trocar o modelo de IA

Se o professor indicar outro modelo, baixe-o com `ollama pull <modelo>` e rode com a variável `OLLAMA_MODEL` (por exemplo `OLLAMA_MODEL=llama3.1:8b`).

## Estrutura dos arquivos

```
consumo.py        Calcula o consumo a partir das leituras de nível
detector.py       Mediana + MAD, gravidade e gatilho por tempo
llm.py            Causas candidatas, chamada ao Ollama e validação
agente.py         Une tudo e escuta o MQTT
simulador.py      Cenários de teste sem hardware
db.py             Banco SQLite (pets, consumo, eventos, alertas, estado)
api.py            API REST (FastAPI)
dashboard.html    Telas do tutor e da clínica
pets.json         Perfis iniciais dos pets (Rex e Mimi)
test_*.py         58 testes automatizados
sprint3/          Entrega anterior, mantida como histórico
```

## API

| Método | Rota | Para que serve |
|---|---|---|
| GET | `/pets` | Lista os pets |
| GET | `/pets/{id}` | Perfil do pet |
| PUT | `/pets/{id}/perfil` | A clínica atualiza idade, peso, condições e medicações |
| GET | `/pets/{id}/estado` | Situação atual (nível, consumo, status) |
| GET | `/pets/{id}/alertas` | Alertas gerados pela IA |
| GET | `/pets/{id}/consumo` | Histórico de consumo diário |
| GET | `/pets/{id}/eventos` | Consumos e reabastecimentos detectados |
| GET | `/pets/{id}/resumo-clinica` | Visão consolidada para a clínica |
| GET | `/saude` | Verifica se a API está no ar |

## Tecnologias

- **Python 3**: lógica do agente e testes (`unittest`)
- **paho-mqtt**: comunicação com o broker MQTT
- **Ollama (llama3.2)**: IA generativa local, sem custo e sem chave de API
- **SQLite**: banco de dados da aplicação
- **FastAPI + Uvicorn**: API REST e entrega do dashboard
- **HTML, CSS e JavaScript**: dashboard, sem bibliotecas externas

## Resultados parciais

- **58 testes automatizados passando**, cobrindo consumo, detecção, validação da IA, agente, banco e API.
- **Queda de consumo**: nos cenários simulados, o sistema detecta a queda e classifica a gravidade (por exemplo, 31% abaixo do esperado é leve e 50% é moderada).
- **Reabastecimento**: quando o tutor enche o pote, o aumento de nível é reconhecido como reabastecimento e não conta como consumo.
- **Personalização**: para a gata Mimi, com doença renal e uso de benazepril, a IA cita a condição e a medicação registradas no perfil. Para o Rex, que não tem condições, ela não cita nenhuma.
- **Segurança do texto**: respostas com fatos inventados, orientação para o tutor mexer em medicação ou palavras coladas são recusadas, e o sistema usa um texto padrão.

## Limitações

- O consumo é estimado pela variação do nível. Evaporação e pet bebendo durante um reabastecimento não são distinguidos.
- A referência inicial de 50 ml por kg por dia é geral e deveria ser ajustada com o veterinário.
- O modelo local é pequeno e eventualmente erra a escrita, e a validação existe justamente para isso.
- O sistema apoia a decisão, **não faz diagnóstico**.
