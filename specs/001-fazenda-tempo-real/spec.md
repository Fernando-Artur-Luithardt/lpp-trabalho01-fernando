# Feature Specification: Fazenda em tempo real — tema 19

**Feature Branch**: `main` (branch atual; nenhum hook de criação configurado)

**Created**: 2026-11-02

**Status**: Ready for planning — decisões 1A e 2A confirmadas em 2026-11-02

**Input**: User description: "Usar docs/especificacao.md como fonte, preservar regras e valores da Fazenda, corrigir o tema para 19 e os estoques dos cenários de disputa e recusa, conferir eventos, causas e testes; trabalhar somente na documentação."

**Fonte de domínio**: [docs/especificacao.md](../../docs/especificacao.md).
**Governança**: [constituição](../../.specify/memory/constitution.md).
**Diretório da feature**: `specs/001-fazenda-tempo-real`.

## User Scenarios & Testing *(mandatory)*

Os cenários usam um Mestre e dois jogadores, A e B, na mesma fazenda. Os tempos são contados no servidor; a comparação das telas ocorre após o recebimento dos eventos. Estados controlados permitem verificar limites isoladamente, sem alterar as regras normais da temporada. Os rótulos USn.m identificam cada cenário pela história e pelo item.

### User Story 1 - Acompanhar e controlar a temporada (Priority: P1)

Como participante, quero acompanhar uma fazenda compartilhada; como Mestre, quero abrir e encerrar a temporada, para controlar quando suas atividades podem ocorrer.

**Why this priority**: estabelece a visão comum e os limites de toda atividade.

**Independent Test**: conectar três participantes, abrir a temporada e observar a produção base sem construir; encerrar e confirmar a ausência de novos efeitos.

**Acceptance Scenarios**:

1. **Given** uma vila aguardando com 150 de trigo, 0 de farinha e nenhuma obra, ocupação ou colheita, **When** os participantes entram, **Then** cada um recebe `estado.sincronizado` com o mesmo estado atual, sem alterar a vila.
2. **Given** a vila aguardando, **When** o Mestre emite `vila.abertura_solicitada`, **Then** todos recebem `vila.iniciada`, a fase passa a aberta e os ciclos de produção e colheita começam, sem crédito imediato de recursos.
3. **Given** uma vila aberta sem moinhos nem ações posteriores, **When** passam 5 s, **Then** todos recebem `recurso.produzido`, o trigo passa a 160 e a farinha permanece em zero, sem `farinha.moida`.
4. **Given** um Jogador, **When** ele pede abertura ou encerramento, **Then** apenas ele recebe `operacao.recusada` com “Só o Mestre pode abrir a temporada” ou “Só o Mestre pode encerrar a temporada”; não há mudança de estado.
5. **Given** a temporada já aberta, **When** o Mestre pede abertura novamente, **Then** recebe “A temporada já foi aberta” e nenhum relógio é reiniciado. **Given** a temporada fora da fase aberta, **When** pede encerramento, **Then** recebe “A temporada não está aberta”.
6. **Given** a temporada aberta com uma obra e uma colheita pendentes, **When** o Mestre emite `vila.encerramento_solicitado` antes dos prazos, **Then** todos recebem `vila.encerrada`; depois disso não ocorre produção, moagem, conclusão de obra, amadurecimento nem expiração, mesmo atravessando os prazos pendentes.
7. **Given** a fase encerrada, **When** um Jogador pede construção ou coleta, **Then** recebe “A temporada não está aberta”, sem alteração de estado. Um novo pedido de abertura pelo Mestre recebe “A temporada já foi aberta”.
8. **Given** a temporada em andamento, **When** um participante entra, **Then** recebe o estado atual e acompanha os próximos fatos sem repetir débitos, créditos ou obras já registrados. No painel, cada evento recebido apresenta causa, dados e reação; recusas não aparecem nos outros clientes.

### User Story 2 - Construir e transformar trigo em farinha (Priority: P2)

Como Jogador, quero construir moinhos com o trigo comum, acompanhar sua conclusão e ver a farinha acumulada, para melhorar a produção e o resultado da temporada.

