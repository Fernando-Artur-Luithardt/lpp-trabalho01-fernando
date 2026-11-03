# Pesquisa técnica — Fazenda em tempo real

**Data**: 2026-11-02
**Estado**: Phase 0 concluída; decisões técnicas pesquisadas e decisões de domínio 1A e 2A confirmadas na [spec](spec.md).

## 1. Preservação do kit

**Decision**: manter `server.py`, `client/index.html` e `client/assets/` como base, usando Python, python-socketio, Uvicorn, Vue e Phaser. Manter as dependências atuais e os assets.

**Rationale**: o servidor já é uma aplicação ASGI; o cliente já oferece `pedir`, `ouvir`, `atualizar`, `registrar`, `avisar` e uma fila de chamadas visuais enquanto o Phaser carrega. Não é necessário criar outro projeto, compilador de frontend ou framework web.

**Alternatives considered**: reescrever a interface, separar frontend em pacote ou introduzir outro servidor web acrescenta trabalho sem requisito correspondente.

**Evidência local**: `server.py`, `requirements.txt` e `client/index.html`. O cliente fixa Vue 3.5.13, Socket.IO 4.7.5 e Phaser 3.90.0 por CDN. As dependências Python não têm versões fixadas; a implementação deve registrar as versões efetivamente verificadas.

## 2. Uma vila em memória e um processo

**Decision**: uma única vila em memória, um processo Uvicorn, participantes associados ao `sid`. O papel vem da entrada e permanece associado à sessão; não confiar em papel declarado em cada pedido. Validar o papel recebido na entrada; o kit acadêmico não exige cadastro ou autenticação externa.

**Rationale**: todos compartilham os mesmos estoques. Eventos dirigidos ao `sid` atendem recusas e sincronização; fatos vão para todos. Desconectar um participante não reinicia nem encerra a vila. O servidor continua responsável pelos temporizadores.

**Alternatives considered**: banco de dados, múltiplos workers e broker exigiriam coordenação fora do escopo.

