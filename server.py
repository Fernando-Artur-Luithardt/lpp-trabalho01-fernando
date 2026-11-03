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

# Uma fazenda por processo. As próximas etapas acrescentam suas transições.
TEMA = 19
TRIGO_INICIAL = 150
LIMITE_AGRICULTORES = 3
CUSTO_OBRA = 50
TEMPO_OBRA = 8
INTERVALO_PRODUCAO = 5
PRODUCAO_BASE = 10

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
