import asyncio
from copy import deepcopy
from itertools import count
import unittest
from unittest.mock import AsyncMock, patch

import server


PEDIDO_ABERTURA = "vila.abertura_solicitada"
PEDIDO_CONSTRUCAO = "construcao.solicitada"
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
        p = patch.object(server, "agendar", create=True)
        self.agendar = p.start()
        self.addCleanup(p.stop)

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

    async def construir(self, sid, *dados):
        await server.sio.handlers["/"][PEDIDO_CONSTRUCAO](sid, *dados)

    def conferir_recusa(self, sid, motivo, anterior, causa=PEDIDO_ABERTURA):
        self.emit.assert_awaited_once()
        chamada = self.emit.await_args
        self.assertEqual(chamada.args[0], "operacao.recusada")
        self.assertEqual(chamada.kwargs, {"to": sid})
        self.assertEqual(chamada.args[1]["causa"], causa)
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
        self.agendar.assert_called_once_with(server.ciclo_producao, 100.0)
        primeiro_evento = self.emit.await_args.args[1]
        anterior = server.snapshot()
        self.emit.reset_mock()
        self.relogio.return_value = 120.0
        await self.abrir("M")
        self.conferir_recusa("M", "A temporada já foi aberta", anterior)
        self.agendar.assert_called_once_with(server.ciclo_producao, 100.0)
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

    def preparar_obras(self, quantidade, status="em_andamento"):
        # Estados artificiais pertencem somente aos testes, sem rotas na aplicação.
        server.estado["obras"] = [{
            "id": 100 + i, "status": status, "iniciada_em": 90.0,
            "concluir_em": 98.0, "concluida_em": 98.0 if status == "concluida" else None,
            "iniciada_em_ms": 990_000, "concluir_em_ms": 998_000,
            "concluida_em_ms": 998_000 if status == "concluida" else None,
        } for i in range(quantidade)]

    async def test_construcao_recusas_na_ordem_fase_papel_trigo_agricultor(self):
        await self.participantes()
        casos = [
            ("aguardando", "A", 150, 0, "A temporada não está aberta"),
            ("encerrada", "A", 150, 0, "A temporada não está aberta"),
            ("aguardando", "M", 49, 3, "A temporada não está aberta"),
            ("encerrada", "M", 49, 3, "A temporada não está aberta"),
            ("aberta", "M", 150, 0, "Só o Jogador pode construir"),
            ("aberta", "M", 49, 3, "Só o Jogador pode construir"),
            ("aberta", "A", 49, 0, "Trigo insuficiente"),
            ("aberta", "A", 49, 3, "Trigo insuficiente"),
            ("aberta", "B", 50, 3, "Sem agricultor livre"),
            ("aberta", "B", 100, 3, "Sem agricultor livre"),
        ]
        for fase, sid, trigo, ocupados, motivo in casos:
            with self.subTest(fase=fase, sid=sid, trigo=trigo, ocupados=ocupados):
                server.estado.update(fase=fase, trigo=trigo)
                self.preparar_obras(ocupados)
                anterior = server.snapshot()
                interno = deepcopy(server.estado)
                self.emit.reset_mock()
                await self.construir(sid, {"papel": "jogador", "trigo": 999, "custo": 0})
                self.conferir_recusa(sid, motivo, anterior, PEDIDO_CONSTRUCAO)
                self.assertEqual(server.estado, interno)
        self.assertEqual(next(server.identidades), 1, "Recusas não consomem identidade")

    async def test_construcao_com_50_debita_uma_vez_e_publica_contrato(self):
        await self.participantes()
        await self.abrir("M")
        server.estado["trigo"] = 50
        self.relogio.return_value = 110.0  # O prazo nasce da obra, não da abertura.
        self.emit.reset_mock()
        await self.construir("A", {"papel": "mestre", "custo": 0, "tempo_obra": 1, "obra_id": 99})
        obra = {
            "id": 1, "status": "em_andamento", "iniciada_em_ms": 1_010_000,
            "concluir_em_ms": 1_018_000, "concluida_em_ms": None,
        }
        self.assertEqual(server.snapshot()["obras"], [obra])
        self.assertEqual(server.estado["obras"], [{**obra, "iniciada_em": 110.0,
                                                "concluir_em": 118.0, "concluida_em": None}])
        self.assertEqual(server.estado["trigo"], 0)
        self.assertEqual(server.snapshot()["trabalhadores"], 1)
        self.assertEqual(server.snapshot()["em_obra"], 1)
        self.assertEqual(server.snapshot()["concluidas"], 0)
        self.assertEqual(server.snapshot()["producao"], 10)
        self.assertEqual(server.estado["farinha"], 0)
        self.emit.assert_awaited_once_with("construcao.iniciada", {
            "estado": server.snapshot(), "causa": PEDIDO_CONSTRUCAO,
            "servidor_em_ms": 1_010_000, "obra_id": 1, "custo": 50,
        }, to=None)
        self.assertEqual(server.tarefas, set())
        server.esperar.assert_not_awaited()

    async def test_obras_tem_ids_distintos_snapshots_copiados_e_limite_tres(self):
        await self.participantes()
        await self.abrir("M")
        server.estado["trigo"] = 200
        self.emit.reset_mock()
        for sid in ("A", "B", "A"):
            await self.construir(sid)
        eventos = [c.args[1] for c in self.emit.await_args_list]
        self.assertEqual([e["obra_id"] for e in eventos], [1, 2, 3])
        self.assertEqual([e["estado"]["trigo"] for e in eventos], [150, 100, 50])
        self.assertEqual([len(e["estado"]["obras"]) for e in eventos], [1, 2, 3])
        self.assertEqual([e["estado"]["trabalhadores"] for e in eventos], [1, 2, 3])
        self.emit.reset_mock()
        anterior = server.snapshot()
        await self.construir("B")
        self.conferir_recusa("B", "Sem agricultor livre", anterior, PEDIDO_CONSTRUCAO)

    async def test_entrada_tardia_preserva_obras_prazos_e_estado_apos_oito_segundos(self):
        await self.participantes()
        await self.abrir("M")
        await self.construir("A")
        anterior = server.snapshot()
        await server.disconnect("B")
        self.relogio.return_value = 120.0
        self.emit.reset_mock()
        await server.connect("B2", {}, {"papel": "jogador"})
        self.emit.assert_awaited_once_with("estado.sincronizado", {
            "estado": anterior, "causa": "conexao", "servidor_em_ms": 1_020_000,
        }, to="B2")
        self.assertEqual(server.estado["trigo"], 100)
        self.assertEqual(server.snapshot()["trabalhadores"], 1)
        self.assertEqual(server.snapshot()["concluidas"], 0)

    async def test_moinhos_concluidos_nao_limitam_novas_obras(self):
        await self.participantes()
        await self.abrir("M")
        self.preparar_obras(20, "concluida")
        await self.construir("A")
        self.assertEqual(server.snapshot()["concluidas"], 20)
        self.assertEqual(server.snapshot()["trabalhadores"], 1)
        self.assertEqual(server.snapshot()["em_obra"], 1)
        self.assertEqual(server.estado["trigo"], 100)

    async def test_construcao_espera_lock_e_reavalia_estoque(self):
        await self.participantes()
        await self.abrir("M")
        self.emit.reset_mock()
        async with server.lock:
            tarefa = asyncio.create_task(self.construir("A"))
            await asyncio.sleep(0)
            self.emit.assert_not_awaited()
            self.assertEqual(server.estado["obras"], [])
            server.estado["trigo"] = 49
            anterior = server.snapshot()
        await tarefa
        self.conferir_recusa("A", "Trigo insuficiente", anterior, PEDIDO_CONSTRUCAO)


class TemporizadoresTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendario_ancorado_e_fase(self):
        prazos = []
        async def produzir(prazo):
            prazos.append(prazo)
            return len(prazos) < 3
        with patch.object(server, 'produzir_em', side_effect=produzir):
            await server.ciclo_producao(100)
        self.assertEqual(prazos, [105, 110, 115])
        with patch.object(server, 'estado', deepcopy(ESTADO_INICIAL)), patch.object(server, 'lock', asyncio.Lock()), patch.object(server, 'agora', return_value=105), patch.object(server.sio, 'emit', new_callable=AsyncMock) as emit:
            self.assertFalse(await server.produzir_em(105))
            self.assertEqual(server.estado['trigo'],150)
            emit.assert_not_awaited()

    async def test_sequencia_controlada(self):
        tempo = [100.0]
        async def esperar(segundos):
            self.assertFalse(server.lock.locked())
            tempo[0] += segundos
        with patch.object(server, 'estado', deepcopy(ESTADO_INICIAL)), patch.object(server, 'lock', asyncio.Lock()), patch.object(server, 'agora', side_effect=lambda: tempo[0]), patch.object(server, 'esperar', side_effect=esperar), patch.object(server.sio, 'emit', new_callable=AsyncMock) as emit:
            server.estado['fase'] = 'aberta'
            obra = server.criar_obra()
            server.estado['obras'].append(obra)
            server.estado['trigo'] = 100
            await server.produzir_em(105)
            self.assertEqual(server.estado['trigo'], 110)
            await server.concluir_obra(obra['id'])
            self.assertEqual(tempo[0], 108)
            self.assertEqual(server.snapshot()['trabalhadores'], 0)
            await server.produzir_em(110)
            self.assertEqual(server.estado['trigo'], 130)
            self.assertEqual(server.estado['farinha'], 0)
            self.assertEqual([c.args[0] for c in emit.await_args_list], ['recurso.produzido','construcao.concluida','recurso.produzido'])
            self.assertEqual(emit.await_args_list[0].args[1]['estado']['trigo'],110)
            self.assertTrue(all(c.kwargs == {'to':None} for c in emit.await_args_list))
            await server.concluir_obra(obra['id'])
            self.assertEqual(emit.await_count,3)
            server.estado['fase']='encerrada'
            await server.produzir_em(115)
            self.assertEqual(emit.await_count,3)

if __name__ == "__main__":
    unittest.main()
