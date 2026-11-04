import asyncio
from copy import deepcopy
from itertools import count
import time

import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, static_files={
    "/": "client/index.html",
    "/assets": "client/assets",      # mapa, tileset e sprites da vila
})

# Uma fazenda por processo, com decisões serializadas pelo lock.
TEMA = 19
TRIGO_INICIAL = 150
LIMITE_AGRICULTORES = 3
CUSTO_OBRA = 50
TEMPO_OBRA = 8
INTERVALO_PRODUCAO = 5
PRODUCAO_BASE = 10
INTERVALO_COLHEITA = 20
PRAZO_COLHEITA = 10
VALOR_COLHEITA = 30

estado = {
    "tema": TEMA,
    "fase": "aguardando",
    "trigo": TRIGO_INICIAL,
    "farinha": 0,
    "limite": LIMITE_AGRICULTORES,
    "custo": CUSTO_OBRA,
    "tempo_obra": TEMPO_OBRA,
    "intervalo": INTERVALO_PRODUCAO,
    "obras": [],
    "colheita": None,
    "aberta_em_ms": None,
    "encerrada_em_ms": None,
}

lock = asyncio.Lock()
sessoes = {}
identidades = count(1)
tarefas = set()
aberta_em = None
esperar = asyncio.sleep  # Substituível junto ao relógio em testes de temporizadores.
_referencia_tempo = None


def agora():
    return asyncio.get_running_loop().time()


def instante_publico(instante=None):
    """Converte o relógio monotônico usando uma única referência civil."""
    global _referencia_tempo
    atual = agora()
    if _referencia_tempo is None:
        _referencia_tempo = (atual, time.time() * 1000)
    monotono, civil_ms = _referencia_tempo
    return round(civil_ms + ((atual if instante is None else instante) - monotono) * 1000)


def snapshot():
    """Chamado sob o lock; nenhuma referência mutável escapa do estado."""
    copia = deepcopy(estado)
    # Instantes monotônicos das obras pertencem somente ao servidor.
    campos_obra = ("id", "status", "iniciada_em_ms", "concluir_em_ms", "concluida_em_ms")
    copia["obras"] = [{campo: obra[campo] for campo in campos_obra}
                      for obra in estado["obras"]]
    if copia["colheita"] is not None:
        copia["colheita"].pop("expira_em", None)
    em_obra = sum(obra["status"] == "em_andamento" for obra in copia["obras"])
    concluidas = sum(obra["status"] == "concluida" for obra in copia["obras"])
    copia.update(trabalhadores=em_obra, em_obra=em_obra, concluidas=concluidas,
                 producao=PRODUCAO_BASE + 10 * concluidas)
    return copia


async def publicar(evento, causa, *, sid=None, **dados):
    """O chamador mantém o lock da decisão até o fim da publicação.

    Sem sid, publica para todos; com sid, somente para esse participante.
    Esperas de temporizadores e cancelamentos devem ficar fora do lock.
    """
    await sio.emit(evento, {
        **deepcopy(dados),
        "estado": snapshot(),
        "causa": causa,
        "servidor_em_ms": instante_publico(),
    }, to=sid)


@sio.event
async def connect(sid, environ, auth=None):
    if not isinstance(auth, dict) or auth.get("papel") not in ("mestre", "jogador"):
        raise socketio.exceptions.ConnectionRefusedError("Papel inválido")
    nome = auth.get("nome", "")
    if not isinstance(nome, str):
        raise socketio.exceptions.ConnectionRefusedError("Nome inválido")
    async with lock:
        sessoes[sid] = {"nome": nome.strip() or "Anônimo", "papel": auth["papel"]}
        try:
            await publicar("estado.sincronizado", "conexao", sid=sid)
        except Exception:
            sessoes.pop(sid, None)
            raise


@sio.event
async def disconnect(sid, reason=None):
    async with lock:
        sessoes.pop(sid, None)


async def recusar(sid, causa, motivo):
    """Chamado sob o lock; informa a recusa sem modificar a fazenda."""
    await publicar("operacao.recusada", causa, sid=sid, motivo=motivo)


