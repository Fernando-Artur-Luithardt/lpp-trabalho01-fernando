# Vila em Tempo Real — Fazenda (tema 19)

Etapas 1–7 implementadas: conexão, abertura, construções, produção a cada cinco
segundos, conclusão após oito segundos, moagem e colheitas de 30 trigo a cada
20 segundos, disponíveis por 10 segundos. Somente Jogadores constroem e coletam.
O servidor mantém a fazenda em memória, decide todas as alterações e interrompe
os efeitos pendentes ao encerrar, preservando o retrato final.

## Integrantes

- Fernando Artur Luithardt — [@Fernando-Artur-Luithardt](https://github.com/Fernando-Artur-Luithardt)

## Como instalar e executar

Requer Python 3.11+ e navegador com acesso às CDNs do kit. Na raiz do projeto:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Acesse <http://127.0.0.1:8000>. Use um único processo Uvicorn, sem workers
adicionais. Parar com Ctrl+C e reiniciar o servidor reinicia a fazenda;
desconectar ou recarregar uma aba preserva o estado do servidor.

Ambiente verificado em 2026-11-03: Python **3.14.7**, python-socketio **5.18.0**,
python-engineio **4.15.1**, Uvicorn **0.54.0** e Chrome **156.0.8078.80**.
Dependências já instaladas na `.venv`, conferidas com `python -m pip check`.
Cliente original mantido: Vue **3.5.13**, Socket.IO **4.7.5** e Phaser **3.90.0**.
Nenhuma dependência foi adicionada e os assets do kit foram preservados.

## Como testar conexão com duas abas

1. Abra o endereço em duas abas. Na primeira, informe **Mestre** e clique em
   **Entrar como Mestre**. Na segunda, informe **Jogador A** e entre como Jogador.
2. Confira em ambas: fase **aguardando**, **150 trigo**, **0 farinha**,
   **0/3 agricultores**, **0 moinhos**, **0 obras** e nenhuma colheita.
   A produção bruta indicada é a taxa configurada; a produção começa após a abertura.
3. No painel de cada aba deve existir exatamente um `estado.sincronizado`, com
   sentido recebido (`on`), horário, causa **conexao**, dados e reação de atualização.
   A entrada de A não acrescenta outro evento no painel do Mestre.
4. Recarregue a aba de A e entre novamente. Ela recebe o estado atual; o Mestre
   mantém os mesmos valores e o mesmo único evento. O mapa aparece uma única vez.
5. Para repetir a aceitação completa V1, abra uma terceira aba, **Jogador B**,
   entre como Jogador e repita a recarga. M e A não recebem o snapshot de B.
6. Para conferir reconexão sem recarregar, use o modo **Offline** da aba Network
   das ferramentas do navegador na aba B até aparecer a indicação de conexão
   interrompida. Volte para **No throttling/Online** e aguarde a reconexão automática.
   B recebe mais um snapshot, mantém os valores e o mesmo canvas; M e A permanecem
   com seus painéis inalterados. Não reinicie o servidor durante esse ensaio.

Nome vazio vira **Anônimo**. O servidor só aceita os papéis `mestre` e `jogador`;
papel desconhecido rejeita a conexão, sem enviar snapshot. As escutas são
registradas uma vez, antes de conectar. A desconexão remove somente a sessão.

## Evidência da Etapa 1 — V1

Verificação executada em **2026-11-03**, com um processo Uvicorn e três páginas
reais do Chrome headless, controladas pelo protocolo de depuração do navegador.
As páginas carregaram o HTML, Vue, Socket.IO, Phaser e os assets do próprio kit.
O roteiro acima permite repetir a conferência manualmente.

| Condição / ação | Resultado observado |
| --- | --- |
| M, A e B entram sequencialmente | Mesmo snapshot de domínio nas três páginas: aguardando, trigo 150, farinha 0, ocupação 0/3, obras vazias e colheita null. |
| Entrada de A/B | Um `estado.sincronizado` por página, causa `conexao`, dados e reação; nenhum snapshot adicional nos participantes anteriores. |
| Recarregar B e entrar novamente | Estado preservado; painéis de M/A idênticos aos anteriores. Um canvas e nenhuma obra desenhada em B. |
| Interromper o transporte de B e aguardar reconexão automática | Um novo snapshot somente em B, uma única escuta, mesma instância de jogo e mesmo elemento canvas. |
| Conferir cena antes/depois da reconexão | Três objetos na cena (duas camadas do mapa e faixa), zero registros de obras; nenhuma duplicação. |
| Conectar com papel inválido | `connect_error` com “Papel inválido”; nenhum `estado.sincronizado`. |
| Conectar com nome vazio | Conexão aceita; mesmo estado. Fallback “Anônimo” conferido também no teste do tratador. |
| Erros JavaScript | Nenhuma exceção nas três páginas. |

Também passaram **seis testes temporários com `unittest`**, sem novas dependências:
três participantes/destinatários; papel inválido/nome vazio; desconexão/reentrada
com estado atual; cópia independente e contadores derivados; aquisição do lock e
emissão dentro dele; referência civil fixa com relógio controlado. Estados
artificiais existiram apenas nesses testes, em processo separado da aplicação.

Comandos executados nesta sessão:

```sh
.venv/bin/python -m pip check
.venv/bin/python -m py_compile server.py
.venv/bin/python /tmp/fazenda-etapa1-checks.py -v
node /tmp/fazenda-etapa1-browser.mjs
git diff --check
```

Os scripts em `/tmp` foram instrumentos temporários desta verificação e não
integram o repositório. O roteiro com abas acima é reproduzível em uma instalação
nova. A suíte permanente `tests/test_server.py` foi acrescentada em T010,
na Etapa 2, descrita abaixo. Entrada durante obra e barras foram verificadas na
Etapa 3; os demais eventos de atividade serão verificados nas respectivas etapas.

## Como testar a abertura — Etapa 2

1. Inicie um servidor novo e entre como **Mestre** e **Jogador A** em duas abas.
   Para o roteiro completo V2, abra também **Jogador B** em uma terceira aba.
   Todas devem começar em aguardando, com trigo 150 e farinha 0.
2. No Mestre, clique em **Abrir temporada**. O painel registra o pedido
   `vila.abertura_solicitada`, causado pela ação local. As três abas recebem
   `vila.iniciada` com causa `vila.abertura_solicitada`; a fase e a faixa do mapa
   passam a **aberta**, sem crédito de trigo, farinha ou ocupação de agricultores.
3. Anote `aberta_em_ms` no painel e clique em **Abrir temporada** novamente.
   Somente o Mestre recebe `operacao.recusada`, motivo **A temporada já foi aberta**.
   Os painéis de A/B não ganham eventos; o estado e `aberta_em_ms` não mudam.
   O horário de envio `servidor_em_ms` pode mudar, pois identifica outra mensagem.
4. Recarregue B e entre novamente. B recebe um snapshot privado da temporada
   aberta, com o instante original, sem repetir `vila.iniciada` nem duplicar o mapa.
5. Execute a suíte abaixo para verificar pedidos de Jogador diretamente no
   tratador, inclusive com `papel: mestre` no payload. O motivo deve ser
   **Só o Mestre pode abrir a temporada**, antes da validação da fase.

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

O botão Abrir continua disponível ao Mestre conectado para demonstrar a recusa
da segunda abertura. O servidor decide a aceitação; o clique não muda a fase
localmente. Não há produção automática nesta etapa, mesmo após abrir.

## Evidência da Etapa 2 — V2

Verificação em **2026-11-03**, sobre a Etapa 1 (`fba2ec0`), para o commit
`feat: controla abertura da temporada`. Mesmo ambiente descrito acima, um
processo Uvicorn e três páginas reais do Chrome headless (M/A/B), controladas
por automação. HTML, Socket.IO, Vue, Phaser e assets foram carregados normalmente.

| Condição / ação | Resultado observado |
| --- | --- |
| M/A/B conectados, temporada aguardando | Mesmo estado inicial, trigo 150, farinha 0, ocupação 0/3 e abertura null. |
| A pede abertura pelo método do cliente, sem depender de botão | Recusa apenas em A, “Só o Mestre pode abrir a temporada”; M/B sem novos eventos e estado preservado. |
| Mestre clica Abrir | Pedido registrado com sentido enviado e causa local; no mesmo turno do clique a fase ainda era aguardando. Após a resposta, um `vila.iniciada` em cada aba, faixa “Temporada aberta” e estoques preservados. |
| Mestre clica Abrir novamente | Recusa privada, “A temporada já foi aberta”; nenhum segundo `vila.iniciada`; painéis de A/B inalterados. |
| Conferência do instante público | `aberta_em_ms` igual a `1793740870536` nas três abas, preservado após a segunda abertura e reconexão. |
| B pede abertura na fase aberta com payload `papel: mestre` | Recusa por papel somente em B; estado e instante preservados. Confirma prioridade papel → fase. |
| Reconectar B sem recarregar | Mesmo estado/instante, mesmo canvas, uma instância Phaser e uma escuta de cada evento. Um novo snapshot e nenhum replay de `vila.iniciada`. |
| B pede novamente após reconectar e depois recarrega | Uma única recusa adicional; após recarga, somente snapshot privado com a fase aberta e instante original. |
| Painel e interface | Pedido/fato/recusa classificados; causa, dados, horário, reação e aviso de ausência de alteração visíveis. Nenhuma exceção JavaScript nas três páginas. |

**Testes permanentes: 11 aprovados.** Escritos antes do tratador de abertura,
primeiro falharam pela ausência desse evento; passaram após a implementação.
Usam `IsolatedAsyncioTestCase`, transporte assíncrono controlado, relógio
substituível e estado isolado por caso, sem esperas reais longas. Cobrem conexão,
sessão/papel inválido, snapshot privado/copiado, abertura global sem crédito,
autoridade da sessão, prioridade papel → fase, repetição sem mudar os instantes,
fase encerrada preparada somente no teste, duas aberturas concorrentes,
aquisição do lock e reentrada após abertura. Não implementam encerramento.

Comandos de verificação:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node /tmp/fazenda-etapa2-browser.mjs
git diff --check
```

O script de navegador é temporário, externo ao repositório. A suíte Python e o
roteiro manual acima são reproduzíveis em uma instalação nova. **Verificação
manual pendente:** repetição de V2 por uma pessoa em três abas de navegador
visível. A verificação M/A/B registrada aqui foi automatizada, com inspeção da
captura da tela do Mestre; não é uma declaração de execução manual humana.
Produção e demais funcionalidades de etapas posteriores não foram antecipadas.

## Como testar construções e recusas — Etapa 3

1. Inicie um servidor novo e entre em três abas: **Mestre**, **Jogador A** e
   **Jogador B**. Com a fase aguardando, A clica **Construir**. Somente A deve
   receber `operacao.recusada`, motivo **A temporada não está aberta**.
   Todas as abas continuam com 150 de trigo, zero obras e zero agricultores ocupados.
2. M abre a temporada; A clica **Construir**. O painel de A registra o pedido
   `construcao.solicitada`. As três abas recebem `construcao.iniciada`, causa
   `construcao.solicitada`, `custo: 50` e o mesmo `obra_id`. O estado passa a
   **100 trigo, 1/3 agricultores, 1 obra e 0 moinhos concluídos**.
3. Após cerca de dois segundos, B constrói outra obra. Confira duas identidades,
   50 de trigo, ocupação 2/3 e barras com progressos diferentes. A primeira barra
   não deve reiniciar quando a segunda obra aparece.
4. Recarregue B e entre novamente. O snapshot privado contém as mesmas obras e
   os mesmos `iniciada_em_ms`/`concluir_em_ms`. As barras mostram o tempo decorrido,
   sem repetir o texto de débito; M/A não recebem eventos pela entrada de B.
   Repita com interrupção da conexão conforme o roteiro de conexão acima.
5. A constrói a terceira obra: trigo 0, ocupação 3/3 e três identidades distintas.
   Uma quarta tentativa recebe **Trigo insuficiente** somente no solicitante:
   a validação do estoque vem antes da disponibilidade de agricultor.
6. Aguarde mais de oito segundos desde a última construção. As barras podem
   completar, mas continuam três obras em andamento, três agricultores ocupados,
   zero moinhos concluídos e os mesmos estoques. A conclusão automática e a
   produção só serão implementadas na **Etapa 4**.
7. Execute a suíte para conferir os estados que exigem preparação controlada:
   49 trigo, exatamente 50 com vaga, três ocupados com pelo menos 50, três ocupados
   com 49 e pedidos diretos de Mestre. Não há controles de administração para
   alterar estoque/obras na aplicação. Reinicie o servidor para um novo ensaio.

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

O botão Construir existe somente para Jogador e permanece disponível enquanto
conectado, permitindo demonstrar as recusas do servidor. A ordem é **fase → papel
→ trigo → agricultor**. O prazo público orienta apenas a barra; o cliente não
decide conclusão, débito ou liberação de agricultor. Ao voltar a uma aba oculta,
o desenho retoma usando o prazo original.

## Evidência da Etapa 3 — V3

Verificação em **2026-11-03**, sobre a Etapa 2 (`46e2f7b`), para o commit
`feat: valida construções e recusas por jogador`. Mesmo ambiente das etapas
anteriores, um processo Uvicorn e três páginas reais do Chrome headless com M/A/B.

| Condição / ação | Resultado observado |
| --- | --- |
| A constrói antes da abertura | Recusa privada por fase; estado preservado e painéis de M/B inalterados. |
| M pede construção diretamente, antes/depois da abertura | “A temporada não está aberta” antes; “Só o Jogador pode construir” depois, inclusive com `papel: jogador` no payload. |
| A clica Construir após abertura | No mesmo turno do clique, ainda 150 trigo e nenhum desenho; após o fato global, 100 trigo, ocupação 1/3 e obra 1 nas três páginas. |
| B constrói com custo/prazo/identidade falsos no payload | Servidor aplica custo 50, prazo 8 s e identidade 2; três páginas passam a 50 trigo e ocupação 2/3. |
| Entrada tardia de B com duas obras | Mesmos registros e prazos; barras em aproximadamente 32% e 4%, nenhum texto de custo repetido, dois canteiros e duas barras. M/A sem novos eventos. |
| Reconexão de B | Mesmo canvas e primeiro sprite, mesmas duas identidades, uma escuta de construção e nenhum desenho duplicado. |
| Terceira obra e quarta tentativa | Obra 3 aceita globalmente, trigo 0 e ocupação 3/3; tentativa seguinte recusada somente em B por trigo insuficiente. |
| Mais de oito segundos após a última obra | Nas três páginas: trigo 0, farinha 0, ocupação 3/3, três canteiros, zero concluídas e nenhum evento de conclusão/produção. Barras cheias somente indicativas. |
| Painel e cena | Pedido/fato/recusa classificados corretamente, causa/dados/reação visíveis; 12 objetos persistentes por cena (mapa/faixa e três conjuntos canteiro/fundo/barra). Nenhuma exceção JavaScript. |

**Testes permanentes: 17 aprovados**, incluindo os 11 anteriores e seis novos
testes, um deles com dez combinações de recusa. Os testes novos foram executados
antes do tratador e falharam pela ausência de `construcao.solicitada`; depois
passaram. A matriz de validação confirmou:

| Estado controlado | Resultado |
| --- | --- |
| Fase aguardando/encerrada, Jogador ou Mestre | Recusa por fase antes de papel/estoque/ocupação. |
| Mestre na fase aberta, inclusive com 49 trigo e três ocupados | “Só o Jogador pode construir”. |
| Jogador com 49 trigo, com vaga ou três ocupados | “Trigo insuficiente”. |
| Jogador com exatamente 50 trigo e vaga | Uma obra, um débito de 50 e um agricultor ocupado. |
| Jogador com três ocupados e 50 ou 100 trigo | “Sem agricultor livre”, sem mutação ou consumo de identidade. |
| Vinte moinhos concluídos preparados no teste | Não ocupam agricultores nem impedem uma nova obra; não há limite pelo total de moinhos. |

Também foram conferidos snapshots copiados, identidades crescentes, prazos
monotônicos e públicos, privacidade, entrada tardia após o prazo e reavaliação
do estoque após esperar pelo lock. Todos os estados artificiais ficaram nos
testes, em processo separado da aplicação.

O ensaio visual detectou e corrigiu a classificação de `construcao.solicitada`:
o classificador do kit reconhecia somente o sufixo com sublinhado. Agora aceita
ponto e sublinhado. Os dados de obras também quebram linhas no painel; uma
conferência adicional com três obras confirmou ausência de transbordamento
horizontal. As abas foram trazidas à frente para verificar barras e aguardar o
fim dos textos temporários, pois o Chrome suspende animações em abas ocultas.

Comandos executados:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node /tmp/fazenda-etapa3-browser.mjs
node /tmp/fazenda-etapa3-layout.mjs
git diff --check
```

Os scripts de navegador são temporários, externos ao repositório. A suíte Python
e o roteiro acima permitem repetir a verificação. **Verificação manual pendente:**
repetição humana de V3 em três abas visíveis. O ensaio M/A/B foi automatizado e a
captura de B foi inspecionada; não foi uma execução manual humana. A repetição
humana de V2 anteriormente registrada também continua pendente.

## Etapa 4 — Produção e conclusão por temporizadores

Verificação de 2026-11-03 sobre `ea6c846`. **19 testes aprovados** com
`python -m unittest discover -s tests -p 'test_*.py' -v`. Os testes de regras
anteriores isolam o agendamento; os testes temporizados substituem relógio e
espera. Foram conferidos calendário ancorado em abertura + 5/10/15 s,
nenhum crédito imediato ou em aguardando, um único agendamento após abertura
repetida, esperas fora do lock, snapshots copiados e conclusão única por identidade.
A sequência controlada foi trigo 100 → 110 em 5 s → liberação do agricultor em
8 s → 130 em 10 s, produção 20 e farinha zero.

V4 também foi executado com um processo Uvicorn e três páginas reais do Chrome
headless: M abriu, A construiu e B entrou cerca de dois segundos depois. B recebeu
uma obra com barra em aproximadamente 27%, preservando início e prazo. Nas três
páginas ocorreram dois `recurso.produzido` e um `construcao.concluida`; o resultado
foi trigo 130, farinha 0, ocupação 0/3, produção 20 e um único moinho, sem barras
restantes ou exceções JavaScript. A obra iniciou em `1793742217768`, tinha prazo
`1793742225768` e concluiu em `1793742225769` ms: 8,001 s desde seu próprio início.
A precisão exata dos intervalos é conferida pelo relógio controlado, não pelos cliques.
Instrumento temporário: `node /tmp/fazenda-etapa4-browser.mjs`.

Para reproduzir V4:

1. Reinicie o servidor; entre como Mestre e Jogador A em duas abas. Abra a temporada
   e construa imediatamente com A, antes dos primeiros dois segundos.
2. Observe 100 de trigo após construir e 110 no primeiro ciclo, cinco segundos
   após a abertura. Entre como Jogador B numa terceira aba durante a obra.
3. B deve receber a mesma identidade e prazo, com progresso já iniciado. Oito
   segundos após o início da obra, as três abas mostram um moinho e agricultor livre.
4. No ciclo de dez segundos desde a abertura, confira trigo 130 e farinha zero.
   No painel, produção tem causa `temporizador`, e conclusão tem causa
   `construcao.iniciada`, `obra_id` e `gatilho: temporizador`.
5. Recarregar uma aba deve sincronizar o moinho existente sem repetir custo.

**Pendente:** repetição manual humana de V4. O roteiro acima foi automatizado;
a conferência com cliques humanos não foi executada. Os registros das Etapas
1–3 descrevem versões históricas; a ausência de conclusão/produção da Etapa 3
foi substituída pelo comportamento desta etapa. Moagem continua fora do escopo.
Codex auxiliou na implementação dos temporizadores, testes e verificação M/A/B.

## Etapa 5 — Encerramento e disputas

Verificação em **2026-11-03**, após `ea6c846`. A suíte permanente passou com
**23 testes**, incluindo encerramento por papel/fase, prioridade Mestre → fase,
recusas privadas, snapshot final, cancelamento de produção e conclusão pendentes,
repetição do encerramento e disputa concorrente pela última vaga. Os testes
controlados confirmam que os temporizadores são cancelados e aguardados sem
manter o lock, e que executar produção/conclusão depois do encerramento não altera
estado nem emite fatos.

V5 foi repetido com um processo Uvicorn e três páginas reais do Chrome headless
(Mestre, A e B). O servidor produziu naturalmente 200 de trigo em 25 s, sem
moinhos. A iniciou duas obras consecutivas: estoque 100, ocupação 2/3. Antes de
qualquer obra ou novo ciclo interferir, A e B pediram a última construção em
concorrência. Uma obra foi aceita, o débito único levou o estoque a 50 e a
ocupação a 3/3. A outra solicitação recebeu somente em B a recusa
“Sem agricultor livre”; M e A não receberam a recusa. A disputa não interferiu
no ciclo nem nas obras antes da ação de encerrar.

M encerrou com as três obras ainda pendentes. As três páginas receberam
`vila.encerrada`, com fase encerrada, 50 de trigo, farinha 0, três agricultores
ocupados e as mesmas três identidades em andamento. Após 21 s, estoques,
contadores e prazos públicos continuavam iguais e não houve produção nem
conclusão. A tentativa de construir depois do fim foi recusada privadamente.
B recarregou já com a temporada encerrada e recebeu o snapshot final, três
registros visuais e a faixa de encerramento; a cena manteve um canvas e nenhuma
exceção JavaScript. O tratamento de `estado.sincronizado` reaplica também a
apresentação de fim, sem duplicar a sombra, em recarga ou reconexão.

Comandos executados:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node /tmp/fazenda-etapa5-browser.mjs
.venv/bin/python -m py_compile server.py tests/test_server.py
git diff --check
```

O instrumento de navegador é temporário e externo ao repositório. **Verificação
manual pendente:** repetir V5 com interação humana em três abas visíveis. A
verificação registrada foi automatizada com M/A/B; não foi uma sessão manual
humana. A retomada por pessoa dos roteiros V2, V3 e V4 continua pendente conforme
as evidências anteriores.

## Etapa 6 — Moagem de farinha

Verificação em **2026-11-03**, sobre o commit `82df3f1`. A suíte permanente
passou com **28 testes**. Os testes com relógio controlado cobrem: um moinho
transforma 5 trigo em 3 farinha por ciclo; dois moinhos aptos transformam 10 em
6; o trigo remanescente e a farinha anterior são preservados; moinhos sem trigo
suficiente são ignorados; não há evento de moagem sem moinho apto; conclusão
exatamente no limite não moe naquele ciclo e habilita o próximo; e temporada
encerrada não produz nem mói. Os snapshots de `recurso.produzido` e
`farinha.moida` são distintos e permanecem inalterados após ciclos seguintes.

V6 foi executado com Mestre, Jogador A e Jogador B em três páginas reais do
Chrome headless. M abriu a temporada e A iniciou uma obra. B entrou durante a
obra e recebeu a mesma identidade e prazo, com um único registro visual. Aos
5 s ocorreu produção sem moagem; a obra concluiu cerca de 8 s após o início.
No ciclo de 10 s, todas as páginas receberam primeiro `recurso.produzido` com
130 de trigo e farinha 0, depois `farinha.moida` com causa
`recurso.produzido`, `moinhos: 1`, `trigo_consumido: 5` e
`farinha_produzida: 3`. O estado final sincronizado foi 125 trigo, 3 farinha,
um moinho concluído e nenhum agricultor ocupado. Os três painéis exibiram o
evento e o aviso de transformação; nenhuma exceção JavaScript ocorreu.

Comandos executados:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m py_compile server.py tests/test_server.py
node /tmp/fazenda-etapa6-browser.mjs
git diff --check
```

O script de navegador é temporário e externo ao repositório. **Verificação
manual pendente:** repetir V6 com interação humana em três abas visíveis. O
ensaio M/A/B registrado foi automatizado. Permanecem pendentes as repetições
manuais humanas de V2–V5 já indicadas acima. O roteiro controlado cobre cenário
sem moinho e estoque insuficiente, que não são alcançados naturalmente pelo
ciclo normal de produção.

## Perguntas

1. **Quais eventos o sistema emite e escuta nesta etapa?** O servidor trata
   `connect` e `disconnect`, associa nome/papel à sessão e emite
   `estado.sincronizado` somente para o `sid` recém-conectado. O cliente escuta
   esse fato e os eventos de transporte `connect`, `disconnect` e `connect_error`.
   Na Etapa 2, também emite `vila.abertura_solicitada` e escuta `vila.iniciada`
   e `operacao.recusada`, com registro e reação via `pedir()` e `ouvir()`.
   Na Etapa 3, o Jogador emite `construcao.solicitada`; o servidor responde com
   `construcao.iniciada` global ou `operacao.recusada` privada. Na Etapa 5,
   `vila.encerramento_solicitado` resulta em `vila.encerrada` global ou recusa
   privada; produção e conclusão são suspensas após o fato de encerramento. Na
   Etapa 6, `recurso.produzido` pode ser seguido por `farinha.moida` no mesmo
   ciclo, com causa `recurso.produzido`. Na Etapa 7, o temporizador emite
   `colheita.amadurecida`; `colheita.coleta_solicitada` gera `colheita.coletada`
   ou recusa privada. Sem coleta, `colheita.estragada` tem causa
   `colheita.amadurecida` e não debita o celeiro.
2. **Como sabe quando atualizar os outros jogadores?** O estado pertence ao
   servidor. Nesta etapa, entrar não muda a fazenda, então somente quem entrou
   recebe o snapshot. Ao aceitar abertura, construção ou encerramento, `publicar`
   envia `vila.iniciada`, `construcao.iniciada` ou `vila.encerrada` para todos; a
   moagem é publicada depois do snapshot de produção. Quando um pedido falha,
   `recusar` envia `operacao.recusada`
   somente ao `sid` solicitante, com o estado inalterado.
3. **Onde aparece o paradigma orientado a eventos?** Em `server.py`, o tratador
   `connect` publica o estado com causa `conexao`. Em `client/index.html`,
   `ouvir('estado.sincronizado', ...)` registra o fato e aciona `atualizar(d)` e
   `jogo.mostrarEstado(d.estado)`. O painel torna visível causa → dados → reação.
   O cliente substitui os valores recebidos e não calcula créditos ou débitos.
   A abertura segue o encadeamento `pedir` → tratador `abrir_vila` →
   `vila.iniciada` → `atualizar`/`jogo.vilaIniciada`; a recusa usa
   `avisar`/`jogo.recusado` e explica que o pedido não alterou o estado.
   A construção segue `pedir` → tratador `construir` → `construcao.iniciada` →
   `atualizar`/`jogo.obraIniciada`. O snapshot reconcilia canteiros e barras por
   identidade sem reproduzir débitos. O encerramento segue `pedir` →
   `encerrar_vila` → `vila.encerrada`; o painel e a cena usam o snapshot recebido
   e congelam a apresentação, inclusive após reconexão. A moagem é uma reação a
   `farinha.moida`: o cliente substitui os estoques pelo novo snapshot e avisa as
   quantidades, sem recalcular a transformação.

## Uso de IA

Codex auxiliou na implementação e verificação da Etapa 1: estado e sessões no
servidor, sincronização privada, adaptação do cliente e painel, reconciliação da
cena e este roteiro. Foram reaproveitados o kit, seus métodos e os assets existentes.
Na Etapa 2, auxiliou no tratador de abertura, nas recusas privadas, nas escutas
do cliente, nos 11 testes permanentes e no roteiro automatizado com M/A/B.
Na Etapa 3, auxiliou na validação de construções, nos registros individuais,
nas barras indicativas, na correção do classificador do painel e nas verificações
com testes controlados e navegador. Na Etapa 5, auxiliou no encerramento com
cancelamento dos temporizadores, na sincronização visual do estado final e na
verificação da disputa concorrente com três clientes. Na Etapa 6, auxiliou na
moagem sob lock, nos snapshots sequenciais de produção/moagem e na verificação
V6 com os três participantes. Na Etapa 7, auxiliou nos testes de fronteira e
concorrência, nos temporizadores de colheita, nas reações do cliente e na
verificação final automatizada com M/A/B. Os resultados e limites dessa
verificação estão registrados abaixo.

## Extras

Nenhum extra de domínio implementado nesta etapa.

## Etapa 7 — Colheitas e verificação final

Implementação e verificação em **2026-11-04**, a partir de `3505dda`. Mantidos
Python 3.14.7, as dependências e os assets do kit. README e rodapé identificam
Fernando Artur Luithardt, conforme autoria e repositório Git.

A abertura agenda amadurecimentos em abertura + n×20 s. Cada colheita tem
identidade própria, vale 30 e dura 10 s. A coleta não ocupa agricultor. Sob o
mesmo lock, o servidor valida fase → papel → disponibilidade/prazo. O tratador
captura o relógio monotônico antes de qualquer espera e solicita imediatamente
o lock. Só aceita chegada estritamente anterior ao vencimento; o relógio do
cliente não decide. A remoção da identidade invalida a expiração antiga.
Encerrar cancela as tarefas e preserva inclusive a colheita ainda disponível.

Exemplos de causa → dados → reação:

- `temporizador` → `colheita.amadurecida`, identidade, valor 30, prazo 10 →
  mostrar valor e prazo indicativo; avisar sem creditar o celeiro.
- `colheita.coleta_solicitada` → `colheita.coletada`, identidade, quantidade 30 →
  aplicar snapshot, retirar indicador e avisar crédito confirmado.
- `colheita.amadurecida` → `colheita.estragada`, identidade, valor_perdido 30,
  gatilho temporizador → retirar indicador e avisar perda sem débito no celeiro.
- Pedido inválido → `operacao.recusada`, motivo e estado corrente → somente o
  solicitante recebe o aviso; o pedido não altera recursos.

A contagem pode chegar a zero enquanto aguarda o fato do servidor. Ela não
remove colheitas, confirma perda nem credita recursos. Ao encerrar, usa
`encerrada_em_ms` e interrompe seu intervalo local. O botão Coletar pertence
somente ao Jogador; os testes também enviam pedidos proibidos diretamente ao
servidor, sem depender dos controles da interface.

### Suíte controlada

**38 testes passaram** com `unittest`, incluindo os 28 anteriores e dez novos
casos de colheita. Os testes verificam amadurecimento sem antecipação, calendário
20/40/60, unicidade, snapshots copiados e sem campos monotônicos, crédito único,
sem ocupação de agricultor, disputa A/B, causas e destinatários. Verificam também
chegada em T−ε/T/T+ε com timer atrasado, duas coletas antes de T aguardando o lock
até T+ε, timer que acorda cedo, identidade antiga, prioridade fase/papel, perda
única sem débito e encerramento à frente da coleta na fila. Com obra, produção,
amadurecimento e expiração pendentes, o retrato final permanece inalterado e a
conexão tardia recebe esse mesmo retrato.

A execução inicial dos novos testes falhou por ausência dos tratadores; depois
da implementação, a suíte completa passou. Não foram alterados requisitos,
contratos ou as decisões 1A/2A.

### Aceitação em três clientes

Os roteiros usam três páginas reais do Chrome headless (Mestre, A e B), Socket.IO,
Vue e Phaser, com servidores Uvicorn reiniciados entre temporadas. Estados
artificiais e precisão da fronteira temporal ficam somente nos testes unitários.
O instrumento externo usa o protocolo de depuração do Chrome, sem dependência
nova no projeto. Falhas iniciais de sintaxe/serialização do instrumento foram
corrigidas antes dos resultados; não eram falhas do domínio.

| Roteiro | Condição, ações e resultado |
| --- | --- |
| V1 | M/A/B recebem 150 trigo/0 farinha/0 agricultores; snapshots privados. Reconexão de B recebe novo snapshot e mantém um canvas. |
| V1 — entrada tardia/recarga | B entra durante obra e colheita pendentes, recebe as mesmas identidades e prazos; recarrega durante a temporada e após encerrar, mantendo um canvas e o retrato correto. M/A não recebem seus snapshots privados. Rodapé conferido no navegador. |
| V2 | M abre sem crédito imediato; segunda abertura recebe recusa somente em M. Validação de Jogador coberta pela suíte. |
| V3 | Pedido direto de A antes da abertura recebe recusa privada; após abrir, uma obra debita 50 em todos. Estoque 49/50, vagas e prioridade do Mestre verificados em estados controlados. |
| V4 | Obra gera 100 → 110 trigo, conclui sem clique e libera agricultor. Reconexão durante a obra preserva identidade e prazo, sem duplicar canvas. |
| V5 | Aos 25 s, 200 trigo; duas obras deixam 100 e 2/3 ocupados. A/B disputam: uma aceitação, uma recusa privada, 50 trigo e 3/3. Encerramento preserva tudo por mais de 20 s e reconexão recebe o retrato final. |
| V6 | Produção mostra 130 e é seguida de moagem com causa `recurso.produzido`, consumo 5, produção 3, estado 125 trigo/3 farinha nos três clientes. Painel mostra causa/dados/reação. |
| V7 — disputa/fim | Colheita de 30 aos 20 s; A/B disputam, um crédito e uma recusa privada. Nenhuma perda da identidade coletada; nova colheita aos 40 s. Obra e colheita pendentes preservadas após encerramento por mais de 20 s; contagem congelada. |
| V7 — perda | Sem obras/coletas, amadurecimento aos 20 s e perda única aos 30 s; após a produção simultânea, 210 trigo/0 farinha. Coleta posterior recusada somente em A. |

### Cobertura e pendências de entrega

| Cenários / critérios | Evidência na versão final |
| --- | --- |
| US1.1–US1.8 | V1/V2/V4/V5/V7 e testes de sessão, papéis, abertura, produção, encerramento e reconexão. |
| US2.1–US2.9 | V3–V6 e testes controlados de estoque/vagas, ordem de validação, disputa, prazos, moagem e elegibilidade na fronteira do intervalo. |
| US3.1–US3.9 | V7 e dez testes controlados de colheita, incluindo os papéis de 1A e a fronteira estrita de 2A. |
| SC-001 / SC-006 | Comparação dos estados M/A/B; fatos globais, recusas privadas e painel com causa/dados/reação. |
| SC-002 / SC-003 | Sequência 100/110/130/125 e farinha 3; disputa pela última vaga com estoque suficiente. |
| SC-004 / SC-005 | Crédito/perda únicos; nenhuma atividade após encerrar com obra e colheita pendentes por mais de um ciclo de 20 s. |
| SC-007 | Resultados de todos os grupos de cenários registrados acima; limites exatos demonstrados por relógio controlado. |

Comandos de verificação:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m py_compile server.py tests/test_server.py
.venv/bin/python -m pip check
node /tmp/fazenda-etapa7-browser.mjs
node /tmp/fazenda-etapa7-browser.mjs --remaining
git diff --check
```

O script de navegador em `/tmp` é um instrumento temporário, não parte da
aplicação. O [quickstart](specs/001-fazenda-tempo-real/quickstart.md) mantém os
passos para repetir V1–V7. A suíte permanente e os roteiros automatizados passaram;
**permanece pendente repetir V1–V7 manualmente com interação humana em três abas
visíveis antes da apresentação acadêmica**. A automação registrada não equivale
a essa sessão manual. Não há pendência funcional conhecida; os requisitos de
milissegundos devem continuar sendo conferidos por testes controlados.

Não existe `.specify/extensions.yml`; não há hooks de implementação registrados.
