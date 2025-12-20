let searchTimeout;
const searchInput = document.getElementById('searchInput');
const packsGrid = document.getElementById('packsGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const modal = document.getElementById('modal');
const resultsCount = document.getElementById('resultsCount');

const packCardTemplate = document.getElementById('packCardTemplate');
const stickerItemTemplate = document.getElementById('stickerItemTemplate');

let currentPackName = null;

// Initial load
searchPacks('');

// Search on input
searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   searchTimeout = setTimeout(() => {
      searchPacks(e.target.value);
   }, 300);
});

// Event delegation for modal close and actions
document.addEventListener('click', async (e) => {
   const action = e.target.dataset.action;
   if (action === 'close-modal' || (e.target === modal)) {
      closeModal();
   } else if (action === 'export-packs') {
      await exportAllPacks();
   } else if (action === 'export-current-pack') {
      await exportCurrentPack();
   }
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

function createPackCard(pack) {
   const clone = packCardTemplate.content.cloneNode(true);
   const card = clone.querySelector('.pack-card');
   // Set text content
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   clone.querySelector('[data-field="last_update"]').textContent = formatDate(pack.last_update);
   // Set artist input
   const artistInput = clone.querySelector('[data-field="artist-input"]');
   artistInput.value = pack.artist || 'Unknown';
   artistInput.id = `artist-${pack.name}`;
   // Add event listeners
   clone.querySelector('[data-action="save-artist"]').addEventListener('click', () => {
      updateArtist(pack.name);
   });
   clone.querySelector('[data-action="view-stickers"]').addEventListener('click', () => {
      showPack(pack.name);
   });
   return clone;
}

function createStickerItem(packName, sticker, emoji) {
   const clone = stickerItemTemplate.content.cloneNode(true);
   const img = clone.querySelector('[data-field="image"]');
   const filePath = `/sticker_files/${encodeURIComponent(packName)}/${encodeURIComponent(sticker.file_path)}`;
   img.src = filePath;
   img.title = emoji || '';
   return clone;
}

async function searchPacks(query) {
   loading.style.display = 'block';
   packsGrid.style.display = 'none';
   emptyState.style.display = 'none';
   resultsCount.style.display = 'none';
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}`);
      const packs = await response.json();
      loading.style.display = 'none';
      if (packs.length === 0) {
         emptyState.style.display = 'block';
         return;
      }
      resultsCount.style.display = 'block';
      resultsCount.textContent = `Found ${packs.length} sticker pack${packs.length !== 1 ? 's' : ''}`;
      packsGrid.style.display = 'grid';
      packsGrid.innerHTML = '';
      packs.forEach(pack => {
         packsGrid.appendChild(createPackCard(pack));
      });
   } catch (error) {
      console.error('Error searching packs:', error);
      loading.style.display = 'none';
      emptyState.style.display = 'block';
   }
}

async function showPack(packName) {
   currentPackName = packName;
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}`);
      const pack = await response.json();
      document.getElementById('modalTitle').textContent = pack.title;
      document.getElementById('modalSubtitle').textContent = `${pack.name} • ${pack.artist}`;
      const modalStickers = document.getElementById('modalStickers');
      modalStickers.innerHTML = '';
      pack.stickers.forEach(sticker => {
         modalStickers.appendChild(createStickerItem(packName, sticker, sticker.emoji));
      });
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
         body: JSON.stringify({ artist })
      });
      if (response.ok) {
         input.style.borderColor = 'var(--success)';
         setTimeout(() => {
            input.style.borderColor = '';
         }, 1000);
      }
   } catch (error) {
      console.error('Error updating artist:', error);
      alert('Failed to update artist');
   }
}

async function exportAllPacks() {
   try {
      const response = await fetch('/api/export/packs');
      if (response.ok) {
         const blob = await response.blob();
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement('a');
         a.href = url;
         a.download = 'sticker_packs.json';
         document.body.appendChild(a);
         a.click();
         window.URL.revokeObjectURL(url);
         document.body.removeChild(a);
      } else {
         alert('Failed to export packs');
      }
   } catch (error) {
      console.error('Error exporting packs:', error);
      alert('Failed to export packs');
   }
}

async function exportCurrentPack() {
   if (!currentPackName) return;
   try {
      const response = await fetch(`/api/export/pack/${encodeURIComponent(currentPackName)}`);
      if (response.ok) {
         const blob = await response.blob();
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement('a');
         a.href = url;
         a.download = `${currentPackName}_stickers.json`;
         document.body.appendChild(a);
         a.click();
         window.URL.revokeObjectURL(url);
         document.body.removeChild(a);
      } else {
         alert('Failed to export pack');
      }
   } catch (error) {
      console.error('Error exporting pack:', error);
      alert('Failed to export pack');
   }
}

function closeModal() {
   modal.classList.remove('active');
   currentPackName = null;
}
