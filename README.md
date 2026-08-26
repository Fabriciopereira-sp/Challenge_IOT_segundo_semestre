markdown
# CLYVO VET — Agente de IA do Bebedouro Inteligente

Componente de Inteligência Artificial da disciplina **Disruptive
Architectures: IoT, IoB & Generative IA**, desenvolvido em cima do
projeto do bebedouro inteligente CLYVO VET.

Projeto original (Sprint 1 e 2 — hardware e dashboard):
[https://github.com/Fabriciopereira-sp/IOT_challenge_2026.git]

## Integrantes

- Fabrício Henrique Pereira — RM563237
- Henrique Sinkevicius Maran — RM562977
- Leonardo José Pereira — RM563065
- Miguel Henrique Oliveira Dias — RM565492
- Pedro Henrique de Oliveira — RM562312

## Entrega — Sprint 3

- Vídeo pitch: [colar aqui o link do YouTube]
- Documentação completa (problema, abordagem de IA, dados utilizados): [documentacao_bebedouro.md](./documentacao_bebedouro.md)
- Diagrama de arquitetura: [diagrama_arquitetura.svg](./diagrama_arquitetura.svg)

## O que este agente faz

1. Observa os dados do bebedouro (nível de água, temperatura) publicados
   via MQTT pelo ESP32.
2. Compara o consumo de água do pet com a média histórica dos últimos
   dias, detectando automaticamente padrões anômalos (ex: consumo muito
   abaixo do normal, indicando risco de desidratação/problema renal).
3. Quando uma anomalia é detectada, aciona um modelo de IA generativa
   (LLM) rodando localmente via **Ollama** para gerar uma mensagem de
   alerta personalizada e humanizada para o tutor do pet.
4. Publica essa mensagem de volta via MQTT, para ser exibida no
   dashboard.

## Como rodar

### 1. Instalar o Ollama

Baixe e instale em: https://ollama.com/download

### 2. Baixar o modelo de IA (grátis, roda local)

ollama pull llama3.2


### 3. Instalar as dependências Python

pip install -r requirements.txt


### 4. Rodar o agente em modo simulado

python agente_bebedouro.py simulado


### 5. (Opcional) Rodar em modo tempo real, conectado ao ESP32

python agente_bebedouro.py mqtt


## Estrutura dos arquivos

├── agente_bebedouro.py # Script principal do agente
├── dataset_historico.json # Dados simulados de consumo (7 dias)
├── requirements.txt # Dependências Python
├── documentacao_bebedouro.md # Problema, abordagem e dados (Sprint 3)
├── diagrama_arquitetura.svg # Diagrama arquitetural
└── README.md # Este arquivo


## Tecnologias utilizadas

- **Python** — lógica do agente
- **paho-mqtt** — comunicação com o broker MQTT (broker.hivemq.com),
  o mesmo já usado no firmware do ESP32
- **Ollama** — execução local de LLM (IA generativa), sem custo e sem
  necessidade de internet ou chave de API
- Detecção de anomalia por comparação estatística entre o consumo
  atual e a média histórica de consumo do pet

## Resultados parciais

O agente foi testado em modo simulado com um cenário de queda de
consumo (dataset com pet "Rex" bebendo 480ml, contra uma média
histórica de ~802ml), detectando corretamente a anomalia e gerando a
mensagem de alerta via IA local.