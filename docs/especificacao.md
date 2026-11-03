# Especificação — Vila em Tempo Real

**Integrante(s):** (Fernando Artur Luithardt @Fernando-Artur-Luithardt)
**Tipo de vila (sorteio):** 19 — Fazenda (trigo → farinha; construção: moinho; trabalhadores: agricultores; o que expira: a colheita estraga se não for coletada)

> Documento escrito ANTES do código. Descreve o comportamento na linguagem da fazenda, sem citar tecnologia.

**Especificação Spec Kit:** [Fazenda em tempo real](../specs/001-fazenda-tempo-real/spec.md). Este documento é a fonte das regras de domínio; alterações de regras, eventos ou decisões devem ser refletidas nos dois documentos.

## 1. Regras da vila

- **Recurso primário e refinado:** o recurso primário é o **trigo**. O recurso refinado é a **farinha**, produzida pelos moinhos a partir do trigo.
- **Papéis:** o **Mestre** abre e encerra a temporada. Somente o **Jogador** constrói moinhos e coleta colheitas; o Mestre não executa essas duas ações.
- **Estoque inicial:** 150 de trigo e 0 de farinha.
- **Custo de uma construção:** cada moinho custa **50 de trigo**, debitados quando a obra começa.
- **Tempo da obra:** **8 segundos**. A obra termina sozinha, sem ninguém pedir.
- **Limite de trabalhadores:** **3 agricultores**. Cada obra ocupa 1 agricultor até terminar. Com 3 de 3 ocupados, nenhuma obra nova pode começar.
- **Produção automática:** a cada **5 segundos**, a fazenda produz **10 de trigo** (produção base). Cada moinho concluído aumenta a produção em **+10 de trigo por intervalo**.
- **Moagem (recurso refinado):** logo depois de cada produção, cada moinho concluído transforma **5 de trigo em 3 de farinha**. Se não houver trigo suficiente para um moinho, ele não mói naquele intervalo. A farinha não é gasta: fica guardada no celeiro e mostra o resultado da temporada.
- **Colheita com prazo (evento próprio):** a cada **20 segundos** desde a abertura, uma colheita amadurece na lavoura, valendo **30 de trigo**, e fica disponível por **10 segundos**.
  - Só pode existir uma colheita disponível por vez. Se já houver uma, nenhuma nova amadurece naquele ciclo.
  - Qualquer Jogador pode coletá-la. Quem pedir primeiro leva; a coleta não ocupa agricultor.
  - O pedido deve ser recebido pelo servidor estritamente antes do instante de expiração. No instante exato ou depois dele, a coleta é recusada com "Não há colheita para coletar", mesmo que o temporizador ainda não tenha processado a perda. O relógio do cliente não decide a validade.
  - Se ninguém coletar dentro do prazo, a colheita **estraga** e os 30 de trigo se perdem.
- **O que muda quando uma obra termina:** o agricultor volta a ficar livre, as obras concluídas aumentam em 1, a produção sobe em +10 de trigo por intervalo e o novo moinho passa a moer farinha a partir do intervalo seguinte.
- **Recusas possíveis** (sempre só para quem pediu):
  - abrir a temporada: "Só o Mestre pode abrir a temporada" ou "A temporada já foi aberta";
  - construir: "A temporada não está aberta", "Só o Jogador pode construir", "Trigo insuficiente" ou "Sem agricultor livre" (fase, papel, estoque e agricultor, nessa ordem);
  - coletar: "A temporada não está aberta", "Só o Jogador pode coletar" ou "Não há colheita para coletar" (fase, papel e colheita disponível dentro do prazo, nessa ordem);
  - encerrar a temporada: "Só o Mestre pode encerrar a temporada" ou "A temporada não está aberta".
- **Encerramento:** quando o Mestre encerra, a produção, a moagem e as colheitas param. Obras em andamento não terminam. Qualquer ação nova é recusada.

## 2. Eventos

