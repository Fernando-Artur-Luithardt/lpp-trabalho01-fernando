# Implementation Plan: Fazenda em tempo real — tema 19

**Branch**: `main` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-fazenda-tempo-real/spec.md`.

**Estado**: planejamento concluído; implementação não iniciada. As decisões 1A e 2A foram confirmadas pelo usuário. O identificador da feature é `001-fazenda-tempo-real`; ele é independente da branch Git, que permanece `main`.

## Summary

Implementar a Fazenda do tema 19 no kit existente, com estado em memória sob autoridade do servidor e clientes que reagem aos eventos. Python, python-socketio e Uvicorn permanecem no servidor; Vue e Phaser permanecem no cliente. Produção, obras e colheitas usam tarefas e relógio do servidor. Preservar o painel e sua relação entre causa, dados e reação.

Entregar sete etapas sequenciais, cada uma executável, verificável com três abas e registrada em um commit. O roteiro rápido admite duas abas para fluxos simples, mas a conclusão da etapa usa Mestre, Jogador A e Jogador B, conforme a constituição. As etapas intermediárias só verificam os comportamentos já introduzidos; a aceitação final exige todos os cenários da spec.

## Technical Context

**Language/Version**: Python 3.11 ou superior, com versão efetivamente usada registrada no README; JavaScript de navegador, sem etapa de compilação.

**Primary Dependencies**: `python-socketio` e `uvicorn` de `requirements.txt`; Vue 3.5.13, Socket.IO cliente 4.7.5 e Phaser 3.90.0 já referenciados pelo HTML. Não adicionar framework, broker ou biblioteca de agendamento.

**Storage**: memória de um único processo; uma vila por execução. Reiniciar o servidor reinicia o estado; persistência e múltiplos workers ficam fora do escopo.

**Testing**: três abas de navegador para integração; `unittest`, `IsolatedAsyncioTestCase` e `unittest.mock` para regras, concorrência, destinatários e temporizadores com relógio controlado. Testes serão criados na implementação, não nesta etapa documental.

**Target Platform**: execução local com Uvicorn e navegador atual com acesso às CDNs do kit.

**Project Type**: aplicação web acadêmica orientada a eventos, servida pela aplicação ASGI existente.

**Performance Goals**: três clientes compartilham cada fato sem recarregar a página; respeitar intervalos do domínio (5 s, 8 s, 20 s e 10 s), sem estoque negativo, ocupação acima de 3 ou crédito duplicado. Não impor metas de carga sem requisito.

**Constraints**: custo 50; estoque inicial 150 de trigo e 0 de farinha; produção 10 + 10 por moinho; moagem 5 → 3 por moinho; colheita 30. Somente Jogador constrói/coleta. Validar fase → papel → condições da operação. Coleta exige chegada ao tratador antes do prazo, com relógio monotônico do servidor.

**Scale/Scope**: um Mestre e dois jogadores na demonstração, uma temporada por execução; quantidade de moinhos não limitada pelo número de lotes gráficos.

## Constitution Check

*Verificação inicial antes da pesquisa e reavaliação após o desenho dos contratos.*

| Princípio | Antes do desenho | Evidência após o desenho |
| --- | --- | --- |
| I. Kit e especificação | PASS | Mesmos arquivos e stack; tema 19 e valores preservados; novas recusas aprovadas em 1A. |
| II. Autoridade do servidor | PASS | Lock global, validação ordenada, estado por transição e recusas dirigidas ao `sid`. |
| III. Clientes e painel | PASS | `pedir`, `ouvir`, `atualizar`, `registrar` e métodos visuais reutilizados; contratos incluem causa e reação. |
| IV. Temporizadores | PASS | Prazos monotônicos, tarefas guardadas, cancelamento e revalidação de fase/identidade; nenhuma conclusão local. |
| V. Etapas e commits | PASS | Sete etapas com arquivos, eventos, verificação em abas e um commit por etapa. |

Q1 e Q2 foram resolvidas por 1A e 2A, sem exceções à constituição. A conclusão desta revisão é documental; não declara testes da aplicação aprovados.

## Project Structure

### Documentation (this feature)

```text
specs/001-fazenda-tempo-real/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── events.md
└── checklists/
    └── requirements.md
