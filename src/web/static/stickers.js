let searchTimeout;
const searchInput = document.getElementById('searchInput');
const stickersGrid = document.getElementById('stickersGrid');
const loading = document.getElementById('loading');
const emptyState = document.getElementById('emptyState');
const resultsCount = document.getElementById('resultsCount');
const emojiModal = document.getElementById('emojiModal');
const emojiInput = document.getElementById('emojiInput');
const emojiEditPreview = document.getElementById('emojiEditPreview');

const stickerCardTemplate = document.getElementById('stickerCardTemplate');

let currentEditSticker = null;
let currentPage = 1;
let totalPages = 1;
let currentQuery = '';
let isLoadingMore = false;

// Initial load
searchStickers('');

// Search on input
searchInput.addEventListener('input', (e) => {
   clearTimeout(searchTimeout);
   currentPage = 1;
   searchTimeout = setTimeout(() => {
      searchStickers(e.target.value);
   }, 300);
});

// Scroll pagination
window.addEventListener('scroll', () => {
   if (isLoadingMore || currentPage >= totalPages) return;
   const scrollTop = window.scrollY;
   const windowHeight = window.innerHeight;
   const docHeight = document.documentElement.scrollHeight;
   if (scrollTop + windowHeight >= docHeight - 500) {
      isLoadingMore = true;
      currentPage++;
      searchStickers(currentQuery, true);
   }
});

// Event delegation
document.addEventListener('click', (e) => {
   const action = e.target.dataset.action;
   if (action === 'close-emoji-modal' || (e.target === emojiModal)) {
      closeEmojiModal();
   } else if (action === 'save-emoji') {
      saveEmoji();
   }
});

function escapeHtml(text) {
   const div = document.createElement('div');
   div.textContent = text;
   return div.innerHTML;
}

function createStickerCard(item) {
   const clone = stickerCardTemplate.content.cloneNode(true);
   const card = clone.querySelector('.sticker-card');
   const filePath = `/sticker_files/${encodeURIComponent(item.pack_name)}/${encodeURIComponent(item.sticker.file_path)}`;
   const img = clone.querySelector('[data-field="image"]');
   img.src = filePath;
   const emojiDiv = clone.querySelector('[data-field="emoji"]');
   if (item.emoji) {
      emojiDiv.textContent = item.emoji;
      emojiDiv.style.display = 'block';
   } else {
      emojiDiv.style.display = 'none';
   }
   clone.querySelector('[data-field="pack_title"]').textContent = item.pack_title;
   clone.querySelector('[data-field="pack_title"]').title = item.pack_title;
   clone.querySelector('[data-field="artist"]').textContent = item.artist;
   clone.querySelector('[data-field="artist"]').title = item.artist;
   // Add edit emoji functionality
   clone.querySelector('[data-action="edit-emoji"]').addEventListener('click', () => {
      openEmojiModal(item, filePath);
   });
   return clone;
}

async function searchStickers(query, append = false) {
   currentQuery = query;
   if (!append) {
      loading.style.display = 'block';
      stickersGrid.style.display = 'none';
      emptyState.style.display = 'none';
      resultsCount.style.display = 'none';
      currentPage = 1;
   }
   try {
      const response = await fetch(`/api/stickers/search?q=${encodeURIComponent(query)}&page=${currentPage}&per_page=100`);
      const data = await response.json();
      loading.style.display = 'none';
      isLoadingMore = false;
      totalPages = data.total_pages;
      if (data.stickers.length === 0 && !append) {
         emptyState.style.display = 'block';
         return;
      }
      if (!append) {
         resultsCount.style.display = 'block';
         resultsCount.textContent = `Found ${data.total} sticker${data.total !== 1 ? 's' : ''}`;
         stickersGrid.style.display = 'grid';
         stickersGrid.innerHTML = '';
      }
      data.stickers.forEach(item => {
         stickersGrid.appendChild(createStickerCard(item));
      });
   } catch (error) {
      console.error('Error searching stickers:', error);
      loading.style.display = 'none';
      isLoadingMore = false;
      if (!append) {
         emptyState.style.display = 'block';
      }
   }
}

function openEmojiModal(stickerItem, imagePath) {
   currentEditSticker = stickerItem;
   emojiEditPreview.src = imagePath;
   emojiInput.value = stickerItem.emoji || '';
   emojiModal.classList.add('active');
   emojiInput.focus();
}

function closeEmojiModal() {
   emojiModal.classList.remove('active');
   currentEditSticker = null;
}

async function saveEmoji() {
   if (!currentEditSticker) return;
   const emojis = emojiInput.value.trim();
   const packName = currentEditSticker.pack_name;
   const uniqueId = currentEditSticker.sticker.file_unique_id;
   try {
      const response = await fetch(`/api/packs/${encodeURIComponent(packName)}/emoji`, {
         method: 'POST',
         headers: {
            'Content-Type': 'application/json'
         },
         body: JSON.stringify({
            unique_id: uniqueId,
            emojis: emojis
         })
      });
      if (response.ok) {
         // Update the emoji in the current display
         currentEditSticker.emoji = emojis;
         closeEmojiModal();
         // Refresh the search to show updated emojis
         currentPage = 1;
         searchStickers(searchInput.value);
      } else {
         alert('Failed to save emoji');
      }
   } catch (error) {
      console.error('Error saving emoji:', error);
      alert('Failed to save emoji');
   }
}