| Evento | Emite | Recebe | O que muda no estado |
|---|---|---|---|
| `vila.abertura_solicitada` | Mestre | Servidor | (é um pedido; nada muda) |
| `vila.iniciada` | Servidor | Todos | A fase passa de "aguardando" para "aberta"; a produção automática e o relógio das colheitas começam |
| `construcao.solicitada` | Jogador | Servidor | (é um pedido; nada muda) |
| `construcao.iniciada` | Servidor | Todos | Trigo −50; agricultores ocupados +1; obras em andamento +1; a contagem de 8 s começa |
| `operacao.recusada` | Servidor | Só quem pediu | Nada muda; quem pediu recebe o motivo da recusa |
| `recurso.produzido` | Servidor | Todos | Trigo + produção atual (10 + 10 por moinho concluído); disparado pelo temporizador, a cada 5 s |
| `farinha.moida` | Servidor | Todos | Para cada moinho que moeu: trigo −5 e farinha +3; só ocorre se houver moinho concluído e trigo suficiente |
| `construcao.concluida` | Servidor | Todos | Agricultores ocupados −1; obras em andamento −1; obras concluídas +1; produção +10 de trigo por intervalo |
| `colheita.amadurecida` | Servidor | Todos | Aparece uma colheita disponível de 30 de trigo, com prazo de 10 s |
| `colheita.coleta_solicitada` | Jogador | Servidor | (é um pedido; nada muda) |
| `colheita.coletada` | Servidor | Todos | Trigo +30; a colheita disponível desaparece; o prazo deixa de valer |
| `colheita.estragada` | Servidor | Todos | A colheita disponível desaparece sem render nada; disparado pelo temporizador ao fim do prazo |
| `vila.encerramento_solicitado` | Mestre | Servidor | (é um pedido; nada muda) |
| `vila.encerrada` | Servidor | Todos | A fase passa a "encerrada"; produção, moagem e colheitas param; novas ações são recusadas |

**Encadeamento (causa de cada fato ou recusa):**

- `vila.iniciada` ← `vila.abertura_solicitada`
- `construcao.iniciada` ← `construcao.solicitada`
- `construcao.concluida` ← `construcao.iniciada` (temporizador)
- `recurso.produzido` ← temporizador
- `farinha.moida` ← `recurso.produzido` (causa imediata; a produção foi disparada pelo temporizador)
- `colheita.amadurecida` ← temporizador
- `colheita.coletada` ← `colheita.coleta_solicitada`
- `colheita.estragada` ← `colheita.amadurecida` (temporizador)
- `vila.encerrada` ← `vila.encerramento_solicitado`
- `operacao.recusada` ← o pedido que falhou na validação (abertura, construção, coleta ou encerramento)

## 3. Cenários de teste (Dado / Quando / Então, escritos com eventos)

### Recusa

**Dado** que a temporada está "aguardando" (o Mestre ainda não abriu) e o Jogador A está conectado,
**quando** o Jogador A emite `construcao.solicitada`,
**então** o servidor emite `operacao.recusada` apenas para o Jogador A, com o motivo "A temporada não está aberta"; nenhum outro participante recebe nada; o trigo continua em 150 e os agricultores ocupados continuam em 0.

*Variante:* **dado** que a temporada está aberta, os 3 agricultores estão ocupados e há pelo menos **50 de trigo** (estoque suficiente para uma construção), **quando** o Jogador A emite `construcao.solicitada`, **então** o servidor emite `operacao.recusada` apenas para ele, com o motivo "Sem agricultor livre", e o trigo não é debitado.

### Passagem do tempo

**Dado** que a temporada acabou de ser aberta (`vila.iniciada`), com 150 de trigo, produção de 10 por intervalo de 5 s e nenhum moinho,
**quando** o Jogador A emite `construcao.solicitada`, a obra começa no instante de referência da abertura (t = 0) e, depois disso, ninguém faz mais nada,
**então**:

1. o servidor emite `construcao.iniciada` para todos: trigo 100, agricultores ocupados 1 de 3;
2. aos 5 s, o servidor emite `recurso.produzido` (causa: temporizador): trigo 110;
3. aos 8 s, o servidor emite `construcao.concluida` (causa: `construcao.iniciada`, temporizador): agricultores ocupados 0 de 3, obras concluídas 1, produção passa a 20 por intervalo;
4. aos 10 s, o servidor emite `recurso.produzido`: trigo 130; em seguida emite `farinha.moida` (causa: `recurso.produzido`): trigo 125 e farinha 3.

Tudo isso aparece nas telas do Mestre, do Jogador A e de qualquer outro Jogador sem que ninguém clique. Os 8 s da obra são contados desde `construcao.iniciada`; se ela começar depois da abertura, sua conclusão se desloca pelo mesmo tempo, sem deslocar os ciclos de produção.

### Disputa entre dois jogadores

