# Especificação — Vila em Tempo Real

**Integrante(s):** (Fernando Artur Luithardt @Fernando-Artur-Luithardt)
**Tipo de vila (sorteio):** 2 — Fazenda (trigo → farinha; construção: moinho; trabalhadores: agricultores; o que expira: a colheita estraga se não for coletada)

> Documento escrito ANTES do código. Descreve o comportamento na linguagem da fazenda, sem citar tecnologia.

## 1. Regras da vila

- **Recurso primário e refinado:** o recurso primário é o **trigo**. O recurso refinado é a **farinha**, produzida pelos moinhos a partir do trigo.
- **Papéis:** o **Mestre** abre e encerra a temporada. O **Jogador** constrói moinhos e coleta colheitas.
- **Estoque inicial:** 150 de trigo e 0 de farinha.
- **Custo de uma construção:** cada moinho custa **50 de trigo**, debitados quando a obra começa.
- **Tempo da obra:** **8 segundos**. A obra termina sozinha, sem ninguém pedir.
- **Limite de trabalhadores:** **3 agricultores**. Cada obra ocupa 1 agricultor até terminar. Com 3 de 3 ocupados, nenhuma obra nova pode começar.
- **Produção automática:** a cada **5 segundos**, a fazenda produz **10 de trigo** (produção base). Cada moinho concluído aumenta a produção em **+10 de trigo por intervalo**.
- **Moagem (recurso refinado):** logo depois de cada produção, cada moinho concluído transforma **5 de trigo em 3 de farinha**. Se não houver trigo suficiente para um moinho, ele não mói naquele intervalo. A farinha não é gasta: fica guardada no celeiro e mostra o resultado da temporada.
- **Colheita com prazo (evento próprio):** a cada **20 segundos** desde a abertura, uma colheita amadurece na lavoura, valendo **30 de trigo**, e fica disponível por **10 segundos**.
  - Só pode existir uma colheita disponível por vez. Se já houver uma, nenhuma nova amadurece naquele ciclo.
  - Qualquer Jogador pode coletá-la. Quem pedir primeiro leva; a coleta não ocupa agricultor.
  - Se ninguém coletar dentro do prazo, a colheita **estraga** e os 30 de trigo se perdem.
- **O que muda quando uma obra termina:** o agricultor volta a ficar livre, as obras concluídas aumentam em 1, a produção sobe em +10 de trigo por intervalo e o novo moinho passa a moer farinha a partir do intervalo seguinte.
- **Recusas possíveis** (sempre só para quem pediu):
  - abrir a temporada: "Só o Mestre pode abrir a temporada" ou "A temporada já foi aberta";
  - construir: "A temporada não está aberta", "Trigo insuficiente" ou "Sem agricultor livre" (verificados nessa ordem);
  - coletar: "A temporada não está aberta" ou "Não há colheita para coletar";
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

**Encadeamento (causa de cada fato):**

- `vila.iniciada` ← `vila.abertura_solicitada`
- `construcao.iniciada` ← `construcao.solicitada`
- `construcao.concluida` ← `construcao.iniciada` (temporizador)
- `recurso.produzido` ← temporizador
- `farinha.moida` ← `recurso.produzido` (temporizador)
- `colheita.amadurecida` ← temporizador
- `colheita.coletada` ← `colheita.coleta_solicitada`
- `colheita.estragada` ← `colheita.amadurecida` (temporizador)
- `vila.encerrada` ← `vila.encerramento_solicitado`

## 3. Cenários de teste (Dado / Quando / Então, escritos com eventos)

### Recusa

**Dado** que a temporada está "aguardando" (o Mestre ainda não abriu) e o Jogador A está conectado,
**quando** o Jogador A emite `construcao.solicitada`,
**então** o servidor emite `operacao.recusada` apenas para o Jogador A, com o motivo "A temporada não está aberta"; nenhum outro participante recebe nada; o trigo continua em 150 e os agricultores ocupados continuam em 0.

*Variante:* **dado** que a temporada está aberta e os 3 agricultores estão ocupados, **quando** o Jogador A emite `construcao.solicitada`, **então** o servidor emite `operacao.recusada` apenas para ele, com o motivo "Sem agricultor livre", e o trigo não é debitado.

### Passagem do tempo

**Dado** que a temporada acabou de ser aberta (`vila.iniciada`), com 150 de trigo, produção de 10 por intervalo de 5 s e nenhum moinho,
**quando** o Jogador A emite `construcao.solicitada` e, depois disso, ninguém faz mais nada,
**então**:

1. o servidor emite `construcao.iniciada` para todos: trigo 100, agricultores ocupados 1 de 3;
2. aos 5 s, o servidor emite `recurso.produzido` (causa: temporizador): trigo 110;
3. aos 8 s, o servidor emite `construcao.concluida` (causa: `construcao.iniciada`, temporizador): agricultores ocupados 0 de 3, obras concluídas 1, produção passa a 20 por intervalo;
4. aos 10 s, o servidor emite `recurso.produzido`: trigo 130; em seguida emite `farinha.moida` (causa: `recurso.produzido`): trigo 125 e farinha 3.

Tudo isso aparece nas telas do Mestre, do Jogador A e de qualquer outro Jogador sem que ninguém clique.

### Disputa entre dois jogadores

**Dado** que a temporada está aberta, há 2 de 3 agricultores ocupados e o trigo é de pelo menos 50,
**quando** os jogadores A e B emitem `construcao.solicitada` ao mesmo tempo,
**então** o servidor decide um pedido de cada vez: emite `construcao.iniciada` para todos referente a um deles (agricultores 3 de 3, trigo debitado uma única vez em 50) e emite `operacao.recusada` apenas para o outro, com o motivo "Sem agricultor livre". Os agricultores ocupados nunca passam de 3 e o trigo nunca fica negativo.

### Extra 1 — Colheita estragada (evento próprio)

**Dado** que a temporada está aberta e 20 s se passaram desde a abertura,
**quando** o servidor emite `colheita.amadurecida` (colheita de 30 de trigo, prazo de 10 s) e nenhum Jogador emite `colheita.coleta_solicitada` dentro do prazo,
**então** ao fim dos 10 s o servidor emite `colheita.estragada` para todos (causa: `colheita.amadurecida`, temporizador): a colheita desaparece e o trigo não aumenta.

### Extra 2 — Disputa pela colheita (evento próprio)

**Dado** que há uma colheita disponível dentro do prazo,
**quando** os jogadores A e B emitem `colheita.coleta_solicitada` ao mesmo tempo,
**então** o servidor emite `colheita.coletada` para todos referente a um deles (trigo +30, uma única vez) e emite `operacao.recusada` apenas para o outro, com o motivo "Não há colheita para coletar".