**Why this priority**: é o ciclo produtivo central da Fazenda e demonstra efeitos autônomos e disputa por capacidade limitada.

**Independent Test**: partir de uma temporada aberta, construir um moinho e observar sua conclusão, produção e moagem; usar estados controlados para limites e recusas.

**Acceptance Scenarios**:

1. **Given** a fase aguardando e A conectado, **When** A emite `construcao.solicitada`, **Then** só A recebe “A temporada não está aberta”; permanecem 150 de trigo e zero agricultores ocupados.
2. **Given** a temporada aberta, 3 agricultores ocupados e pelo menos 50 de trigo, **When** A pede construção, **Then** só A recebe “Sem agricultor livre”, sem débito.
3. **Given** a temporada aberta, 49 de trigo e 3 agricultores ocupados, **When** A pede construção, **Then** só A recebe “Trigo insuficiente”. Fora da fase aberta, a recusa é “A temporada não está aberta”, independentemente do estoque e da ocupação.
4. **Given** a temporada aberta, exatamente 50 de trigo e um agricultor livre, **When** A pede construção, **Then** todos recebem `construcao.iniciada`; o estoque passa a zero e uma obra ocupa um agricultor.
5. **Given** abertura com 150 de trigo e nenhum moinho, **When** A inicia uma obra no instante de referência t = 0 e ninguém age depois, **Then** todos veem trigo 100 e ocupação 1; aos 5 s, trigo 110 por `recurso.produzido`; aos 8 s, `construcao.concluida`, ocupação zero, um moinho e produção 20; aos 10 s, trigo 130 por produção, seguido de `farinha.moida`, trigo 125 e farinha 3. O prazo de obra é sempre contado desde seu início, mesmo se posterior à abertura.
6. **Given** temporada aberta, 2 de 3 agricultores ocupados e estoque inicial da disputa de pelo menos 100 de trigo, **When** A e B pedem construção simultaneamente e nenhum outro evento altera essas condições entre as decisões, **Then** apenas uma obra começa, um único débito de 50 ocorre e a ocupação chega a 3; o outro solicitante recebe “Sem agricultor livre”, pois ainda há pelo menos 50 de trigo. Todos recebem o fato aceito; só o perdedor recebe a recusa.
7. **Given** moinhos concluídos e produção de um intervalo, **When** ocorre a moagem posterior, **Then** cada moinho apto consome 5 de trigo e gera 3 de farinha; moinho sem trigo suficiente não mói. Sem moinho apto, não ocorre `farinha.moida`. A farinha nunca é gasta.
8. **Given** um moinho que acaba de ser concluído, **When** chega o intervalo de produção seguinte à conclusão, **Then** a produção inclui seus 10 de trigo adicionais e ele pode moer; não há moagem retroativa de um intervalo já ocorrido.

9. **Given** a temporada aberta, **When** o Mestre pede construção, **Then** só ele recebe “Só o Jogador pode construir”, inclusive quando faltam trigo ou agricultor. Fora da fase aberta recebe “A temporada não está aberta”. Não há débito nem obra.

### User Story 3 - Coletar uma colheita antes que estrague (Priority: P3)

Como Jogador, quero ver a colheita disponível e seu prazo, para coletá-la em benefício da fazenda antes da perda.

**Why this priority**: completa o evento próprio da Fazenda com expiração e disputa, sem alterar o ciclo básico de construções.

**Independent Test**: abrir uma temporada sem construir, aguardar amadurecimento e verificar separadamente coleta, disputa e perda por prazo.

**Acceptance Scenarios**:

1. **Given** uma temporada aberta sem colheita disponível, **When** passam 20 s desde a abertura, **Then** todos recebem `colheita.amadurecida`, valendo 30 de trigo por 10 s, sem crédito no celeiro nesse momento.
2. **Given** colheita disponível dentro do prazo, **When** A emite `colheita.coleta_solicitada`, **Then** todos recebem `colheita.coletada`, o estoque comum aumenta em 30 uma vez, a colheita desaparece e a ocupação de agricultores não muda. O prazo antigo não causa `colheita.estragada` depois.
3. **Given** colheita amadurecida aos 20 s, **When** ninguém coleta durante 10 s, **Then** ocorre `colheita.estragada` aos 30 s, sem crédito nem débito no celeiro por esse evento. Produção e moagem no mesmo instante têm seus efeitos contabilizados separadamente.
4. **Given** temporada aberta e colheita disponível, **When** A e B pedem coleta antes da expiração, sem encerramento entre as decisões, **Then** todos recebem um único `colheita.coletada`, o trigo aumenta em 30 uma vez e só o perdedor recebe “Não há colheita para coletar”.
5. **Given** temporada aberta sem colheita, **When** A pede coleta, **Then** só A recebe “Não há colheita para coletar”. Fora da fase aberta, a recusa é “A temporada não está aberta”.
6. **Given** uma colheita já disponível num estado controlado, **When** chega um novo ciclo de amadurecimento, **Then** não surge outra colheita nem ocorre novo `colheita.amadurecida`. Em execução regular, a expiração de 10 s precede o próximo ciclo de 20 s.
7. **Given** a primeira colheita coletada ou perdida, **When** chega o ciclo de 40 s desde a abertura, **Then** uma nova colheita amadurece se a temporada continua aberta; coletar não reinicia o calendário de amadurecimento.

8. **Given** a temporada aberta, **When** o Mestre pede coleta, **Then** só ele recebe “Só o Jogador pode coletar”, mesmo sem colheita disponível. Fora da fase aberta recebe “A temporada não está aberta”. Nenhum estoque muda.
9. **Given** uma colheita disponível com expiração T e a temporada aberta, **When** um pedido de Jogador chega antes de T, **Then** pode ser aceito se ainda disponível; **When** chega exatamente em T ou depois, **Then** recebe “Não há colheita para coletar” e não há crédito, mesmo com a execução do temporizador atrasada. O prazo produz uma única perda, independentemente do pedido.

### Edge Cases