**Dado** que a temporada está aberta, há 2 de 3 agricultores ocupados e o estoque inicial da disputa é de pelo menos **100 de trigo**,
**quando** os jogadores A e B emitem `construcao.solicitada` ao mesmo tempo, sem produção, moagem, conclusão de obra ou outro evento que altere essas condições entre as duas decisões,
**então** o servidor decide um pedido de cada vez: emite `construcao.iniciada` para todos referente a um deles (agricultores 3 de 3, trigo debitado uma única vez em 50) e emite `operacao.recusada` apenas para o outro, com o motivo "Sem agricultor livre". Após o primeiro débito, restam pelo menos 50 de trigo; por isso o segundo pedido passa na validação de estoque e é recusado por falta de agricultor. Os agricultores ocupados nunca passam de 3 e o trigo nunca fica negativo.

### Extra 1 — Colheita estragada (evento próprio)

**Dado** que a temporada está aberta e 20 s se passaram desde a abertura,
**quando** o servidor emite `colheita.amadurecida` (colheita de 30 de trigo, prazo de 10 s) e nenhum Jogador emite `colheita.coleta_solicitada` dentro do prazo,
**então** ao fim dos 10 s o servidor emite `colheita.estragada` para todos (causa: `colheita.amadurecida`, temporizador): a colheita desaparece e esse evento não altera o trigo do celeiro: os 30 de trigo não coletados se perdem, sem débito no estoque. A produção e a moagem continuam normalmente e seus efeitos são verificados separadamente, inclusive quando ocorrem no mesmo instante.

### Extra 2 — Disputa pela colheita (evento próprio)

**Dado** que a temporada está aberta e há uma colheita disponível dentro do prazo,
**quando** os jogadores A e B emitem `colheita.coleta_solicitada` ao mesmo tempo, antes da expiração e sem encerramento entre as duas decisões,
**então** o servidor emite `colheita.coletada` para todos referente a um deles (trigo +30, uma única vez) e emite `operacao.recusada` apenas para o outro, com o motivo "Não há colheita para coletar".

## 4. Complementos de observação e verificação

- O estoque de trigo e farinha é compartilhado pela fazenda. “Quem pedir primeiro leva” significa que o pedido vencedor causa um único crédito de 30 no estoque comum, sem inventário pessoal.
- A ordem dos pedidos em disputa é a ordem em que o servidor os decide; a ordem de cliques em relógios diferentes não garante o vencedor.
- O painel deve permitir identificar o pedido enviado, o fato ou recusa recebido, sua causa, os dados relevantes e a reação do cliente. Uma recusa mostra seu motivo sem alterar o estado da vila.
- Todos os fatos da tabela são enviados a todos; cada recusa vai apenas ao solicitante. “Nenhum outro participante recebe nada” no cenário de recusa significa nenhum evento causado pelo pedido recusado; eventos autônomos continuam quando a temporada está aberta.
- Ao entrar, o participante deve visualizar o estado atual, conforme a constituição. Essa sincronização não muda a vila nem repete efeitos de fatos antigos. Essa comunicação usa `estado.sincronizado`, conforme a etapa de conexão solicitada; os 14 eventos de domínio acima são preservados.

### Abertura e controle de papel

**Dado** que a fase é “aguardando”, o estoque é 150 de trigo e 0 de farinha, não há obras, agricultores ocupados nem colheita disponível, **quando** o Mestre solicita a abertura, **então** todos recebem `vila.iniciada` e veem a fase “aberta”, sem alteração imediata do estoque. Os relógios de produção e colheita começam nessa abertura.

**Dado** que um Jogador tenta abrir ou encerrar a temporada, **quando** o pedido é validado, **então** apenas ele recebe `operacao.recusada`, respectivamente com “Só o Mestre pode abrir a temporada” ou “Só o Mestre pode encerrar a temporada”, sem mudança de estado.

**Dado** que a temporada já foi aberta, **quando** o Mestre pede abertura novamente, **então** recebe “A temporada já foi aberta”, sem reiniciar os relógios. **Dado** que a temporada não está aberta, **quando** o Mestre pede encerramento, **então** recebe “A temporada não está aberta”.

### Ordem de validação e limites

**Dado** que a temporada está aberta, há 49 de trigo e os 3 agricultores estão ocupados, **quando** um Jogador pede construção, **então** recebe “Trigo insuficiente”, sem alteração de estoque ou ocupação. Com a temporada fora da fase aberta, a mesma tentativa recebe “A temporada não está aberta”.

**Dado** que há exatamente 50 de trigo, um agricultor livre e a temporada aberta, **quando** um Jogador pede construção, **então** todos recebem `construcao.iniciada`, o estoque passa a zero e exatamente um agricultor é ocupado.

### Coleta e prazo cancelado

