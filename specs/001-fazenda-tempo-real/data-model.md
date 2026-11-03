# Modelo de dados — Fazenda em tempo real

**Referências**: [spec](spec.md), [eventos](contracts/events.md), [pesquisa](research.md).
**Estado**: desenho para implementação; valores de domínio preservados, decisões 1A e 2A incorporadas.

## Vila e temporada

Uma instância de estado por processo, sem persistência. Campos públicos do snapshot:

| Campo | Tipo / inicial | Regra |
| --- | --- | --- |
| `tema` | inteiro / 19 | Fazenda. |
| `fase` | texto / `aguardando` | `aguardando` → `aberta` → `encerrada`; sem reabertura. |
| `trigo` | inteiro / 150 | Compartilhado, nunca negativo. Substitui `toras` no cliente. |
| `farinha` | inteiro / 0 | Compartilhada, nunca gasta. |
| `trabalhadores` | inteiro / 0 | Agricultores ocupados; igual à quantidade de obras em andamento. |
| `limite` | inteiro / 3 | Capacidade de agricultores, não limite de moinhos. |
| `custo` | inteiro / 50 | Trigo debitado no início de uma obra. |
| `tempo_obra` | segundos / 8 | Prazo desde o início da obra. |
| `intervalo` | segundos / 5 | Intervalo de produção. |
| `producao` | inteiro / 10 | Produção bruta por intervalo: `10 + 10 * concluidas`. |
| `concluidas` | inteiro / 0 | Quantidade de moinhos concluídos. |
| `em_obra` | inteiro / 0 | Quantidade de obras em andamento. |
| `obras` | lista / vazia | Obras em andamento e concluídas, por identidade estável. |
| `colheita` | objeto ou null / null | A única colheita disponível; retirada ao coletar ou estragar. |
| `aberta_em_ms` | instante ou null / null | Instante público de abertura, apenas para apresentação. |
| `encerrada_em_ms` | instante ou null / null | Instante do retrato final. |

`trabalhadores`, `em_obra`, `concluidas` e `producao` são projeções das obras; calculá-las em um único ponto ao produzir o snapshot evita contagens divergentes. Manter nomes do kit quando não prejudicam o domínio; a interface apresenta agricultores e moinhos.

Internamente, guardar instante monotônico de abertura, lock comum, contador de identidades e referências das tarefas. Objetos de tarefa, lock e sessões nunca são serializados. Um snapshot é uma cópia: mutações seguintes não podem mudar dados de um evento já publicado.

## Participante

| Campo | Uso |
| --- | --- |
| `sid` | Identidade da conexão e destino da sincronização/recusa. |
| `nome` | Texto recebido na entrada; usar “Anônimo” se vazio. |
| `papel` | `mestre` ou `jogador`, associado à sessão pelo servidor. |

O kit permite escolher papel na entrada; não há autenticação externa neste escopo. Papel desconhecido rejeita a conexão. Desconectar remove a sessão, sem cancelar obras ou a temporada. Reentrar cria nova sessão e recebe snapshot; pedidos não fornecem um papel alternativo. Não criar regra de limite de Mestres sem requisito: a demonstração usa um Mestre, e as operações continuam serializadas caso outro se conecte.

## Obra e moinho

| Campo público | Uso |
| --- | --- |
| `id` | Inteiro crescente, estável na execução; também é `obra_id` nos eventos. |
| `status` | `em_andamento` ou `concluida`. |
| `iniciada_em_ms` | Instante de início para apresentação. |
| `concluir_em_ms` | Prazo de conclusão para apresentação. |
| `concluida_em_ms` | Instante da conclusão efetiva ou null. |

Internamente, guardar os instantes monotônicos equivalentes. Cada obra em andamento ocupa um agricultor. Na conclusão, liberar o agricultor e manter a identidade do moinho. Não é necessário guardar propriedade individual: os benefícios são da fazenda.