- Estoque 49, exatamente 50 e pelo menos 100: US2.3, US2.4 e US2.6 distinguem insuficiência, limite de custo e disputa pelo último agricultor.
- O segundo pedido concorrente deve reavaliar o estado atualizado; o trigo nunca fica negativo, a ocupação nunca excede 3 e a colheita não rende duas vezes.
- Um pedido recusado não gera fato nem altera estado; fatos autônomos podem continuar durante a temporada aberta.
- Produção e expiração podem ocorrer aos 30 s. A perda não reduz nem congela o estoque: somente descarta a colheita ainda não creditada.
- Sem moinhos não há moagem. A regra de moagem insuficiente deve ser verificada em estado controlado, sem presumir que esse estado ocorre em todos os ciclos normais.
- Temporada encerrada conserva o retrato final e não permite efeitos atrasados; obra ou colheita pendente não implica reembolso.
- Coleta recebida exatamente na expiração ou depois é recusada, mesmo se o temporizador atrasar (US3.9). O Mestre não pode construir nem coletar, e a fase é validada antes do papel (US2.9 e US3.8).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A fazenda DEVE ser identificada como tema **19 — Fazenda**, com trigo, farinha, moinhos e agricultores.
- **FR-002**: O estado inicial DEVE conter fase aguardando, 150 de trigo, 0 de farinha, 3 agricultores de capacidade e zero agricultores ocupados, obras e colheitas disponíveis (US1.1).
- **FR-003**: Ao entrar, cada cliente DEVE receber `estado.sincronizado` com o estado corrente, sem mutação nem repetição de efeitos; alterações posteriores DEVEM chegar por eventos (US1.1 e US1.8).
- **FR-004**: O servidor DEVE controlar o estado, validar cada pedido e decidir concorrentemente sem duplicar débitos, obras ou créditos (US2.6 e US3.4).
- **FR-005**: Somente o Mestre DEVE abrir e encerrar a temporada. A abertura DEVE iniciar os ciclos, sem reiniciá-los em pedidos repetidos (US1.2, US1.4 e US1.5).
- **FR-006**: Toda construção aceita DEVE custar 50 de trigo no início, ocupar um agricultor por 8 s e adicionar uma obra em andamento (US2.4 e US2.5).
- **FR-007**: A construção DEVE validar fase aberta, papel Jogador, trigo suficiente e agricultor livre, nessa ordem, preservando os motivos da fonte. Recusas NÃO DEVEM alterar estado (US2.1–US2.3).
- **FR-008**: A conclusão de uma obra DEVE liberar um agricultor, retirar uma obra em andamento, adicionar um moinho concluído e aumentar a produção em 10 por intervalo (US2.5).
- **FR-009**: A produção DEVE ocorrer automaticamente a cada 5 s desde a abertura, creditando 10 de trigo mais 10 por moinho concluído (US1.3 e US2.5).
- **FR-010**: Após cada produção, cada moinho concluído apto DEVE transformar 5 de trigo em 3 de farinha, sem permitir estoque negativo; sem trigo suficiente para um moinho, ele não mói naquele intervalo. A farinha DEVE permanecer acumulada e não ser gasta (US2.7).
- **FR-011**: Um moinho DEVE começar a moer a partir do intervalo seguinte à sua conclusão, sem efeito retroativo (US2.8).
- **FR-012**: A cada 20 s desde a abertura, DEVE amadurecer uma colheita de 30 de trigo por 10 s, somente se não houver outra disponível (US3.1, US3.6 e US3.7).
- **FR-013**: Coletar DEVE creditar 30 no estoque compartilhado uma única vez, retirar a colheita, invalidar sua expiração e não ocupar agricultor (US3.2 e US3.4).
- **FR-014**: Expirar DEVE retirar a colheita não coletada sem alterar o trigo do celeiro por esse evento (US3.3).
- **FR-015**: A coleta DEVE validar fase aberta, papel Jogador e disponibilidade dentro do prazo, nessa ordem, com os motivos exatos da fonte; a disputa DEVE aceitar somente um pedido (US3.4 e US3.5).
- **FR-016**: O encerramento DEVE mudar a fase para encerrada, parar produção, moagem e colheitas e impedir conclusão de obras pendentes. Nenhum efeito atrasado DEVE alterar o estado após `vila.encerrada` (US1.6 e US1.7).
- **FR-017**: Fatos de domínio DEVEM ser enviados a todos; `operacao.recusada` DEVE ir apenas a quem pediu, contendo motivo e causa. Clientes DEVEM mostrar o estado recebido, sem confirmar resultados por conta própria (US1.8, US2.6 e US3.4).
- **FR-018**: O painel DEVE preservar nome, sentido, horário, causa, dados relevantes e reação dos eventos, distinguindo pedidos, fatos e recusas. Temporizadores DEVEM ser reconhecíveis como causas dos efeitos autônomos (US1.8 e US2.5).
- **FR-019**: A disponibilidade e os resultados de produção, obras e colheitas DEVEM depender dos temporizadores do servidor; relógios locais NÃO DEVEM decidir créditos ou conclusões (US2.5 e US3.3).
- **FR-020**: Construção e coleta DEVEM ser exclusivas do Jogador. Com a fase aberta, pedidos do Mestre DEVEM receber “Só o Jogador pode construir” ou “Só o Jogador pode coletar”, respectivamente; fora dela, “A temporada não está aberta” tem prioridade. Validar papel antes de estoque, agricultor ou disponibilidade (US2.9 e US3.8; decisão 1A).
- **FR-021**: Uma coleta só PODE ser aceita se o pedido chegar ao servidor estritamente antes do instante de expiração, além de passar nas demais validações. No instante exato ou depois, DEVE ser recusada com “Não há colheita para coletar”; atraso na execução da expiração NÃO prolonga a validade. O instante é determinado pelo servidor (US3.9; decisão 2A).

### Regras e valores preservados da fonte

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


### Eventos e causas

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


`estado.sincronizado` complementa os 14 eventos de domínio: é emitido pelo servidor somente para o participante que entra, causado pela entrada, e não muda o estado da vila. Foi solicitado explicitamente para a etapa de conexão.

Os dados devem permitir observar o estado resultante e o efeito do fato: fase e estoques; ocupação e obras; produção atual; identificação da obra ou colheita quando aplicável; valor e prazo da colheita; trigo consumido e farinha produzida na moagem; motivo e pedido causador na recusa. O formato técnico será detalhado no planejamento.

