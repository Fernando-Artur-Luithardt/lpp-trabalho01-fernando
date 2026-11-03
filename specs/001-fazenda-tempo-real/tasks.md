---
description: "Tarefas da Fazenda, tema 19, nas sete etapas do plano"
---

# Tasks: Fazenda em tempo real — tema 19

**Input**: documentos de `specs/001-fazenda-tempo-real/`.
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/events.md](contracts/events.md) e [quickstart.md](quickstart.md); regras de domínio em `docs/especificacao.md` e governança em `.specify/memory/constitution.md`.
**Estado**: Etapas 1–2 implementadas e verificadas por testes e navegador automatizado em 2026-11-03; repetição manual humana de V2 pendente conforme README. Etapas 3–7 pendentes.
**Tests**: verificações de aceitação da spec e testes focados já previstos no plano, usando `unittest`, relógio controlado e três abas. Não adicionar framework de testes.
**Organization**: as sete etapas solicitadas pelo usuário determinam a ordem. Setup e fundamentos integram a etapa 1; acabamento e aceitação final integram a etapa 7. Os rótulos de história mantêm a rastreabilidade sem criar fases ou commits extras.

## Format: `[ID] [P?] [Story] Description`

- IDs T001–T055 são únicos e ordenados. Todas as tarefas começam desmarcadas.
- `[P]` permite trabalho simultâneo somente após as dependências indicadas e em arquivos distintos. Não permite executar duas edições no mesmo arquivo ou pular o commit anterior.
- `[US1]`: acompanhar e controlar a temporada (P1); `[US2]`: construir e transformar trigo em farinha (P2); `[US3]`: coletar antes que a colheita estrague (P3).
- Setup/fundamentos e acabamento transversal não recebem rótulo de história. As demais tarefas recebem exatamente um rótulo; dependências entre histórias são explicitadas.
- Cada tarefa informa arquivos e dependências. “Dep.: nenhuma” autoriza somente o início da implementação futura, não sua execução por este comando.

## Path Conventions

Todos os caminhos nas tarefas são relativos à raiz do repositório. Reutilizar `server.py`, `client/index.html`, `requirements.txt` e `client/assets/`. Os testes serão criados em `tests/test_server.py`; as instruções e evidências por etapa ficam em `README.md`. Não criar outro projeto, banco de dados ou compilação do frontend.

## Regras de execução e decisões confirmadas

- **1A**: construir e coletar são exclusivos do Jogador. Validar **fase → papel → condições da operação**. Com fase aberta, pedidos do Mestre recebem “Só o Jogador pode construir” ou “Só o Jogador pode coletar”. Fora dela, “A temporada não está aberta” tem prioridade. Abrir/encerrar continuam validando Mestre antes da fase.
- **2A**: só aceitar coleta recebida no tratador do servidor **estritamente antes** do prazo. Capturar `loop.time()` antes de qualquer espera e solicitar imediatamente o lock, sem outro `await` intermediário. No instante exato ou depois, recusar com “Não há colheita para coletar”, mesmo com timer atrasado. Pedido recebido antes não perde validade apenas por esperar pelo lock.
- Usar o mesmo lock para validação, alteração, snapshot e publicação, inclusive nos timers e na sincronização. Recusa não altera a vila. Guardar referências das tarefas; nunca manter o lock durante esperas de segundos ou espera de cancelamento.
- Preservar `pedir()`, `ouvir()`, `atualizar()`, `registrar()`, `avisar()`, a fila `chamar` e os métodos visuais existentes. O painel deve mostrar causa, dados e reação. Cliente não confirma créditos/débitos por conta própria.
- Uma etapa só termina depois da verificação e de **um commit próprio**. As tarefas de commit agrupam apenas alterações da etapa e sua evidência no `README.md`; não fazer um commit por tarefa nem incluir alterações preexistentes sem relação. Os commits abaixo são ações futuras.
- Duas abas servem ao ensaio rápido; a aceitação da etapa usa **Mestre, A e B**. Estados artificiais são preparados nos testes, não por botões ou rotas de administração na aplicação.
- A etapa 2 ainda não tem produção; a etapa 3 ainda não conclui obras; a etapa 4 ainda não mói farinha. Verificar o incremento entregue sem alterar as regras finais nem declarar uma história completa antes de todos os seus critérios estarem cobertos.

## Etapa 1 — Conexão e estado.sincronizado

**Goal**: cada participante recebe e representa o mesmo estado inicial, sem mudar a vila.
**História**: US1; infraestrutura comum para US2 e US3.
**Dependência de entrada**: nenhuma.
**Eventos**: conexão/reconexão → `estado.sincronizado`, somente para o `sid` que entrou, causa `conexao`.
**Independent Test**: V1 do quickstart; três abas mostram 150 trigo, 0 farinha, 0/3 agricultores, nenhuma obra/colheita e fase aguardando. Recarregar B não muda M/A nem duplica a cena.

