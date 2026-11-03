# Vila em Tempo Real — Fazenda (tema 19)

Etapas 1 e 2 implementadas: conexão, sincronização privada e abertura única da
temporada pelo Mestre. O servidor mantém uma fazenda compartilhada em memória.
Encerrar, construir, produzir, moer e coletar pertencem às próximas etapas;
seus controles permanecem desabilitados nesta entrega.

## Integrantes

- Nome — @usuario-github

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
   A produção bruta indicada é a taxa configurada; ainda não há produção automática.
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
na Etapa 2, descrita abaixo. Entrada durante obra, barras e demais eventos de
atividade serão verificados nas respectivas etapas.

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

## Perguntas

1. **Quais eventos o sistema emite e escuta nesta etapa?** O servidor trata
   `connect` e `disconnect`, associa nome/papel à sessão e emite
   `estado.sincronizado` somente para o `sid` recém-conectado. O cliente escuta
   esse fato e os eventos de transporte `connect`, `disconnect` e `connect_error`.
   Na Etapa 2, também emite `vila.abertura_solicitada` e escuta `vila.iniciada`
   e `operacao.recusada`, com registro e reação via `pedir()` e `ouvir()`.
2. **Como sabe quando atualizar os outros jogadores?** O estado pertence ao
   servidor. Nesta etapa, entrar não muda a fazenda, então somente quem entrou
   recebe o snapshot. Ao aceitar a abertura, `publicar` envia `vila.iniciada`
   para todos; quando um pedido falha, `recusar` envia `operacao.recusada`
   somente ao `sid` solicitante, com o estado inalterado.
3. **Onde aparece o paradigma orientado a eventos?** Em `server.py`, o tratador
   `connect` publica o estado com causa `conexao`. Em `client/index.html`,
   `ouvir('estado.sincronizado', ...)` registra o fato e aciona `atualizar(d)` e
   `jogo.mostrarEstado(d.estado)`. O painel torna visível causa → dados → reação.
   O cliente substitui os valores recebidos e não calcula créditos ou débitos.
   A abertura segue o encadeamento `pedir` → tratador `abrir_vila` →
   `vila.iniciada` → `atualizar`/`jogo.vilaIniciada`; a recusa usa
   `avisar`/`jogo.recusado` e explica que o pedido não alterou o estado.

## Uso de IA

Codex auxiliou na implementação e verificação da Etapa 1: estado e sessões no
servidor, sincronização privada, adaptação do cliente e painel, reconciliação da
cena e este roteiro. Foram reaproveitados o kit, seus métodos e os assets existentes.
Na Etapa 2, auxiliou no tratador de abertura, nas recusas privadas, nas escutas
do cliente, nos 11 testes permanentes e no roteiro automatizado com M/A/B.

## Extras

Nenhum extra de domínio implementado nesta etapa.
