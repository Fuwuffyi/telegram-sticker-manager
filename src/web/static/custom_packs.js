const loading = document.getElementById('loading');
const customPacksGrid = document.getElementById('customPacksGrid');
const emptyState = document.getElementById('emptyState');
const resultsCount = document.getElementById('resultsCount');
const createModal = document.getElementById('createModal');
const editModal = document.getElementById('editModal');
const sortBy = document.getElementById('sortBy');
const filterSignalCheck = document.getElementById('filterSignalCheck');
const filterNeedsUpdateCheck = document.getElementById('filterNeedsUpdateCheck');

const customPackCardTemplate = document.getElementById('customPackCardTemplate');
const editableStickerTemplate = document.getElementById('editableStickerTemplate');
const selectableStickerTemplate = document.getElementById('selectableStickerTemplate');
const selectablePackTemplate = document.getElementById('selectablePackTemplate');
const loadMoreTemplate = document.getElementById('loadMoreTemplate');
const loadingTemplate = document.getElementById('loadingTemplate');

let currentEditingPack = null;
let currentPackStickers = [];
let selectedStickersToAdd = new Set();
let selectedPacksToAdd = new Set();

let searchTimeout;
let currentPage = 1;
let totalPages = 1;
let isLoadingMore = false;

let stickerSearchPage = 1;
let stickerSearchTotal = 1;
let packSearchPage = 1;
let packSearchTotal = 1;

let allPacks = [];
let currentSortBy = 'name_asc';
let currentFilters = {
   onSignal: false,
   needsUpdate: false
};

loadCustomPacks();

sortBy.addEventListener('change', (e) => {
   currentSortBy = e.target.value;
   currentPage = 1;
   applyFiltersAndSort();
});

filterSignalCheck.addEventListener('change', (e) => {
   currentFilters.onSignal = e.target.checked;
   document.getElementById('filterSignal').classList.toggle('active', e.target.checked);
   currentPage = 1;
   applyFiltersAndSort();
});

filterNeedsUpdateCheck.addEventListener('change', (e) => {
   currentFilters.needsUpdate = e.target.checked;
   document.getElementById('filterNeedsUpdate').classList.toggle('active', e.target.checked);
   currentPage = 1;
   applyFiltersAndSort();
});

window.addEventListener('scroll', () => {
   if (isLoadingMore || currentPage >= totalPages) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      isLoadingMore = true;
      currentPage++;
      applyFiltersAndSort(true);
   }
});

document.addEventListener('click', async (e) => {
   const action = e.target.dataset.action;
   if (action === 'create-pack') {
      openCreateModal();
   } else if (action === 'close-create-modal' || (e.target === createModal)) {
      closeCreateModal();
   } else if (action === 'save-new-pack') {
      await createNewPack();
   } else if (action === 'close-edit-modal') {
      closeEditModal();
   } else if (action === 'save-pack-changes') {
      await savePackChanges();
   } else if (action === 'export-custom-packs') {
      await exportCustomPacks();
   } else if (e.target.classList.contains('tab-btn')) {
      switchTab(e.target.dataset.tab);
   } else if (action === 'load-more-search-stickers') {
      await loadMoreSearchStickers();
   } else if (action === 'load-more-search-packs') {
      await loadMoreSearchPacks();
   }
});

document.getElementById('stickerSearchInput')?.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   stickerSearchPage = 1;
   searchTimeout = setTimeout(() => searchStickersToAdd(e.target.value), 300);
});

document.getElementById('packSearchInput')?.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   packSearchPage = 1;
   searchTimeout = setTimeout(() => searchPacksToAdd(e.target.value), 300);
});

function sortPacks(packs, sortBy) {
   const sorted = [...packs];
   switch (sortBy) {
      case 'name_asc':
         sorted.sort((a, b) => a.name.localeCompare(b.name));
         break;
      case 'name_desc':
         sorted.sort((a, b) => b.name.localeCompare(a.name));
         break;
      case 'title_asc':
         sorted.sort((a, b) => a.title.localeCompare(b.title));
         break;
      case 'title_desc':
         sorted.sort((a, b) => b.title.localeCompare(a.title));
         break;
      case 'count_desc':
         sorted.sort((a, b) => b.sticker_count - a.sticker_count);
         break;
      case 'count_asc':
         sorted.sort((a, b) => a.sticker_count - b.sticker_count);
         break;
      case 'modified_desc':
         sorted.sort((a, b) => (b.last_modified || 0) - (a.last_modified || 0));
         break;
      case 'modified_asc':
         sorted.sort((a, b) => (a.last_modified || 0) - (b.last_modified || 0));
         break;
   }
   return sorted;
}

