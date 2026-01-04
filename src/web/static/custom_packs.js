const loading = document.getElementById('loading');
const customPacksGrid = document.getElementById('customPacksGrid');
const emptyState = document.getElementById('emptyState');
const resultsCount = document.getElementById('resultsCount');
const createModal = document.getElementById('createModal');
const editModal = document.getElementById('editModal');
const sortBy = document.getElementById('sortBy');
const filterSignal = document.getElementById('filterSignal');
const filterNeedsUpdate = document.getElementById('filterNeedsUpdate');

const customPackCardTemplate = document.getElementById('customPackCardTemplate');
const editableStickerTemplate = document.getElementById('editableStickerTemplate');
const selectableStickerTemplate = document.getElementById('selectableStickerTemplate');
const selectablePackTemplate = document.getElementById('selectablePackTemplate');
const loadMoreTemplate = document.getElementById('loadMoreTemplate');
const loadingTemplate = document.getElementById('loadingTemplate');
const thumbnailTemplate = document.getElementById('thumbnailTemplate');

let currentEditingPack = null;
let currentPackStickers = [];
let allPackStickers = new Map();

let searchTimeout;
let isLoadingMore = false;

let stickerSearchPage = 1;
let stickerSearchHasMore = false;
let stickerSearchQuery = '';
let isLoadingStickers = false;

let packSearchPage = 1;
let packSearchHasMore = false;
let packSearchQuery = '';
let isLoadingPacks = false;

let allPacks = [];
let currentSortBy = 'name_asc';

let currentFilters = {
   onSignal: 'disabled',
   needsUpdate: 'disabled'
};

let displayedCount = 0;
const itemsPerBatch = 50;

// Drag and drop state
let draggedElement = null;
let draggedIndex = null;
let dragOverElement = null;

loadCustomPacks();

sortBy.addEventListener('change', (e) => {
   currentSortBy = e.target.value;
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
   applyFiltersAndSort();
}

window.addEventListener('scroll', () => {
   if (isLoadingMore) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      loadMoreCustomPacks();
   }
});

function loadMoreCustomPacks() {
   if (isLoadingMore) return;
   let filtered = filterPacks(allPacks, currentFilters);
   let sorted = sortPacks(filtered, currentSortBy);
   if (displayedCount >= sorted.length) return;
   isLoadingMore = true;
   const startIdx = displayedCount;
   const endIdx = Math.min(displayedCount + itemsPerBatch, sorted.length);
   const batch = sorted.slice(startIdx, endIdx);
   batch.forEach(pack => customPacksGrid.appendChild(createCustomPackCard(pack)));
   displayedCount = endIdx;
   isLoadingMore = false;
}

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
   }
});

document.getElementById('stickerSearchInput')?.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   stickerSearchPage = 1;
   stickerSearchQuery = e.target.value;
   searchTimeout = setTimeout(() => searchStickersToAdd(e.target.value, false), 300);
});

document.getElementById('packSearchInput')?.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   packSearchPage = 1;
   packSearchQuery = e.target.value;
   searchTimeout = setTimeout(() => searchPacksToAdd(e.target.value, false), 300);
});

// Add scroll listener for sticker search results
document.getElementById('add-stickers')?.addEventListener('scroll', (e) => {
   if (isLoadingStickers) return;
   // Check if the tab is currently active
   const addStickersTab = document.getElementById('add-stickers');
   if (!addStickersTab.classList.contains('active')) return;
   const container = e.target;
   const scrollTop = container.scrollTop;
   const scrollHeight = container.scrollHeight;
   const clientHeight = container.clientHeight;
   if (scrollTop + clientHeight >= scrollHeight - 500 && stickerSearchHasMore) {
      loadMoreSearchStickers();
   }
});

