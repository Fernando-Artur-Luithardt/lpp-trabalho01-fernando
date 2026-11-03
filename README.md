# Vila em Tempo Real — Fazenda (tema 19)

Etapa 1 implementada: conexão dos participantes e `estado.sincronizado` privado.
O servidor mantém uma fazenda compartilhada em memória. Abrir/encerrar temporada,
construir, produzir, moer e coletar pertencem às próximas etapas; os botões de
atividade permanecem desabilitados nesta entrega.

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

## Como testar com duas abas

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
nova. A suíte permanente `tests/test_server.py` continua prevista para T010,
na Etapa 2. Entrada durante obra, barras e eventos de atividade serão verificados
nas respectivas etapas; esta entrega cobre somente conexão e sincronização.

## Perguntas

1. **Quais eventos o sistema emite e escuta nesta etapa?** O servidor trata
   `connect` e `disconnect`, associa nome/papel à sessão e emite
   `estado.sincronizado` somente para o `sid` recém-conectado. O cliente escuta
   esse fato e os eventos de transporte `connect`, `disconnect` e `connect_error`.
2. **Como sabe quando atualizar os outros jogadores?** O estado pertence ao
   servidor. Nesta etapa, entrar não muda a fazenda, então somente quem entrou
   recebe o snapshot. A função `publicar` já distingue envio privado de envio
   global; fatos de alteração compartilhada serão acrescentados nas próximas etapas.
3. **Onde aparece o paradigma orientado a eventos?** Em `server.py`, o tratador
   `connect` publica o estado com causa `conexao`. Em `client/index.html`,
   `ouvir('estado.sincronizado', ...)` registra o fato e aciona `atualizar(d)` e
   `jogo.mostrarEstado(d.estado)`. O painel torna visível causa → dados → reação.
   O cliente substitui os valores recebidos e não calcula créditos ou débitos.

## Uso de IA

Codex auxiliou na implementação e verificação da Etapa 1: estado e sessões no
servidor, sincronização privada, adaptação do cliente e painel, reconciliação da
cena e este roteiro. Foram reaproveitados o kit, seus métodos e os assets existentes.

## Extras

Nenhum extra de domínio implementado nesta etapa.
