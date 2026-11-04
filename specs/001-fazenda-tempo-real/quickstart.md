# Guia de execução e verificação — Fazenda em tempo real

Este guia descreve a verificação após implementar cada etapa do [plano](plan.md). O servidor e o cliente ainda são o kit inicial; este documento não declara que os comportamentos ou os testes já existem.

## Preparação

Na raiz do repositório, usar Python 3.11 ou superior e as dependências do kit. Se `.venv` ainda não existir:

```sh
python3 -m venv .venv
```

Ativar e instalar:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Usar um processo, sem `--workers` adicionais. Para os roteiros temporizados, não usar recarga automática: editar um arquivo/reiniciar o processo reinicia a vila. O endereço é `http://127.0.0.1:8000`. O navegador precisa carregar as CDNs de Vue, Socket.IO e Phaser.

Abrir três abas: **M** como Mestre, **A** como Jogador A e **B** como Jogador B. Duas abas bastam para ensaiar fluxos sem disputa, mas registrar a aceitação de cada etapa com as três. Desmarcar “ocultar recurso.produzido” para observar causalidade. O painel mostra os eventos mais recentes no topo e guarda um histórico limitado; registrar a evidência antes que saia da lista.

Para começar uma temporada independente, parar o servidor com Ctrl+C, iniciá-lo novamente e recarregar as abas. Isso é reinício do ambiente de teste, não funcionalidade de reabertura da temporada.

## V1 — Conexão

1. Entrar nas três abas. Esperado em todas: tema Fazenda, fase aguardando, trigo 150, farinha 0, agricultores 0/3 e zero obras.
2. Confirmar um `estado.sincronizado` na entrada de cada aba, com causa `conexao`, estado e reação. Entrar B não acrescenta snapshot nos painéis de M e A.
3. Recarregar B. Os estoques e contadores de M/A não mudam; B recebe o estado atual. Não há desenhos duplicados.
4. Repetir a entrada tardia depois que existirem obras na etapa 4; B deve representar a mesma vila sem repetir débitos ou reiniciar barras em oito segundos.

## V2 — Abertura

1. Com três abas conectadas e vila aguardando, M clica Abrir temporada.
2. Confirmar o pedido no painel de M e `vila.iniciada` nas três abas, com causa `vila.abertura_solicitada`; fase aberta e sem crédito imediato de trigo.
3. M clica Abrir novamente. Apenas M recebe `operacao.recusada`, motivo “A temporada já foi aberta”; A/B não recebem essa recusa e os ciclos não reiniciam.
4. Validar pedido de abertura por Jogador nos testes automatizados, já que o botão não está disponível para esse papel. Ausência do botão não comprova validação no servidor.

A etapa 2 verifica abertura; produção passa a ser exigida no roteiro da etapa 4.

## V3 — Construções e recusas

1. Em temporada nova ainda aguardando, A clica Construir. Apenas A vê “A temporada não está aberta”, sem mudança dos 150 de trigo nem da ocupação; M/B não recebem evento causado por essa recusa.
2. M abre e A constrói. As três abas recebem `construcao.iniciada`: trigo −50, agricultores +1, obra em andamento +1, com causa `construcao.solicitada` e identidade da obra.
3. Conferir que o desenho usa o fato recebido e que o pedido sozinho não debita trigo no cliente.
4. Executar os casos automatizados com estados controlados: 49 de trigo; exatamente 50 com agricultor livre; 3 ocupados e pelo menos 50 de trigo; 3 ocupados e 49 de trigo. Esperar, respectivamente, insuficiência, aceitação, falta de agricultor e insuficiência com prioridade.
5. Verificar também Mestre pedindo construção: com fase aberta, “Só o Jogador pode construir”, mesmo sem trigo; fora da fase aberta, “A temporada não está aberta”.

Não introduzir botões de alteração de estoque para preparar testes. Na etapa 3, conclusão automática ainda não foi implementada; usar uma nova execução por ensaio quando necessário.

## V4 — Produção e obras

1. Reiniciar, conectar M/A e abrir. A constrói logo após a abertura, idealmente antes de dois segundos. Não realizar novas ações.
2. O trigo passa a 100 no início da obra e a 110 no primeiro ciclo aos 5 s da abertura.
3. A obra termina 8 s depois de `construcao.iniciada`, sem clique. Todos veem um moinho, agricultor livre e produção 20 por intervalo.
4. Se a conclusão preceder o ciclo de 10 s, esse ciclo mostra 130 de trigo. Na etapa 4, farinha permanece zero; após a etapa 6, seguir V6.
5. Durante a obra, entrar B. B recebe o estado atual e a mesma identidade de obra; sua barra indica o tempo restante. A conclusão cria um único moinho em cada aba.
6. Teste automatizado com início de obra em t = 0 verifica exatamente os instantes 5, 8 e 10 s. O roteiro manual mede os 8 s desde o evento de início; não exigir simultaneidade perfeita de cliques com a abertura.

## V5 — Encerramento e disputa

### Último agricultor com estoque suficiente

1. Reiniciar e conectar M, A e B. M abre; ninguém constrói nem coleta até o trigo atingir pelo menos 200 (sem moinhos, aos 25 s).
2. Logo após um ciclo de produção, A inicia duas obras rapidamente. Confirmar ocupação 2/3 e trigo de pelo menos 100.
3. A e B pedem a terceira obra quase juntos, antes de qualquer obra terminar e sem outro evento entre as decisões. Confirmar exatamente uma obra aceita e um débito de 50, com ocupação 3/3.
4. O perdedor recebe “Sem agricultor livre”; o vencedor e M não recebem a recusa. Todos recebem o fato aceito. Conferir pelo menos 50 de trigo após o débito, garantindo que o teste não caiu em “Trigo insuficiente”.
5. Se um timer interferir nas precondições entre os pedidos, repetir o ensaio. O teste concorrente automatizado reproduz o cenário sem depender de cliques simultâneos.

