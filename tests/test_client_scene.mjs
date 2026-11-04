// Regressão da cena real do HTML; somente relógio e primitivas gráficas são dublês.
// Executar: node --test tests/test_client_scene.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const html = readFileSync(new URL('../client/index.html', import.meta.url), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(source => source.includes('function criarJogo()'));
assert.ok(script, 'Executar a implementação da cena, sem copiar sua lógica');

function cliente() {
  let tempo = 0;
  let cena;
  const objetos = new Set();
  function desenho() {
    const objeto = {
      scaleX: 1,
      setOrigin() { return this; }, setDepth() { return this; },
      setPosition(x, y) { this.x = x; this.y = y; return this; },
      setFrame(frame) { this.frame = frame; return this; },
      setText(text) { this.text = text; return this; },
      destroy() { objetos.delete(this); },
    };
    objetos.add(objeto);
    return objeto;
  }
  class Scene {
    constructor() {
      this.add = { sprite: desenho, rectangle: desenho, text: desenho };
      this.cameras = { main: { setZoom() { return this; }, centerOn() {} } };
      this.make = { tilemap: () => ({
        widthInPixels: 288, heightInPixels: 144,
        addTilesetImage() {}, createLayer: desenho,
        getObjectLayer: () => ({ objects: [
          { name: 'lote1', x: 10, y: 10 }, { name: 'acampamento', x: 20, y: 20 },
        ] }),
      }) };
    }
  }
  const contexto = {
    performance: { now: () => tempo },
    Phaser: {
      Scene, AUTO: 0, Math: { Clamp: (value, min, max) => Math.max(min, Math.min(max, value)) },
      Game: class { constructor(config) { cena = new config.scene(); cena.create(); } },
    },
  };
  runInNewContext(script, contexto);
  const jogo = contexto.criarJogo();
  return { jogo, get cena() { return cena; }, objetos,
    avancar(ms) { tempo += ms; cena.update(); },
    progresso() { return cena.barras.get(1).barra.scaleX; },
  };
}

const obra = Object.freeze({ id: 1, status: 'em_andamento',
  iniciada_em_ms: 1000, concluir_em_ms: 9000, concluida_em_ms: null });
function estado(fase = 'encerrada', fim = 5000) {
  return Object.freeze({ fase, encerrada_em_ms: fim, trigo: 100, farinha: 0,
    trabalhadores: 1, obras: Object.freeze([obra]) });
}
function sincronizar(c, snapshot, recebido = 30000) {
  c.jogo.mostrarEstado(snapshot, recebido);
  if (snapshot.fase === 'encerrada') c.jogo.vilaEncerrada();
}

test('cliente presente calcula 50% no encerramento, mesmo com entrega atrasada', () => {
  const c = cliente(); c.jogo.iniciar('jogo');
  sincronizar(c, estado('aberta', null), 1000);
  c.avancar(2000); assert.equal(c.progresso(), 0.25);
  const final = estado(); const antes = JSON.stringify(final);
  sincronizar(c, final, 30000);
  assert.equal(c.progresso(), 0.5);
  c.avancar(60000); assert.equal(c.progresso(), 0.5);
  assert.equal(JSON.stringify(final), antes);
  assert.equal(c.cena.registros.get(1).frame, 1, 'obra continua como canteiro');
});

test('recarga e entrada tardia reconciliam 50%, inclusive pela fila anterior à criação', () => {
  for (const antesDaCena of [false, true]) {
    const c = cliente();
    if (!antesDaCena) c.jogo.iniciar('jogo');
    sincronizar(c, estado(), 60000);
    if (antesDaCena) c.jogo.iniciar('jogo');
    assert.equal(c.progresso(), 0.5);
    c.avancar(60000); assert.equal(c.progresso(), 0.5);
  }
});

test('reconexão corrige progresso local e sincronizações repetidas não duplicam objetos', () => {
  const c = cliente(); c.jogo.iniciar('jogo');
  sincronizar(c, estado('aberta', null), 1000);
  c.avancar(20000); assert.equal(c.progresso(), 1);
  sincronizar(c, estado()); assert.equal(c.progresso(), 0.5);
  const quantidade = c.objetos.size;
  const barra = c.cena.barras.get(1).barra;
  const canteiro = c.cena.registros.get(1);
  for (let i = 0; i < 3; i++) {
    sincronizar(c, estado(), 90000 + i * 1000);
    c.avancar(10000);
    assert.equal(c.progresso(), 0.5);
    assert.equal(c.objetos.size, quantidade);
    assert.equal(c.cena.barras.get(1).barra, barra);
    assert.equal(c.cena.registros.get(1), canteiro);
  }
});

test('progresso encerrado respeita limites zero e um sem alterar a obra', () => {
  for (const [fim, esperado] of [[0, 0], [1000, 0], [9000, 1], [12000, 1]]) {
    const c = cliente(); c.jogo.iniciar('jogo');
    sincronizar(c, estado('encerrada', fim));
    assert.equal(c.progresso(), esperado);
    assert.equal(c.cena.registros.get(1).frame, 1);
  }
});
