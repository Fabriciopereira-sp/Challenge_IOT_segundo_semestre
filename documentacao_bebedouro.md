# Documentação técnica da solução de IA - Sprint 4

## 1. Problema de negócio

O bebedouro inteligente da CLYVO VET mede a água disponível para o pet. Saber só se o pote está cheio ou vazio não basta: um dos sinais mais precoces e silenciosos de problemas de saúde (desidratação, doença renal, dor, diabetes) é **mudar a quantidade de água que o pet bebe**. O tutor raramente percebe isso, e a clínica só sabe do problema quando o quadro já avançou.

A IA resolve este problema: **detectar quando o consumo de água do pet foge do padrão dele, explicar as causas prováveis com base no perfil do pet e avisar tutor e clínica**, dentro da jornada contínua de cuidado.

| Quem | Valor entregue |
|---|---|
| Pet | Problemas percebidos mais cedo |
| Tutor | Mensagem simples dizendo o que observar e quando procurar o veterinário |
| Clínica | Resumo técnico com métricas, causas ordenadas e possibilidade de manter o perfil do pet atualizado |

## 2. Abordagem de IA e justificativa

A solução combina duas técnicas, cada uma usada onde é a mais adequada. Esta divisão responde diretamente ao ponto da avaliação anterior de que a LLM estava sendo subutilizada e de que técnicas mais baratas bastariam para detectar o problema.

### 2.1 Detecção: estatística robusta (motor de regras inteligente)

Detectar uma anomalia de consumo é uma conta, e uma conta não precisa de LLM. Por isso a detecção usa:

- **Mediana e MAD** (desvio absoluto mediano) do histórico do pet. A média é frágil, porque um único dia com muita água distorce o padrão. A mediana ignora esse dia.
- **Referência pelo peso** quando há menos de 3 dias de histórico (50 ml por kg por dia, valor geral a ser ajustado com o veterinário). Isso resolve o início de uso de um pet novo.
- **Três situações**: queda (30% ou mais abaixo do esperado), aumento (50% ou mais acima) e sem consumo (pote com água e ninguém bebendo por mais de 12 horas). O limite de 12 horas existe porque o pet passa cerca de 9 horas da noite sem beber, o que é normal.
- **Gravidade**: leve, moderada ou alta, conforme o tamanho do desvio (limites de 45% e 60%). Sempre decidida pelas regras, nunca pela LLM.
- **Aquecimento de 24 horas**: nas primeiras horas o sistema só coleta dados e não alerta.

Por que esta escolha: é barata, roda em qualquer máquina, é determinística e **auditável**. Em saúde, é importante poder explicar por que um alerta foi gerado.

### 2.2 Explicação: IA generativa local (LLM via Ollama)

A LLM entra onde as regras não chegam: **interpretar o contexto do pet e escrever para pessoas diferentes**. O fluxo é:

1. As regras montam uma lista de **causas candidatas**, cada uma com a evidência que vem dos dados (por exemplo, "pet com 12 anos, faixa em que dor e problemas dentários são mais comuns" ou "medicações registradas: benazepril").
2. A LLM recebe o perfil do pet, as métricas e as causas candidatas e devolve, em JSON: as causas **ordenadas da mais para a menos provável** com uma justificativa para cada, perguntas para o tutor, a ação recomendada, a mensagem do tutor e o resumo da clínica.

Por que esta escolha: o mesmo alerta precisa de duas linguagens (acolhedora para o tutor e técnica para a clínica) e de uma priorização que depende do perfil. Isso seria impraticável com textos fixos. Rodar a LLM **localmente via Ollama** evita custo de API e dependência de internet, e mantém os dados de saúde na máquina.

### 2.3 Controle de qualidade da LLM (guardrails)

Modelos pequenos erram. Em testes reais com o modelo llama3.2 observamos erros como inventar medicação e diarreia que não estavam no perfil, inverter a direção do consumo, copiar as instruções do prompt, grudar palavras e recomendar que o tutor ajustasse a medicação. Em vez de confiar no modelo, o sistema o **restringe e valida**:

| Controle | Efeito |
|---|---|
| A LLM só usa os ids das causas candidatas | Não consegue inventar causas |
| Termos sem base (diarreia, vômito, febre, convulsão, medicação inexistente) | Resposta recusada |
| Orientação para ajustar, trocar ou suspender medicação | Resposta recusada, porque o tutor não deve mexer em remédio sozinho |
| Palavras coladas | Resposta recusada |
| Gravidade fixada pelas regras | A LLM não consegue minimizar nem aumentar o alerta |
| Duas tentativas e depois **texto padrão seguro** | O alerta sempre chega, mesmo se o Ollama estiver fora do ar |