@sio.on("vila.abertura_solicitada")
async def abrir_vila(sid, dados=None):
    global aberta_em
    causa = "vila.abertura_solicitada"
    async with lock:
        # O papel pertence à sessão, nunca ao payload do pedido.
        if sessoes.get(sid, {}).get("papel") != "mestre":
            await recusar(sid, causa, "Só o Mestre pode abrir a temporada")
            return
        if estado["fase"] != "aguardando":
            await recusar(sid, causa, "A temporada já foi aberta")
            return

        aberta_em = agora()
        estado["aberta_em_ms"] = instante_publico(aberta_em)
        estado["fase"] = "aberta"
        await publicar("vila.iniciada", causa)
        agendar(ciclo_producao, aberta_em)
        agendar(ciclo_colheitas, aberta_em)


def criar_obra():
    """Cria identidade e prazos sob o lock; a conclusão é agendada pelo tratador."""
    inicio = agora()
    prazo = inicio + TEMPO_OBRA
    return {
        "id": next(identidades),
        "status": "em_andamento",
        "iniciada_em": inicio,
        "concluir_em": prazo,
        "concluida_em": None,
        "iniciada_em_ms": instante_publico(inicio),
        "concluir_em_ms": instante_publico(prazo),
        "concluida_em_ms": None,
    }


@sio.on("construcao.solicitada")
async def construir(sid, dados=None):
    causa = "construcao.solicitada"
    async with lock:
        if estado["fase"] != "aberta":
            await recusar(sid, causa, "A temporada não está aberta")
            return
        if sessoes.get(sid, {}).get("papel") != "jogador":
            await recusar(sid, causa, "Só o Jogador pode construir")
            return
        if estado["trigo"] < CUSTO_OBRA:
            await recusar(sid, causa, "Trigo insuficiente")
            return
        if snapshot()["trabalhadores"] >= LIMITE_AGRICULTORES:
            await recusar(sid, causa, "Sem agricultor livre")
            return

        obra = criar_obra()
        estado["trigo"] -= CUSTO_OBRA
        estado["obras"].append(obra)
        await publicar("construcao.iniciada", causa, obra_id=obra["id"], custo=CUSTO_OBRA)
        agendar(concluir_obra, obra["id"])


def agendar(funcao, *args):
    tarefa = asyncio.create_task(funcao(*args))
    tarefas.add(tarefa)
    tarefa.add_done_callback(tarefas.discard)
    return tarefa


async def esperar_ate(prazo):
    while agora() < prazo:
        await esperar(prazo - agora())


