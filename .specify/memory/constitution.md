<!--
Sync Impact Report
- Versão: modelo sem versão ratificada → 1.0.0 (adoção inicial).
- Princípios preenchidos a partir dos cinco espaços do modelo:
  1. I. Reaproveitamento do kit e fidelidade à especificação.
  2. II. Estado e validação sob autoridade do servidor.
  3. III. Clientes reativos e eventos observáveis.
  4. IV. Passagem do tempo controlada pelo servidor.
  5. V. Etapas pequenas, verificáveis e registradas em commits.
- Seções preenchidas: Restrições do projeto acadêmico; Fluxo de desenvolvimento;
  Governance.
- Seções removidas: nenhuma.
- Pendências e placeholders adiados: nenhum.
- Templates e comandos dependentes: preservados; consultam a constituição em execução.
- Nota de revisão: remover este relatório temporário antes de efetuar o commit.
-->
# Vila em Tempo Real — Fazenda Constitution

## Core Principles

### I. Reaproveitamento do kit e fidelidade à especificação

O desenvolvimento DEVE partir do kit existente: servidor Python com Socket.IO/ASGI,
execução com Uvicorn, cliente Vue, visualização Phaser e recursos gráficos fornecidos.
As funções de envio, escuta e registro de eventos DEVEM ser aproveitadas e estendidas.
Substituições de tecnologia, dependências novas e abstrações adicionais DEVEM ter uma
necessidade concreta documentada, vinculada a um requisito ou cenário verificável.

`docs/especificacao.md` DEVE orientar as regras da fazenda, os papéis, os nomes dos eventos,
os destinatários e os cenários de aceitação. Mudanças de comportamento DEVEM ser descritas
na especificação antes de sua implementação. A solução DEVE manter explícitos os emissores,
os tratadores e as reações, permitindo explicar o paradigma orientado a eventos no código.

### II. Estado e validação sob autoridade do servidor

O servidor DEVE ser a única autoridade sobre fase da temporada, estoques, agricultores,
obras, produção e colheitas. Todo pedido DEVE ser validado no servidor quanto ao papel
aplicável, à fase e às condições da operação, respeitando a ordem de recusas da especificação.
Desabilitar um botão no cliente NÃO substitui essa validação.

A validação e a alteração correspondente DEVEM formar uma operação indivisível perante
pedidos concorrentes e temporizadores. O estoque NÃO PODE ficar negativo, os agricultores
ocupados DEVEM permanecer entre zero e três e uma mesma colheita NÃO PODE ser creditada
mais de uma vez. Pedidos de construção e coleta em disputa DEVEM ser decididos um por vez.

Fatos aceitos DEVEM ser enviados a todos os clientes participantes. Uma recusa DEVE preservar
o estado e emitir `operacao.recusada`, com o motivo previsto, apenas para quem pediu.
Essas regras garantem que vários clientes compartilhem uma única fazenda consistente.

### III. Clientes reativos e eventos observáveis

Os clientes DEVEM emitir intenções e atualizar o estado exibido a partir dos dados recebidos
do servidor. Um pedido local NÃO PODE confirmar por conta própria um débito, uma construção,
uma coleta ou uma mudança de fase. Ao entrar na vila, o cliente DEVE receber o estado atual
do servidor para começar a acompanhar os mesmos fatos dos demais participantes.

Cada evento de domínio DEVE ter nome, emissor, destinatários, dados e reação definidos.
Pedidos DEVEM ser distinguíveis dos fatos que confirmam mudanças e das recusas.
As atualizações durante a temporada DEVEM chegar por eventos, sem depender de recarga de
página, consulta periódica do cliente ou novos cliques para revelar mudanças.

O painel de eventos do kit DEVE ser preservado. Cada pedido enviado e cada fato ou recusa
recebido DEVE ser registrado com nome, sentido, horário e dados relevantes. Eventos recebidos
DEVEM tornar visíveis a causa e a reação do cliente; pedidos DEVEM identificar a ação que
os originou. Causas DEVEM apontar o pedido, o evento anterior ou o temporizador responsável,
conforme o encadeamento da especificação. Recusas DEVEM mostrar o motivo e a ausência de
mudança no estado. O painel constitui evidência didática do fluxo causa → dados → reação.

### IV. Passagem do tempo controlada pelo servidor

Produção, conclusão de obras, amadurecimento e expiração de colheitas DEVEM ser disparados
por temporizadores do servidor, independentemente de ações ou relógios dos clientes.
Contagens e animações locais PODEM representar os prazos, mas NÃO PODEM decidir resultados.

Os temporizadores DEVEM respeitar os intervalos da especificação: produção a cada cinco
segundos, obra de oito segundos, amadurecimento a cada vinte segundos desde a abertura e
prazo de coleta de dez segundos. A moagem DEVE ocorrer após a produção e ser causada por
ela; um moinho concluído DEVE começar a moer no intervalo seguinte à conclusão.