function filterPacks(packs, filters) {
   let filtered = [...packs];
   if (filters.onSignal) {
      filtered = filtered.filter(pack => pack.signal_url);
   }
   if (filters.needsUpdate) {
      filtered = filtered.filter(pack => pack.needs_signal_update);
   }
   return filtered;
}

function applyFiltersAndSort(append = false) {
   if (!append) {
      loading.style.display = 'block';
      customPacksGrid.style.display = 'none';
      emptyState.style.display = 'none';
      resultsCount.style.display = 'none';
   }
   let filtered = filterPacks(allPacks, currentFilters);
   let sorted = sortPacks(filtered, currentSortBy);
   loading.style.display = 'none';
   isLoadingMore = false;
   if (sorted.length === 0 && !append) {
      emptyState.style.display = 'block';
      return;
   }
   const perPage = 50;
   const startIdx = append ? (currentPage - 1) * perPage : 0;
   const endIdx = currentPage * perPage;
   const paginated = sorted.slice(startIdx, endIdx);
   totalPages = Math.ceil(sorted.length / perPage);
   if (!append) {
      resultsCount.style.display = 'block';
      resultsCount.textContent = `Found ${sorted.length} custom pack${sorted.length !== 1 ? 's' : ''}`;
      customPacksGrid.style.display = 'grid';
      customPacksGrid.innerHTML = '';
   }
   paginated.forEach(pack => customPacksGrid.appendChild(createCustomPackCard(pack)));
}

async function loadCustomPacks(append = false) {
   if (!append) {
      loading.style.display = 'block';
      customPacksGrid.style.display = 'none';
      emptyState.style.display = 'none';
      resultsCount.style.display = 'none';
      currentPage = 1;
   }
   try {
      const response = await fetch(`/api/custom-packs?page=1&per_page=10000`);
      const data = await response.json();
      const packArray = Object.values(data.packs);
      allPacks = packArray.map(pack => ({
         ...pack,
         needs_signal_update: pack.signal_uploaded_at && pack.last_modified > pack.signal_uploaded_at
      }));
      applyFiltersAndSort(append);
   } catch (error) {
      console.error('Error loading custom packs:', error);
      loading.style.display = 'none';
      isLoadingMore = false;
      if (!append) emptyState.style.display = 'block';
   }
}

function createCustomPackCard(pack) {
   const clone = customPackCardTemplate.content.cloneNode(true);
   const card = clone.querySelector('.pack-card');
   const badgeContainer = clone.querySelector('[data-badge-container]');
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
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   clone.querySelector('[data-action="edit-pack"]').addEventListener('click', () => openEditModal(pack));
   clone.querySelector('[data-action="delete-pack"]').addEventListener('click', async () => {
      if (confirm(`Delete pack "${pack.title}"?`)) {
         await deletePack(pack.name);
      }
   });
   const signalBtn = clone.querySelector('[data-action="upload-signal"]');
   signalBtn.textContent = pack.signal_url ? 'Update Signal' : 'Upload to Signal';
   if (pack.needs_signal_update) {
      signalBtn.classList.add('needs-update');
   }
   signalBtn.addEventListener('click', () => uploadCustomPackToSignal(pack.name));
   return clone;
}

function openCreateModal() {
   document.getElementById('packName').value = '';
   document.getElementById('packTitle').value = '';
   createModal.classList.add('active');
}

function closeCreateModal() {
   createModal.classList.remove('active');
}

async function createNewPack() {
   const name = document.getElementById('packName').value.trim();
   const title = document.getElementById('packTitle').value.trim();
   if (!name || !title) {
      alert('Please fill in all fields');
      return;
   }
   try {
      const response = await fetch('/api/custom-packs', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ name, title })
      });
      if (response.ok) {
         closeCreateModal();
         currentPage = 1;
         loadCustomPacks();
      } else {
         const error = await response.json();
         alert(error.error || 'Failed to create pack');
      }
   } catch (error) {
      console.error('Error creating pack:', error);
      alert('Failed to create pack');
   }
}

async function deletePack(packName) {
   try {
      const response = await fetch(`/api/custom-packs/${encodeURIComponent(packName)}`, { method: 'DELETE' });
      if (response.ok) {
         currentPage = 1;
         loadCustomPacks();
      } else {
         alert('Failed to delete pack');
      }
   } catch (error) {
      console.error('Error deleting pack:', error);
      alert('Failed to delete pack');
   }
}