### Encerramento com obra pendente

1. Em ensaio próprio, iniciar uma obra e encerrar com M antes dos 8 s.
2. As três abas recebem `vila.encerrada`, com causa `vila.encerramento_solicitado`. Registrar o retrato final de trigo, farinha, ocupação e obras.
3. Esperar mais de 20 s: nenhum fato de atividade nem alteração do retrato final; barras de progresso também ficam paradas.
4. Com os controles desabilitados fora da fase aberta, validar diretamente nos testes que um pedido de construção de A recebe “A temporada não está aberta”. M tenta abrir e recebe “A temporada já foi aberta”; repetir encerramento recebe “A temporada não está aberta”. Recusas são privadas.
5. Recarregar B: o retrato final aparece, sem concluir obras ou empilhar efeitos visuais de encerramento. Verificar pedido de encerramento por Jogador nos testes automatizados.

## V6 — Moagem

1. Repetir o roteiro de uma obra iniciada logo após abertura, antes de dois segundos, sem outras ações.
2. No ciclo de 10 s, inspecionar dois eventos nas três abas: `recurso.produzido` com trigo 130; em seguida `farinha.moida` com consumo 5, produção 3, trigo 125 e farinha 3.
3. Confirmar causa imediata `recurso.produzido` na moagem e dados separados no painel. A ordem visual da lista é inversa à ordem cronológica.
4. Sem moinhos, não há `farinha.moida`. Com mais moinhos, conferir 5 de trigo consumidos e 3 de farinha gerados por moinho apto, em um resumo por intervalo.
5. Nos testes controlados, verificar moinho sem trigo suficiente, nenhum moinho apto e conclusão coincidente com o limite do intervalo (moagem só no ciclo posterior). Não exigir que estados artificiais de insuficiência ocorram naturalmente após toda produção.
6. Encerrar e observar que a farinha acumulada não é gasta e não continua aumentando.

## V7 — Colheitas

### Coleta e disputa

1. Reiniciar, conectar as três abas e abrir, sem construir. Aos 20 s, todas recebem `colheita.amadurecida`: valor 30, prazo 10 s e mesma identidade; não há crédito de colheita nesse momento.
2. Entre 20 s e 30 s, A e B pedem coleta quase juntos. Todos recebem um único `colheita.coletada` e um crédito de 30; só o perdedor recebe “Não há colheita para coletar”. A ocupação de agricultores não muda.
3. Atravessar os 30 s: não ocorre `colheita.estragada` para a identidade coletada. Aos 40 s, se a temporada continua aberta, há novo amadurecimento com outra identidade.

### Perda por prazo

1. Em temporada nova, não coletar. Aos 20 s surge colheita; aos 30 s ocorre uma única `colheita.estragada`, com causa `colheita.amadurecida` e gatilho temporizador.
2. A perda retira a colheita sem debitar trigo. O ciclo de produção aos 30 s continua: sem construção ou coleta, o estoque final após ambos os eventos é 210 de trigo e 0 de farinha.
3. A tenta coletar depois da perda e recebe “Não há colheita para coletar”. No instante exato, o mesmo resultado é obrigatório, mesmo se o timer estiver atrasado.

### Encerramento e papéis

1. Em temporada nova, amadurecer colheita e iniciar uma obra logo após os 20 s. M encerra antes da conclusão e da expiração.
2. Atravessar ambos os prazos e o ciclo de 40 s: não há conclusão, perda, amadurecimento, produção ou moagem posteriores ao encerramento.
3. O Mestre não recebe botão de coleta. O teste direto no servidor deve confirmar “Só o Jogador pode coletar” na fase aberta, inclusive sem colheita; fora dela, “A temporada não está aberta”.

### Fronteira estrita com relógio controlado

Não tentar comprovar precisão de milissegundos com cliques. A suíte deve usar prazo T e estados equivalentes para:

- recebimento T−ε: uma coleta aceita se ainda disponível;
- recebimento T: recusa e nenhum crédito;
- recebimento T+ε: recusa e nenhum crédito;
- recebimento T ou T+ε com timer ainda não executado: mesma recusa; depois, uma única perda causada pelo timer;
- lock ocupado: coleta registrada em T−ε, timer solicitando o lock em T, liberação em T+ε; a coleta é aceita e a perda é invalidada;
- duas coletas válidas antes de T: um crédito e uma recusa;
- timer de uma colheita antiga: nenhum efeito sobre a nova colheita;
- encerramento antes da decisão: prioridade da fase, sem efeito tardio.

## Testes automatizados e evidência por etapa

Após criar os testes durante a implementação:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

Não executar esse comando como prova de cobertura enquanto `tests/` não existir. Os testes focados de `test_server.py` verificam regras e emissão usando relógio e transporte controlados; a integração real de Socket.IO, Vue e Phaser é comprovada pelas abas.

Registrar no README, por etapa: versão/commit, condições iniciais, papéis das abas, sequência realizada, eventos e destinatários esperados, resultado observado e comando dos testes pertinentes. Só marcar a etapa como verificada depois da execução. Cada etapa concluída tem um commit próprio; a entrega final percorre todos os roteiros e cenários da spec.