### Setup e fundamentos compartilhados

- [X] T001 Conferir a execução do kit com Python 3.11+ e dependências existentes de `requirements.txt`, mantendo um processo Uvicorn e registrando versões efetivamente usadas, instalação e abertura de três abas em `README.md`; não adicionar framework ou modificar assets (dep.: nenhuma).
- [X] T002 Definir constantes e estado inicial em `server.py`: tema 19, fase `aguardando`, trigo 150, farinha 0, limite 3, custo 50, tempo_obra 8 s, intervalo 5 s, producao 10, trabalhadores/concluidas/em_obra zero, obras lista vazia, colheita/aberta_em_ms/encerrada_em_ms null. Preservar as restrições do modelo: fase “`aguardando` → `aberta` → `encerrada`; sem reabertura.”; trigo “Compartilhado, nunca negativo.”; farinha “Compartilhada, nunca gasta.”; limite “Capacidade de agricultores, não limite de moinhos.”; trabalhadores “Agricultores ocupados; igual à quantidade de obras em andamento.”; producao “Produção bruta por intervalo: `10 + 10 * concluidas`.”; colheita “A única colheita disponível; retirada ao coletar ou estragar.”; aberta_em_ms “Instante público de abertura, apenas para apresentação.”; encerrada_em_ms “Instante do retrato final.” (dep.: T001).
- [X] T003 Preparar em `server.py` o lock global, o relógio monotônico/espera substituíveis para testes, identidades crescentes e registro de tarefas; produzir snapshots copiados com contagens derivadas das obras, sem serializar sessões/lock/tarefas, e envelope `estado`, `causa`, `servidor_em_ms` com referência civil fixa só para apresentação; centralizar envio global versus `to=sid`, preservando a ordem dentro do lock e excluindo esperas longas (dep.: T002).

### Implementação da US1

- [X] T004 [P] [US1] Implementar conexão, desconexão e sincronização em `server.py`: vincular `sid` a nome/papel, aplicar nome “Texto recebido na entrada; usar ‘Anônimo’ se vazio.” e papel “`mestre` ou `jogador`, associado à sessão pelo servidor.”, rejeitar papel desconhecido, emitir `estado.sincronizado` com causa `conexao` apenas ao participante; reconexão recebe snapshot atual e desconexão remove somente a sessão, sem reiniciar a vila (dep.: T003).
- [X] T005 [P] [US1] Adaptar entrada e estado Vue em `client/index.html`: substituir toras por trigo, exibir farinha e agricultores, criar socket com conexão automática desativada, registrar `ouvir('estado.sincronizado', ...)` e eventos de conexão/desconexão uma vez antes de conectar, aplicar `atualizar(d)` e `jogo.mostrarEstado(d.estado)`; conservar o contêiner Phaser ou reconstruí-lo de modo único na reconexão (dep.: T003).
- [X] T006 [US1] Adaptar `resumir`, `registrar` e a apresentação do painel em `client/index.html` para estoques/ocupação/obras/colheita, causa, dados, sentido, horário e reação; preservar o filtro e a classificação de pedidos/fatos/recusas, deixando a causa do pedido local explícita em `pedir()` sem torná-la autoridade no servidor (dep.: T005).
- [X] T007 [US1] Tornar `mostrarEstado` idempotente em `client/index.html`, preservando mapa/assets e fila `chamar`, sem duplicar objetos nem reproduzir créditos/débitos ao sincronizar; preparar reconciliação por identidade dos registros `obras`, com lista inicialmente vazia, sem impor limite pelo número de lotes (dep.: T006).
- [X] T008 [US1] Executar V1 de `specs/001-fazenda-tempo-real/quickstart.md` com M/A/B e registrar em `README.md` estado inicial, destinatário privado do snapshot, reconexão sem mutação e ausência de desenhos duplicados; corrigir falhas antes de fechar a etapa (dep.: T004, T007).
- [X] T009 [US1] Criar o commit da etapa 1, `feat: sincroniza estado inicial da fazenda`, reunindo as alterações pertinentes de `server.py`, `client/index.html` e a evidência em `README.md`; não incluir trabalho preexistente alheio à etapa (dep.: T008).

**Checkpoint**: conexão e snapshot verificáveis; não declarar produção, obras ou colheitas implementadas.

## Etapa 2 — Abertura da temporada

**Goal**: Mestre abre uma única vez, e todos veem a mesma fase; recusas são privadas.
**História**: US1 (P1).
**Dependência de entrada**: commit T009.
**Eventos**: `vila.abertura_solicitada` → `vila.iniciada` ou `operacao.recusada`.
**Independent Test**: V2; M abre, todos veem aberta sem crédito imediato; segunda abertura é recusada somente a M, sem reiniciar referência temporal.

