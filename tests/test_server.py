import asyncio
from copy import deepcopy
from itertools import count
import unittest
from unittest.mock import AsyncMock, patch

import server


PEDIDO_ABERTURA = "vila.abertura_solicitada"
ESTADO_INICIAL = deepcopy(server.estado)


class ServidorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Cada caso recebe estado, sessões, relógio e transporte independentes.
        substitutos = {
            "estado": deepcopy(ESTADO_INICIAL),
            "sessoes": {},
            "lock": asyncio.Lock(),
            "identidades": count(1),
            "tarefas": set(),
            "aberta_em": None,
            "_referencia_tempo": (100.0, 1_000_000),
            "esperar": AsyncMock(),
        }
        for nome, valor in substitutos.items():
            p = patch.object(server, nome, valor)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(server, "agora", return_value=100.0)
        self.relogio = p.start()
        self.addCleanup(p.stop)
        p = patch.object(server.sio, "emit", new_callable=AsyncMock)
        self.emit = p.start()
        self.addCleanup(p.stop)
        self.emit.side_effect = self.transmitir

    async def transmitir(self, evento, dados, *, to):
        self.assertTrue(server.lock.locked(), "Publicar dentro da operação protegida")
        await asyncio.sleep(0)  # Simula transporte cedendo execução para concorrentes.

    async def participantes(self):
        for sid, papel in (("M", "mestre"), ("A", "jogador"), ("B", "jogador")):
            await server.connect(sid, {}, {"nome": sid, "papel": papel})
        self.emit.reset_mock()

    async def abrir(self, sid, *dados):
        # Exercita também o registro do nome público no Socket.IO.
        await server.sio.handlers["/"][PEDIDO_ABERTURA](sid, *dados)

    def conferir_recusa(self, sid, motivo, anterior):
        self.emit.assert_awaited_once()
        chamada = self.emit.await_args
        self.assertEqual(chamada.args[0], "operacao.recusada")
        self.assertEqual(chamada.kwargs, {"to": sid})
        self.assertEqual(chamada.args[1]["causa"], PEDIDO_ABERTURA)
        self.assertEqual(chamada.args[1]["motivo"], motivo)
        self.assertEqual(chamada.args[1]["estado"], anterior)
        self.assertEqual(server.snapshot(), anterior)

    async def test_conexao_tem_snapshot_privado_e_sessao(self):
        for sid, papel in (("M", "mestre"), ("A", "jogador"), ("B", "jogador")):
            await server.connect(sid, {}, {"nome": sid, "papel": papel})
            chamada = self.emit.await_args
            self.assertEqual(chamada.args[0], "estado.sincronizado")
            self.assertEqual(chamada.kwargs, {"to": sid})
            self.assertEqual(chamada.args[1]["causa"], "conexao")
            self.assertEqual(chamada.args[1]["estado"], server.snapshot())
            self.assertEqual(server.sessoes[sid], {"nome": sid, "papel": papel})
        self.assertEqual(self.emit.await_count, 3)
        self.assertEqual(server.estado, ESTADO_INICIAL)

    async def test_nome_vazio_e_papel_invalido(self):
        for auth in (None, {}, [], {"papel": "admin"}, {"papel": ["mestre"]}):
            with self.subTest(auth=auth):
                with self.assertRaises(server.socketio.exceptions.ConnectionRefusedError):
                    await server.connect("invalido", {}, auth)
        self.emit.assert_not_awaited()
        self.assertEqual(server.sessoes, {})
        await server.connect("A", {}, {"nome": "  ", "papel": "jogador"})
        self.assertEqual(server.sessoes["A"]["nome"], "Anônimo")

    async def test_snapshot_copiado_inclusive_registros(self):
        server.estado["obras"] = [{
            "id": 1, "status": "em_andamento", "iniciada_em_ms": 100,
            "concluir_em_ms": 8100, "concluida_em_ms": None, "iniciada_em": 1.0,
        }]
        await server.connect("A", {}, {"papel": "jogador"})
        publicado = self.emit.await_args.args[1]["estado"]
        server.estado["trigo"] = 0
        server.estado["obras"][0]["status"] = "concluida"
        self.assertEqual(publicado["trigo"], 150)
        self.assertEqual(publicado["obras"][0]["status"], "em_andamento")
        self.assertNotIn("iniciada_em", publicado["obras"][0])
        self.assertEqual(publicado["trabalhadores"], 1)
        self.assertEqual(server.snapshot()["producao"], 20)

    async def test_mestre_abre_para_todos_sem_credito_imediato(self):
        await self.participantes()
        anterior = server.snapshot()
        await self.abrir("M")
        esperado = {**anterior, "fase": "aberta", "aberta_em_ms": 1_000_000}
        self.emit.assert_awaited_once_with("vila.iniciada", {
            "estado": esperado, "causa": PEDIDO_ABERTURA, "servidor_em_ms": 1_000_000,
        }, to=None)
        self.assertEqual(server.snapshot(), esperado)
        self.assertEqual(server.aberta_em, 100.0)
        self.assertEqual(server.tarefas, set())  # Produção pertence à Etapa 4.
        server.esperar.assert_not_awaited()

    async def test_jogador_recusado_antes_da_fase(self):
        await self.participantes()
        for fase in ("aguardando", "aberta", "encerrada"):
            with self.subTest(fase=fase):
                server.estado["fase"] = fase
                anterior = server.snapshot()
                self.emit.reset_mock()
                await self.abrir("A", {"papel": "mestre", "trigo": 999, "aberta_em_ms": 0})
                self.conferir_recusa("A", "Só o Mestre pode abrir a temporada", anterior)
                self.assertIsNone(server.aberta_em)

    async def test_mestre_usa_sessao_e_nao_payload(self):
        await self.participantes()
        await self.abrir("M", {"papel": "jogador", "aberta_em_ms": 0, "trigo": 999})
        self.assertEqual(server.estado["fase"], "aberta")
        self.assertEqual(server.estado["trigo"], 150)
        self.assertEqual(server.estado["aberta_em_ms"], 1_000_000)

    async def test_segunda_abertura_preserva_estado_e_instantes(self):
        await self.participantes()
        await self.abrir("M")
        primeiro_evento = self.emit.await_args.args[1]
        anterior = server.snapshot()
        self.emit.reset_mock()
        self.relogio.return_value = 120.0
        await self.abrir("M")
        self.conferir_recusa("M", "A temporada já foi aberta", anterior)
        self.assertEqual(server.aberta_em, 100.0)
        self.assertEqual(server.estado["aberta_em_ms"], 1_000_000)
        self.assertEqual(primeiro_evento["estado"], anterior)
        self.assertEqual(primeiro_evento["servidor_em_ms"], 1_000_000)
        self.assertEqual(self.emit.await_args.args[1]["servidor_em_ms"], 1_020_000)

    async def test_temporada_encerrada_nao_reabre(self):
        await self.participantes()
        server.estado.update(fase="encerrada", aberta_em_ms=1_000_000, encerrada_em_ms=1_010_000)
        server.aberta_em = 100.0
        anterior = server.snapshot()
        await self.abrir("M")
        self.conferir_recusa("M", "A temporada já foi aberta", anterior)
        self.assertEqual(server.aberta_em, 100.0)

    async def test_duas_aberturas_concorrentes_publicam_um_fato(self):
        await self.participantes()
        await server.connect("M2", {}, {"papel": "mestre"})
        self.emit.reset_mock()
        await asyncio.gather(self.abrir("M"), self.abrir("M2"))
        fato, recusa = self.emit.await_args_list
        self.assertEqual(fato.args[0], "vila.iniciada")
        self.assertEqual(fato.kwargs, {"to": None})
        self.assertEqual(recusa.args[0], "operacao.recusada")
        self.assertEqual(recusa.kwargs, {"to": "M2"})
        self.assertEqual(fato.args[1]["estado"], recusa.args[1]["estado"])
        self.assertEqual(server.aberta_em, 100.0)

    async def test_abertura_aguarda_lock_antes_de_validar(self):
        await self.participantes()
        async with server.lock:
            tarefa = asyncio.create_task(self.abrir("M"))
            await asyncio.sleep(0)
            self.emit.assert_not_awaited()
            self.assertEqual(server.estado["fase"], "aguardando")
            self.relogio.return_value = 105.0
        await tarefa
        self.assertEqual(server.aberta_em, 105.0)
        self.assertEqual(server.estado["aberta_em_ms"], 1_005_000)

    async def test_reentrada_recebe_abertura_original_sem_reiniciar(self):
        await self.participantes()
        await self.abrir("M")
        anterior = server.snapshot()
        await server.disconnect("B")
        self.assertNotIn("B", server.sessoes)
        self.emit.reset_mock()
        self.relogio.return_value = 110.0
        await server.connect("B2", {}, {"nome": "B", "papel": "jogador"})
        self.emit.assert_awaited_once()
        self.assertEqual(self.emit.await_args.args[0], "estado.sincronizado")
        self.assertEqual(self.emit.await_args.kwargs, {"to": "B2"})
        self.assertEqual(self.emit.await_args.args[1]["estado"], anterior)
        self.assertEqual(server.aberta_em, 100.0)


if __name__ == "__main__":
    unittest.main()
