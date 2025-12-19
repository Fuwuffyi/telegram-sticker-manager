let searchTimeout;
const searchInput = document.getElementById('searchInput');
const stickersGrid = document.getElementById('stickersGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const resultsCount = document.getElementById('resultsCount');

// Initial load
searchStickers('');

// Search on input
searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   searchTimeout = setTimeout(() => {
      searchStickers(e.target.value);
   }, 300);
});

function escapeHtml(text) {
   const div = document.createElement('div');
   div.textContent = text;
   return div.innerHTML;
}

async function searchStickers(query) {
   loading.style.display = 'block';
   stickersGrid.style.display = 'none';
   emptyState.style.display = 'none';
   resultsCount.style.display = 'none';
   try {
      const response = await fetch(`/api/stickers/search?q=${encodeURIComponent(query)}`);
      const stickers = await response.json();
      loading.style.display = 'none';
      if (stickers.length === 0) {
         emptyState.style.display = 'block';
         return;
      }
      resultsCount.style.display = 'block';
      resultsCount.textContent = `Found ${stickers.length} sticker${stickers.length !== 1 ? 's' : ''}`;
      stickersGrid.style.display = 'grid';
      stickersGrid.innerHTML = stickers.map(item => {
            const filePath = `/sticker_files/${encodeURIComponent(item.pack_name)}/${encodeURIComponent(item.sticker.file_path)}`;
            return `
                <div class="sticker-card">
                    <div class="sticker-preview">
                        <img src="${filePath}" alt="Sticker" loading="lazy">
                    </div>
                    <div class="sticker-info">
                        ${item.emoji ? `<div class="sticker-emoji">${escapeHtml(item.emoji)}</div>` : ''}
                        <div class="sticker-pack-name" title="${escapeHtml(item.pack_title)}">
                            ${escapeHtml(item.pack_title)}
                        </div>
                        <div class="sticker-artist" title="${escapeHtml(item.artist)}">
                            ${escapeHtml(item.artist)}
                        </div>
                    </div>
                </div>
            `;
         })
         .join('');
   } catch (error) {
      console.error('Error searching stickers:', error);
      loading.style.display = 'none';
      emptyState.style.display = 'block';
   }
}
