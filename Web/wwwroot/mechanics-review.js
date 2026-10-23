const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
try {
  const response = await fetch('mechanics-review.json');
  if (!response.ok) throw new Error('Review data could not be loaded.');
  const review = await response.json();
  document.querySelector('#summary').textContent = review.summary;
  document.querySelector('#gallery').innerHTML = review.art.map(art => `<figure><a href="${escape(art.file)}" target="_blank" rel="noopener" aria-label="Open ${escape(art.title)} concept at full resolution"><img src="${escape(art.file)}" alt="${escape(art.title)} concept sheet" loading="lazy" decoding="async"></a><figcaption><strong>${escape(art.title)}</strong>${escape(art.caption)}</figcaption></figure>`).join('');
  const items = review.groups.flatMap(group => group.items);
  document.querySelector('#counts').textContent = `${items.filter(item=>item.done).length} implemented · ${items.filter(item=>!item.done).length} planned. Checked boxes reflect the current browser build, not the concept illustrations.`;
  document.querySelector('#features').innerHTML = review.groups.map(group => `<section class="feature-group"><h3>${escape(group.title)}</h3>${group.items.map(item=>`<div class="feature" data-status="${item.done?'done':'planned'}"><input type="checkbox" ${item.done?'checked':''} disabled aria-label="${escape(item.title)} — ${item.done?'implemented':'planned'}"><div><strong>${escape(item.title)}</strong><p>${escape(item.detail)}</p></div><span class="status ${item.done?'done':'planned'}">${item.done?'IMPLEMENTED':'PLANNED'}</span></div>`).join('')}</section>`).join('');
  document.querySelector('#source-list').innerHTML = review.sources.map(source=>`<li><a href="${escape(source.url)}">${escape(source.title)}</a></li>`).join('');
  document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-filter]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
    document.querySelectorAll('.feature').forEach(item=>item.hidden=button.dataset.filter!=='all'&&item.dataset.status!==button.dataset.filter);
    document.querySelectorAll('.feature-group').forEach(group=>group.hidden=!group.querySelector('.feature:not([hidden])'));
  }));
} catch(error) {
  document.querySelector('#summary').textContent = `${error.message} The downloadable checklist remains available.`;
}