Cada alerta guarda a **origem do texto** (`llm` ou `padrao`) e, quando é padrão, o motivo.

### 2.4 Comportamento de agente

O sistema observa, decide e age sem que ninguém peça: lê os dados continuamente, avalia por tempo, escolhe se alerta e publica o resultado. O **gatilho é por tempo** (a cada 5 minutos de dados), e não mais por uma mensagem de "vazio" do sensor, o que corrige a incoerência apontada na avaliação anterior.

Para evitar spam, o alerta tem **cooldown de 6 horas**, e só é repetido antes disso se o status mudar ou a gravidade piorar.

## 3. Dados utilizados

| Dado | Origem | Uso |
|---|---|---|
| Nível da água (distância em cm) | Sensor ultrassônico HC-SR04 no ESP32, via MQTT | Base do cálculo do consumo (1 cm equivale a 40 ml) |
| Temperatura ambiente | Sensor DHT22 no ESP32, via MQTT | Contexto: dia quente torna o consumo baixo mais preocupante |
| Consumo e reabastecimentos | Calculados pelo agente a partir do nível | Alimentam o padrão do pet e a detecção |
| Histórico de consumo diário | Banco SQLite (semente inicial em `pets.json`, depois medições reais) | Mediana e MAD |
| Perfil do pet (espécie, raça, idade, peso) | Cadastro no banco, editável pela clínica | Referência por peso e personalização do texto |
| Condições e medicações | Cadastro no banco, editável pela clínica | Causas candidatas e personalização |

**Como o consumo é calculado:** o nível cai quando o pet bebe. Quedas pequenas (menos de 5 ml) são tratadas como ruído. Uma **subida de 80 ml ou mais** é tratada como **reabastecimento** feito pelo tutor e não conta como consumo, o que responde ao ponto da avaliação sobre o que acontece quando o pote é enchido.

**Dados previstos para evolução:** vacinas, consultas e histórico clínico detalhado ainda não são usados. O banco foi estruturado para recebê-los, e eles enriqueceriam as causas candidatas.

## 4. Arquitetura e fluxo de dados

O diagrama completo está em [diagrama_arquitetura.svg](./diagrama_arquitetura.svg).

1. O **ESP32** publica nível e temperatura no **broker MQTT**.
2. A **aplicação (agente)** consome as mensagens, calcula o consumo e avalia a situação.
3. O agente lê o **perfil do pet** no **banco de dados**.
4. Havendo anomalia, o agente chama a **API de IA (Ollama)** para ordenar e explicar as causas.
5. O agente grava no banco as leituras, os eventos, o estado atual e os alertas.
6. A **API REST (FastAPI)** lê o banco e serve o **dashboard** do tutor e da clínica.
7. A **clínica** atualiza o perfil do pet pela API. Na análise seguinte, o agente já usa o perfil novo.

## 5. Personalização

A personalização acontece em dois níveis:

- **Por pet:** o padrão de consumo é do próprio pet (mediana do histórico dele), e não uma média geral.
- **Por perfil:** idade, peso, condições e medicações entram nas causas e nas justificativas. Em teste, a gata Mimi (12 anos, doença renal, benazepril) recebe causas ligadas à condição e à medicação, enquanto o Rex (9 anos, sem condições) não.

## 6. Verificação

- **58 testes automatizados** (`python -m unittest`) cobrindo o cálculo do consumo, a detecção, o gatilho, a validação da LLM, o agente, o banco e a API.
- **Simulador** com cenários comprimidos no tempo (`normal`, `queda`, `aumento`, `refil`, `sem_consumo`) para demonstrar o sistema sem hardware.
- **Teste com a LLM real** (llama3.2 no Ollama): a saída para o Rex e para a Mimi foi gerada pela LLM, citando apenas dados do perfil.

## 7. Limitações e próximos passos

- O consumo é uma estimativa pela variação do nível. Evaporação e o pet bebendo durante o reabastecimento não são separados.
- O modelo local é pequeno, por isso existem a validação e o texto padrão. Um modelo maior (variável `OLLAMA_MODEL`) melhoraria a escrita.
- O sistema **apoia a decisão e não faz diagnóstico**.
- Próximos passos: usar vacinas e consultas como dados, e ligar o dashboard a um aplicativo móvel do tutor.