async function uploadCustomPackToSignal(packName) {
   if (!confirm('Upload this custom pack to Signal? This may take a few moments.')) {
      return;
   }
   try {
      const response = await fetch(`/api/custom-packs/${encodeURIComponent(packName)}/upload-signal`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (response.ok) {
         alert(`Successfully uploaded to Signal!\n\nURL: ${data.signal_url}`);
         currentPage = 1;
         await loadCustomPacks();
      } else {
         alert(`Failed to upload to Signal: ${data.error}`);
      }
   } catch (error) {
      console.error('Error uploading to Signal:', error);
      alert('Failed to upload to Signal');
   }
}

async function openEditModal(pack) {
   currentEditingPack = pack;
   currentPackStickers = [...pack.stickers];
   selectedStickersToAdd.clear();
   selectedPacksToAdd.clear();
   document.getElementById('editModalTitle').textContent = pack.name;
   document.getElementById('editPackTitle').value = pack.title;
   renderCurrentStickers();
   editModal.classList.add('active');
   stickerSearchPage = 1;
   await searchStickersToAdd('');
}

function closeEditModal() {
   editModal.classList.remove('active');
   currentEditingPack = null;
}

function switchTab(tabName) {
   document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
   });
   document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.toggle('active', content.id === tabName);
   });
   if (tabName === 'add-packs') {
      packSearchPage = 1;
      searchPacksToAdd('');
   }
}

function renderCurrentStickers() {
   const grid = document.getElementById('currentStickersGrid');
   const empty = document.getElementById('currentEmpty');
   grid.innerHTML = '';
   if (currentPackStickers.length === 0) {
      empty.style.display = 'block';
      return;
   }
   empty.style.display = 'none';
   currentPackStickers.forEach((sticker, index) => {
      grid.appendChild(createEditableSticker(sticker, index));
   });
}

function createEditableSticker(sticker, index) {
   const clone = editableStickerTemplate.content.cloneNode(true);
   const filePath = `/sticker_files/${encodeURIComponent(sticker.pack_name)}/${encodeURIComponent(sticker.file_path)}`;
   clone.querySelector('[data-field="image"]').src = filePath;
   const emojiDiv = clone.querySelector('[data-field="emoji"]');
   if (sticker.emoji) {
      emojiDiv.textContent = sticker.emoji;
   } else {
      emojiDiv.style.display = 'none';
   }
   const packTitle = clone.querySelector('[data-field="pack_title"]');
   packTitle.textContent = sticker.pack_title || sticker.pack_name;
   clone.querySelector('[data-action="remove-sticker"]').addEventListener('click', () => {
      currentPackStickers.splice(index, 1);
      renderCurrentStickers();
   });
   return clone;
}

async function searchStickersToAdd(query, append = false) {
   const grid = document.getElementById('searchStickersGrid');
   if (!append) {
      grid.innerHTML = '';
      grid.appendChild(loadingTemplate.content.cloneNode(true));
      stickerSearchPage = 1;
   }
   try {
      const response = await fetch(`/api/stickers/search?q=${encodeURIComponent(query)}&page=${stickerSearchPage}&per_page=100`);
      const data = await response.json();
      stickerSearchTotal = data.total_pages;
      if (!append) {
         grid.innerHTML = '';
      } else {
         const loadMoreBtn = grid.querySelector('.load-more-btn');
         if (loadMoreBtn) loadMoreBtn.remove();
      }
      data.stickers.forEach(item => grid.appendChild(createSelectableSticker(item)));
      if (stickerSearchPage < stickerSearchTotal) {
         const loadMore = loadMoreTemplate.content.cloneNode(true);
         loadMore.querySelector('[data-field="text"]').textContent = `Load More (${stickerSearchPage}/${stickerSearchTotal})`;
         loadMore.querySelector('button').dataset.action = 'load-more-search-stickers';
         grid.appendChild(loadMore);
      }
   } catch (error) {
      console.error('Error searching stickers:', error);
      grid.innerHTML = '<div class="error">Failed to load stickers</div>';
   }
}

async function loadMoreSearchStickers() {
   if (stickerSearchPage >= stickerSearchTotal) return;
   stickerSearchPage++;
   const query = document.getElementById('stickerSearchInput').value;
   await searchStickersToAdd(query, true);
}