**Dado** que a temporada está aberta e existe colheita disponível dentro do prazo, **quando** um Jogador solicita coleta, **então** todos recebem `colheita.coletada`, o estoque comum ganha 30 de trigo uma única vez e a ocupação dos agricultores não muda. Ao chegar o antigo prazo, não ocorre `colheita.estragada` para essa colheita.

**Dado** que a temporada está aberta e não há colheita disponível, **quando** um Jogador pede coleta, **então** só ele recebe “Não há colheita para coletar”. Se a temporada não estiver aberta, recebe “A temporada não está aberta”.

### Moagem e ciclo seguinte

**Dado** um intervalo de produção com moinhos concluídos, **quando** ocorre `recurso.produzido`, **então** a moagem vem depois, consumindo 5 de trigo e acrescentando 3 de farinha por moinho que puder moer. Um moinho sem trigo suficiente não mói; com nenhum moinho apto, não há `farinha.moida`. A farinha acumulada nunca é gasta.

**Dado** que ainda existe colheita disponível ao chegar um ciclo de amadurecimento, **quando** o ciclo é avaliado, **então** não aparece outra colheita nem ocorre novo `colheita.amadurecida`. Esse é um cenário de estado controlado: em execução regular, o prazo de 10 s termina antes do próximo ciclo de 20 s.

### Encerramento com atividades pendentes

**Dado** que a temporada está aberta, há obra em andamento e colheita disponível, **quando** o Mestre pede encerramento antes dos respectivos prazos, **então** todos recebem `vila.encerrada`. Depois dela, não há produção, moagem, conclusão de obra, amadurecimento ou expiração; pedidos de construção e coleta são recusados com “A temporada não está aberta”. O estado imediatamente posterior ao encerramento permanece inalterado ao atravessar os prazos que estavam pendentes.

## 5. Premissas e decisões confirmadas

As premissas abaixo tornam a verificação explícita sem mudar valores da fazenda:

- A demonstração usa um Mestre e dois jogadores conectados à mesma vila. Novas temporadas, recuperação após reinício e troca de papéis não fazem parte desta entrega.
- A fase encerrada é final para a temporada. Preservam-se os estoques e os registros de obras e colheitas como retrato final, sem reembolso, conclusão, coleta ou expiração posterior. Os controles exibem que a temporada acabou.
- Para observar a moagem, considera-se um resumo por intervalo com o total de moinhos que moeram, trigo consumido e farinha produzida. A fonte não exige um evento separado por moinho; os efeitos por moinho são preservados.
- Eventos independentes com o mesmo horário não têm uma ordem global exigida. A moagem deve seguir sua produção, e um moinho só participa a partir do intervalo posterior à sua conclusão. No instante exato do prazo de coleta, a expiração prevalece, conforme Q2 abaixo.
- Os tempos indicam instantes do domínio contados pelo servidor; o tempo de entrega às telas não muda os prazos.

**Q1 — Permissões do Mestre (1A, confirmada em 2026-11-02):** construção e coleta são exclusivas do Jogador. Validar primeiro a fase, depois o papel e então as condições da operação. Com a temporada aberta, recusar pedidos do Mestre com “Só o Jogador pode construir” ou “Só o Jogador pode coletar”; fora da fase aberta, usar “A temporada não está aberta”. As recusas vão somente ao solicitante e não alteram o estado.

**Q2 — Coleta no instante de expiração (2A, confirmada em 2026-11-02):** adotar prazo estrito de recebimento no servidor. Uma coleta só pode ser aceita se recebida antes da expiração e se passar pelas demais validações. No instante exato ou depois, responder “Não há colheita para coletar”; atrasos na execução do temporizador não prolongam o prazo.

### Cenários das decisões confirmadas

**Dado** que a temporada está aberta, **quando** o Mestre solicita construção ou coleta, **então** somente ele recebe, respectivamente, “Só o Jogador pode construir” ou “Só o Jogador pode coletar”, mesmo que também faltem trigo, agricultor ou colheita. Fora da fase aberta, ambas as ações recebem primeiro “A temporada não está aberta”. Nenhum pedido recusado altera o estado.

**Dado** que há uma colheita disponível com expiração no instante T e a temporada continua aberta, **quando** um pedido de Jogador chega ao servidor antes de T, **então** ele pode ser aceito, sujeito à disponibilidade e à ordem dos pedidos. **Quando** chega exatamente em T ou depois, **então** recebe “Não há colheita para coletar” e não há crédito. A perda ocorre uma única vez por causa do prazo; não é efeito do pedido recusado. O cenário deve incluir execução atrasada do temporizador para confirmar que o prazo não é estendido.