// Add scroll listener for pack search results
document.getElementById('add-packs')?.addEventListener('scroll', (e) => {
   if (isLoadingPacks) return;
   // Check if the tab is currently active
   const addPacksTab = document.getElementById('add-packs');
   if (!addPacksTab.classList.contains('active')) return;
   const container = e.target;
   const scrollTop = container.scrollTop;
   const scrollHeight = container.scrollHeight;
   const clientHeight = container.clientHeight;
   if (scrollTop + clientHeight >= scrollHeight - 500 && packSearchHasMore) {
      loadMoreSearchPacks();
   }
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
   return filtered;
}

function applyFiltersAndSort() {
   loading.style.display = 'block';
   customPacksGrid.style.display = 'none';
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
   resultsCount.textContent = `Found ${sorted.length} custom pack${sorted.length !== 1 ? 's' : ''}`;
   customPacksGrid.style.display = 'grid';
   customPacksGrid.innerHTML = '';
   displayedCount = 0;
   const firstBatch = sorted.slice(0, Math.min(itemsPerBatch, sorted.length));
   firstBatch.forEach(pack => customPacksGrid.appendChild(createCustomPackCard(pack)));
   displayedCount = firstBatch.length;
}

async function loadCustomPacks() {
   loading.style.display = 'block';
   customPacksGrid.style.display = 'none';
   emptyState.style.display = 'none';
   resultsCount.style.display = 'none';
   try {
      const response = await fetch('/api/custom-packs');
      const data = await response.json();
      const packArray = Object.values(data.packs);
      allPacks = packArray.map(pack => ({
         ...pack,
         needs_signal_update: pack.signal_uploaded_at && pack.last_modified > pack.signal_uploaded_at
      }));
      applyFiltersAndSort();
   } catch (error) {
      console.error('Error loading custom packs:', error);
      loading.style.display = 'none';
      emptyState.style.display = 'block';
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
         img.src = `/sticker_files/${encodeURIComponent(thumb.pack_name)}/${encodeURIComponent(thumb.file_path)}`;
         img.alt = thumb.emoji || '';
         thumbnailContainer.appendChild(imgClone);
      });
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
   allPackStickers.clear();
   try {
      const response = await fetch(`/api/custom-packs/${encodeURIComponent(pack.name)}`);
      const data = await response.json();
      currentPackStickers = [...data.stickers];
   } catch (error) {
      console.error('Error loading pack stickers:', error);
      currentPackStickers = [];
   }
   document.getElementById('editModalTitle').textContent = pack.name;
   document.getElementById('editPackTitle').value = pack.title;
   renderCurrentStickers();
   editModal.classList.add('active');
   // Reset sticker search state
   stickerSearchPage = 1;
   stickerSearchQuery = '';
   const stickersGrid = document.getElementById('searchStickersGrid');
   stickersGrid.innerHTML = '<div class="empty-state"><p>Switch to this tab to search stickers</p></div>';
   // Reset pack search state
   packSearchPage = 1;
   packSearchQuery = '';
   const packsGrid = document.getElementById('searchPacksGrid');
   packsGrid.innerHTML = '<div class="empty-state"><p>Switch to this tab to search packs</p></div>';
}

function closeEditModal() {
   editModal.classList.remove('active');
   currentEditingPack = null;
   allPackStickers.clear();
}

function switchTab(tabName) {
   document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
   });
   document.querySelectorAll('.tab-content').forEach(content => {
      content.classList.toggle('active', content.id === tabName);
   });
   // Load data only when switching to the tab
   if (tabName === 'add-stickers') {
      const grid = document.getElementById('searchStickersGrid');
      // Only load if empty or showing placeholder
      if (grid.querySelector('.empty-state')) {
         stickerSearchPage = 1;
         searchStickersToAdd('', false);
      }
   } else if (tabName === 'add-packs') {
      const grid = document.getElementById('searchPacksGrid');
      // Only load if empty or showing placeholder
      if (grid.querySelector('.empty-state')) {
         packSearchPage = 1;
         searchPacksToAdd('', false);
      }
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
   const card = clone.querySelector('.sticker-card');
   // Make card draggable
   card.draggable = true;
   card.dataset.index = index;
   // Drag start
   card.addEventListener('dragstart', (e) => {
      draggedElement = card;
      draggedIndex = parseInt(card.dataset.index);
      card.style.opacity = '0.5';
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/html', card.innerHTML);
   });
   // Drag end
   card.addEventListener('dragend', (e) => {
      card.style.opacity = '1';
      // Remove all drag-over indicators
      document.querySelectorAll('.sticker-card').forEach(c => {
         c.style.borderColor = '';
      });
   });
   // Drag over
   card.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (draggedElement && draggedElement !== card) {
         // Visual feedback
         card.style.borderColor = 'var(--accent)';
      }
   });
   // Drag leave
   card.addEventListener('dragleave', (e) => {
      card.style.borderColor = '';
   });
   // Drop
   card.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      card.style.borderColor = '';
      if (draggedElement && draggedElement !== card) {
         const targetIndex = parseInt(card.dataset.index);
         // Perform the reorder in the array
         const movedSticker = currentPackStickers[draggedIndex];
         currentPackStickers.splice(draggedIndex, 1);
         // Adjust target index if we removed an element before it
         const adjustedTargetIndex = draggedIndex < targetIndex ? targetIndex - 1 : targetIndex;
         currentPackStickers.splice(adjustedTargetIndex, 0, movedSticker);
         // Re-render the entire grid
         renderCurrentStickers();
      }
   });
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
      refreshPackSelectionDisplay();
   });
   return clone;
}

