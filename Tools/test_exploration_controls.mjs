import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('../Web/wwwroot/exploration-controls.js', import.meta.url), 'utf8');
const { createHeldMovement } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const flush = async () => { await Promise.resolve(); await Promise.resolve(); };
function harness(stepOverride) {
  let enabled = true, next = 0;
  const timers = new Map(), calls = [];
  const controls = createHeldMovement({
    canMove: () => enabled,
    step: async (...direction) => { calls.push(direction); await stepOverride?.(); },
    setTimer: callback => { timers.set(++next, callback); return next; },
    clearTimer: id => timers.delete(id)
  });
  return { controls, calls, timers, disable: () => { enabled = false; },
    async advance() { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach(callback => callback()); await flush(); } };
}
{
  const h = harness();
  h.controls.press('w', 0, -1); await flush();
  await h.advance(); await h.advance();
  assert.deepEqual(h.calls, [[0, -1], [0, -1], [0, -1]]);
  h.controls.release('w'); await h.advance();
  assert.equal(h.calls.length, 3); assert.equal(h.timers.size, 0);
}
{
  let finish;
  const h = harness(() => new Promise(resolve => { finish = resolve; }));
  h.controls.press('w', 0, -1);
  h.controls.press('d', 1, 0);
  await h.advance(); await h.advance();
  assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0);
  h.controls.release('w'); h.controls.release('d');
  finish(); await flush(); await h.advance();
  assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0);
}
{
  const h = harness();
  h.controls.press('w', 0, -1); await flush();
  h.disable(); await h.advance(); await h.advance();
  assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0);
}
{
  const h = harness();
  h.controls.press('w', 0, -1); await flush();
  h.controls.press('d', 1, 0); await h.advance();
  h.controls.release('d'); await h.advance();
  assert.deepEqual(h.calls, [[0, -1], [1, 0], [0, -1]]);
  h.controls.dispose(); await h.advance(); assert.equal(h.calls.length, 3);
}
{
  let clock = 0, finish, scheduledDelay;
  const controls = createHeldMovement({canMove: () => true,
    now: () => clock, intervalMs: 150,
    step: () => new Promise(resolve => { finish = resolve; }),
    setTimer: (_callback, delay) => { scheduledDelay = delay; return 1; }, clearTimer: () => {}});
  controls.press('d', 1, 0); clock = 60; finish(); await flush();
  assert.equal(scheduledDelay, 90, 'Command time counts toward walking cadence');
  controls.dispose();
}
console.log('Exploration held movement tests passed');
