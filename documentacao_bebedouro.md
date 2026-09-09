# Documentação da Solução de IA — Sprint 3

## 1. Problema de Negócio

O bebedouro inteligente da CLYVO VET monitora, em tempo real, o nível de
água disponível para o pet. No entanto, apenas saber se o bebedouro está
cheio ou vazio não é suficiente para prevenir um dos riscos mais comuns e
silenciosos na saúde de pets: a **queda gradual no consumo de água**, que
pode indicar desidratação, início de doenças renais ou outros problemas
de saúde — muitas vezes antes que o tutor perceba qualquer sintoma
visível.

O problema que a IA resolve é: **detectar automaticamente quando o
consumo de água de um pet está significativamente abaixo do seu padrão
habitual, e comunicar isso ao tutor de forma clara e imediata**, para que
ele possa agir (levar ao veterinário, verificar o ambiente, checar se o
pet está doente) antes que o quadro se agrave.

Esse problema se encaixa diretamente na jornada contínua de cuidado do
pet: o bebedouro deixa de ser apenas um sensor de nível e passa a ser um
ponto de monitoramento de saúde preventivo.

## 2. Abordagem de IA Escolhida e Justificativa

A solução combina duas técnicas complementares, formando um **agente de
IA** que observa os dados, decide quando agir e executa uma ação sozinho:

### 2.1 Detecção de anomalia (motor de regras estatístico)

O consumo de água do dia é comparado com a média de consumo dos últimos
7 dias do mesmo pet. Se a queda for igual ou superior a 30%, o sistema
classifica isso como uma anomalia.

**Por que essa abordagem:**
- É interpretável: qualquer pessoa entende a lógica ("hoje ele bebeu bem
  menos que o normal")
- Não exige treinamento de modelo nem grande volume de dados históricos
  para funcionar, o que é adequado para um produto que está começando a
  coletar dados de cada pet
- É computacionalmente leve, podendo rodar em um dispositivo simples

### 2.2 IA Generativa (LLM local via Ollama)

Quando uma anomalia é detectada, os dados brutos (percentual de queda,
temperatura do dia, nome do pet) são enviados a um modelo de linguagem
(LLM) rodando localmente via Ollama, que gera uma mensagem de alerta
personalizada e humanizada para o tutor.

**Por que essa abordagem:**
- Transforma um dado técnico ("queda de 40%") em uma comunicação clara e
  empática, mais próxima de como um veterinário explicaria a situação
- Rodar localmente via Ollama elimina custos com APIs pagas e dependência
  de internet, o que é vantajoso para um produto pensado para clínicas e
  tutores de diferentes portes
- Permite personalização (usa o nome do pet, o contexto climático, o
  grau de gravidade) sem precisar programar manualmente cada variação de
  mensagem

### 2.3 Comportamento de agente

O sistema não espera que o tutor pergunte nada: ele observa os dados
continuamente, decide sozinho quando uma situação exige atenção, e age
gerando e publicando o alerta de forma autônoma. Esse comportamento
caracteriza um **agente de IA**, diferente de um simples chatbot que
apenas responde perguntas.

## 3. Dados Utilizados

| Dado | Origem | Uso na solução |
|---|---|---|
| Nível de água (cm) | Sensor ultrassônico HC-SR04 (ESP32) | Indica se o bebedouro está com água disponível |
| Temperatura ambiente (°C) | Sensor DHT22 (ESP32) | Contextualiza o risco (dias quentes aumentam a necessidade de hidratação) e é usado na mensagem gerada pela IA |
| Consumo diário estimado (ml) | Calculado a partir das leituras de nível ao longo do dia | Base para o cálculo da média histórica e detecção de anomalia |
| Histórico dos últimos 7 dias | Armazenado (simulado em `dataset_historico.json` nesta etapa; em produção viria do banco de dados da aplicação) | Referência para calcular a média de consumo esperado do pet |
| Nome/perfil do pet | Cadastro do tutor no aplicativo | Personalização da mensagem gerada pela IA |

Nesta Sprint 3, os dados históricos estão simulados em um arquivo JSON
(`dataset_historico.json`) para permitir o desenvolvimento e teste da
lógica de IA de forma independente, sem depender da finalização do banco
de dados relacional/NoSQL do projeto (desenvolvido em outra disciplina
do Challenge). Na Sprint 4, essa fonte de dados será substituída pela
integração real com o banco de dados da aplicação.