### Key Entities *(include if feature involves data)*

- **Temporada/Fazenda**: tema 19, fase aguardando/aberta/encerrada, instante de abertura, estoques compartilhados de trigo e farinha, produção por intervalo e capacidade de 3 agricultores.
- **Participante**: nome, papel Mestre ou Jogador e vínculo com o cliente que deve receber recusas e sincronização.
- **Obra/Moinho**: identidade, início, prazo de 8 s e situação em andamento/concluída; ocupa um agricultor enquanto em andamento e produz/moe depois de concluída.
- **Colheita**: identidade, valor 30, instante de amadurecimento e prazo de 10 s; disponível, coletada ou estragada durante a fase aberta; no máximo uma disponível.
- **Evento**: nome, emissor, destinatários, causa, dados e reação observável; pedido não confirma mudança e recusa não altera o estado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mestre e dois jogadores exibem os mesmos estoques, ocupação, obras e fase após cada fato recebido em todos os cenários; não há recarga manual para revelar mudanças.
- **SC-002**: No roteiro de uma obra iniciada na abertura, todos observam trigo 100, 110, 130 e 125 na sequência prescrita, farinha 3 aos 10 s e agricultor liberado aos 8 s, sem novos cliques após o pedido.
- **SC-003**: Na disputa com pelo menos 100 de trigo e um agricultor livre, há exatamente uma obra aceita, um débito de 50 e uma recusa privada por falta de agricultor; a ocupação nunca excede 3.
- **SC-004**: Em cada disputa por colheita há um crédito de 30 e uma recusa privada. Sem coleta, a colheita desaparece 10 s após amadurecer, sem crédito ou débito causado pela perda.
- **SC-005**: Após encerrar com obra e colheita pendentes, atravessar seus prazos e ao menos um ciclo de 20 s não produz qualquer mudança de estado ou novo fato de atividade.
- **SC-006**: O painel permite ao avaliador identificar, para cada fato ou recusa dos roteiros, causa, dados e reação; em todas as recusas só o solicitante recebe o motivo.
- **SC-007**: Todos os cenários de aceitação definidos têm resultado registrado antes da entrega; os cenários US2.9, US3.8 e US3.9 verificam as decisões confirmadas sobre papéis e limite estrito de coleta.

## Assumptions

- `docs/especificacao.md` é a fonte de domínio e deve permanecer consistente com esta especificação. Os valores e motivos originais foram preservados; as três correções solicitadas e as duas novas recusas por papel, aprovadas na decisão 1A, estão aplicadas em ambos.
- A constituição determina o reaproveitamento do kit, a autoridade do servidor, a preservação do painel e as etapas pequenas com verificação e commit próprios. O planejamento detalhará essas etapas.
- O cenário acadêmico usa uma vila compartilhada, um Mestre e dois jogadores; múltiplas vilas, novas temporadas na mesma execução, recuperação após reinício e troca de papéis ficam fora desta entrega.
- “Quem pedir primeiro leva” significa pedido decidido primeiro pelo servidor e crédito no estoque comum, sem inventário pessoal.
- Ao encerrar, conserva-se o retrato final de estoques e atividades pendentes, sem reembolso ou efeitos posteriores; os controles indicam temporada encerrada.
- A moagem será observável como resumo do intervalo com os totais de moinhos aptos, trigo consumido e farinha produzida; não se pressupõe um evento separado por moinho.
- Eventos independentes com o mesmo horário não exigem ordem global. A moagem segue sua produção; o moinho participa do intervalo posterior à conclusão. No limite exato da coleta, o prazo estrito confirmado em 2A prevalece.
- Os tempos são do domínio no servidor; a entrega às telas pode ocorrer depois. Para o exemplo de 8 s e 10 s, o início da obra coincide com o instante de referência da abertura.
- Q1 e Q2 estão resolvidas por “1A 2A”, confirmado pelo usuário em 2026-11-02 e registrado na seção 5 da fonte: ações exclusivas do Jogador e prazo estrito de coleta no servidor.
