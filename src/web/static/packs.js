let searchTimeout;
const searchInput = document.getElementById('searchInput');
const packsGrid = document.getElementById('packsGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const modal = document.getElementById('modal');
const resultsCount = document.getElementById('resultsCount');

const packCardTemplate = document.getElementById('packCardTemplate');
const thumbnailTemplate = document.getElementById('thumbnailTemplate');
const stickerItemTemplate = document.getElementById('stickerItemTemplate');
const loadMoreTemplate = document.getElementById('loadMoreTemplate');

let currentPackName = null;
let currentPage = 1;
let totalPages = 1;
let currentQuery = '';
let currentModalPage = 1;
let totalModalPages = 1;
let isLoadingMore = false;

searchPacks('');

searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   currentPage = 1;
   searchTimeout = setTimeout(() => searchPacks(e.target.value), 300);
});

window.addEventListener('scroll', () => {
   if (isLoadingMore || currentPage >= totalPages) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      isLoadingMore = true;
      currentPage++;
      searchPacks(currentQuery, true);
   }
});

document.addEventListener('click', async (e) => {
   const action = e.target.dataset.action;
   if (action === 'close-modal' || (e.target === modal)) {
      closeModal();
   } else if (action === 'export-packs') {
      await exportAllPacks();
   } else if (action === 'export-current-pack') {
      await exportCurrentPack();
   } else if (action === 'load-more-stickers') {
      await loadMoreStickers();
   }
});

function formatDate(timestamp) {
   return new Date(timestamp * 1000).toLocaleDateString();
}

function createPackCard(pack) {
   const clone = packCardTemplate.content.cloneNode(true);
   const card = clone.querySelector('.pack-card');
   // Handle badges
   const badgeContainer = clone.querySelector('[data-badge-container]');
   // Add custom pack badge if applicable
   if (pack.used_in_custom_packs) {
      const customBadge = document.createElement('div');
      customBadge.className = 'badge badge-custom';
      customBadge.innerHTML = '▴<span class="badge-tooltip">Used in Custom Packs</span>';
      badgeContainer.appendChild(customBadge);
   }
   // Add Signal badge
   if (pack.signal_url) {
      const signalBadge = document.createElement('a');
      signalBadge.className = pack.needs_signal_update ? 'badge badge-update' : 'badge badge-signal';
      signalBadge.href = pack.signal_url;
      signalBadge.target = '_blank';
      signalBadge.rel = 'noopener noreferrer';
      if (pack.needs_signal_update) {
         signalBadge.innerHTML = '✱<span class="badge-tooltip">Update Available on Signal</span>';
      } else {
         signalBadge.innerHTML = '✔<span class="badge-tooltip">On Signal</span>';
      }
      signalBadge.addEventListener('click', (e) => {
         e.stopPropagation();
      });
      badgeContainer.appendChild(signalBadge);
   }
   if (pack.thumbnails?.length) {
      const thumbnailContainer = clone.querySelector('.pack-thumbnail');
      pack.thumbnails.forEach(thumb => {
         const imgClone = thumbnailTemplate.content.cloneNode(true);
         const img = imgClone.querySelector('img');
         img.src = `/sticker_files/${encodeURIComponent(pack.name)}/${encodeURIComponent(thumb.file_path)}`;
         img.alt = thumb.emoji || '';
         thumbnailContainer.appendChild(imgClone);
      });
   }
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="link"]').href = `https://t.me/addstickers/${pack.name}`;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   clone.querySelector('[data-field="last_update"]').textContent = formatDate(pack.last_update);
   const artistInput = clone.querySelector('[data-field="artist-input"]');
   artistInput.value = pack.artist || 'Unknown';
   artistInput.id = `artist-${pack.name}`;
   clone.querySelector('[data-action="save-artist"]').addEventListener('click', () => updateArtist(pack.name));
   clone.querySelector('[data-action="view-stickers"]').addEventListener('click', () => showPack(pack.name));
   clone.querySelector('[data-action="delete-pack"]').addEventListener('click', async () => {
      if (confirm(`Delete pack "${pack.title}"? This will permanently delete all ${pack.sticker_count} stickers.`)) {
         await deletePack(pack.name);
      }
   });
   const signalBtn = clone.querySelector('[data-action="upload-signal"]');
   signalBtn.textContent = pack.signal_url ? 'Update Signal' : 'Upload to Signal';
   if (pack.needs_signal_update) {
      signalBtn.classList.add('needs-update');
   }
   signalBtn.addEventListener('click', () => uploadToSignal(pack.name));
   return clone;
}