- [X] T010 [P] [US1] Criar `tests/test_server.py` com `IsolatedAsyncioTestCase`, transporte/relógio controlados e estado isolado por caso; cobrir snapshot privado/copiado, sessão e papel inválido, `vila.iniciada` global com causa correta, abertura por Jogador recusada antes da fase, abertura repetida e ausência de alteração/duplicação da referência temporal; preparar testes antes dos novos tratadores, sem esperas reais longas (dep.: T009).
- [X] T011 [US1] Implementar `vila.abertura_solicitada` em `server.py` sob o lock, usando papel da sessão: primeiro “Só o Mestre pode abrir a temporada”, depois “A temporada já foi aberta”; na aceitação, registrar abertura monotônica e `aberta_em_ms`, mudar fase e publicar `vila.iniciada` para todos; centralizar `operacao.recusada` com `motivo`, causa do pedido e estado inalterado somente para `sid` (dep.: T010).
- [X] T012 [P] [US1] Ligar `abrirVila()` a `pedir('vila.abertura_solicitada')` em `client/index.html`; registrar via `ouvir` as reações `atualizar`/`jogo.vilaIniciada` e `avisar`/`jogo.recusado` para fatos/recusas; não confirmar abertura no clique nem registrar escutas novamente em cada reconexão (dep.: T009).
- [X] T013 [US1] Executar os testes pertinentes de `tests/test_server.py` e V2 de `specs/001-fazenda-tempo-real/quickstart.md` nas três abas, registrando em `README.md` abertura única, nenhuma produção imediata, recusa privada e validação direta de pedido de Jogador sem depender da existência de botão (dep.: T011, T012).
- [X] T014 [US1] Criar o commit da etapa 2, `feat: controla abertura da temporada`, com `server.py`, `client/index.html`, `tests/test_server.py` e `README.md` verificados (dep.: T013).

**Checkpoint**: abertura e recusa por papel demonstráveis; os ciclos automáticos entram nas etapas 4 e 7.

## Etapa 3 — Construções e recusas

**Goal**: aceitar obras com débito único e aplicar recusas na ordem aprovada em 1A.
**História**: US2 (P2).
**Dependência de entrada**: commit T014.
**Eventos**: `construcao.solicitada` → `construcao.iniciada` ou `operacao.recusada`.
**Independent Test**: V3; construção aceita aparece nas três abas com −50 trigo e +1 agricultor; recusas não mudam estado e chegam só a quem pediu.

- [ ] T015 [P] [US2] Acrescentar em `tests/test_server.py` os casos US2.1–US2.4 e US2.9: fase fechada, trigo 49, exatamente 50 com vaga, 3 ocupados e pelo menos 50, 3 ocupados com 49 e Mestre com fase aberta/fechada; conferir ordem fase → papel → estoque → agricultor, destinatários, causa, payload `obra_id`/`custo` e ausência de alteração em cada recusa (dep.: T014).
- [ ] T016 [US2] Implementar registros de obra e projeções em `server.py`: `id` “Inteiro crescente, estável na execução; também é `obra_id` nos eventos.”; `status` “`em_andamento` ou `concluida`.”; `iniciada_em_ms` “Instante de início para apresentação.”; `concluir_em_ms` “Prazo de conclusão para apresentação.”; `concluida_em_ms` “Instante da conclusão efetiva ou null.”; guardar equivalentes monotônicos, ocupar um agricultor por obra e calcular contadores em um ponto, sem propriedade individual ou limite de moinhos por lotes (dep.: T015).
- [ ] T017 [US2] Implementar `construcao.solicitada` em `server.py`, sem aceitar custo/papel/estoque do payload: sob o lock, recusar na ordem “A temporada não está aberta” → “Só o Jogador pode construir” → “Trigo insuficiente” → “Sem agricultor livre”; na aceitação debitar 50, ocupar uma vaga, criar obra com prazo de 8 s e emitir `construcao.iniciada` global com causa do pedido e snapshot posterior (dep.: T016).
- [ ] T018 [P] [US2] Ligar `construir()` a `pedir('construcao.solicitada')` em `client/index.html`, manter controle exclusivo do Jogador, ouvir `construcao.iniciada` para atualizar o estado recebido e acionar o método visual; exibir custo em trigo e tratar recusa via infraestrutura existente, sem débito otimista (dep.: T014).
- [ ] T019 [US2] Adaptar `obraIniciada`, `criarObra` e `mostrarEstado` em `client/index.html` para identidade da obra e prazo público do snapshot, reconciliando entrada tardia sem reiniciar a contagem em 8 s ou repetir o texto de custo; manter as barras apenas indicativas e aguardar o fato de conclusão para desenhar moinho (dep.: T018).
- [ ] T020 [US2] Executar os testes de `tests/test_server.py` e V3 de `specs/001-fazenda-tempo-real/quickstart.md` com três abas, documentando em `README.md` a aceitação única, as recusas por fase/papel/estoque/agricultor e a privacidade; preparar estados artificiais só nos testes e registrar que conclusão automática pertence à próxima etapa (dep.: T017, T019).
- [ ] T021 [US2] Criar o commit da etapa 3, `feat: valida construções e recusas por jogador`, com `server.py`, `client/index.html`, `tests/test_server.py` e `README.md` verificados (dep.: T020).