function createSelectableSticker(item) {
   const clone = selectableStickerTemplate.content.cloneNode(true);
   const card = clone.querySelector('.sticker-card');
   const filePath = `/sticker_files/${encodeURIComponent(item.pack_name)}/${encodeURIComponent(item.sticker.file_path)}`;
   const stickerKey = `${item.pack_name}:${item.sticker.file_unique_id}`;
   clone.querySelector('[data-field="image"]').src = filePath;
   const emojiDiv = clone.querySelector('[data-field="emoji"]');
   if (item.emoji) {
      emojiDiv.textContent = item.emoji;
   } else {
      emojiDiv.style.display = 'none';
   }
   const packTitle = clone.querySelector('[data-field="pack_title"]');
   packTitle.textContent = item.pack_title;
   packTitle.title = item.pack_title;
   if (selectedStickersToAdd.has(stickerKey)) {
      card.classList.add('selected');
   }
   card.addEventListener('click', () => {
      if (selectedStickersToAdd.has(stickerKey)) {
         selectedStickersToAdd.delete(stickerKey);
         card.classList.remove('selected');
      } else {
         selectedStickersToAdd.add(stickerKey);
         card.classList.add('selected');
         currentPackStickers.push({
            pack_name: item.pack_name,
            pack_title: item.pack_title,
            file_unique_id: item.sticker.file_unique_id,
            file_path: item.sticker.file_path,
            emoji: item.emoji
         });
         renderCurrentStickers();
      }
   });
   return clone;
}

async function searchPacksToAdd(query, append = false) {
   const grid = document.getElementById('searchPacksGrid');
   if (!append) {
      grid.innerHTML = '';
      grid.appendChild(loadingTemplate.content.cloneNode(true));
      packSearchPage = 1;
   }
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}&page=${packSearchPage}&per_page=50`);
      const data = await response.json();
      packSearchTotal = data.total_pages;
      if (!append) {
         grid.innerHTML = '';
      } else {
         const loadMoreBtn = grid.querySelector('.load-more-btn');
         if (loadMoreBtn) loadMoreBtn.remove();
      }
      data.packs.forEach(pack => grid.appendChild(createSelectablePack(pack)));
      if (packSearchPage < packSearchTotal) {
         const loadMore = loadMoreTemplate.content.cloneNode(true);
         loadMore.querySelector('[data-field="text"]').textContent = `Load More (${packSearchPage}/${packSearchTotal})`;
         loadMore.querySelector('button').dataset.action = 'load-more-search-packs';
         grid.appendChild(loadMore);
      }
   } catch (error) {
      console.error('Error searching packs:', error);
      grid.innerHTML = '<div class="error">Failed to load packs</div>';
   }
}

async function loadMoreSearchPacks() {
   if (packSearchPage >= packSearchTotal) return;
   packSearchPage++;
   const query = document.getElementById('packSearchInput').value;
   await searchPacksToAdd(query, true);
}

function createSelectablePack(pack) {
   const clone = selectablePackTemplate.content.cloneNode(true);
   const card = clone.querySelector('.pack-card');
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   if (selectedPacksToAdd.has(pack.name)) {
      card.classList.add('selected');
   }
   card.addEventListener('click', async () => {
      if (selectedPacksToAdd.has(pack.name)) {
         selectedPacksToAdd.delete(pack.name);
         card.classList.remove('selected');
      } else {
         selectedPacksToAdd.add(pack.name);
         card.classList.add('selected');
         await addPackStickers(pack.name);
      }
   });
   return clone;
}

async function addPackStickers(packName) {
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}?page=1&per_page=1000`);
      const pack = await response.json();
      pack.stickers.forEach(sticker => {
         if (!currentPackStickers.some(s => s.pack_name === packName && s.file_unique_id === sticker.file_unique_id)) {
            currentPackStickers.push({
               pack_name: packName,
               pack_title: pack.title,
               file_unique_id: sticker.file_unique_id,
               file_path: sticker.file_path,
               emoji: sticker.emoji
            });
         }
      });
      renderCurrentStickers();
   } catch (error) {
      console.error('Error adding pack stickers:', error);
      alert('Failed to add pack stickers');
   }
}

async function savePackChanges() {
   if (!currentEditingPack) return;
   const title = document.getElementById('editPackTitle').value.trim();
   if (!title) {
      alert('Title cannot be empty');
      return;
   }
   try {
      const response = await fetch(`/api/custom-packs/${encodeURIComponent(currentEditingPack.name)}`, {
         method: 'PUT',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ title, stickers: currentPackStickers })
      });
      if (response.ok) {
         closeEditModal();
         currentPage = 1;
         loadCustomPacks();
      } else {
         alert('Failed to save changes');
      }
   } catch (error) {
      console.error('Error saving pack:', error);
      alert('Failed to save changes');
   }
}

async function exportCustomPacks() {
   try {
      const response = await fetch('/api/export/custom-packs');
      if (response.ok) {
         const blob = await response.blob();
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement('a');
         a.href = url;
         a.download = 'custom_packs.json';
         document.body.appendChild(a);
         a.click();
         window.URL.revokeObjectURL(url);
         document.body.removeChild(a);
      } else {
         alert('Failed to export custom packs');
      }
   } catch (error) {
      console.error('Error exporting custom packs:', error);
      alert('Failed to export custom packs');
   }
}