def moer_moinhos(instante_intervalo):
    """Mói moinhos concluídos estritamente antes do intervalo; requer o lock."""
    if estado["fase"] != "aberta":
        return None
    concluidos_antes = sum(
        obra["status"] == "concluida"
        and obra["concluida_em"] is not None
        and obra["concluida_em"] < instante_intervalo
        for obra in estado["obras"]
    )
    moinhos = min(concluidos_antes, estado["trigo"] // 5)
    if not moinhos:
        return None

    trigo_consumido = moinhos * 5
    farinha_produzida = moinhos * 3
    estado["trigo"] -= trigo_consumido
    estado["farinha"] += farinha_produzida
    return {
        "moinhos": moinhos,
        "trigo_consumido": trigo_consumido,
        "farinha_produzida": farinha_produzida,
    }


async def produzir_em(prazo):
    await esperar_ate(prazo)
    async with lock:
        if estado["fase"] != "aberta":
            return False
        quantidade = snapshot()["producao"]
        estado["trigo"] += quantidade
        await publicar("recurso.produzido", "temporizador", quantidade=quantidade)
        moagem = moer_moinhos(prazo)
        if moagem:
            await publicar("farinha.moida", "recurso.produzido", **moagem)
        return True


async def ciclo_producao(inicio):
    ciclo = 1
    while await produzir_em(inicio + ciclo * INTERVALO_PRODUCAO):
        ciclo += 1


async def concluir_obra(obra_id):
    obra = next((o for o in estado["obras"] if o["id"] == obra_id), None)
    if obra is None:
        return
    await esperar_ate(obra["concluir_em"])
    async with lock:
        if estado["fase"] != "aberta" or obra["status"] != "em_andamento":
            return
        obra["status"] = "concluida"
        obra["concluida_em"] = agora()
        obra["concluida_em_ms"] = instante_publico(obra["concluida_em"])
        await publicar("construcao.concluida", "construcao.iniciada",
                       obra_id=obra_id, gatilho="temporizador")


@sio.on("vila.encerramento_solicitado")
async def encerrar_vila(sid, dados=None):
    global estado
    causa = "vila.encerramento_solicitado"
    async with lock:
        if sessoes.get(sid, {}).get("papel") != "mestre":
            await recusar(sid, causa, "Só o Mestre pode encerrar a temporada")
            return
        if estado["fase"] != "aberta":
            await recusar(sid, causa, "A temporada não está aberta")
            return
        estado["fase"] = "encerrada"
        estado["encerrada_em_ms"] = instante_publico()
        pendentes = tuple(tarefa for tarefa in tarefas
                          if tarefa is not asyncio.current_task() and not tarefa.done())
        for tarefa in pendentes:
            tarefa.cancel()
        await publicar("vila.encerrada", causa)

    # Nunca esperar pelo cancelamento enquanto se mantém o lock necessário
    # para encerrar com segurança os tratadores de temporizador.
    if pendentes:
        await asyncio.gather(*pendentes, return_exceptions=True)


async def amadurecer_em(prazo):
    await esperar_ate(prazo)
    async with lock:
        if estado["fase"] != "aberta":
            return False
        if estado["colheita"] is None:
            inicio = agora()
            colheita = {
                "id": next(identidades), "valor": VALOR_COLHEITA,
                "amadurecida_em_ms": instante_publico(inicio),
                "expira_em_ms": instante_publico(inicio + PRAZO_COLHEITA),
                "expira_em": inicio + PRAZO_COLHEITA,
            }
            estado["colheita"] = colheita
            await publicar("colheita.amadurecida", "temporizador",
                           colheita_id=colheita["id"], valor=VALOR_COLHEITA,
                           prazo=PRAZO_COLHEITA)
            agendar(expirar_colheita, colheita["id"], colheita["expira_em"])
        return True


async def ciclo_colheitas(inicio):
    ciclo = 1
    while await amadurecer_em(inicio + ciclo * INTERVALO_COLHEITA):
        ciclo += 1


async def expirar_colheita(colheita_id, prazo):
    # Só entra na fila do lock no prazo ou depois; coletas anteriores têm precedência.
    await esperar_ate(prazo)
    async with lock:
        colheita = estado["colheita"]
        if (estado["fase"] != "aberta" or colheita is None
                or colheita["id"] != colheita_id):
            return
        estado["colheita"] = None
        await publicar("colheita.estragada", "colheita.amadurecida",
                       colheita_id=colheita_id, valor_perdido=VALOR_COLHEITA,
                       gatilho="temporizador")


@sio.on("colheita.coleta_solicitada")
async def coletar(sid, dados=None):
    recebido_em = agora()
    async with lock:  # Nenhuma espera entre registrar a chegada e solicitar o lock.
        causa = "colheita.coleta_solicitada"
        if estado["fase"] != "aberta":
            await recusar(sid, causa, "A temporada não está aberta")
            return
        if sessoes.get(sid, {}).get("papel") != "jogador":
            await recusar(sid, causa, "Só o Jogador pode coletar")
            return
        colheita = estado["colheita"]
        if colheita is None or recebido_em >= colheita["expira_em"]:
            await recusar(sid, causa, "Não há colheita para coletar")
            return
        # Remover a identidade invalida a expiração, sem cancelar/esperar sob o lock.
        estado["colheita"] = None
        estado["trigo"] += VALOR_COLHEITA
        await publicar("colheita.coletada", causa,
                       colheita_id=colheita["id"], quantidade=VALOR_COLHEITA)