Phaser associa objetos ao `id`, usando ordem estável para posicionamento. Não concluir pela posição inicial de uma lista. Entrada tardia reconstrói o estado sem reproduzir textos de débito ou novos créditos. A barra representa tempo restante, mas só `construcao.concluida` confirma o moinho.

Ao encerrar, obras em andamento permanecem como registros não concluídos no retrato final; sem liberar agricultores, reembolsar trigo ou continuar barras. A fase global indica que não terminarão nessa temporada.

## Colheita

| Campo público | Uso |
| --- | --- |
| `id` | Inteiro crescente, diferente a cada amadurecimento. |
| `valor` | Sempre 30 de trigo. |
| `amadurecida_em_ms` | Instante público do amadurecimento. |
| `expira_em_ms` | Instante público 10 s depois, somente para apresentação. |

Internamente, `expira_em` usa o mesmo relógio monotônico do recebimento dos pedidos. Fora do estado disponível, o snapshot usa null; o evento que retirou a colheita preserva seu `colheita_id` e explica coleta/perda. Histórico adicional não é necessário.

Transições: ausente → disponível pelo ciclo de 20 s; disponível → ausente por coleta aceita ou expiração, nunca pelas duas. Ao encerrar com colheita disponível, manter o retrato final e desabilitar a coleta; não emitir perda posterior.

## Relógios e fronteiras

- Usar `loop.time()` para decisões; nunca confiar em horário do cliente ou comparar diretamente relógios monotônicos de máquinas diferentes.
- Converter os instantes para milissegundos públicos com uma referência civil fixada na execução; enviar `servidor_em_ms` no envelope para estimar a apresentação local. Alterações de relógio civil não mudam os prazos internos.
- Os instantes públicos permanecem estáveis nos snapshots. Ao encerrar, congelar a apresentação no `encerrada_em_ms`; não reduzir estoques nem mudar estado para acompanhar uma contagem local.
- Produção ocorre em `abertura + n*5 s`; amadurecimento em `abertura + n*20 s`, com n começando em 1. Uma tarefa atrasada verifica novamente fase/identidade antes do efeito. Não antecipar um ciclo.
- Moagem vem após produção no mesmo ciclo. Elegibilidade exige moinho concluído antes do instante daquele intervalo; conclusão exatamente no limite só habilita moagem no próximo, independentemente da ordem de execução dos callbacks.
- Recebimento de coleta é a entrada no tratador, antes de qualquer espera. Capturar esse instante e solicitar o lock imediatamente, sem outro `await`. Prazo válido exige `recebido_em < expira_em`.
- A tarefa de expiração só pede o lock no prazo ou depois. A justiça do lock preserva pedidos que já estavam aguardando antes do prazo. Se a coleta recebeu o lock antes da expiração, mas seu recebimento já foi em T ou depois, recusar sem crédito; o timer ainda deve publicar a perda uma única vez.
- Recusar um pedido não modifica o estado. A expiração continua sendo transição autônoma causada pelo temporizador, mesmo quando um pedido atrasado permite constatar que o prazo venceu.

## Validações ordenadas

| Pedido | Ordem | Motivos correspondentes |
| --- | --- | --- |
| Abrir | Mestre → aguardando | “Só o Mestre pode abrir a temporada”; “A temporada já foi aberta”. |
| Construir | aberta → Jogador → trigo ≥ 50 → ocupação < 3 | “A temporada não está aberta”; “Só o Jogador pode construir”; “Trigo insuficiente”; “Sem agricultor livre”. |
| Coletar | aberta → Jogador → colheita disponível e recebimento antes do prazo | “A temporada não está aberta”; “Só o Jogador pode coletar”; “Não há colheita para coletar”. |
| Encerrar | Mestre → aberta | “Só o Mestre pode encerrar a temporada”; “A temporada não está aberta”. |

Publicar somente a primeira recusa aplicável, dirigida ao solicitante. Todas as decisões, inclusive as dos timers, passam pelo mesmo lock. Após qualquer transição, preservar trigo ≥ 0, farinha ≥ 0, ocupação entre 0 e 3 e no máximo uma colheita disponível.