**Checkpoint**: 1A aplicada à construção; invariantes de estoque e ocupação já protegidas pelo lock.

## Etapa 4 — Produção e conclusão das obras

**Goal**: a passagem do tempo produz trigo e conclui obras sem cliques.
**Histórias**: US1 (produção base) e US2 (obra e aumento de produção).
**Dependência de entrada**: commit T021.
**Eventos**: `recurso.produzido` e `construcao.concluida`.
**Independent Test**: V4; com obra em t = 0, trigo 100 → 110 aos 5 s → 130 aos 10 s, ocupação liberada aos 8 s; sem moagem nesta etapa. Entrada tardia acompanha o mesmo prazo.

- [ ] T022 [P] [US1] Acrescentar em `tests/test_server.py` testes com relógio controlado para produção base em abertura + n×5 s, n iniciando em 1, nenhuma produção em aguardando, ausência de crédito imediato, tarefa única após abertura repetida, emissão global com `quantidade`/causa `temporizador` e snapshot que não se altera após novas transições (dep.: T021).
- [ ] T023 [US2] Acrescentar em `tests/test_server.py` testes de conclusão em início +8 s, identidade da obra, liberação única do agricultor, contadores derivados, produção +10, dados `obra_id`/`gatilho: temporizador` e causa `construcao.iniciada`; testar a sequência de t = 0, 5, 8 e 10 s e início posterior à abertura (dep.: T022).
- [ ] T024 [US1] Implementar em `server.py` a tarefa de produção ancorada na abertura e seu registro de referência; esperar fora do lock, revalidar fase dentro dele, creditar `10 + 10 * concluidas` e publicar `recurso.produzido` com snapshot após crédito; usar relógio monotônico, não antecipar ciclos nem reiniciar calendário ao conectar clientes (dep.: T023).
- [ ] T025 [US2] Agendar em `server.py` uma conclusão por obra aceita, guardando referência e identidade; ao vencer início +8 s, revalidar fase/status sob o lock, concluir uma vez, liberar agricultor, atualizar produção/contadores e publicar `construcao.concluida`; manter `concluida_em_ms` e o instante monotônico para elegibilidade da moagem posterior (dep.: T024).
- [ ] T026 [P] [US1] Ouvir `recurso.produzido` em `client/index.html` com `atualizar(d)` e `jogo.recursoProduzido`, adaptando o texto de toras para trigo e identificando `porMinuto` como produção bruta; manter o painel com quantidade, causa de temporizador e reação sem somar novamente o delta (dep.: T021).
- [ ] T027 [US2] Ouvir `construcao.concluida` e adaptar `jogo.obraConcluida` em `client/index.html` para concluir pelo `obra_id`, sem `shift()`; encerrar a barra correta, reconciliar moinho e ocupação com o snapshot e manter entrada tardia sem duplicação de objetos (dep.: T026).
- [ ] T028 [US2] Executar os testes pertinentes em `tests/test_server.py` e V4 de `specs/001-fazenda-tempo-real/quickstart.md`, com B entrando durante uma obra; registrar em `README.md` os tempos medidos a partir de seus eventos, mudanças sem cliques e farinha ainda zero nesta etapa; separar precisão do teste controlado do tempo de cliques manuais (dep.: T025, T027).
- [ ] T029 [US2] Criar o commit da etapa 4, `feat: produz trigo e conclui obras por temporizadores`, com `server.py`, `client/index.html`, `tests/test_server.py` e `README.md` verificados (dep.: T028).

**Checkpoint**: produção e obras automáticas observáveis em três clientes; nenhuma regra de moagem antecipada.

## Etapa 5 — Encerramento e disputas

**Goal**: encerrar sem efeitos atrasados e provar a disputa pela última vaga.
**Histórias**: US1 (encerramento) e US2 (disputa por agricultor).
**Dependência de entrada**: commit T029.
**Eventos**: `vila.encerramento_solicitado` → `vila.encerrada`/`operacao.recusada`; disputa usa os eventos existentes de construção.
**Independent Test**: V5; 2/3 ocupados e pelo menos 100 de trigo geram uma aceitação e uma recusa privada; encerrar uma obra pendente mantém o retrato final por mais de 20 s.

