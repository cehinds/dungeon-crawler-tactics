/** Cardinal hold movement with one command in flight and no queued repeats. */
export function createHeldMovement({ canMove, step, intervalMs = 150,
  setTimer = setTimeout, clearTimer = clearTimeout }) {
  const held = new Map();
  let timer = null;
  let inFlight = false;
  let disposed = false;
  const clear = () => { if (timer !== null) clearTimer(timer); timer = null; };
  const stop = () => { held.clear(); clear(); };
  const tick = async () => {
    clear();
    if (disposed || inFlight || !held.size) return;
    if (!canMove()) { stop(); return; }
    const direction = [...held.values()].at(-1);
    inFlight = true;
    try { await step(...direction); }
    catch (error) { stop(); console.error('Exploration movement failed', error); }
    finally {
      inFlight = false;
      if (!disposed && held.size) timer = setTimer(tick, intervalMs);
    }
  };
  return {
    press(id, dx, dy) {
      if (disposed || held.has(id)) return;
      held.set(id, [dx, dy]);
      if (!inFlight && timer === null) void tick();
    },
    release(id) { held.delete(id); if (!held.size) clear(); },
    stop,
    dispose() { disposed = true; stop(); }
  };
}

const directions = {
  arrowup: [0, -1], w: [0, -1], arrowright: [1, 0], d: [1, 0],
  arrowdown: [0, 1], s: [0, 1], arrowleft: [-1, 0], a: [-1, 0],
  north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0]
};
const isEditable = target => Boolean(target?.closest?.('input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]'));
const isControl = target => Boolean(target?.closest?.(
  'input, textarea, select, button, a[href], [contenteditable]:not([contenteditable="false"]), [role="textbox"], [role="button"]'));

/** Attach once; delegated pointer handling survives map/HUD replacement. */
export function attachExplorationControls({ canMove, step, interact, focusMap, intervalMs = 150 }) {
  const movement = createHeldMovement({ canMove, step, intervalMs });
  const listeners = [];
  const listen = (target, type, handler) => {
    target.addEventListener(type, handler);
    listeners.push(() => target.removeEventListener(type, handler));
  };
  listen(document, 'keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || isEditable(event.target)) return;
    const key = event.key.toLowerCase();
    const direction = directions[key];
    if (!direction && (isControl(event.target) || key !== 'e' && key !== ' ')) return;
    // Native repeat must not inspect transient command-busy state mid-step.
    if (event.repeat) { event.preventDefault(); return; }
    if (!canMove()) { movement.stop(); return; }
    event.preventDefault();
    focusMap?.();
    if (direction) movement.press(`key:${key}`, ...direction);
    else { movement.stop(); void interact?.(); }
  });
  listen(document, 'keyup', event => movement.release(`key:${event.key.toLowerCase()}`));
  listen(window, 'blur', () => movement.stop());
  listen(document, 'visibilitychange', () => { if (document.hidden) movement.stop(); });
  listen(document, 'pointerdown', event => {
    const button = event.target?.closest?.('[data-walk]');
    const direction = directions[button?.dataset.walk];
    if (!direction || button.disabled || event.button !== 0 || !canMove()) return;
    event.preventDefault();
    focusMap?.();
    movement.press(`pointer:${event.pointerId}`, ...direction);
  });
  const releasePointer = event => movement.release(`pointer:${event.pointerId}`);
  listen(document, 'pointerup', releasePointer);
  listen(document, 'pointercancel', releasePointer);
  listen(document, 'click', event => {
    const button = event.target?.closest?.('[data-walk]');
    const direction = directions[button?.dataset.walk];
    if (event.detail !== 0 || !direction || button.disabled || !canMove()) return;
    event.preventDefault();
    focusMap?.();
    // Release immediately: keyboard/assistive activation requests one step.
    movement.press('activation', ...direction);
    movement.release('activation');
  });
  return { stop: movement.stop, dispose() { movement.dispose(); listeners.forEach(remove => remove()); } };
}