Só PODE existir uma colheita disponível por vez. A coleta DEVE invalidar sua expiração
pendente, impedindo um evento posterior de perda da mesma colheita. Encerrar a temporada
DEVE interromper a produção, a moagem e as colheitas, impedir a conclusão das obras em
andamento e recusar novas ações. Temporizadores pendentes DEVEM ser cancelados ou
invalidados, e nenhum deles PODE alterar o estado após o encerramento.

### V. Etapas pequenas, verificáveis e registradas em commits

O desenvolvimento DEVE ser dividido em etapas com um objetivo delimitado e critérios de
aceitação observáveis. Cada etapa funcional DEVE deixar o projeto executável e permitir
verificar seu comportamento com vários clientes conectados. Uma etapa NÃO PODE acumular
funcionalidades independentes que possam ser verificadas e entregues separadamente.

Antes de concluir cada etapa funcional, a verificação DEVE usar um Mestre e dois jogadores
em clientes distintos, comparar os estados exibidos e inspecionar os eventos recebidos.
O registro da verificação DEVE indicar condições iniciais, ações, eventos esperados,
destinatários e resultado observado. Etapas apenas documentais DEVEM verificar coerência
com a especificação e com os artefatos afetados.

Cada etapa concluída e verificada DEVE corresponder a um commit próprio, com mensagem que
identifique o resultado. Falhas DEVEM ser resolvidas antes de declarar a etapa concluída.
Essa disciplina permite demonstrar, revisar e reproduzir a evolução do trabalho acadêmico.

## Restrições do projeto acadêmico

- O escopo DEVE permanecer na fazenda descrita em `docs/especificacao.md`: trigo, farinha,
  moinhos, agricultores, temporada e colheita perecível. Extras DEVEM ser especificados e
  verificados em etapas próprias, preservando os cenários obrigatórios.
- Os valores iniciais, custos, rendimentos, limites e motivos de recusa DEVEM seguir a
  especificação. A constituição define as garantias; a especificação detalha o domínio.
- O trabalho DEVE permitir demonstrar quem emite, quem escuta e qual reação cada evento
  provoca, incluindo eventos autônomos e recusas dirigidas a um único cliente.
- O README DEVE registrar instalação, execução, roteiro com vários clientes, respostas
  sobre o paradigma, integrantes e uso de IA, conforme a estrutura fornecida pelo kit.

## Fluxo de desenvolvimento

1. Antes de implementar uma etapa, identificar o requisito na especificação e descrever
   seus critérios de aceitação em termos de pedidos, fatos, recusas e mudanças de estado.
   Especificar os dados dos eventos e sua causa quando a etapa introduzir ou alterar eventos.
2. Implementar a menor mudança que satisfaça esses critérios, mantendo visíveis a validação
   do servidor e as reações do cliente e aproveitando os pontos de extensão do kit.
3. Verificar a etapa com Mestre, Jogador A e Jogador B e registrar o resultado. Aplicar os
   cenários pertinentes de recusa, passagem do tempo, disputa por agricultor, colheita
   estragada e disputa pela colheita. As condições iniciais DEVEM satisfazer as validações
   anteriores à condição que se pretende testar, inclusive a disponibilidade de trigo.
4. Em mudanças de temporizadores ou de ciclo da temporada, verificar também o encerramento
   com operações pendentes e a ausência de alterações posteriores. Em disputas, confirmar
   que há uma única alteração aceita e que só o solicitante recusado recebe a recusa.
5. Comparar o estado nos clientes e o painel de eventos, executar as verificações
   automatizadas existentes pertinentes à mudança e corrigir divergências. A verificação
   manual reproduzível com vários clientes DEVE integrar a aceitação, mesmo havendo testes
   automatizados.
6. Atualizar a documentação afetada e registrar um commit exclusivo da etapa verificada
   antes de iniciar a próxima. A entrega final DEVE executar todos os cenários da
   especificação e demonstrar o encerramento sem novos efeitos dos temporizadores.

## Governance

Esta constituição rege as decisões de arquitetura e desenvolvimento do projeto.
Especificações, planos, tarefas e revisões DEVEM verificar conformidade com seus princípios.
Antes de concluir uma etapa, o responsável DEVE conferir o reaproveitamento do kit,
a autoridade do servidor, a consistência entre clientes, os temporizadores, o painel e as
evidências de verificação pertinentes à mudança.

Uma alteração desta constituição DEVE registrar a motivação, as regras afetadas, o impacto
nos artefatos existentes e a adaptação necessária. O responsável pelo projeto DEVE revisar
e aceitar a alteração antes de usá-la para justificar uma implementação divergente.
Conflitos entre especificação e constituição DEVEM ser resolvidos explicitamente nos
documentos antes da implementação; desvios silenciosos NÃO são permitidos.

O versionamento DEVE seguir MAJOR.MINOR.PATCH: MAJOR para remoções ou redefinições
incompatíveis de princípios, MINOR para novos princípios ou ampliação material das regras
e PATCH para esclarecimentos sem mudança de obrigação. A data de ratificação DEVE ser
preservada e a data de última alteração DEVE acompanhar cada emenda. A versão 1.0.0
representa a adoção inicial dos princípios deste projeto.

**Version**: 1.0.0 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
