module.exports = async function handler(request, response) {
  const id = String(request.query.id || '').trim();
  const title = String(request.query.title || 'Anime').trim();
  if (!id) return response.status(400).json({ error: 'Anime kimliği eksik.' });

  try {
    const url = `https://animecix.tv/secure/related-videos?episode=1&season=1&titleId=${encodeURIComponent(id)}&videoId=637113`;
    const upstream = await fetch(url, { headers: { Accept: 'application/json' } });
    const data = upstream.ok ? await upstream.json() : { videos: [] };
    const videos = Array.isArray(data.videos) ? data.videos : [];
    const episodes = videos.map((video, index) => ({
      id: video.url || video.id || `${id}-${index + 1}`,
      number: Number(video.episode || video.number || index + 1),
      title: video.name || `Bölüm ${index + 1}`,
      url: video.url || null
    }));
    return response.status(200).json({ id, title, episodes, provider: 'AnimeCix' });
  } catch (error) {
    return response.status(502).json({ error: 'Bölümler alınamadı.', detail: error.message });
  }
};