async function searchStickersToAdd(query, append = false) {
   if (isLoadingStickers) return;
   const grid = document.getElementById('searchStickersGrid');
   if (!append) {
      grid.innerHTML = '';
      grid.appendChild(loadingTemplate.content.cloneNode(true));
      stickerSearchPage = 1;
   } else {
      grid.appendChild(loadingTemplate.content.cloneNode(true));
   }
   isLoadingStickers = true;
   try {
      const response = await fetch(`/api/stickers/search?q=${encodeURIComponent(query)}&page=${stickerSearchPage}&per_page=100`);
      const data = await response.json();
      if (!append) {
         grid.innerHTML = '';
      } else {
         const loadingEl = grid.querySelector('.loading');
         if (loadingEl) loadingEl.remove();
      }
      stickerSearchHasMore = data.total > stickerSearchPage * 100;
      data.stickers.forEach(item => grid.appendChild(createSelectableSticker(item)));
   } catch (error) {
      console.error('Error searching stickers:', error);
      if (!append) {
         grid.innerHTML = '<div class="error">Failed to load stickers</div>';
      }
   } finally {
      isLoadingStickers = false;
   }
}

async function loadMoreSearchStickers() {
   if (!stickerSearchHasMore || isLoadingStickers) return;
   stickerSearchPage++;
   await searchStickersToAdd(stickerSearchQuery, true);
}

function createSelectableSticker(item) {
   const clone = selectableStickerTemplate.content.cloneNode(true);
   const card = clone.querySelector('.sticker-card');
   const filePath = `/sticker_files/${encodeURIComponent(item.pack_name)}/${encodeURIComponent(item.sticker.file_path)}`;
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
   const isSelected = currentPackStickers.some(
      s => s.file_unique_id === item.sticker.file_unique_id
   );
   if (isSelected) {
      card.classList.add('selected');
   }
   card.addEventListener('click', () => {
      const existingIndex = currentPackStickers.findIndex(
         s => s.file_unique_id === item.sticker.file_unique_id
      );
      if (existingIndex !== -1) {
         currentPackStickers.splice(existingIndex, 1);
         card.classList.remove('selected');
      } else {
         currentPackStickers.push({
            pack_name: item.pack_name,
            pack_title: item.pack_title,
            file_unique_id: item.sticker.file_unique_id,
            file_path: item.sticker.file_path,
            emoji: item.emoji
         });
         card.classList.add('selected');
      }
      renderCurrentStickers();
      refreshPackSelectionDisplay();
   });
   return clone;
}

async function searchPacksToAdd(query, append = false) {
   if (isLoadingPacks) return;
   const grid = document.getElementById('searchPacksGrid');
   if (!append) {
      grid.innerHTML = '';
      grid.appendChild(loadingTemplate.content.cloneNode(true));
      packSearchPage = 1;
   } else {
      grid.appendChild(loadingTemplate.content.cloneNode(true));
   }
   isLoadingPacks = true;
   try {
      const response = await fetch(`/api/packs/search?q=${encodeURIComponent(query)}&page=${packSearchPage}&per_page=50`);
      const data = await response.json();
      if (!append) {
         grid.innerHTML = '';
      } else {
         const loadingEl = grid.querySelector('.loading');
         if (loadingEl) loadingEl.remove();
      }
      packSearchHasMore = data.total > packSearchPage * 50;
      for (const pack of data.packs) {
         if (!allPackStickers.has(pack.name)) {
            await fetchPackStickers(pack.name);
         }
         grid.appendChild(createSelectablePack(pack));
      }
   } catch (error) {
      console.error('Error searching packs:', error);
      if (!append) {
         grid.innerHTML = '<div class="error">Failed to load packs</div>';
      }
   } finally {
      isLoadingPacks = false;
   }
}

