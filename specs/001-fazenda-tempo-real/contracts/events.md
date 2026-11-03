# Contrato de eventos — Fazenda em tempo real

**Referências**: [requisitos](../spec.md), [modelo](../data-model.md), [roteiro](../quickstart.md).
**Transporte**: Socket.IO da aplicação ASGI existente; nenhuma rota HTTP de mutação adicional.

## Conexão e pedidos

A conexão usa `auth: { nome, papel }`, com papel `mestre` ou `jogador`. O servidor associa esses dados ao `sid`. Após aceitar a entrada ou reconexão, envia `estado.sincronizado` somente àquela conexão. O cliente registra escutas antes de conectar.

Os quatro pedidos de domínio são `vila.abertura_solicitada`, `construcao.solicitada`, `colheita.coleta_solicitada` e `vila.encerramento_solicitado`. Não precisam de payload de regras: custo, quantidades, papel e prazos são determinados pelo servidor. `pedir(nome)` registra o envio e o emite; o painel atribui a ação local como causa do pedido sem exigir que o servidor confie nela.

A coleta se refere à colheita disponível no momento de recebimento/decisão; a interface não escolhe um estoque ou prêmio. `colheita_id` identifica os fatos e protege tarefas de expiração. O instante de chegada vem do tratador no servidor, nunca do payload do cliente. Resultados são comunicados pelos eventos abaixo, sem um segundo protocolo de confirmação.

## Envelope das mensagens do servidor

| Campo | Regra |
| --- | --- |
| `estado` | Snapshot completo após o fato ou no momento da sincronização; nas recusas, snapshot corrente sem mudança causada pelo pedido. Campos definidos no modelo. |
| `causa` | Nome do pedido/evento anterior; `temporizador` para produção/amadurecimento; `conexao` para sincronização. |
| `servidor_em_ms` | Referência temporal pública para apresentação; não faz parte do estado de domínio. |
| Dados específicos | Campos da tabela abaixo que explicam o efeito. |

`reacao` é uma descrição do cliente passada a `ouvir(nome, reacao, funcao)`. Não é uma ordem arbitrária enviada pelo servidor. O painel preserva nomes, direção, horário, causa, dados e reação. A recusa é identificada pelo nome `operacao.recusada`, mantendo a classificação existente.

## Catálogo completo

“Todos” significa todas as conexões participantes, incluindo quem solicitou. “Solicitante” significa somente o `sid` do pedido. Os emissores de pedidos na tabela representam papéis autorizados; o servidor também deve tratar e recusar pedidos de outros papéis.

| Evento | Emissor → destino | Causa | Dados específicos / efeito | Reação do cliente |
| --- | --- | --- | --- | --- |
| `estado.sincronizado` | Servidor → conexão que entrou | `conexao` | Estado corrente; nenhuma mudança | `atualizar`, `jogo.mostrarEstado` sem repetir efeitos. |
| `vila.abertura_solicitada` | Mestre → servidor | Ação local de abrir | Sem payload obrigatório | Registrar envio por `pedir`. |
| `vila.iniciada` | Servidor → todos | `vila.abertura_solicitada` | Fase aberta; referência dos ciclos | `atualizar`, `jogo.vilaIniciada`. |
| `construcao.solicitada` | Jogador → servidor | Ação local de construir | Sem payload obrigatório | Registrar envio por `pedir`. |
| `construcao.iniciada` | Servidor → todos | `construcao.solicitada` | `obra_id`, `custo: 50`; trigo −50 e ocupação +1 | `atualizar`, `jogo.obraIniciada` com identidade e prazo. |
| `operacao.recusada` | Servidor → solicitante | Nome do pedido recusado | `motivo`; estado não alterado pelo pedido | `avisar`, `jogo.recusado`; explicitar que nada foi alterado. |
| `recurso.produzido` | Servidor → todos | `temporizador` | `quantidade`: trigo produzido; estado após o crédito | `atualizar`, `jogo.recursoProduzido`. |
| `construcao.concluida` | Servidor → todos | `construcao.iniciada` | `obra_id`, `gatilho: temporizador`; libera agricultor e acrescenta moinho | `atualizar`, `jogo.obraConcluida` pelo identificador. |
| `farinha.moida` | Servidor → todos | `recurso.produzido` | `moinhos`: quantidade que moeu; `trigo_consumido`, `farinha_produzida` | `atualizar`, aviso de transformação; painel mostra os totais. |
| `colheita.amadurecida` | Servidor → todos | `temporizador` | `colheita_id`, `valor: 30`, `prazo: 10`; dados temporais no snapshot | `atualizar`, exibir colheita e contagem indicativa, avisar. |
| `colheita.coleta_solicitada` | Jogador → servidor | Ação local de coletar | Sem payload obrigatório | Registrar envio por `pedir`. |
| `colheita.coletada` | Servidor → todos | `colheita.coleta_solicitada` | `colheita_id`, `quantidade: 30`; retirar colheita e creditar trigo | `atualizar`, retirar indicador e avisar crédito. |
| `colheita.estragada` | Servidor → todos | `colheita.amadurecida` | `colheita_id`, `valor_perdido: 30`, `gatilho: temporizador`; nenhum débito no celeiro | `atualizar`, retirar indicador e avisar perda. |
| `vila.encerramento_solicitado` | Mestre → servidor | Ação local de encerrar | Sem payload obrigatório | Registrar envio por `pedir`. |
| `vila.encerrada` | Servidor → todos | `vila.encerramento_solicitado` | Fase encerrada e retrato final | `atualizar`, `jogo.vilaEncerrada`; parar progresso e desabilitar ações. |

