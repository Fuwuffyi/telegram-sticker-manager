let searchTimeout;
const searchInput = document.getElementById('searchInput');
const packsGrid = document.getElementById('packsGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const modal = document.getElementById('modal');
const resultsCount = document.getElementById('resultsCount');
const sortBy = document.getElementById('sortBy');
const filterSignal = document.getElementById('filterSignal');
const filterNeedsUpdate = document.getElementById('filterNeedsUpdate');
const filterCustomPacks = document.getElementById('filterCustomPacks');
const updateAllBtn = document.getElementById('updateAllPacksBtn');

if (updateAllBtn) {
   updateAllBtn.addEventListener('click', updateAllPacks);
}

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
let allPacks = [];
let currentSortBy = 'last_update_desc';

let currentFilters = {
   onSignal: 'disabled',
   needsUpdate: 'disabled',
   inCustomPacks: 'disabled'
};

searchPacks('');

searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   currentPage = 1;
   searchTimeout = setTimeout(() => searchPacks(e.target.value), 300);
});

sortBy.addEventListener('change', (e) => {
   currentSortBy = e.target.value;
   currentPage = 1;
   applyFiltersAndSort();
});

filterSignal.addEventListener('click', (e) => {
   e.preventDefault();
   cycleFilterState('onSignal', filterSignal);
});

filterNeedsUpdate.addEventListener('click', (e) => {
   e.preventDefault();
   cycleFilterState('needsUpdate', filterNeedsUpdate);
});

filterCustomPacks.addEventListener('click', (e) => {
   e.preventDefault();
   cycleFilterState('inCustomPacks', filterCustomPacks);
});

function cycleFilterState(filterKey, element) {
   const states = ['disabled', 'show', 'hide'];
   const currentIdx = states.indexOf(currentFilters[filterKey]);
   const nextIdx = (currentIdx + 1) % states.length;
   currentFilters[filterKey] = states[nextIdx];
   element.classList.remove('show', 'hide');
   if (states[nextIdx] === 'show') {
      element.classList.add('show');
   } else if (states[nextIdx] === 'hide') {
      element.classList.add('hide');
   }
   currentPage = 1;
   applyFiltersAndSort();
}

let displayedCount = 0;
const itemsPerBatch = 50;

window.addEventListener('scroll', () => {
   if (isLoadingMore) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      loadMorePacks();
   }
});

function loadMorePacks() {
   if (isLoadingMore) return;
   let filtered = filterPacks(allPacks, currentFilters);
   let sorted = sortPacks(filtered, currentSortBy);
   if (displayedCount >= sorted.length) return;
   isLoadingMore = true;
   const startIdx = displayedCount;
   const endIdx = Math.min(displayedCount + itemsPerBatch, sorted.length);
   const batch = sorted.slice(startIdx, endIdx);
   batch.forEach(pack => packsGrid.appendChild(createPackCard(pack)));
   displayedCount = endIdx;
   isLoadingMore = false;
}

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
   const badgeContainer = clone.querySelector('[data-badge-container]');
   if (pack.used_in_custom_packs) {
      const customBadge = document.createElement('div');
      customBadge.className = 'badge badge-custom';
      customBadge.innerHTML = '▴<span class="badge-tooltip">Used in Custom Packs</span>';
      badgeContainer.appendChild(customBadge);
   }
   if (pack.signal_url) {
      const signalBadge = document.createElement('a');
      signalBadge.className = pack.needs_signal_update ? 'badge badge-update' : 'badge badge-signal';
      signalBadge.href = pack.signal_url;
      signalBadge.target = '_blank';
      signalBadge.rel = 'noopener noreferrer';
      if (pack.needs_signal_update) {
         signalBadge.innerHTML = '✱<span class="badge-tooltip">Update Available on Signal</span>';
      } else {
         signalBadge.innerHTML = '✓<span class="badge-tooltip">On Signal</span>';
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
   artistInput.value = pack.artist || 'Unclassified';
   artistInput.id = `artist-${pack.name}`;
   clone.querySelector('[data-action="save-artist"]').addEventListener('click', () => updateArtist(pack.name));
   const actionsContainer = clone.querySelector('.pack-actions');
   actionsContainer.innerHTML = '';
   const firstRow = document.createElement('div');
   firstRow.className = 'pack-actions-row';
   const viewBtn = document.createElement('button');
   viewBtn.className = 'btn btn-primary';
   viewBtn.textContent = 'View Stickers';
   viewBtn.addEventListener('click', () => showPack(pack.name));
   firstRow.appendChild(viewBtn);
   const signalBtn = document.createElement('button');
   signalBtn.className = 'btn btn-signal';
   signalBtn.textContent = pack.signal_url ? 'Update Signal' : 'Signal Upload';
   if (pack.needs_signal_update) {
      signalBtn.classList.add('needs-update');
   }
   signalBtn.addEventListener('click', () => uploadToSignal(pack.name));
   firstRow.appendChild(signalBtn);
   actionsContainer.appendChild(firstRow);
   const secondRow = document.createElement('div');
   secondRow.className = 'pack-actions-row';
   const updateBtn = document.createElement('button');
   updateBtn.className = 'btn btn-warning';
   updateBtn.textContent = 'Update Pack';
   updateBtn.dataset.packName = pack.name;
   updateBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await updateSinglePack(pack.name, updateBtn);
   });
   secondRow.appendChild(updateBtn);
   const deleteBtn = document.createElement('button');
   deleteBtn.className = 'btn btn-danger';
   deleteBtn.textContent = 'Delete';
   deleteBtn.addEventListener('click', async () => {
      if (confirm(`Delete pack "${pack.title}"? This will permanently delete all ${pack.sticker_count} stickers.`)) {
         await deletePack(pack.name);
      }
   });
   secondRow.appendChild(deleteBtn);
   actionsContainer.appendChild(secondRow);
   return clone;
}