async function loadMoreSearchPacks() {
   if (!packSearchHasMore || isLoadingPacks) return;
   packSearchPage++;
   await searchPacksToAdd(packSearchQuery, true);
}

async function fetchPackStickers(packName) {
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}?per_page=10000`);
      const pack = await response.json();
      allPackStickers.set(packName, pack.stickers || []);
   } catch (error) {
      console.error(`Error fetching stickers for pack ${packName}:`, error);
      allPackStickers.set(packName, []);
   }
}

function createSelectablePack(pack) {
   const clone = selectablePackTemplate.content.cloneNode(true);
   const card = clone.querySelector('.pack-card');
   if (pack.thumbnails?.length) {
      const thumbnailContainer = clone.querySelector('.pack-thumbnail');
      pack.thumbnails.slice(0, 2).forEach(thumb => {
         const imgClone = thumbnailTemplate.content.cloneNode(true);
         const img = imgClone.querySelector('img');
         img.src = `/sticker_files/${encodeURIComponent(pack.name)}/${encodeURIComponent(thumb.file_path)}`;
         img.alt = thumb.emoji || '';
         thumbnailContainer.appendChild(imgClone);
      });
   }
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   updatePackCardSelection(card, pack.name);
   card.addEventListener('click', async () => {
      await togglePackSelection(pack.name);
      updatePackCardSelection(card, pack.name);
      renderCurrentStickers();
   });
   return clone;
}

function updatePackCardSelection(card, packName) {
   const packStickers = allPackStickers.get(packName) || [];
   const selectedCount = currentPackStickers.filter(s => s.pack_name === packName).length;
   card.classList.remove('selected', 'partial');
   if (selectedCount === packStickers.length && packStickers.length > 0) {
      card.classList.add('selected');
   } else if (selectedCount > 0) {
      card.classList.add('partial');
   }
}

async function togglePackSelection(packName) {
   if (!allPackStickers.has(packName)) {
      await fetchPackStickers(packName);
   }
   const packStickers = allPackStickers.get(packName) || [];
   const selectedCount = currentPackStickers.filter(s => s.pack_name === packName).length;
   // Remove all stickers from this pack
   currentPackStickers = currentPackStickers.filter(s => s.pack_name !== packName);
   // If not fully selected, add all stickers
   if (selectedCount !== packStickers.length) {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}`);
      const pack = await response.json();
      packStickers.forEach(sticker => {
         currentPackStickers.push({
            pack_name: packName,
            pack_title: pack.title,
            file_unique_id: sticker.file_unique_id,
            file_path: sticker.file_path,
            emoji: sticker.emoji
         });
      });
   }
}

function refreshPackSelectionDisplay() {
   document.querySelectorAll('#searchPacksGrid .pack-card').forEach(card => {
      const packName = card.querySelector('[data-field="name"]').textContent;
      updatePackCardSelection(card, packName);
   });
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
         a.download = 'custom_packs.zip';
         document.body.appendChild(a);
         a.click();
         window.URL.revokeObjectURL(url);
         document.body.removeChild(a);
      } else {
         const error = await response.json();
         alert(error.error || 'Failed to export custom packs');
      }
   } catch (error) {
      console.error('Error exporting custom packs:', error);
      alert('Failed to export custom packs');
   }
}

async function exportSingleCustomPack(packName) {
   try {
      const response = await fetch(`/api/export/custom-pack/${encodeURIComponent(packName)}`);
      if (response.ok) {
         const blob = await response.blob();
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement('a');
         a.href = url;
         a.download = `${packName}_custom.json`;
         document.body.appendChild(a);
         a.click();
         window.URL.revokeObjectURL(url);
         document.body.removeChild(a);
      } else {
         const error = await response.json();
         alert(error.error || 'Failed to export custom pack');
      }
   } catch (error) {
      console.error('Error exporting custom pack:', error);
      alert('Failed to export custom pack');
   }
}
