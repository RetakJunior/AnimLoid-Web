const form = document.querySelector('#search-form');
const input = document.querySelector('#search-input');
const provider = document.querySelector('#provider');
const results = document.querySelector('#results');
const status = document.querySelector('#status');
const resultsTitle = document.querySelector('#results-title');
const dialog = document.querySelector('#detail-dialog');
const detailContent = document.querySelector('#detail-content');

const fallbackCover = 'https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=900&q=80';

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;' }[char]));
}

function cardTemplate(anime) {
  const cover = anime.cover || fallbackCover;
  return `<article class="anime-card" data-id="${escapeHtml(anime.id)}" data-title="${escapeHtml(anime.title)}">
    <div class="poster-wrap"><img src="${escapeHtml(cover)}" alt="${escapeHtml(anime.title)} kapak görseli" loading="lazy" onerror="this.src='${fallbackCover}'" /><span class="provider-tag">${escapeHtml(anime.providerLabel || 'Provider')}</span></div>
    <div class="card-info"><h3>${escapeHtml(anime.title)}</h3><p>${escapeHtml(anime.type || 'anime')} ${anime.year ? `<span>/</span> ${escapeHtml(anime.year)}` : ''}</p></div>
  </article>`;
}

async function readApiResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('API sunucusu çalışmıyor. Live Server yerine terminalde “npm install” ve “npm run dev” komutlarını kullan.');
  }
  return response.json();
}

async function search(query) {
  status.className = 'status loading';
  status.textContent = 'Provider yanıtı bekleniyor...';
  results.innerHTML = '';
  resultsTitle.textContent = `“${query}” sonuçları`;
  try {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&provider=${provider.value}`);
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Arama başarısız.');
    if (!data.results.length) {
      status.className = 'status';
      status.textContent = 'Bu arama için sonuç bulunamadı.';
      return;
    }
    status.className = 'status result-count';
    status.textContent = `${data.results.length} anime bulundu · ${data.provider}${data.fallback ? ' · geçici katalog' : ''}`;
    results.innerHTML = data.results.map(cardTemplate).join('');
  } catch (error) {
    status.className = 'status error';
    status.textContent = error.message;
  }
}

async function showDetails(id, title) {
  detailContent.innerHTML = `<div class="detail-loading">${escapeHtml(title)} yükleniyor...</div>`;
  dialog.showModal();
  try {
    const response = await fetch(`/api/details?id=${encodeURIComponent(id)}&title=${encodeURIComponent(title)}`);
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Detaylar alınamadı.');
    const episodes = data.episodes.length ? data.episodes.map((episode) => `<a class="episode" href="${escapeHtml(episode.url || '#')}" ${episode.url ? 'target="_blank" rel="noreferrer"' : ''}><span>${String(episode.number).padStart(2, '0')}</span><b>${escapeHtml(episode.title)}</b><small>${episode.url ? 'İZLE ↗' : 'URL YOK'}</small></a>`).join('') : '<p class="empty-detail">Bu provider bölüm listesini şu anda paylaşmadı.</p>';
    detailContent.innerHTML = `<p class="eyebrow">${escapeHtml(data.provider)} / DETAIL</p><h2>${escapeHtml(data.title)}</h2><p class="detail-copy">Bölüm listesi ve provider bağlantıları.</p><div class="episodes">${episodes}</div>`;
  } catch (error) {
    detailContent.innerHTML = `<p class="eyebrow">HATA</p><h2>Detay alınamadı</h2><p class="detail-copy">${escapeHtml(error.message)}</p>`;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (query.length >= 2) search(query);
});

document.querySelectorAll('[data-query]').forEach((button) => button.addEventListener('click', () => {
  input.value = button.dataset.query;
  search(button.dataset.query);
}));

results.addEventListener('click', (event) => {
  const card = event.target.closest('.anime-card');
  if (card) showDetails(card.dataset.id, card.dataset.title);
});

document.querySelector('.close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
