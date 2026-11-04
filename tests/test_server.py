import asyncio
from copy import deepcopy
from itertools import count
import unittest
from unittest.mock import AsyncMock, patch

import server


PEDIDO_ABERTURA = "vila.abertura_solicitada"
PEDIDO_CONSTRUCAO = "construcao.solicitada"
PEDIDO_ENCERRAMENTO = "vila.encerramento_solicitado"
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

    async def encerrar(self, sid, *dados):
        await server.sio.handlers["/"][PEDIDO_ENCERRAMENTO](sid, *dados)

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
        self.assertEqual(self.agendar.call_count, 2)
        self.agendar.assert_any_call(server.ciclo_producao, 100.0)
        self.agendar.assert_any_call(server.ciclo_colheitas, 100.0)
        primeiro_evento = self.emit.await_args.args[1]
        anterior = server.snapshot()
        self.emit.reset_mock()
        self.relogio.return_value = 120.0
        await self.abrir("M")
        self.conferir_recusa("M", "A temporada já foi aberta", anterior)
        self.assertEqual(self.agendar.call_count, 2)
        self.agendar.assert_any_call(server.ciclo_producao, 100.0)
        self.agendar.assert_any_call(server.ciclo_colheitas, 100.0)
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
            self.assertEqual(server.estado['trigo'], 125)
            self.assertEqual(server.estado['farinha'], 3)
            self.assertEqual([c.args[0] for c in emit.await_args_list], ['recurso.produzido','construcao.concluida','recurso.produzido','farinha.moida'])
            self.assertEqual(emit.await_args_list[0].args[1]['estado']['trigo'],110)
            self.assertEqual(emit.await_args_list[2].args[1]['estado']['trigo'],130)
            self.assertEqual(emit.await_args_list[2].args[1]['estado']['farinha'],0)
            self.assertEqual(emit.await_args_list[3].args[1]['estado']['trigo'],125)
            self.assertEqual(emit.await_args_list[3].args[1]['estado']['farinha'],3)
            self.assertEqual(emit.await_args_list[3].args[1]['causa'],'recurso.produzido')
            moagem = emit.await_args_list[3].args[1]
            self.assertEqual((moagem['moinhos'], moagem['trigo_consumido'], moagem['farinha_produzida']), (1,5,3))
            self.assertEqual(moagem['causa'], 'recurso.produzido')
            self.assertTrue(all(c.kwargs == {'to':None} for c in emit.await_args_list))
            retrato_moagem = emit.await_args_list[3].args[1]['estado']
            await server.produzir_em(115)
            self.assertEqual(server.estado['trigo'],140)
            self.assertEqual(server.estado['farinha'],6)
            self.assertEqual(retrato_moagem['trigo'],125)
            self.assertEqual(retrato_moagem['farinha'],3)
            await server.concluir_obra(obra['id'])
            self.assertEqual(emit.await_count,6)

    async def test_sem_moinho_apto_nao_emite_farinha_moida(self):
        estado = deepcopy(ESTADO_INICIAL)
        estado['fase'] = 'aberta'
        emit = AsyncMock()
        with patch.object(server, 'estado', estado), patch.object(server, 'lock', asyncio.Lock()), \
             patch.object(server, 'agora', return_value=105.0), patch.object(server.sio, 'emit', emit):
            await server.produzir_em(105.0)
        self.assertEqual(estado['trigo'], 160)
        self.assertEqual(estado['farinha'], 0)
        self.assertEqual([chamada.args[0] for chamada in emit.await_args_list], ['recurso.produzido'])

    async def test_moinho_sem_trigo_suficiente_e_pulado(self):
        estado = deepcopy(ESTADO_INICIAL)
        estado['fase'] = 'aberta'
        estado['trigo'] = 4
        estado['obras'] = [{
            'id': 1, 'status': 'concluida', 'iniciada_em': 90.0,
            'concluir_em': 98.0, 'concluida_em': 99.0,
            'iniciada_em_ms': 990_000, 'concluir_em_ms': 998_000,
            'concluida_em_ms': 999_000,
        }]
        with patch.object(server, 'estado', estado):
            resultado = server.moer_moinhos(105.0)
        self.assertIsNone(resultado)
        self.assertEqual(estado['trigo'], 4)
        self.assertEqual(estado['farinha'], 0)

    async def test_cada_moinho_apto_moe_cinco_trigos_em_tres_farinha(self):
        estado = deepcopy(ESTADO_INICIAL)
        estado['fase'] = 'aberta'
        estado['trigo'] = 13
        estado['farinha'] = 4
        estado['obras'] = [{
            'id': i, 'status': 'concluida', 'iniciada_em': 90.0,
            'concluir_em': 98.0, 'concluida_em': 99.0,
            'iniciada_em_ms': 990_000, 'concluir_em_ms': 998_000,
            'concluida_em_ms': 999_000,
        } for i in (1, 2)]
        with patch.object(server, 'estado', estado):
            resultado = server.moer_moinhos(105.0)
        self.assertEqual(resultado, {
            'moinhos': 2, 'trigo_consumido': 10, 'farinha_produzida': 6,
        })
        self.assertEqual(estado['trigo'], 3)
        self.assertEqual(estado['farinha'], 10)

    async def test_conclusao_no_limite_so_habilita_moagem_no_ciclo_seguinte(self):
        estado = deepcopy(ESTADO_INICIAL)
        estado['fase'] = 'aberta'
        estado['trigo'] = 100
        estado['obras'] = [{
            'id': 1, 'status': 'concluida', 'iniciada_em': 97.0,
            'concluir_em': 105.0, 'concluida_em': 105.0,
            'iniciada_em_ms': 997_000, 'concluir_em_ms': 1_005_000,
            'concluida_em_ms': 1_005_000,
        }]
        emit = AsyncMock()
        tempo = [105.0]
        with patch.object(server, 'estado', estado), patch.object(server, 'lock', asyncio.Lock()), \
             patch.object(server, 'agora', side_effect=lambda: tempo[0]), patch.object(server, 'esperar', new_callable=AsyncMock), \
             patch.object(server.sio, 'emit', emit):
            await server.produzir_em(105.0)
            self.assertEqual([c.args[0] for c in emit.await_args_list], ['recurso.produzido'])
            self.assertEqual(estado['trigo'], 120)
            tempo[0] = 110.0
            await server.produzir_em(110.0)
        self.assertEqual([c.args[0] for c in emit.await_args_list],
                         ['recurso.produzido', 'recurso.produzido', 'farinha.moida'])
        self.assertEqual(estado['trigo'], 135)
        self.assertEqual(estado['farinha'], 3)

    async def test_encerrada_nao_produz_ou_moe(self):
        estado = deepcopy(ESTADO_INICIAL)
        estado['fase'] = 'encerrada'
        estado['trigo'] = 17
        estado['obras'] = [{
            'id': 1, 'status': 'concluida', 'iniciada_em': 90.0,
            'concluir_em': 98.0, 'concluida_em': 99.0,
            'iniciada_em_ms': 990_000, 'concluir_em_ms': 998_000,
            'concluida_em_ms': 999_000,
        }]
        emit = AsyncMock()
        with patch.object(server, 'estado', estado), patch.object(server, 'lock', asyncio.Lock()), \
             patch.object(server, 'agora', return_value=105.0), patch.object(server.sio, 'emit', emit):
            self.assertFalse(await server.produzir_em(105.0))
            self.assertIsNone(server.moer_moinhos(105.0))
        self.assertEqual(estado['trigo'], 17)
        self.assertEqual(estado['farinha'], 0)
        emit.assert_not_awaited()


class EncerramentoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Reutiliza o fixture sem herdar e duplicar os testes das etapas anteriores.
        ServidorTests.setUp(self)

    async def transmitir(self, evento, dados, *, to):
        await ServidorTests.transmitir(self, evento, dados, to=to)

    async def participantes(self):
        await ServidorTests.participantes(self)

    async def abrir(self, sid, *dados):
        await ServidorTests.abrir(self, sid, *dados)

    async def construir(self, sid, *dados):
        await ServidorTests.construir(self, sid, *dados)

    async def encerrar(self, sid, *dados):
        await ServidorTests.encerrar(self, sid, *dados)

    def conferir_recusa(self, sid, motivo, anterior, causa=PEDIDO_ABERTURA):
        ServidorTests.conferir_recusa(self, sid, motivo, anterior, causa)

    async def test_recusas_por_papel_antes_da_fase_e_destino_privado(self):
        await self.participantes()
        for fase, motivo in [("aguardando", "Só o Mestre pode encerrar a temporada"),
                             ("aberta", "Só o Mestre pode encerrar a temporada"),
                             ("encerrada", "Só o Mestre pode encerrar a temporada")]:
            server.estado["fase"] = fase
            anterior = server.snapshot()
            self.emit.reset_mock()
            await self.encerrar("A", {"papel": "mestre"})
            self.conferir_recusa("A", motivo, anterior, PEDIDO_ENCERRAMENTO)
        server.estado["fase"] = "aguardando"
        anterior = server.snapshot()
        self.emit.reset_mock()
        await self.encerrar("M")
        self.conferir_recusa("M", "A temporada não está aberta", anterior, PEDIDO_ENCERRAMENTO)

    async def test_encerramento_preserva_snapshot_e_cancela_tarefas_fora_do_lock(self):
        await self.participantes()
        await self.abrir("M")
        server.estado["trigo"] = 77
        await self.construir("A")
        final_obra = server.snapshot()
        async def aguardar_timer(_segundos):
            await asyncio.Future()
        with patch.object(server, "esperar", side_effect=aguardar_timer):
            producao_pendente = asyncio.create_task(server.ciclo_producao(server.aberta_em))
            conclusao_pendente = asyncio.create_task(server.concluir_obra(1))
            server.tarefas.update((producao_pendente, conclusao_pendente))
            await asyncio.sleep(0)
            self.emit.reset_mock()
            await self.encerrar("M")
            self.assertTrue(producao_pendente.cancelled())
            self.assertTrue(conclusao_pendente.cancelled())
        chamada = self.emit.await_args
        self.assertEqual(chamada.args[0], "vila.encerrada")
        self.assertEqual(chamada.kwargs, {"to": None})
        self.assertEqual(chamada.args[1]["causa"], PEDIDO_ENCERRAMENTO)
        self.assertEqual(chamada.args[1]["estado"]["fase"], "encerrada")
        self.assertEqual(chamada.args[1]["estado"]["trigo"], 27)
        self.assertEqual(chamada.args[1]["estado"]["trabalhadores"], 1)
        self.assertEqual(chamada.args[1]["estado"]["obras"], final_obra["obras"])
        self.assertFalse(server.lock.locked())
        retrato = server.snapshot()
        self.relogio.return_value += 30
        await server.produzir_em(130)
        await server.concluir_obra(1)
        self.assertEqual(server.snapshot(), retrato)
        self.assertEqual(self.emit.await_count, 1)
        self.emit.reset_mock()
        await self.construir("A")
        self.conferir_recusa("A", "A temporada não está aberta", retrato, PEDIDO_CONSTRUCAO)

    async def test_repeticao_e_reabertura_sao_recusadas_sem_mudar_retrato(self):
        await self.participantes()
        await self.abrir("M")
        await self.encerrar("M")
        final = server.snapshot()
        self.emit.reset_mock()
        await self.encerrar("M")
        self.conferir_recusa("M", "A temporada não está aberta", final, PEDIDO_ENCERRAMENTO)

    async def test_disputa_pelo_ultimo_agricultor(self):
        await self.participantes()
        await self.abrir("M")
        server.estado["trigo"] = 200
        await self.construir("A")
        await self.construir("B")
        self.assertEqual(server.snapshot()["trabalhadores"], 2)
        self.assertEqual(server.estado["trigo"], 100)
        self.emit.reset_mock()
        await asyncio.gather(self.construir("A"), self.construir("B"))
        fatos = [c for c in self.emit.await_args_list if c.args[0] == "construcao.iniciada"]
        recusas = [c for c in self.emit.await_args_list if c.args[0] == "operacao.recusada"]
        self.assertEqual(len(fatos), 1)
        self.assertEqual(fatos[0].kwargs, {"to": None})
        self.assertEqual(len(recusas), 1)
        self.assertEqual(recusas[0].kwargs["to"], "B")
        self.assertEqual(recusas[0].args[1]["motivo"], "Sem agricultor livre")
        self.assertEqual(server.estado["trigo"], 50)
        self.assertEqual(server.snapshot()["trabalhadores"], 3)
        self.assertEqual(server.snapshot()["em_obra"], 3)


