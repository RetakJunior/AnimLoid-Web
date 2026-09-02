const form = document.querySelector('#search-form');
const input = document.querySelector('#search-input');
const provider = document.querySelector('#provider');
const results = document.querySelector('#results');
const status = document.querySelector('#status');
const resultsTitle = document.querySelector('#results-title');
const dialog = document.querySelector('#detail-dialog');
const detailContent = document.querySelector('#detail-content');
const historyKey = 'animloid-watch-history';
const recommendationData = [{ title: 'Attack on Titan', query: 'Attack on Titan' }, { title: 'Jujutsu Kaisen', query: 'Jujutsu Kaisen' }, { title: 'Demon Slayer', query: 'Demon Slayer' }, { title: 'Vinland Saga', query: 'Vinland Saga' }];

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

function getHistory() {
  try { return JSON.parse(localStorage.getItem(historyKey) || '[]'); } catch { return []; }
}

function saveHistory(history) { localStorage.setItem(historyKey, JSON.stringify(history.slice(0, 100))); renderProfile(); }

function trackEpisode(anime, episode) {
  const history = getHistory();
  const item = { animeId: anime.id, title: anime.title, cover: anime.cover || fallbackCover, episode: episode.number, episodeTitle: episode.title || `Bölüm ${episode.number}`, minutes: 24, watchedAt: Date.now() };
  const existing = history.findIndex((entry) => entry.animeId === item.animeId && entry.episode === item.episode);
  if (existing >= 0) history.splice(existing, 1);
  history.unshift(item);
  saveHistory(history);
}

function watchTemplate(anime, episodes, index, stream) {
    const episode = episodes[index];
    const previous = index > 0 ? `<button class="watch-nav" data-watch-index="${index - 1}">← Önceki</button>` : '<span></span>';
    const next = index < episodes.length - 1 ? `<button class="watch-nav next" data-watch-index="${index + 1}">Sonraki →</button>` : '<span></span>';
    trackEpisode(anime, episode);
    const playerUrl = stream?.url || episode.url;
    const directVideo = playerUrl && /\.(mp4|m3u8)(\?|$)/i.test(playerUrl);
    const player = playerUrl ? (directVideo ? `<video class="video-player" controls autoplay playsinline src="${escapeHtml(playerUrl)}"></video>` : `<iframe class="video-frame" src="${escapeHtml(playerUrl)}" title="${escapeHtml(episode.title || 'Anime bölümü')}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>`) : `<div class="player-mark">A</div><strong>${escapeHtml(episode.title || `Bölüm ${episode.number}`)}</strong><small>Bu provider oynatıcı bağlantısı döndürmedi</small>`;
    return `<div class="watch-layout"><section class="watch-main"><p class="eyebrow">${escapeHtml(anime.title)} / İZLE</p><div class="player-stage">${player}</div><div class="watch-controls">${previous}<span>${String(episode.number).padStart(2, '0')} / ${String(episodes.length).padStart(2, '0')}</span>${next}</div></section><aside class="episode-sidebar"><p class="eyebrow">BÖLÜMLER</p><div class="watch-episodes">${episodes.map((item, itemIndex) => `<button class="watch-episode ${itemIndex === index ? 'active' : ''}" data-watch-index="${itemIndex}"><span>${String(item.number).padStart(2, '0')}</span><b>${escapeHtml(item.title || `Bölüm ${item.number}`)}</b></button>`).join('')}</div></aside></div>`;
}

async function openWatch(anime, episodes, index) {
  detailContent.innerHTML = '<div class="detail-loading">Video akışı aranıyor...</div>';
  let stream = null;
  try {
    const episode = episodes[index];
    const response = await fetch(`/api/provider?action=streams&id=${encodeURIComponent(anime.id)}&episode=${encodeURIComponent(episode.id)}&provider=${provider.value}`);
    const data = await readApiResponse(response);
    stream = data.streams?.[0] || null;
  } catch { stream = null; }
  detailContent.innerHTML = watchTemplate(anime, episodes, index, stream);
}