- [ ] T030 [P] [US1] Acrescentar em `tests/test_server.py` testes de encerramento por Mestre/Jogador, fase inválida, abertura após encerramento, snapshot final, produção/conclusão pendentes, cancelamento sem travamento e nenhum fato de atividade após `vila.encerrada`; conferir motivos, ordem Mestre → fase e destinatário privado das recusas (dep.: T029).
- [ ] T031 [US2] Acrescentar em `tests/test_server.py` a disputa concorrente US2.6 com 2/3 ocupados e estoque inicial de pelo menos 100, sem timer entre as decisões: um débito de 50, uma obra aceita, uma recusa “Sem agricultor livre”, estoque restante pelo menos 50, ocupação máxima 3; verificar que o perdedor também recebe o fato global e só ele recebe a recusa (dep.: T030).
- [ ] T032 [US1] Implementar `vila.encerramento_solicitado` em `server.py`: validar “Só o Mestre pode encerrar a temporada” antes de “A temporada não está aberta”; sob o lock mudar fase, registrar `encerrada_em_ms`, invalidar efeitos e publicar `vila.encerrada`; cancelar/aguardar tarefas fora do lock sem cancelar a tarefa atual, preservando estoques, obras e ocupação sem conclusão ou reembolso posteriores (dep.: T031).
- [ ] T033 [P] [US1] Ligar `encerrarVila()` a `pedir('vila.encerramento_solicitado')` e ouvir `vila.encerrada` em `client/index.html`; aplicar snapshot, reutilizar `jogo.vilaEncerrada`, parar barras e impedir novas ações visuais, sem empilhar sombras ou alterar o estado local por contagem de tempo (dep.: T029).
- [ ] T034 [US2] Executar e ajustar, se necessário, a serialização de `server.py` e os testes concorrentes de `tests/test_server.py` para que validação, débito, ocupação, snapshot e publicação permaneçam indivisíveis perante outros pedidos e temporizadores; não adiar a primeira proteção por lock para esta tarefa nem introduzir regras alternativas de disputa (dep.: T032, T033).
- [ ] T035 [US1] Completar em `client/index.html` a sincronização de uma vila encerrada em `mostrarEstado`, congelando apresentação em `encerrada_em_ms`, sem reiniciar barras de obras ou duplicar sombra; manter os controles coerentes com a fase ao recarregar/reconectar B (dep.: T033).
- [ ] T036 [US1] Executar V5 de `specs/001-fazenda-tempo-real/quickstart.md` com M/A/B e os testes de `tests/test_server.py`, registrando em `README.md` a preparação natural de pelo menos 200 trigo antes de duas obras, disputa com pelo menos 100 restante, encerramento pendente e estabilidade após os prazos; repetir ensaio manual se outro evento interferir entre os pedidos (dep.: T034, T035).
- [ ] T037 [US1] Criar o commit da etapa 5, `feat: encerra temporada e verifica disputas`, com `server.py`, `client/index.html`, `tests/test_server.py` e `README.md` verificados (dep.: T036).

**Checkpoint**: ciclo básico com início/fim e disputas entregue; revalidar encerramento quando moagem e colheitas forem adicionadas.

## Etapa 6 — Moagem de farinha

**Goal**: transformar trigo em farinha após a produção, sem duplicar efeitos no cliente.
**História**: US2 (P2).
**Dependência de entrada**: commit T037.
**Eventos**: `recurso.produzido` → `farinha.moida`, com essa causa imediata.
**Independent Test**: V6; no roteiro de uma obra em t = 0, aos 10 s observar produção com trigo 130 seguida de moagem com trigo 125/farinha 3 em todas as abas.

- [ ] T038 [P] [US2] Acrescentar em `tests/test_server.py` testes US2.5/US2.7/US2.8: 5 trigo → 3 farinha por moinho apto, ausência de moagem sem moinho apto, estoque insuficiente controlado, conclusão exatamente no limite habilitando somente o ciclo seguinte, conservação/acúmulo de farinha e nenhum efeito após encerramento; conferir snapshots distintos e causa `recurso.produzido` (dep.: T037).
- [ ] T039 [US2] Implementar a operação de moagem em `server.py`, com trigo nunca negativo e farinha nunca gasta; selecionar moinhos concluídos antes do instante do intervalo, consumir 5 e gerar 3 por moinho apto, pulando moinho sem trigo suficiente; não criar custo adicional ou limite de moinhos (dep.: T038).
- [ ] T040 [US2] Integrar a moagem ao ciclo de produção em `server.py` na mesma operação protegida: emitir primeiro `recurso.produzido` com sua cópia do estado e depois um resumo `farinha.moida` com `moinhos`, `trigo_consumido`, `farinha_produzida`, causa `recurso.produzido` e estado posterior, somente quando houver moagem; preservar o bloqueio de atividade após encerramento (dep.: T039).
- [ ] T041 [P] [US2] Ouvir `farinha.moida` em `client/index.html`, aplicando `atualizar(d)` e `avisar` com quantidades transformadas; mostrar farinha acumulada, produção bruta e causa/dados/reação no painel, sem somar delta novamente nem exigir método de moagem inexistente no Phaser (dep.: T037).
- [ ] T042 [US2] Executar os testes de `tests/test_server.py` e V6 de `specs/001-fazenda-tempo-real/quickstart.md` com três abas; registrar em `README.md` produção 130 seguida de moagem 125/3, nenhum evento sem moinho apto, farinha preservada e fim dos efeitos após encerramento; atualizar a evidência do roteiro temporal final sem apagar o histórico das etapas (dep.: T040, T041).
- [ ] T043 [US2] Criar o commit da etapa 6, `feat: transforma trigo em farinha após a produção`, com `server.py`, `client/index.html`, `tests/test_server.py` e `README.md` verificados (dep.: T042).

