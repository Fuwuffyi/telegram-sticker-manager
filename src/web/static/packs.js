let searchTimeout;
const searchInput = document.getElementById('searchInput');
const packsGrid = document.getElementById('packsGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const modal = document.getElementById('modal');

// Initial load
searchPacks('');

// Search on input
searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   searchTimeout = setTimeout(() => {
      searchPacks(e.target.value);
   }, 300);
});

function formatDate(timestamp) {
   const date = new Date(timestamp * 1000);
   return date.toLocaleDateString();
}

function escapeHtml(text) {
   const div = document.createElement('div');
   div.textContent = text;
   return div.innerHTML;
}

async function searchPacks(query) {
   loading.style.display = 'block';
   packsGrid.style.display = 'none';
   emptyState.style.display = 'none';
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}`);
      const packs = await response.json();
      loading.style.display = 'none';
      if (packs.length === 0) {
         emptyState.style.display = 'block';
         return;
      }
      packsGrid.style.display = 'grid';
      packsGrid.innerHTML = packs.map(pack => `
            <div class="pack-card">
                <div class="pack-header">
                    <div class="pack-title">${escapeHtml(pack.title)}</div>
                    <div class="pack-name">${escapeHtml(pack.name)}</div>
                </div>
                <div class="pack-info">
                    <span>${pack.sticker_count} stickers</span>
                    <span>${formatDate(pack.last_update)}</span>
                </div>
                <div class="pack-artist">
                    <input
                        type="text"
                        class="artist-input"
                        value="${escapeHtml(pack.artist || 'Unknown')}"
                        id="artist-${escapeHtml(pack.name)}"
                    >
                    <button class="artist-save" onclick="updateArtist('${escapeHtml(pack.name)}')">Save</button>
                </div>
                <div class="pack-actions">
                    <button class="btn btn-primary" onclick="showPack('${escapeHtml(pack.name)}')">
                        View Stickers
                    </button>
                </div>
            </div>
        `)
         .join('');
   } catch (error) {
      console.error('Error searching packs:', error);
      loading.style.display = 'none';
      emptyState.style.display = 'block';
   }
}

async function showPack(packName) {
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}`);
      const pack = await response.json();
      document.getElementById('modalTitle')
         .textContent = pack.title;
      document.getElementById('modalSubtitle')
         .textContent = `${pack.name} • ${pack.artist}`;
      const stickersHtml = pack.stickers.map(sticker => {
            const filePath = `/sticker_files/${encodeURIComponent(packName)}/${encodeURIComponent(sticker.file_path)}`;
            return `
                <div class="sticker-item" title="${escapeHtml(sticker.emoji || '')}">
                    <img src="${filePath}" alt="Sticker" loading="lazy">
                </div>
            `;
         })
         .join('');
      document.getElementById('modalStickers')
         .innerHTML = stickersHtml;
      modal.classList.add('active');
   } catch (error) {
      console.error('Error loading pack:', error);
      alert('Failed to load pack stickers');
   }
}

async function updateArtist(packName) {
   const input = document.getElementById(`artist-${packName}`);
   const artist = input.value.trim() || 'Unknown';
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}/artist`, {
         method: 'POST',
         headers: {
            'Content-Type': 'application/json'
         },
         body: JSON.stringify({
            artist
         })
      });
      if (response.ok) {
         input.style.borderColor = '#4caf50';
         setTimeout(() => {
            input.style.borderColor = '#e0e0e0';
         }, 1000);
      }
   } catch (error) {
      console.error('Error updating artist:', error);
      alert('Failed to update artist');
   }
}

function closeModal() {
   modal.classList.remove('active');
}

// Close modal on outside click
modal.addEventListener('click', (e) => {
   if (e.target === modal) {
      closeModal();
   }
});