**Fonte**: [python-socketio — servidor ASGI, sessões e destinatários](https://python-socketio.readthedocs.io/en/stable/server.html).

## 3. Exclusão mútua e publicação ordenada

**Decision**: um `asyncio.Lock` para pedidos, temporizadores e snapshot inicial. Dentro da região protegida: validar, alterar, obter cópia do estado e publicar o evento correspondente em ordem. Recusas usam o mesmo caminho de validação, sem mutar estado. O lock não fica retido durante os intervalos de segundos nem enquanto se aguarda término de tarefas canceladas.

**Rationale**: a disputa deve incluir a interferência de produção, conclusão e expiração. Para três clientes, publicar sob o mesmo lock evita observar fatos fora da ordem das transições, com poucas estruturas adicionais.

**Alternatives considered**: uma fila dedicada de comandos/publicação também seria válida, mas aumenta a estrutura do exemplo acadêmico. Locks separados por pedido não protegem as invariantes globais.

**Fonte**: [asyncio.Lock](https://docs.python.org/3/library/asyncio-sync.html#lock). A publicação dentro da mesma região é uma escolha deste projeto, não uma exigência da biblioteca.

## 4. Tarefas, prazos e encerramento

**Decision**: tarefas assíncronas referenciadas pelo servidor; relógio monotônico interno; ciclos de produção e amadurecimento ancorados na abertura; uma tarefa de conclusão por obra e expiração vinculada ao identificador da colheita. Revalidar fase e identidade antes de todo efeito. Encerrar invalida os efeitos e cancela as tarefas; aguardar sua finalização fora do lock.

**Rationale**: cancelamento é cooperativo e não basta sozinho. Um timer antigo não pode estragar uma colheita nova. Prazos absolutos evitam acumular o tempo de execução a cada ciclo. O processamento de produção e sua moagem deve manter a ordem e as condições previstas no domínio.

**Alternatives considered**: timers dos clientes causariam divergência; um scheduler externo é desnecessário. Esperar por tarefas que precisam do lock enquanto ele está retido cria risco de travamento.

**Fontes**: [tarefas e cancelamento](https://docs.python.org/3/library/asyncio-task.html), [agendamento e relógio do event loop](https://docs.python.org/3/library/asyncio-eventloop.html#scheduling-delayed-callbacks).

A ordem de callbacks com o mesmo prazo não deve ser tomada como regra de negócio. A decisão 2A exige recusar coleta recebida no limite exato ou depois dele, mesmo se o callback de expiração atrasar.

## 5. Snapshots, painel e cliente

**Decision**: cada fato leva uma cópia do estado após sua transição, causa e dados do efeito. A entrada recebe `estado.sincronizado` somente no cliente correspondente. Usar `ouvir` para registrar e executar reações e `pedir` para registrar e emitir pedidos. Atualizar Vue via `atualizar(d)` e chamar o método visual pertinente, sem aplicar o crédito novamente no cliente.

**Rationale**: essa estrutura se encaixa no kit, torna a causalidade inspecionável e permite comparar as abas diretamente. Reconectar recebe novo snapshot e não repete fatos antigos. Registrar escutas uma vez por socket, evitando duplicações em reconexões.

**Alternatives considered**: replicar regras de produção ou aplicar apenas deltas locais aumenta o risco de divergência; consultar o estado periodicamente não atende ao paradigma solicitado.

**Evidência local**: `atualizar`, `pedir`, `ouvir`, `registrar` e `resumir` em `client/index.html`.

## 6. Ajustes visuais necessários

**Decision**: reaproveitar os métodos visuais e adaptar somente o necessário: substituir textos de toras por trigo; mostrar farinha e colheita; reconciliar snapshots sem duplicar sprites; identificar obras; usar tempo restante na entrada tardia; interromper progresso ao encerrar e não empilhar sombras de encerramento.

**Rationale**: `mostrarEstado` atualmente adiciona objetos sem limpar/reconciliar; `obraConcluida` remove a primeira obra da lista; `vilaEncerrada` apenas desenha uma sombra. As barras atuais usam a duração total mesmo quando o participante entra depois. A fila `chamar` já trata chegada de eventos antes da criação da cena e deve ser preservada.

**Alternatives considered**: reescrever o mapa ou substituir os assets não é necessário. Os lotes gráficos não constituem um limite de moinhos: a fonte não prevê tal limite. A indicação por minuto deve ser identificada como produção bruta, porque a moagem consome trigo.

## 7. Verificação proporcional ao risco

**Decision**: roteiro manual com Mestre, A e B e testes focados usando `unittest`, `IsolatedAsyncioTestCase` e `unittest.mock`, sem adicionar dependência só para testes. Testar invariantes, destinatários, ordem de validação, corrida entre pedidos e tarefas, cancelamento e fronteiras de prazo com relógio/espera controláveis. As abas verificam transporte, Vue, Phaser e painel de ponta a ponta.

**Rationale**: testes de regra e concorrência justificam-se pelo risco de crédito duplicado e efeitos após encerramento. Evitar esperar vinte segundos por caso automatizado e evitar testar apenas cópias da implementação.

**Alternatives considered**: somente cliques manuais não tornam disputas reproduzíveis; uma suíte visual completa ou novo framework de testes não é necessária para este trabalho.

## 8. Decisões de domínio confirmadas

**Decision**: 1A e 2A, confirmadas pelo usuário em 2026-11-02. Somente Jogador constrói e coleta; validar fase, papel e demais condições. Usar “Só o Jogador pode construir” e “Só o Jogador pode coletar” com a temporada aberta. Coleta só é válida quando recebida no servidor antes da expiração; exatamente no prazo ou depois, “Não há colheita para coletar”.

**Rationale**: preservar a separação de papéis do kit e tornar o prazo de dez segundos inequívoco e reproduzível.

**Alternatives considered**: permitir o Mestre jogar e decidir empate pela ordem de execução do timer foram apresentados e não escolhidos pelo usuário.

## 9. Recebimento estrito sem penalizar espera interna

**Decision**: “recebido pelo servidor” significa a entrada no tratador de coleta, antes de qualquer espera. Registrar `loop.time()` e solicitar imediatamente o lock global, sem outro `await` entre esses passos. Consultar sessão dentro do lock se necessário. Comparar o instante registrado com o prazo monotônico. A tarefa de expiração só solicita o lock depois de conferir que o prazo chegou; se acordar cedo, espera novamente fora dele.

**Rationale**: `asyncio.Lock` atende os aguardantes em ordem. Assim, a coleta registrada antes do prazo já está à frente da expiração, mesmo que ambas esperem outra operação. Essa é uma inferência de projeto baseada na garantia documentada de justiça do lock. O Socket.IO não fornece ao tratador o instante físico de chegada do pacote à rede; não usar timestamps enviados pelo cliente.

**Alternatives considered**: comparar apenas o horário após adquirir o lock penalizaria pedidos válidos; introduzir fila adicional é desnecessário enquanto não houver espera intermediária entre captura e aquisição. Aceitar pedido no limite por atraso do timer contraria 2A.

**Fonte**: [justiça do asyncio.Lock](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock).

**Verificação**: com prazo T, manter o lock ocupado, registrar coleta em T−ε e expiração em T, liberar em T+ε: a coleta ganha uma vez. Repetir com chegada em T e T+ε: recusar independentemente de o timer já ter executado. Verificar também duas coletas antes de T: apenas a primeira aceita ganha.

**Gate de saída**: PASS — nenhuma decisão de domínio pendente. Prosseguir para modelo de dados, contratos e quickstart. As decisões técnicas reutilizam o kit e não alteram os valores da Fazenda.
