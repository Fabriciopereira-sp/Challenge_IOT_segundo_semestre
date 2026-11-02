# Evidências: respostas reais da LLM (Ollama, llama3.2)
Alertas extraídos do banco `clyvo.db` gerado na execução do simulador (`python simulador.py queda --pet <pet> --db`). Todos têm `origem_analise = llm`, ou seja, o texto veio do modelo e passou pelas validações.
A mensagem do tutor pode ser substituída pelo texto seguro quando o modelo orienta medicação; nesse caso as causas e o resumo da clínica escritos pela IA são mantidos (ver README, item 5 de "Como funciona").

## Alerta 10 - mimi - queda (leve)
- Origem da análise: **llm**
- Motivo: consumo 31% abaixo do esperado

**Mensagem ao tutor:** Mimi está com o consumo de água fora do padrão (consumo 31% abaixo do esperado). Observe o comportamento nas próximas horas e troque a água do pote.

**Resumo para a clínica:** Mimi está apresentando consumo de água abaixo do esperado, o que pode ser devido a várias causas. É importante avaliar a possibilidade de ajustar a medicação e monitorar seu comportamento, além de verificar se a água está sempre fresca e limpa.

Causas ordenadas pela IA:
- {"causa": "Condição já em acompanhamento", "justificativa": "Devido à doença renal crônica em acompanhamento, é provável que Mimi esteja experimentando desconforto ou dor que afete seu consumo de água."}
- {"causa": "Efeito de medicação em uso", "justificativa": "O benazepril, medicação registrada, pode causar efeitos secundários que afetem o consumo de água de Mimi."}
- {"causa": "Mudança de rotina ou estresse", "justificativa": "A mudança de rotina ou estresse pode ter afetado o comportamento de Mimi, levando a um consumo de água mais baixo."}
- {"causa": "Água parada ou pote sujo", "justificativa": "A água parada ou pote sujo pode ser uma causa menos provável, mas não pode ser descartada, especialmente se Mimi tem um cheiro ou sabor alterado que a afete."}
- {"causa": "Mal-estar ou dor (ex.: dentária)", "justificativa": "O mal-estar ou dor, especialmente dentária, é uma causa menos provável, mas não pode ser descartada, especialmente considerando a idade de Mimi."}

## Alerta 11 - mimi - queda (leve)
- Origem da análise: **llm**
- Motivo: consumo 44% abaixo do esperado

**Mensagem ao tutor:** Mimi está com o consumo de água fora do padrão (consumo 44% abaixo do esperado). Observe o comportamento nas próximas horas e troque a água do pote.

**Resumo para a clínica:** O consumo de água de Mimi está abaixo do esperado. A causa provável é a doença renal crônica em acompanhamento. Vamos verificar se há problemas dentários e ajustar a medicação se necessário.

Causas ordenadas pela IA:
- {"causa": "Condição já em acompanhamento", "justificativa": "Mimi tem doença renal crônica em acompanhamento, o que pode afetar seu consumo de água. A condição já é registrada e tem evidência de que ela pode causar mudanças no comportamento e no consumo de água."}
- {"causa": "Efeito de medicação em uso", "justificativa": "A medicação benazepril pode ter efeito sobre o consumo de água de Mimi. É importante verificar se a medicação está sendo administrada corretamente e se há efeitos colaterais que possam afetar o consumo de água."}
- {"causa": "Mudança de rotina ou estresse", "justificativa": "Mimi é um gato de 12 anos que pode estar com problemas dentários, o que pode causar mal-estar e afetar seu consumo de água. Além disso, mudanças na rotina ou estresse podem afetar o comportamento e o consumo de água."}
- {"causa": "Mal-estar ou dor (ex.: dentária)", "justificativa": "O mal-estar ou dor em Mimi pode ser causado por problemas dentários, o que pode afetar seu consumo de água. É importante verificar se há problemas dentários e se a dor está sendo gerenciada corretamente."}
- {"causa": "Água parada ou pote sujo", "justificativa": "A água parada ou pote sujo pode ser uma causa de redução do consumo de água em Mimi. É importante verificar se o pote está limpo e se a água está fresca."}

## Alerta 12 - mimi - queda (moderada)
- Origem da análise: **llm**
- Motivo: consumo 50% abaixo do esperado

**Mensagem ao tutor:** Mimi está com o consumo de água fora do padrão (consumo 50% abaixo do esperado). Observe o comportamento nas próximas horas e troque a água do pote.

**Resumo para a clínica:** O consumo de água de Mimi está abaixo do esperado, o que pode ser devido a uma condição médica ou a mudanças no ambiente. É importante avaliar a situação e tomar medidas para melhorar o bem-estar do pet.

Causas ordenadas pela IA:
- {"causa": "Condição já em acompanhamento", "justificativa": "A doença renal crônica em acompanhamento é uma condição conhecida que pode afetar o apetite e o consumo de água de um pet. Com 12 anos, Mimi é uma idade em que dor e problemas dentários são mais comuns, o que pode contribuir para o mal-estar e a alteração do consumo."}
- {"causa": "Efeito de medicação em uso", "justificativa": "A medicação benazepril, prescrita para a doença renal crônica, pode ter efeitos colaterais que afetam o apetite e o consumo de água de Mimi."}
- {"causa": "Mudança de rotina ou estresse", "justificativa": "A mudança de rotina ou estresse pode afetar o comportamento de Mimi e contribuir para a alteração do consumo de água."}
- {"causa": "Água parada ou pote sujo", "justificativa": "A água parada ou pote sujo pode ter um cheiro ou sabor alterado que afasta Mimi de beber água."}
- {"causa": "Mal-estar ou dor (ex.: dentária)", "justificativa": "O mal-estar ou dor, possivelmente relacionada a problemas dentários, pode afetar o apetite e o consumo de água de Mimi."}

## Alerta 13 - rex - queda (leve)
- Origem da análise: **llm**
- Motivo: consumo 31% abaixo do esperado

**Mensagem ao tutor:** O Rex está apresentando consumo abaixo do esperado, o que pode ser devido a mudanças na rotina ou estresse. É importante verificar a água e garantir que o pet esteja bem. Além disso, é recomendável uma verificação de saúde para descartar problemas de saúde relacionados ao consumo.

**Resumo para a clínica:** O Rex está apresentando consumo abaixo do esperado, o que pode ser devido a mudanças na rotina ou estresse. É importante verificar a água e garantir que o pet esteja bem. Além disso, é recomendável uma verificação de saúde para descartar problemas de saúde relacionados ao consumo.

Modelo: `llama3.2`

Causas ordenadas pela IA:
- {"causa": "Mudança de rotina ou estresse", "justificativa": "A mudança de rotina ou estresse pode afetar o comportamento do Rex, levando a um consumo abaixo do esperado. Como o pet está em uma faixa de idade em que dor e problemas dentários são mais comuns, é importante verificar se há algum problema de saúde relacionado."}
- {"causa": "Mal-estar ou dor (ex.: dentária)", "justificativa": "O mal-estar ou dor, especialmente em uma faixa de idade em que dor e problemas dentários são mais comuns, pode ser uma causa para o consumo abaixo do esperado do Rex."}
- {"causa": "Água parada ou pote sujo", "justificativa": "A água parada ou pote sujo pode ser uma causa para o consumo abaixo do esperado do Rex, considerando que os pets costumam rejeitar água com cheiro ou sabor alterado."}