**Checkpoint**: US2 completa, com recursos refinados e todos os seus cenários verificáveis.

## Etapa 7 — Colheitas com prazo

**Goal**: amadurecer, coletar uma vez ou perder por prazo, respeitando 1A e 2A.
**História**: US3 (P3), com regressão final das três histórias.
**Dependência de entrada**: commit T043.
**Eventos**: `colheita.amadurecida`, `colheita.coleta_solicitada`, `colheita.coletada`, `colheita.estragada`, `operacao.recusada` e integração com `vila.encerrada`.
**Independent Test**: V7; aos 20 s há colheita de 30 por 10 s; uma coleta válida credita uma vez, ausência de coleta gera uma perda aos 30 s; no limite exato e depois, a coleta é recusada.

### Testes e implementação da US3

- [ ] T044 [P] [US3] Acrescentar em `tests/test_server.py` testes de amadurecimento a cada 20 s ancorado na abertura, uma colheita disponível, crédito único de 30, ausência de ocupação de agricultor, expiração em 10 s sem débito no celeiro, próximo ciclo aos 40 s, disputa entre dois jogadores e timer antigo sem efeito; validar causas, identidades, dados e destinatários dos eventos (dep.: T043).
- [ ] T045 [US3] Acrescentar em `tests/test_server.py` os casos 1A/2A: fase antes de papel, Mestre recusado com “Só o Jogador pode coletar”, ausência de colheita, chegada T−ε/T/T+ε, timer atrasado, lock ocupado com chegada T−ε/expiração T/liberação T+ε e duas coletas antes de T; verificar crédito único, nenhuma mutação causada por recusa, expiração única e encerramento com atividade pendente (dep.: T044).
- [ ] T046 [US3] Definir a entidade colheita em `server.py`, respeitando as restrições do modelo: `id` “Inteiro crescente, diferente a cada amadurecimento.”; `valor` “Sempre 30 de trigo.”; `amadurecida_em_ms` “Instante público do amadurecimento.”; `expira_em_ms` “Instante público 10 s depois, somente para apresentação.”; guardar prazo monotônico e referência de tarefa separados do snapshot, usar null após coleta/perda e preservar identidade nos fatos (dep.: T045).
- [ ] T047 [US3] Implementar em `server.py` o calendário de amadurecimento abertura + n×20 s, n começando em 1; esperar fora do lock, revalidar fase e ausência de colheita, criar a entidade e emitir `colheita.amadurecida` global com causa `temporizador`, `colheita_id`, `valor: 30` e `prazo: 10`, sem crédito no estoque; não reiniciar o calendário ao coletar (dep.: T046).
- [ ] T048 [US3] Implementar a expiração em `server.py` por identidade e prazo monotônico: se acordar cedo, esperar fora do lock; só pedir o lock em T ou depois, conferir fase/identidade, retirar a colheita uma vez e emitir `colheita.estragada` com causa `colheita.amadurecida`, `gatilho: temporizador`, `colheita_id` e `valor_perdido: 30`, sem alterar o trigo do celeiro (dep.: T047).
- [ ] T049 [US3] Implementar `colheita.coleta_solicitada` em `server.py`: capturar o recebimento na entrada do tratador e imediatamente adquirir o lock, sem outro `await`; validar fase → papel → existência/prazo e aceitar somente `recebido_em < expira_em`; usar as três recusas exatas do contrato; na aceitação retirar a colheita, creditar 30 uma vez, invalidar sua expiração e publicar `colheita.coletada` com causa do pedido, `colheita_id` e `quantidade: 30`, sem ocupar agricultor (dep.: T048).
- [ ] T050 [US3] Integrar amadurecimento/expiração ao encerramento em `server.py`, invalidando e cancelando as tarefas sem esperar dentro do lock; preservar o retrato final da colheita pendente, não publicar perda posterior e garantir que timer de identidade antiga não afete colheita nova; manter moagem, produção e obras igualmente paradas (dep.: T049).
- [ ] T051 [P] [US3] Acrescentar em `client/index.html` botão Coletar exclusivo do Jogador ligado a `pedir('colheita.coleta_solicitada')`, indicador de valor/prazo e escutas via `ouvir` para amadurecimento/coleta/perda; usar `atualizar` e `avisar`, causa/dados/reação no painel e relógio apenas indicativo, retirando o indicador pelos fatos recebidos e congelando-o ao encerrar, sem inferir crédito/perda pelo relógio local (dep.: T043).
- [ ] T052 [US3] Executar os testes de `tests/test_server.py` e V7 de `specs/001-fazenda-tempo-real/quickstart.md` com M/A/B; registrar em `README.md` disputa, coleta e cancelamento da perda, expiração separada da produção simultânea (210 trigo/0 farinha aos 30 s sem obras/coletas), recusas por papel/prazo e encerramento com obra/colheita pendentes; comprovar instantes exatos com relógio controlado, não com cliques (dep.: T050, T051).