function renderProfile() {
  const history = getHistory();
  const series = [...new Map(history.map((item) => [item.animeId, item])).values()];
  document.querySelector('#watched-episodes').textContent = history.length;
  document.querySelector('#watched-hours').textContent = (history.length * 24 / 60).toFixed(1);
  document.querySelector('#watched-series').textContent = series.length;
  const recent = document.querySelector('#recent-watch');
  const latest = history[0];
  recent.innerHTML = latest ? `<button class="recent-card" data-query="${escapeHtml(latest.title)}"><img src="${escapeHtml(latest.cover)}" alt="" /><span><b>${escapeHtml(latest.title)}</b><small>${escapeHtml(latest.episodeTitle)} · devam et ↗</small></span></button>` : '<p class="profile-empty">Henüz bölüm izlenmedi.</p>';
  const watchedList = document.querySelector('#watched-list');
  watchedList.innerHTML = series.length ? series.slice(0, 5).map((item) => `<button class="watched-item" data-query="${escapeHtml(item.title)}"><span>${escapeHtml(item.title)}</span><small>${history.filter((entry) => entry.animeId === item.animeId).length} bölüm</small></button>`).join('') : '<p class="profile-empty">İzleme geçmişin burada görünecek.</p>';
  document.querySelector('#recommendations-list').innerHTML = recommendationData.map((item) => `<button class="recommendation" data-query="${escapeHtml(item.query)}">${escapeHtml(item.title)} <span>↗</span></button>`).join('');
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
    const response = await fetch(`/api/provider?action=search&q=${encodeURIComponent(query)}&provider=${provider.value}`);
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
    const response = await fetch(`/api/provider?action=details&id=${encodeURIComponent(id)}&provider=${provider.value}`);
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Detaylar alınamadı.');
    const details = data.details;
    const anime = { id, title: details.title, cover: details.cover };
    const episodes = details.episodes.length ? details.episodes.map((episode, index) => `<button class="episode" data-watch-index="${index}" data-episode="${escapeHtml(JSON.stringify(episode))}" data-anime="${escapeHtml(JSON.stringify(anime))}"><span>${String(episode.number).padStart(2, '0')}</span><b>${escapeHtml(episode.title || `Bölüm ${episode.number}`)}</b><small>İZLE ↗</small></button>`).join('') : '<p class="empty-detail">Bu provider bölüm listesini şu anda paylaşmadı.</p>';
    detailContent.innerHTML = `<p class="eyebrow">${escapeHtml(data.provider)} / DETAIL</p><h2>${escapeHtml(details.title)}</h2><p class="detail-copy">${escapeHtml(details.description || 'Bölüm listesi ve provider bağlantıları.')}</p><div class="episodes">${episodes}</div>`;
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

detailContent.addEventListener('click', (event) => {
  const episode = event.target.closest('.episode');
  if (!episode) return;
  event.preventDefault();
  const anime = JSON.parse(episode.dataset.anime);
  const episodeList = [...detailContent.querySelectorAll('.episode')].map((item) => JSON.parse(item.dataset.episode));
  openWatch(anime, episodeList, Number(episode.dataset.watchIndex));
});

detailContent.addEventListener('click', (event) => {
  const navigation = event.target.closest('[data-watch-index]');
  if (!navigation || navigation.classList.contains('episode')) return;
  const current = detailContent.querySelector('.watch-episode.active');
  const episodes = [...detailContent.querySelectorAll('.watch-episode')].map((item) => ({ number: Number(item.querySelector('span').textContent), title: item.querySelector('b').textContent }));
  if (current) openWatch({ title: detailContent.querySelector('.watch-main .eyebrow').textContent.split(' / ')[0] }, episodes, Number(navigation.dataset.watchIndex));
});

document.addEventListener('click', (event) => {
  const queryButton = event.target.closest('[data-query]');
  if (!queryButton || queryButton.closest('.quick-searches')) return;
  event.preventDefault();
  input.value = queryButton.dataset.query;
  search(queryButton.dataset.query);
  window.scrollTo({ top: document.querySelector('.results-section').offsetTop, behavior: 'smooth' });
});

document.querySelector('#clear-history').addEventListener('click', () => { localStorage.removeItem(historyKey); renderProfile(); });
renderProfile();

document.querySelector('.close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