function createStickerItem(packName, sticker) {
   const clone = stickerItemTemplate.content.cloneNode(true);
   const img = clone.querySelector('[data-field="image"]');
   img.src = `/sticker_files/${encodeURIComponent(packName)}/${encodeURIComponent(sticker.file_path)}`;
   img.title = sticker.emoji || '';
   return clone;
}

function createLoadMoreButton(current, total) {
   const clone = loadMoreTemplate.content.cloneNode(true);
   clone.querySelector('[data-field="text"]').textContent = `Load More (${current}/${total})`;
   return clone;
}

async function searchPacks(query, append = false) {
   currentQuery = query;
   if (!append) {
      loading.style.display = 'block';
      packsGrid.style.display = 'none';
      emptyState.style.display = 'none';
      resultsCount.style.display = 'none';
      currentPage = 1;
   }
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}&page=${currentPage}&per_page=50`);
      const data = await response.json();
      loading.style.display = 'none';
      isLoadingMore = false;
      totalPages = data.total_pages;
      if (data.packs.length === 0 && !append) {
         emptyState.style.display = 'block';
         return;
      }
      if (!append) {
         resultsCount.style.display = 'block';
         resultsCount.textContent = `Found ${data.total} sticker pack${data.total !== 1 ? 's' : ''}`;
         packsGrid.style.display = 'grid';
         packsGrid.innerHTML = '';
      }
      data.packs.forEach(pack => packsGrid.appendChild(createPackCard(pack)));
   } catch (error) {
      console.error('Error searching packs:', error);
      loading.style.display = 'none';
      isLoadingMore = false;
      if (!append) emptyState.style.display = 'block';
   }
}

async function showPack(packName) {
   currentPackName = packName;
   currentModalPage = 1;
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}?page=1&per_page=100`);
      const pack = await response.json();
      totalModalPages = pack.total_pages;
      document.getElementById('modalTitle').textContent = pack.title;
      document.getElementById('modalSubtitle').textContent = `${pack.name} • ${pack.artist}`;
      const modalStickers = document.getElementById('modalStickers');
      modalStickers.innerHTML = '';
      pack.stickers.forEach(sticker => modalStickers.appendChild(createStickerItem(packName, sticker)));
      if (totalModalPages > 1) {
         modalStickers.appendChild(createLoadMoreButton(currentModalPage, totalModalPages));
      }
      modal.classList.add('active');
   } catch (error) {
      console.error('Error loading pack:', error);
      alert('Failed to load pack stickers');
   }
}

async function loadMoreStickers() {
   if (!currentPackName || currentModalPage >= totalModalPages) return;
   currentModalPage++;
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(currentPackName)}?page=${currentModalPage}&per_page=100`);
      const pack = await response.json();
      const modalStickers = document.getElementById('modalStickers');
      const loadMoreBtn = modalStickers.querySelector('.load-more-btn');
      if (loadMoreBtn) loadMoreBtn.remove();
      pack.stickers.forEach(sticker => modalStickers.appendChild(createStickerItem(currentPackName, sticker)));
      if (currentModalPage < totalModalPages) {
         modalStickers.appendChild(createLoadMoreButton(currentModalPage, totalModalPages));
      }
   } catch (error) {
      console.error('Error loading more stickers:', error);
      alert('Failed to load more stickers');
   }
}

async function updateArtist(packName) {
   const input = document.getElementById(`artist-${packName}`);
   const artist = input.value.trim() || 'Unknown';
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}/artist`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ artist })
      });
      if (response.ok) {
         input.style.borderColor = 'var(--success)';
         setTimeout(() => input.style.borderColor = '', 1000);
      }
   } catch (error) {
      console.error('Error updating artist:', error);
      alert('Failed to update artist');
   }
}

async function uploadToSignal(packName) {
   if (!confirm('Upload this pack to Signal? This may take a few moments.')) {
      return;
   }
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}/upload-signal`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (response.ok) {
         alert(`Successfully uploaded to Signal!\n\nURL: ${data.signal_url}`);
         // Refresh the pack list to show updated status
         currentPage = 1;
         await searchPacks(currentQuery);
      } else {
         alert(`Failed to upload to Signal: ${data.error}`);
      }
   } catch (error) {
      console.error('Error uploading to Signal:', error);
      alert('Failed to upload to Signal');
   }
}

async function deletePack(packName) {
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}`, { method: 'DELETE' });
      if (response.ok) {
         currentPage = 1;
         await searchPacks(currentQuery);
      } else {
         const error = await response.json();
         alert(error.error || 'Failed to delete pack');
      }
   } catch (error) {
      console.error('Error deleting pack:', error);
      alert('Failed to delete pack');
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
   currentModalPage = 1;
   totalModalPages = 1;
}