### Acabamento e aceitação transversal, no mesmo commit da etapa 7

- [ ] T053 Executar toda a suíte de `tests/test_server.py` com `python -m unittest discover -s tests -p 'test_*.py' -v` e todos os roteiros V1–V7 de `specs/001-fazenda-tempo-real/quickstart.md` sobre a versão final; registrar em `README.md` a cobertura dos cenários US1.1–US1.8, US2.1–US2.9 e US3.1–US3.9 e dos critérios SC-001–SC-007, incluindo entrada tardia, painel, três abas e nenhuma atividade após encerramento (dep.: T052).
- [ ] T054 Finalizar `README.md` com integrante, tema 19, instalação/execução, exemplos de eventos/causas/reações, respostas sobre o paradigma, uso de IA e evidências de cada etapa; conferir consistência com `docs/especificacao.md` e `specs/001-fazenda-tempo-real/contracts/events.md`, corrigindo implementação/documentação de uso sem alterar silenciosamente regras ou decisões 1A/2A (dep.: T053).
- [ ] T055 Criar o commit da etapa 7, `feat: adiciona colheitas com coleta e expiração`, reunindo `server.py`, `client/index.html`, `tests/test_server.py` e `README.md`, inclusive acabamento e aceitação final verificados; manter um único commit desta etapa e preservar alterações preexistentes alheias (dep.: T054).

**Checkpoint**: US1, US2 e US3 cobertas; todas as etapas verificadas e registradas, sem decisões pendentes.

## Dependencies & Execution Order

### Dependências das etapas e commits

```text
Etapa 1: T001–T009
  → Etapa 2: T010–T014
  → Etapa 3: T015–T021
  → Etapa 4: T022–T029
  → Etapa 5: T030–T037
  → Etapa 6: T038–T043
  → Etapa 7: T044–T055
```

O commit final de cada intervalo é dependência da etapa seguinte. Dentro da etapa, respeitar os `dep.` de cada tarefa; quando não houver execução paralela, seguir a ordem numérica. Testes do comportamento são escritos antes da implementação correspondente; os testes já existentes devem continuar passando ao fechar a etapa.

### Dependências e conclusão das histórias

| História | Entregas e dependências | Critério de verificação independente |
| --- | --- | --- |
| US1 (P1) | Conexão/abertura nas etapas 1–2; produção base na 4; encerramento na 5. Os cenários com colheita pendente são completados na 7. | Sem construir/coletar, abrir, observar 160 trigo aos 5 s, sincronizar entrada tardia e encerrar sem atividade posterior; verificar papéis e painel. |
| US2 (P2) | Usa sessão/abertura da US1; obra na 3, conclusão na 4, disputa na 5 e moagem na 6. | Partir de temporada aberta com estado controlado, construir e acompanhar 100 → 110 → 130 → 125 trigo/3 farinha; testar recusas e disputa sem depender de coleta. |
| US3 (P3) | Usa sessão/abertura, lock, relógio e encerramento da US1; segue a etapa 6 pela sequência de entrega, mas sua verificação não exige construir moinhos. | Abrir sem construir, esperar colheita, coletar/disputar ou deixar expirar; validar 1A/2A e encerramento pendente. |

As histórias são verificáveis isolando o comportamento pertinente, mas a sequência de implementação e commits é a das sete etapas. Não executar histórias inteiras em paralelo: elas compartilham `server.py`, `client/index.html` e `tests/test_server.py`.

### Rastreabilidade de requisitos e contratos