```

`tasks.md` será produzido por `$speckit-tasks`. `docs/especificacao.md` continua como fonte de domínio; `README.md` receberá instruções e evidências durante a implementação. `.specify/feature.json` identifica este diretório para os comandos seguintes.

### Source Code (repository root)

```text
server.py                  # estado, sessões, eventos, relógio e tarefas
requirements.txt           # dependências atuais
client/
├── index.html             # Vue, Socket.IO, painel e métodos Phaser existentes
└── assets/                # mapa, tileset e sprites preservados
tests/                     # a criar na implementação
└── test_server.py          # invariantes, recusas, disputas e prazos controlados
README.md
```

**Structure Decision**: manter a estrutura simples do kit. Organizar `server.py` em constantes/estado, operações de domínio, publicação, temporizadores e tratadores. Extrair apenas funções pequenas necessárias para testar relógio e regras; não criar camadas ou serviços sem necessidade. Nenhum arquivo de aplicação ou teste é alterado pelo planejamento.

## Design Decisions

- O servidor associa nome e papel ao `sid` na conexão. Papel inválido impede a conexão; não criar um evento de domínio para erro de protocolo. As ações usam a sessão, nunca um papel enviado junto do pedido.
- Um `asyncio.Lock` serializa validação, mutação, snapshot e emissão; esperas de segundos e espera de cancelamento ocorrem fora do lock. Conexão e temporizadores seguem o mesmo mecanismo.
- Guardar referências das tarefas e identidade das obras/colheitas. Ao encerrar, mudar a fase e invalidar efeitos antes de publicar `vila.encerrada`; cancelar e aguardar tarefas fora do lock, sem cancelar a tarefa que executa o encerramento.
- Produção usa ciclos ancorados na abertura. Publicar `recurso.produzido` com seu estado e depois, na mesma operação protegida, `farinha.moida` com o estado posterior, quando houver moagem. Um moinho só mói em um ciclo posterior à sua conclusão.
- Capturar o recebimento da coleta e imediatamente solicitar o lock, sem espera intermediária. O temporizador de expiração só entra na fila do lock no prazo ou depois. Esse ordenamento preserva pedidos recebidos a tempo; no limite e depois, recusar mesmo que a colheita ainda não tenha sido removida pelo timer.
- Dados enviados incluem snapshots completos e campos explicativos, conforme [contrato](contracts/events.md). O cliente não soma/subtrai novamente recursos recebidos no snapshot.
- Criar o socket com conexão automática desativada, registrar `ouvir` e os eventos de conexão/desconexão uma vez, então conectar. Preservar a fila `chamar` do Phaser. Evitar perder o canvas em reconexões: manter o contêiner montado ou reconstruir a cena de modo explícito e único.
- `mostrarEstado` deve reconciliar objetos por identidade, sem duplicação e sem reproduzir efeitos antigos. A obra conclui por `obra_id`, não por `shift()`. Barras usam prazo recebido apenas para apresentação e param no encerramento.
- Adaptar textos, `estado.toras` e `resumir` para trigo; acrescentar farinha e colheita. Preservar contagens/campos do kit quando compatíveis, explicando que `trabalhadores` representa agricultores ocupados. Identificar `porMinuto` como produção bruta.

## Implementation Stages

### Etapa 1 — Conexão e estado.sincronizado

**Arquivos**: `server.py`, `client/index.html`, `README.md`. Reutilizar `requirements.txt` e os assets.

**Entrega**: estado inicial da Fazenda, nome/papel por sessão, entrada e reconexão com snapshot privado. Preparar o estado Vue com trigo, farinha e colheita; adaptar `resumir`. Registrar escutas antes da conexão. Reconciliar o desenho inicial e manter o canvas em reconexões.

**Eventos e reação**: conexão → `estado.sincronizado` → `ouvir`, `atualizar(d)`, `jogo.mostrarEstado(d.estado)`. O painel mostra causa `conexao`, dados e reação de sincronização.

**Verificação**: duas abas mostram 150 de trigo, 0 de farinha, 0/3 agricultores e fase aguardando; repetir com a terceira aba. Recarregar B não muda os outros clientes nem duplica desenhos. O painel de A não recebe o snapshot destinado a B. Ver [V1](quickstart.md#v1--conexão).

**Commit**: `feat: sincroniza estado inicial da fazenda`.

### Etapa 2 — Abertura da temporada

**Arquivos**: `server.py`, `client/index.html`, `README.md`; iniciar `tests/test_server.py` para autorização e abertura única.

**Entrega**: validar Mestre antes da fase; abrir apenas de aguardando; registrar instante de abertura para os ciclos das etapas seguintes. Infraestrutura de recusa já atende abertura inválida; construção e coleta serão acrescentadas depois.

**Eventos e reação**: `pedir('vila.abertura_solicitada')` → `vila.iniciada` → `atualizar` e `jogo.vilaIniciada`; recusa → `avisar` e `jogo.recusado` via `ouvir`.

**Verificação**: Mestre abre e ambas as abas de Jogador mostram aberta; segunda abertura recebe recusa só no Mestre. Pedido de Jogador deve falhar no servidor, mesmo fora dos botões da interface. Nesta etapa, produção será verificada quando introduzida na etapa 4. Ver [V2](quickstart.md#v2--abertura).

**Commit**: `feat: controla abertura da temporada`.

### Etapa 3 — Construções e recusas

**Arquivos**: `server.py`, `client/index.html`, `tests/test_server.py`, `README.md`.

**Entrega**: construir com validação fase → Jogador → trigo → agricultor; debitar 50, ocupar um agricultor e criar obra com identidade e prazo. A conclusão automática entra na próxima etapa. Acrescentar dados de obras ao snapshot e reconciliar entrada tardia.

**Eventos e reação**: `pedir('construcao.solicitada')` → `construcao.iniciada` → `atualizar`, `jogo.obraIniciada`; `operacao.recusada` → motivo e reação somente no solicitante.

**Verificação**: antes da abertura, A recebe recusa e B permanece sem evento relacionado. Após abrir, construção de A aparece nas três abas com −50 trigo e +1 agricultor. Testes de estados controlados verificam 49/50 trigo, 3 ocupados com pelo menos 50, e recusa do Mestre antes de avaliar estoque. Ver [V3](quickstart.md#v3--construções-e-recusas).

**Commit**: `feat: valida construções e recusas por jogador`.

### Etapa 4 — Produção e conclusão das obras

**Arquivos**: `server.py`, `client/index.html`, `tests/test_server.py`, `README.md`.

**Entrega**: tarefas de produção a cada 5 s e conclusão 8 s após o início. Guardar tarefas, conferir fase e concluir a obra por identidade. Publicar snapshots distintos por fato. Reutilizar barras como indicação, sem criar moinho antes do fato recebido.

**Eventos e reação**: `recurso.produzido` → `atualizar`, `jogo.recursoProduzido`; `construcao.concluida` → `atualizar`, `jogo.obraConcluida`. Causas: temporizador e `construcao.iniciada`, respectivamente.

**Verificação**: duas abas acompanham mudança sem cliques; abrir B durante uma obra deve mostrar progresso restante e receber a mesma conclusão. Para obra iniciada logo após abertura, observar 100 → 110 → 130 de trigo até 10 s, ocupação retornando a zero; farinha ainda zero porque a moagem entra na etapa 6. Teste com relógio controlado verifica os instantes exatos da spec. Ver [V4](quickstart.md#v4--produção-e-obras).

**Commit**: `feat: produz trigo e conclui obras por temporizadores`.

### Etapa 5 — Encerramento e disputas

**Arquivos**: `server.py`, `client/index.html`, `tests/test_server.py`, `README.md`.

**Entrega**: encerramento somente pelo Mestre, fase final, invalidação/cancelamento de tarefas e interrupção de barras visuais. Consolidar testes concorrentes do lock já usado desde as primeiras operações; não adiar consistência para esta etapa.

**Eventos e reação**: `pedir('vila.encerramento_solicitado')` → `vila.encerrada` → `atualizar`, `jogo.vilaEncerrada`; disputas usam `construcao.solicitada`, `construcao.iniciada` e `operacao.recusada`.

**Verificação**: três abas, 2 agricultores ocupados e pelo menos 100 de trigo; A e B disputam o terceiro: uma obra e uma recusa privada. Encerrar antes de a obra acabar e atravessar seu prazo e um ciclo de produção: nenhuma mudança. Repetir encerramento, tentar reabrir e tentar construir. Ver [V5](quickstart.md#v5--encerramento-e-disputa).

**Commit**: `feat: encerra temporada e verifica disputas`.

### Etapa 6 — Moagem de farinha

**Arquivos**: `server.py`, `client/index.html`, `tests/test_server.py`, `README.md`.

**Entrega**: após cada produção, moer 5 de trigo em 3 de farinha por moinho apto. Emitir um resumo do intervalo com quantidades; farinha acumula e não é gasta. Mostrar estoques separados e produção bruta. Reutilizar painel/avisos; uma reação visual pequena pode usar `flutuar`, sem novos assets.

**Eventos e reação**: `recurso.produzido` → `farinha.moida`, com causa imediata `recurso.produzido`; `ouvir` atualiza snapshot e anuncia trigo consumido/farinha gerada. Não há método de moagem pronto no kit: usar `avisar` como reação inicial explícita.

**Verificação**: com uma obra iniciada na abertura, as três abas mostram aos 10 s trigo 130 no evento de produção e depois 125 e farinha 3 na moagem. Sem moinho, nenhum evento de moagem. Testar estoque insuficiente de forma controlada e assegurar que moinho concluído não mói retroativamente. Ver [V6](quickstart.md#v6--moagem).

**Commit**: `feat: transforma trigo em farinha após a produção`.

### Etapa 7 — Colheitas com prazo

**Arquivos**: `server.py`, `client/index.html`, `tests/test_server.py`, `README.md`.

**Entrega**: amadurecer a cada 20 s, disponibilizar 30 de trigo por 10 s, coletar uma única vez ou perder por prazo. Implementar 1A/2A, identificar colheita para impedir que um timer antigo expire outra, e invalidar expiração após coleta. Acrescentar botão só para Jogador e indicador de prazo, sem usar relógio local para decidir crédito.

**Eventos e reação**: `colheita.amadurecida`, `pedir('colheita.coleta_solicitada')`, `colheita.coletada`, `colheita.estragada`, `operacao.recusada`. `ouvir` atualiza Vue, indicador de colheita e avisos, preservando causa, dados e reação no painel; não exigir métodos Phaser inexistentes.

**Verificação**: três abas, amadurecimento aos 20 s, disputa antes dos 30 s com um crédito de 30 e recusa privada; antiga expiração não dispara. Em outra temporada, ninguém coleta e aos 30 s a colheita estraga, separando essa perda da produção simultânea. Testes controlam T−ε, T e T+ε, espera por lock, Mestre tentando coletar e encerramento com prazo pendente. Ver [V7](quickstart.md#v7--colheitas).

**Commit**: `feat: adiciona colheitas com coleta e expiração`.

## Validation and Completion

Cada commit de implementação inclui a documentação afetada e o registro da verificação: condições iniciais, abas/papéis, eventos e destinatários esperados, resultado observado e testes executados. Não declarar uma etapa concluída com falha conhecida. Os cenários por estado controlado devem ficar nos testes, sem comandos de administração ocultos na aplicação.

Reexecutar os testes pertinentes após cada etapa e, ao final, todos os cenários da spec com três clientes, incluindo entrada tardia e encerramento. [quickstart.md](quickstart.md) contém comandos e roteiros; [data-model.md](data-model.md) define campos e invariantes; [contracts/events.md](contracts/events.md) define as mensagens.

## Complexity Tracking

Nenhuma violação constitucional ou complexidade adicional a justificar. O lock, as identidades das entidades e o relógio controlável atendem diretamente às disputas e aos prazos exigidos. Phase 0 e Phase 1 concluídas; o próximo artefato é `tasks.md`, via `$speckit-tasks`.