async function updateAllPacks() {
   if (!confirm('Update ALL sticker packs? This may take a long time.')) {
      return;
   }
   updateAllBtn.disabled = true;
   const originalText = updateAllBtn.textContent;
   updateAllBtn.textContent = 'Updating all…';
   try {
      const response = await fetch('/api/packs/update-all', {
         method: 'POST'
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
         throw new Error(data.error || 'Bulk update failed');
      }
      alert(
         `Update complete:\n` +
         `${data.updated} succeeded\n` +
         `${data.failed} failed`
      );
      await searchPacks(currentQuery);
   } catch (err) {
      console.error(err);
      alert(`Failed to update all packs:\n${err.message}`);
   } finally {
      updateAllBtn.disabled = false;
      updateAllBtn.textContent = originalText;
   }
}

async function updateSinglePack(packName, button) {
   if (!confirm(`Update sticker pack "${packName}"?`)) return;
   button.disabled = true;
   const originalText = button.textContent;
   button.textContent = 'Updating…';
   try {
      const response = await fetch(
         `/api/packs/${encodeURIComponent(packName)}/update`,
         { method: 'POST' }
      );
      const data = await response.json();
      if (!response.ok || !data.success) {
         throw new Error(data.error || 'Update failed');
      }
      await searchPacks(currentQuery);
   } catch (err) {
      console.error(err);
      alert(`Failed to update pack:\n${err.message}`);
   } finally {
      button.disabled = false;
      button.textContent = originalText;
   }
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

function sortPacks(packs, sortBy) {
   const sorted = [...packs];
   switch (sortBy) {
      case 'last_update_desc':
         sorted.sort((a, b) => b.last_update - a.last_update);
         break;
      case 'last_update_asc':
         sorted.sort((a, b) => a.last_update - b.last_update);
         break;
      case 'title_asc':
         sorted.sort((a, b) => a.title.localeCompare(b.title));
         break;
      case 'title_desc':
         sorted.sort((a, b) => b.title.localeCompare(a.title));
         break;
      case 'name_asc':
         sorted.sort((a, b) => a.name.localeCompare(b.name));
         break;
      case 'name_desc':
         sorted.sort((a, b) => b.name.localeCompare(a.name));
         break;
      case 'artist_asc':
         sorted.sort((a, b) => a.artist.localeCompare(b.artist));
         break;
      case 'artist_desc':
         sorted.sort((a, b) => b.artist.localeCompare(a.artist));
         break;
      case 'count_desc':
         sorted.sort((a, b) => b.sticker_count - a.sticker_count);
         break;
      case 'count_asc':
         sorted.sort((a, b) => a.sticker_count - b.sticker_count);
         break;
   }
   return sorted;
}

function filterPacks(packs, filters) {
   let filtered = [...packs];
   if (filters.onSignal === 'show') {
      filtered = filtered.filter(pack => pack.signal_url);
   } else if (filters.onSignal === 'hide') {
      filtered = filtered.filter(pack => !pack.signal_url);
   }
   if (filters.needsUpdate === 'show') {
      filtered = filtered.filter(pack => pack.needs_signal_update);
   } else if (filters.needsUpdate === 'hide') {
      filtered = filtered.filter(pack => !pack.needs_signal_update);
   }
   if (filters.inCustomPacks === 'show') {
      filtered = filtered.filter(pack => pack.used_in_custom_packs);
   } else if (filters.inCustomPacks === 'hide') {
      filtered = filtered.filter(pack => !pack.used_in_custom_packs);
   }
   return filtered;
}

function applyFiltersAndSort() {
   loading.style.display = 'block';
   packsGrid.style.display = 'none';
   emptyState.style.display = 'none';
   resultsCount.style.display = 'none';
   let filtered = filterPacks(allPacks, currentFilters);
   let sorted = sortPacks(filtered, currentSortBy);
   loading.style.display = 'none';
   if (sorted.length === 0) {
      emptyState.style.display = 'block';
      return;
   }
   resultsCount.style.display = 'block';
   resultsCount.textContent = `Found ${sorted.length} sticker pack${sorted.length !== 1 ? 's' : ''}`;
   packsGrid.style.display = 'grid';
   packsGrid.innerHTML = '';
   displayedCount = 0;
   const firstBatch = sorted.slice(0, Math.min(itemsPerBatch, sorted.length));
   firstBatch.forEach(pack => packsGrid.appendChild(createPackCard(pack)));
   displayedCount = firstBatch.length;
}

async function searchPacks(query) {
   currentQuery = query;
   loading.style.display = 'block';
   packsGrid.style.display = 'none';
   emptyState.style.display = 'none';
   resultsCount.style.display = 'none';
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      allPacks = data.packs.map(pack => ({
         ...pack,
         needs_signal_update: pack.signal_uploaded_at && pack.last_update > pack.signal_uploaded_at
      }));
      applyFiltersAndSort();
   } catch (error) {
      console.error('Error searching packs:', error);
      loading.style.display = 'none';
      emptyState.style.display = 'block';
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
   const artist = input.value.trim() || 'Unclassified';
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}/artist`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ artist })
      });
      if (response.ok) {
         input.style.borderColor = 'var(--success)';
         setTimeout(() => input.style.borderColor = '', 1000);
         const pack = allPacks.find(p => p.name === packName);
         if (pack) pack.artist = artist;
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
