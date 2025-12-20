const loading = document.getElementById('loading');
const customPacksGrid = document.getElementById('customPacksGrid');
const emptyState = document.getElementById('emptyState');
const createModal = document.getElementById('createModal');
const editModal = document.getElementById('editModal');

const customPackCardTemplate = document.getElementById('customPackCardTemplate');
const selectableStickerTemplate = document.getElementById('selectableStickerTemplate');
const selectablePackTemplate = document.getElementById('selectablePackTemplate');

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

// Load custom packs on page load
loadCustomPacks();

// Scroll pagination
window.addEventListener('scroll', () => {
   if (isLoadingMore || currentPage >= totalPages) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      isLoadingMore = true;
      currentPage++;
      loadCustomPacks(true);
   }
});

// Event delegation
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

// Search inputs
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

function escapeHtml(text) {
   const div = document.createElement('div');
   div.textContent = text;
   return div.innerHTML;
}

async function loadCustomPacks(append = false) {
   if (!append) {
      loading.style.display = 'block';
      customPacksGrid.style.display = 'none';
      emptyState.style.display = 'none';
      currentPage = 1;
   }
   try {
      const response = await fetch(`/api/custom-packs?page=${currentPage}&per_page=50`);
      const data = await response.json();
      const packArray = Object.values(data.packs);
      loading.style.display = 'none';
      isLoadingMore = false;
      totalPages = data.total_pages;
      if (packArray.length === 0 && !append) {
         emptyState.style.display = 'block';
         return;
      }
      if (!append) {
         customPacksGrid.style.display = 'grid';
         customPacksGrid.innerHTML = '';
      }
      packArray.forEach(pack => {
         customPacksGrid.appendChild(createCustomPackCard(pack));
      });
   } catch (error) {
      console.error('Error loading custom packs:', error);
      loading.style.display = 'none';
      isLoadingMore = false;
      if (!append) {
         emptyState.style.display = 'block';
      }
   }
}

function createCustomPackCard(pack) {
   const clone = customPackCardTemplate.content.cloneNode(true);
   clone.querySelector('[data-field="title"]').textContent = pack.title;
   clone.querySelector('[data-field="name"]').textContent = pack.name;
   clone.querySelector('[data-field="sticker_count"]').textContent = `${pack.sticker_count} stickers`;
   clone.querySelector('[data-action="edit-pack"]').addEventListener('click', () => {
      openEditModal(pack);
   });
   clone.querySelector('[data-action="delete-pack"]').addEventListener('click', async () => {
      if (confirm(`Delete pack "${pack.title}"?`)) {
         await deletePack(pack.name);
      }
   });
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
      const response = await fetch(`/api/custom-packs/${encodeURIComponent(packName)}`, {
         method: 'DELETE'
      });
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

async function openEditModal(pack) {
   currentEditingPack = pack;
   currentPackStickers = [...pack.stickers];
   selectedStickersToAdd.clear();
   selectedPacksToAdd.clear();
   document.getElementById('editModalTitle').textContent = pack.name;
   document.getElementById('editPackTitle').value = pack.title;
   renderCurrentStickers();
   editModal.classList.add('active');
   // Load stickers to add
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
      const card = createEditableSticker(sticker, index);
      grid.appendChild(card);
   });
}

function createEditableSticker(sticker, index) {
   const card = document.createElement('div');
   card.className = 'sticker-card';
   const filePath = `/sticker_files/${encodeURIComponent(sticker.pack_name)}/${encodeURIComponent(sticker.file_path)}`;
   card.innerHTML = `
      <div class="sticker-preview">
         <img src="${filePath}" alt="" loading="lazy">
      </div>
      <div class="sticker-info">
         ${sticker.emoji ? `<div class="sticker-emoji">${escapeHtml(sticker.emoji)}</div>` : ''}
         <div class="sticker-pack-name">${escapeHtml(sticker.pack_title || sticker.pack_name)}</div>
      </div>
      <button class="btn-remove" title="Remove">×</button>
   `;
   card.querySelector('.btn-remove').addEventListener('click', () => {
      currentPackStickers.splice(index, 1);
      renderCurrentStickers();
   });
   return card;
}

async function searchStickersToAdd(query, append = false) {
   const grid = document.getElementById('searchStickersGrid');
   if (!append) {
      grid.innerHTML = '<div class="loading">Loading...</div>';
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
      data.stickers.forEach(item => {
         const card = createSelectableSticker(item);
         grid.appendChild(card);
      });
      // Add load more button if needed
      if (stickerSearchPage < stickerSearchTotal) {
         const loadMoreBtn = document.createElement('button');
         loadMoreBtn.className = 'btn btn-primary load-more-btn';
         loadMoreBtn.textContent = `Load More (${stickerSearchPage}/${stickerSearchTotal})`;
         loadMoreBtn.dataset.action = 'load-more-search-stickers';
         grid.appendChild(loadMoreBtn);
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
   clone.querySelector('[data-field="pack_title"]').textContent = item.pack_title;
   clone.querySelector('[data-field="pack_title"]').title = item.pack_title;
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
         // Add to current pack stickers
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
      grid.innerHTML = '<div class="loading">Loading...</div>';
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
      data.packs.forEach(pack => {
         const card = createSelectablePack(pack);
         grid.appendChild(card);
      });
      // Add load more button if needed
      if (packSearchPage < packSearchTotal) {
         const loadMoreBtn = document.createElement('button');
         loadMoreBtn.className = 'btn btn-primary load-more-btn';
         loadMoreBtn.textContent = `Load More (${packSearchPage}/${packSearchTotal})`;
         loadMoreBtn.dataset.action = 'load-more-search-packs';
         grid.appendChild(loadMoreBtn);
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
         // Fetch full pack and add all stickers
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
         // Check if already added
         if (!currentPackStickers.some(s => 
            s.pack_name === packName && s.file_unique_id === sticker.file_unique_id
         )) {
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
         body: JSON.stringify({
            title: title,
            stickers: currentPackStickers
         })
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
