// Feedback belongs to the currently active top layer, including native dialogs.
const entries = [];
const host = document.createElement('section');
host.className = 'toast-region';
host.setAttribute('aria-label', 'Notifications');
let nextId = 0;
export function syncFeedbackHost() {
  const dialogs = [...document.querySelectorAll('dialog[open]')];
  const parent = dialogs[dialogs.length - 1] ?? document.body;
  if (host.parentElement !== parent) parent.append(host);
}
function remove(entry) {
  clearTimeout(entry.timer);
  const hadFocus = entry.element.contains(document.activeElement);
  entry.element.remove();
  const index = entries.indexOf(entry);
  if (index >= 0) entries.splice(index, 1);
  if (hadFocus) (entries[0]?.element.querySelector('button') ?? entry.returnFocus)?.focus();
}
function pause(entry) {
  if (!entry.timer) return;
  clearTimeout(entry.timer);
  entry.timer = null;
  entry.remaining = Math.max(0, entry.remaining - (performance.now() - entry.started));
}
function resume(entry) {
  if (entry.hover || entry.element.contains(document.activeElement)) return;
  clearTimeout(entry.timer);
  entry.started = performance.now();
  entry.timer = setTimeout(() => remove(entry), entry.remaining);
}
export function notify(message, severity = 'info') {
  if (!message) return;
  syncFeedbackHost();
  const duplicate = entries.find(entry => entry.message === message && entry.severity === severity);
  if (duplicate) { duplicate.remaining = severity === 'error' ? 10000 : 6500; resume(duplicate); return; }
  while (entries.length >= 3) remove(entries[0]);
  const element = document.createElement('div');
  element.className = `game-toast toast-${severity}`;
  element.dataset.notificationId = String(++nextId);
  const icon = document.createElement('span');
  icon.className = 'toast-icon'; icon.setAttribute('aria-hidden', 'true');
  icon.textContent = {success:'✓',warning:'!',error:'×',info:'i'}[severity] ?? 'i';
  const text = document.createElement('span');
  text.className = 'toast-text';
  text.setAttribute('role', severity === 'error' ? 'alert' : 'status');
  text.setAttribute('aria-atomic', 'true');
  const close = document.createElement('button');
  close.className = 'toast-dismiss'; close.type = 'button'; close.textContent = '×';
  close.setAttribute('aria-label', 'Dismiss notification');
  element.append(icon, text, close);
  const entry = {element,message,severity,returnFocus:document.activeElement,remaining:severity === 'error' ? 10000 : 6500,timer:null,hover:false};
  entries.push(entry); host.append(element);
  // Populate after the live region exists so assistive technology announces the change.
  requestAnimationFrame(() => { text.textContent = message; });
  close.addEventListener('click', () => remove(entry));
  element.addEventListener('pointerenter', () => {entry.hover=true;pause(entry);});
  element.addEventListener('pointerleave', () => {entry.hover=false;resume(entry);});
  element.addEventListener('focusin', () => pause(entry));
  element.addEventListener('focusout', () => setTimeout(() => resume(entry), 0));
  resume(entry);
}
// Native Escape, imported saves, and rerendered drawers can all change the active dialog.
new MutationObserver(syncFeedbackHost).observe(document.body, {subtree:true,childList:true,attributes:true,attributeFilter:['open']});