| Requisitos | Tarefas principais | Eventos / evidência |
| --- | --- | --- |
| FR-001–FR-003 | T002, T004–T008 | Tema/estado inicial e `estado.sincronizado`; V1. |
| FR-004 | T003, T017, T031, T034, T045, T049 | Exclusão mútua, publicação ordenada e disputas; V5/V7. |
| FR-005 | T010–T014, T030, T032 | Abertura/encerramento e recusas privadas; V2/V5. |
| FR-006–FR-008 | T015–T020, T023, T025, T027 | Construção aceita/recusada e conclusão; V3/V4. |
| FR-009 | T022, T024, T026 | `recurso.produzido`; V4. |
| FR-010–FR-011 | T038–T042 | `farinha.moida` após produção; V6. |
| FR-012 | T044, T046–T047 | `colheita.amadurecida`, calendário e unicidade; V7. |
| FR-013–FR-015 | T044–T045, T048–T049, T051–T052 | Pedido de coleta, coleta, perda, recusa e crédito único; V7. |
| FR-016 | T030, T032–T036, T038, T050 | `vila.encerrada`, retrato final e ausência de efeitos tardios; V5/V7. |
| FR-017–FR-018 | T003, T006, T011–T012, T018, T026–T027, T041, T051, T053 | Destinatários, pedidos, fatos, causa/dados/reação e snapshots em todos os eventos. |
| FR-019 | T003, T024–T025, T038, T047–T050 | Relógio e tarefas do servidor; V4/V6/V7. |
| FR-020 (1A) | T015, T017–T018, T045, T049, T051 | Fase antes do papel; recusas exclusivas de Jogador. |
| FR-021 (2A) | T045, T048–T049, T052 | Antes/no limite/depois; timer atrasado e espera interna. |
| SC-001–SC-007 | T008, T013, T020, T028, T036, T042, T052–T054 | Registros de cada etapa e aceitação final no README. |

## Parallel Opportunities

Paralelismo é opcional e limitado ao mesmo estágio com contrato já definido. Não paralelizar duas tarefas de `tests/test_server.py` entre si nem duas tarefas de `client/index.html` entre si.

| Após concluir | Tarefas que podem avançar juntas | Arquivos distintos |
| --- | --- | --- |
| T003 | T004 e T005 | `server.py` / `client/index.html`. |
| T009 | T010 e T012 | `tests/test_server.py` / `client/index.html`. |
| T014 | T015 e T018 | `tests/test_server.py` / `client/index.html`. |
| T021 | T022 e T026 | `tests/test_server.py` / `client/index.html`. |
| T029 | T030 e T033 | `tests/test_server.py` / `client/index.html`. |
| T037 | T038 e T041 | `tests/test_server.py` / `client/index.html`. |
| T043 | T044 e T051 | `tests/test_server.py` / `client/index.html`. |

### Parallel Example: User Story 1

Após T009, escrever os testes de abertura/sessão T010 enquanto se implementam os pedidos e reações T012. T011 depende dos testes definidos; T013 integra e verifica servidor e cliente antes do commit T014.

### Parallel Example: User Story 2

Após T014, escrever os testes de construção T015 enquanto se implementa a interface T018. Implementar a regra do servidor T016–T017 e o ajuste visual T019; juntar somente em T020, com as três abas.

### Parallel Example: User Story 3

Após T043, escrever os testes de colheita T044 enquanto se implementa a interface T051. T045 estende o mesmo arquivo de testes sequencialmente; o servidor segue T046–T050 antes da verificação conjunta T052.

## Implementation Strategy

### MVP First

Etapas 1–2 entregam a primeira demonstração verificável: conexão, sincronização e abertura. O **MVP do ciclo básico** é a entrega até a etapa 5, porque já permite abrir, produzir, construir, disputar e encerrar. Não chamar esse recorte de US1 integral: seu cenário de encerramento com colheita pendente requer a etapa 7. A entrega acadêmica completa inclui as sete etapas.

### Incremental Delivery

1. Executar setup e fundamentos dentro da etapa 1, reaproveitando o kit.
2. Implementar cada comportamento com seus testes e escutas, respeitando dependências.
3. Verificar com duas abas durante desenvolvimento e com M/A/B antes do fechamento; registrar condições, eventos, destinatários e resultado.
4. Corrigir falhas antes do commit exclusivo da etapa; não antecipar o commit seguinte.
5. Acrescentar moagem e colheitas sem mudar os valores da fonte; repetir os cenários de encerramento ao introduzir novas tarefas temporizadas.
6. Fazer o acabamento transversal e a aceitação final dentro da etapa 7, antes de seu commit.

## Resumo e validação do formato

| Etapa | Intervalo | Quantidade |
| --- | --- | --- |
| 1 — Conexão | T001–T009 | 9 |
| 2 — Abertura | T010–T014 | 5 |
| 3 — Construções | T015–T021 | 7 |
| 4 — Produção/obras | T022–T029 | 8 |
| 5 — Encerramento/disputas | T030–T037 | 8 |
| 6 — Moagem | T038–T043 | 6 |
| 7 — Colheitas/aceitação | T044–T055 | 12 |
| **Total** | **T001–T055** | **55** |

Distribuição: **US1: 20**, **US2: 20**, **US3: 9**, **compartilhadas: 6** (três de setup/fundamentos e três de acabamento/commit final). Há 14 tarefas marcadas `[P]`, formando sete pares de arquivos distintos, e sete tarefas de commit.

Todas as tarefas têm checkbox, ID, arquivo(s), dependências e rótulo de história quando aplicável. As verificações ainda serão executadas na implementação; a geração deste arquivo não marca tarefas como concluídas nem executa testes/commits.