## Ordem, consistência e destinatários

- O servidor publica os eventos na ordem das transições protegidas pelo lock. Cliente substitui valores com `atualizar`; não aplica também o delta do payload.
- Produção e moagem têm snapshots distintos: com um moinho e 110 de trigo antes do ciclo, produção mostra 130; moagem mostra 125 e farinha acrescida de 3. Sem moinho apto, não emitir `farinha.moida`.
- Usar a identidade da obra na reação visual e a identidade da colheita em cancelamento/expiração; não depender de FIFO de desenhos nem do valor do estoque para reconhecer a entidade.
- Dois pedidos pela última vaga com pelo menos 100 de trigo geram um fato global e uma recusa privada. O perdedor recebe também o fato global; a privacidade se aplica à recusa, não aos fatos.
- A coleta válida antes do prazo pode aguardar o lock; a expiração não passa à sua frente. No prazo exato ou depois, a coleta nunca recebe crédito. Se o timer ainda não executou, a recusa pode preceder `colheita.estragada`; os eventos têm causas distintas e a perda ocorre uma vez.
- Após `vila.encerrada`, não publicar fatos de produção, moagem, conclusão, amadurecimento, coleta ou perda. Novas conexões ainda podem receber o retrato final por `estado.sincronizado`; novos pedidos recebem recusas privadas.
- Reconectar sincroniza o estado atual sem replay dos efeitos antigos. `mostrarEstado` deve ser idempotente e manter consistente o desenho com os contadores.

## Recusas exatas e prioridade

| Pedido | Ordem dos motivos |
| --- | --- |
| `vila.abertura_solicitada` | “Só o Mestre pode abrir a temporada” → “A temporada já foi aberta”. |
| `construcao.solicitada` | “A temporada não está aberta” → “Só o Jogador pode construir” → “Trigo insuficiente” → “Sem agricultor livre”. |
| `colheita.coleta_solicitada` | “A temporada não está aberta” → “Só o Jogador pode coletar” → “Não há colheita para coletar”. |
| `vila.encerramento_solicitado` | “Só o Mestre pode encerrar a temporada” → “A temporada não está aberta”. |

O último motivo da coleta cobre ausência, coleta anterior e prazo vencido. Somente a primeira condição inválida gera recusa. Desabilitar botões não substitui a verificação no servidor; os testes enviam pedidos de papel indevido diretamente aos tratadores.

## Compatibilidade com o kit

Manter `pedir`, `ouvir`, `registrar`, `avisar` e `atualizar`. Estender `resumir` para trigo, farinha, agricultores, obras e colheita. Adaptar os métodos existentes para receber dados de identidade quando necessário; não há métodos de farinha ou colheita prontos, portanto usar Vue/avisos inicialmente, com reações descritas no painel. Preservar a fila de chamadas visuais anterior à criação da cena.