class ColheitasTests(unittest.IsolatedAsyncioTestCase):
    setUp = ServidorTests.setUp
    transmitir = ServidorTests.transmitir
    participantes = ServidorTests.participantes
    conferir_recusa = ServidorTests.conferir_recusa

    async def preparar(self):
        await self.participantes()
        server.estado['fase'] = 'aberta'
        self.relogio.return_value = 120
        await server.amadurecer_em(120)
        self.emit.reset_mock()
        return deepcopy(server.estado['colheita'])

    async def coletar(self, sid):
        await server.sio.handlers['/']['colheita.coleta_solicitada'](sid, {'valor': 999, 'recebido_em': 0})

    async def test_calendario_unicidade_e_snapshot_publico(self):
        prazos = []
        async def amadurecer(prazo):
            prazos.append(prazo)
            return len(prazos) < 3
        with patch.object(server, 'amadurecer_em', side_effect=amadurecer):
            await server.ciclo_colheitas(100)
        self.assertEqual(prazos, [120, 140, 160])
        await self.participantes()
        self.relogio.return_value = 120
        self.assertFalse(await server.amadurecer_em(120))
        self.emit.assert_not_awaited()
        server.estado['fase'] = 'aberta'
        await server.amadurecer_em(120)
        fato = self.emit.await_args.args[1]
        self.assertEqual(self.emit.await_args.args[0], 'colheita.amadurecida')
        self.assertEqual(self.emit.await_args.kwargs, {'to': None})
        self.assertEqual((fato['causa'], fato['valor'], fato['prazo']), ('temporizador', 30, 10))
        self.assertEqual(set(fato['estado']['colheita']), {'id', 'valor', 'amadurecida_em_ms', 'expira_em_ms'})
        self.assertEqual(fato['estado']['colheita']['expira_em_ms'], 1_030_000)
        self.assertEqual(fato['estado']['trigo'], 150)
        await server.amadurecer_em(120)
        self.assertEqual(self.emit.await_count, 1)
        await self.coletar('A')
        self.assertIsNotNone(fato['estado']['colheita'])
        self.relogio.return_value = 140
        await server.amadurecer_em(140)
        self.assertNotEqual(fato['colheita_id'], server.estado['colheita']['id'])

    async def test_amadurecimento_aguarda_20_segundos_fora_do_lock(self):
        await self.participantes()
        server.estado['fase'] = 'aberta'
        self.relogio.return_value = 119.999
        acordar = asyncio.Event()
        async def esperar(segundos):
            self.assertFalse(server.lock.locked())
            self.assertAlmostEqual(segundos, 0.001)
            await acordar.wait()
        with patch.object(server, 'esperar', side_effect=esperar):
            tarefa = asyncio.create_task(server.amadurecer_em(120))
            await asyncio.sleep(0)
            self.assertIsNone(server.estado['colheita'])
            self.emit.assert_not_awaited()
            self.relogio.return_value = 120
            acordar.set()
            await tarefa
        self.assertEqual(self.emit.await_args.args[0], 'colheita.amadurecida')
        self.assertEqual(server.estado['colheita']['expira_em'], 130)

    async def test_disputa_credito_unico_sem_agricultor_e_timer_antigo(self):
        colheita = await self.preparar()
        await asyncio.gather(self.coletar('A'), self.coletar('B'))
        fato, recusa = self.emit.await_args_list
        self.assertEqual(fato.args[0], 'colheita.coletada')
        self.assertEqual(fato.kwargs, {'to': None})
        self.assertEqual((fato.args[1]['quantidade'], fato.args[1]['colheita_id'], fato.args[1]['causa']), (30, colheita['id'], 'colheita.coleta_solicitada'))
        self.assertEqual(recusa.kwargs, {'to': 'B'})
        self.assertEqual(recusa.args[1]['motivo'], 'Não há colheita para coletar')
        self.assertEqual(server.estado['trigo'], 180)
        self.assertEqual(server.snapshot()['trabalhadores'], 0)
        self.assertIsNone(server.estado['colheita'])
        self.relogio.return_value = 140
        await server.amadurecer_em(140)
        anterior = server.snapshot()
        self.emit.reset_mock()
        await server.expirar_colheita(colheita['id'], 130)
        self.assertEqual(server.snapshot(), anterior)
        self.emit.assert_not_awaited()

    async def test_fronteira_estrita_timer_atrasado_e_expiracao_unica(self):
        for chegada in (129.999, 130, 130.001):
            with self.subTest(chegada=chegada):
                server.estado['colheita'] = None
                colheita = await self.preparar()
                anterior = server.snapshot()
                self.relogio.return_value = chegada
                await self.coletar('A')
                if chegada < 130:
                    self.assertEqual(server.estado['trigo'], anterior['trigo'] + 30)
                else:
                    self.conferir_recusa('A', 'Não há colheita para coletar', anterior, 'colheita.coleta_solicitada')
                self.emit.reset_mock()
                self.relogio.return_value = 131
                await server.expirar_colheita(colheita['id'], 130)
                await server.expirar_colheita(colheita['id'], 130)
                if chegada < 130:
                    self.emit.assert_not_awaited()
                else:
                    self.assertEqual(self.emit.await_count, 1)
                    fato = self.emit.await_args.args[1]
                    self.assertEqual(self.emit.await_args.args[0], 'colheita.estragada')
                    self.assertEqual(self.emit.await_args.kwargs, {'to': None})
                    self.assertEqual((fato['causa'], fato['gatilho'], fato['valor_perdido'], fato['colheita_id']), ('colheita.amadurecida', 'temporizador', 30, colheita['id']))
                    self.assertEqual(server.estado['trigo'], anterior['trigo'])

    async def test_fase_papel_e_ausencia_nessa_ordem(self):
        await self.participantes()
        for fase, sid, motivo in [('aguardando', 'M', 'A temporada não está aberta'), ('encerrada', 'A', 'A temporada não está aberta'), ('encerrada', 'M', 'A temporada não está aberta'), ('aberta', 'M', 'Só o Jogador pode coletar'), ('aberta', 'A', 'Não há colheita para coletar')]:
            with self.subTest(fase=fase, sid=sid):
                server.estado['fase'] = fase
                anterior = server.snapshot()
                self.emit.reset_mock()
                await self.coletar(sid)
                self.conferir_recusa(sid, motivo, anterior, 'colheita.coleta_solicitada')
        await self.preparar()
        anterior = server.snapshot()
        await self.coletar('M')
        self.conferir_recusa('M', 'Só o Jogador pode coletar', anterior, 'colheita.coleta_solicitada')

    async def test_chegada_antes_do_prazo_aguarda_lock_sem_perder_validade(self):
        colheita = await self.preparar()
        async with server.lock:
            self.relogio.return_value = 129.999
            a = asyncio.create_task(self.coletar('A'))
            b = asyncio.create_task(self.coletar('B'))
            await asyncio.sleep(0)
            self.relogio.return_value = 130
            timer = asyncio.create_task(server.expirar_colheita(colheita['id'], 130))
            await asyncio.sleep(0)
            self.emit.assert_not_awaited()
            self.relogio.return_value = 130.001
        await asyncio.gather(a, b, timer)
        self.assertEqual([c.args[0] for c in self.emit.await_args_list], ['colheita.coletada', 'operacao.recusada'])
        self.assertEqual(server.estado['trigo'], 180)

    async def test_expiracao_acorda_cedo_e_espera_fora_do_lock(self):
        colheita = await self.preparar()
        esperas = []
        async def esperar(segundos):
            self.assertFalse(server.lock.locked())
            esperas.append(segundos)
            self.relogio.return_value += min(segundos, 5)
        with patch.object(server, 'esperar', side_effect=esperar):
            await server.expirar_colheita(colheita['id'], 130)
        self.assertEqual(esperas, [10, 5])
        self.assertEqual(server.estado['trigo'], 150)
        self.assertIsNone(server.estado['colheita'])

    async def test_producao_e_perda_aos_30_sem_debito(self):
        await self.preparar()
        colheita = server.estado['colheita']
        for instante in range(105, 131, 5):
            self.relogio.return_value = instante
            await server.produzir_em(instante)
        await server.expirar_colheita(colheita['id'], 130)
        self.assertEqual((server.estado['trigo'], server.estado['farinha']), (210, 0))

    async def test_encerramento_preserva_colheita_e_cancela_atividades(self):
        colheita = await self.preparar()
        obra = server.criar_obra()
        server.estado['obras'].append(obra)
        async def esperar(segundos):
            await asyncio.Future()
        with patch.object(server, 'esperar', side_effect=esperar):
            for coro in (server.ciclo_colheitas(100), server.expirar_colheita(colheita['id'], 130), server.ciclo_producao(120), server.concluir_obra(obra['id'])):
                server.tarefas.add(asyncio.create_task(coro))
            await asyncio.sleep(0)
            await server.encerrar_vila('M')
            self.assertTrue(all(t.done() for t in server.tarefas))
        anterior = server.snapshot()
        self.assertEqual(anterior['colheita']['id'], colheita['id'])
        self.emit.reset_mock()
        self.relogio.return_value = 160
        await server.amadurecer_em(140)
        await server.expirar_colheita(colheita['id'], 130)
        await server.produzir_em(160)
        await server.concluir_obra(obra['id'])
        self.emit.assert_not_awaited()
        await server.connect('B2', {}, {'papel': 'jogador'})
        self.assertEqual(self.emit.await_args.args[1]['estado'], anterior)
        self.emit.reset_mock()
        await self.coletar('A')
        self.conferir_recusa('A', 'A temporada não está aberta', anterior, 'colheita.coleta_solicitada')

    async def test_encerramento_na_fila_antes_da_coleta_tem_prioridade(self):
        await self.preparar()
        async with server.lock:
            fim = asyncio.create_task(server.encerrar_vila('M'))
            await asyncio.sleep(0)
            coleta = asyncio.create_task(self.coletar('A'))
            await asyncio.sleep(0)
        await asyncio.gather(fim, coleta)
        self.assertEqual(server.estado['trigo'], 150)
        self.assertIsNotNone(server.estado['colheita'])
        self.assertEqual(self.emit.await_args.args[1]['motivo'], 'A temporada não está aberta')


if __name__ == "__main__":
    unittest.main()
