# 🐾 CLYVO VET — Agente de IA do Bebedouro Inteligente

Componente de Inteligência Artificial da disciplina **Disruptive Architectures: IoT, IoB & Generative IA**, desenvolvido em cima do projeto do bebedouro inteligente CLYVO VET.

> 🔗 Projeto original (Sprint 1 e 2 — hardware e dashboard): [IOT_challenge_2026](https://github.com/Fabriciopereira-sp/IOT_challenge_2026.git)

---

## 👥 Integrantes

| Nome | RM |
|---|---|
| Fabrício Henrique Pereira | 563237 |
| Henrique Sinkevicius Maran | 562977 |
| Leonardo José Pereira | 563065 |
| Miguel Henrique Oliveira Dias | 565492 |
| Pedro Henrique de Oliveira | 562312 |

---

## 📦 Entrega — Sprint 3

| Item | Link |
|---|---|
| 🎥 Vídeo pitch | [https://youtu.be/Jtuh3-_sWXM] |
| 📄 Documentação completa | [documentacao_bebedouro.md](./documentacao_bebedouro.md) |
| 🗺️ Diagrama de arquitetura | [diagrama_arquitetura.svg](./diagrama_arquitetura.svg) |

---

## 🧠 O que este agente faz

1. **Observa** os dados do bebedouro (nível de água, temperatura) publicados via MQTT pelo ESP32.
2. **Compara** o consumo de água do pet com a média histórica dos últimos dias, detectando automaticamente padrões anômalos — como uma queda que pode indicar risco de desidratação ou problema renal.
3. Quando uma anomalia é detectada, **aciona um modelo de IA generativa (LLM)** rodando localmente via **Ollama**, que gera uma mensagem de alerta personalizada e humanizada para o tutor do pet.
4. **Publica** essa mensagem de volta via MQTT, para ser exibida no dashboard.

---

## ▶️ Como rodar

### 1. Instalar o Ollama

Baixe e instale em: [ollama.com/download](https://ollama.com/download)

### 2. Baixar o modelo de IA (grátis, roda local)

```bash
ollama pull llama3.2
```

### 3. Instalar as dependências Python

```bash
pip install -r requirements.txt
```

### 4. Rodar o agente em modo simulado

```bash
python agente_bebedouro.py simulado
```

### 5. (Opcional) Rodar em modo tempo real, conectado ao ESP32

```bash
python agente_bebedouro.py mqtt
```

---

## 📁 Estrutura dos arquivos

├── agente_bebedouro.py # Script principal do agente
├── dataset_historico.json # Dados simulados de consumo (7 dias)
├── requirements.txt # Dependências Python
├── documentacao_bebedouro.md # Problema, abordagem e dados (Sprint 3)
├── diagrama_arquitetura.svg # Diagrama arquitetural
└── README.md # Este arquivo


---

## 🛠️ Tecnologias utilizadas

- **Python** — lógica do agente
- **paho-mqtt** — comunicação com o broker MQTT (`broker.hivemq.com`), o mesmo já usado no firmware do ESP32
- **Ollama** — execução local de LLM (IA generativa), sem custo e sem necessidade de internet ou chave de API
- **Detecção de anomalia** por comparação estatística entre o consumo atual e a média histórica de consumo do pet

---

## ✅ Resultados parciais

O agente foi testado em modo simulado com um cenário de queda de consumo — dataset com o pet "Rex" bebendo 480ml, contra uma média histórica de ~802ml — detectando corretamente a anomalia (queda de 40,2%) e gerando a mensagem de alerta via IA local com sucesso.