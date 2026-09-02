const PROVIDERS = {
  animecix: {
    label: 'AnimeCix',
    async search(query) {
      const url = `https://animecix.tv/secure/search/${encodeURIComponent(query.replace(/ /g, '-'))}?type=&limit=24`;
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`AnimeCix ${response.status}`);
      const data = await response.json();
      return (data.results || []).map((item) => ({
        id: String(item.id || item._id),
        title: item.name || item.name_english || 'Untitled anime',
        year: item.year || item.release_date?.slice(0, 4) || null,
        type: item.title_type || item.type || 'anime',
        cover: item.poster || item.cover || null,
        description: item.description || '',
        provider: 'animecix',
        providerLabel: 'AnimeCix'
      })).filter((item) => item.id !== 'undefined');
    }
  },
  hianime: {
    label: 'HiAnime',
    async search(query) {
      const url = `https://hianime.to/search?keyword=${encodeURIComponent(query)}`;
      const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0', Accept: 'text/html' } });
      if (!response.ok) throw new Error(`HiAnime ${response.status}`);
      const html = await response.text();
      const results = [];
      const pattern = /<div class="flw-item">[\s\S]*?<a[^>]+href="\/watch\/([^?]+)[^"]*"[^>]*>[\s\S]*?<div class="film-poster">[\s\S]*?(?:data-src|src)="([^"]+)"[\s\S]*?<div class="film-name[\s\S]*?<a[^>]*>([^<]+)</g;
      for (const match of html.matchAll(pattern)) results.push({ id: match[1], cover: match[2], title: match[3].trim(), type: 'anime', provider: 'hianime', providerLabel: 'HiAnime' });
      return results;
    }
  },
  anizle: {
    label: 'Anizle',
    async search() {
      throw new Error('Anizle kataloğu şu anda erişim izni vermiyor. AnimeCix’i deneyin.');
    }
  }
};

async function animecixFallback(query, requestedProvider) {
  const url = `https://animecix.tv/secure/search/${encodeURIComponent(query.replace(/ /g, '-'))}?type=&limit=24`;
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`AnimeCix fallback ${response.status}`);
  const data = await response.json();
  return (data.results || []).map((item) => ({
    id: String(item.id || item._id),
    title: item.name || item.name_english || 'Untitled anime',
    year: item.year || item.release_date?.slice(0, 4) || null,
    type: item.title_type || item.type || 'anime',
    cover: item.poster || item.cover || null,
    description: item.description || '',
    provider: 'animecix',
    providerLabel: `AnimeCix fallback (${requestedProvider})`
  })).filter((item) => item.id !== 'undefined');
}

module.exports = async function handler(request, response) {
  const query = String(request.query.q || '').trim();
  const provider = String(request.query.provider || 'animecix');
  if (query.length < 2) return response.status(400).json({ error: 'En az 2 karakter yaz.' });
  const source = PROVIDERS[provider] || PROVIDERS.animecix;
  try {
    const results = await source.search(query);
    return response.status(200).json({ results, provider: source.label, fallback: false });
  } catch (error) {
    if (provider !== 'animecix') {
      try {
        const results = await animecixFallback(query, source.label);
        return response.status(200).json({
          results,
          provider: `AnimeCix fallback · ${source.label} yanıt vermedi`,
          fallback: true
        });
      } catch (fallbackError) {
        return response.status(502).json({ error: 'Kaynaklar şu an yanıt vermiyor.', detail: fallbackError.message });
      }
    }
    return response.status(502).json({ error: 'AnimeCix şu an yanıt vermiyor.', detail: error.message });
  }
};
