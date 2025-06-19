document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded. Initializing application features.');

    const photoWall = document.getElementById('photo-wall');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const pageInfoSpan = document.getElementById('page-info');
    const orgPathsList = document.getElementById('org-paths-list');
    const globalTagsList = document.getElementById('global-tags-list');

    const sizeInput = document.getElementById('size-input');
    const sortBySelect = document.getElementById('sort-by');
    const sortOrderSelect = document.getElementById('sort-order');
    const refreshBtn = document.getElementById('refresh-btn');

    let currentPage = 1;
    let totalPages = 1;
    let photosPerRow = parseInt(sizeInput.value) || 5;
    let currentSortBy = sortBySelect.value;
    let currentSortOrder = sortOrderSelect.value;

    const selectedMediaIds = new Set();
    let currentMediaItems = [];
    let isXKeyPressed = false; // Flag to track if 'X' key is pressed

    // --- Key press listeners for 'X' key ---
    document.addEventListener('keydown', (event) => {
        if (event.key === 'x' || event.key === 'X') {
            isXKeyPressed = true;
        }
        // Image viewer navigation is handled by its own specific listener below
    });
    document.addEventListener('keyup', (event) => {
        if (event.key === 'x' || event.key === 'X') {
            isXKeyPressed = false;
        }
    });

    // --- Core Data Fetching and Rendering ---
    async function fetchMedia(page = 1, sortBy = currentSortBy, sortOrder = currentSortOrder) {
        try {
            const calculatedPerPage = photosPerRow * 4;
            const response = await fetch(`/api/media?page=${page}&per_page=${calculatedPerPage}&sort_by=${sortBy}&sort_order=${sortOrder}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            currentMediaItems = data.media;
            renderPhotoWall(currentMediaItems);
            currentPage = data.current_page;
            totalPages = data.total_pages;
            updatePaginationControls();
        } catch (error) {
            console.error('Error fetching media:', error);
            photoWall.innerHTML = '<p>Error loading media. Please try again.</p>';
        }
    }

    function renderPhotoWall(mediaItems) {
        photoWall.innerHTML = '';
        if (!mediaItems || mediaItems.length === 0) {
            photoWall.innerHTML = '<p>No media found.</p>';
            return;
        }
        const wallWidth = photoWall.clientWidth;
        const gap = 10;
        const thumbSize = Math.floor((wallWidth - (photosPerRow - 1) * gap) / photosPerRow) - 4;

        mediaItems.forEach(item => {
            const thumbItem = document.createElement('div');
            thumbItem.classList.add('thumbnail-item');
            thumbItem.dataset.id = item.id;
            thumbItem.style.width = `${thumbSize}px`;
            thumbItem.style.height = `${thumbSize}px`;
            thumbItem.style.backgroundImage = `url(/api/media/thumbnail/${item.id})`;

            if (selectedMediaIds.has(item.id)) thumbItem.classList.add('selected');

            thumbItem.addEventListener('click', (event) => {
                if (isXKeyPressed) {
                    event.preventDefault();
                    openImageViewer(item.id);
                } else {
                    toggleSelection(thumbItem, item.id);
                }
            });
            photoWall.appendChild(thumbItem);
        });
    }

    function toggleSelection(thumbElement, mediaId) {
        if (selectedMediaIds.has(mediaId)) {
            selectedMediaIds.delete(mediaId);
            thumbElement.classList.remove('selected');
        } else {
            selectedMediaIds.add(mediaId);
            thumbElement.classList.add('selected');
        }
    }

    function updatePaginationControls() {
        pageInfoSpan.textContent = `Page ${currentPage} of ${totalPages}`;
        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= totalPages;
    }

    // --- Info Panel Data ---
    async function fetchOrgPaths() {
        try {
            const response = await fetch('/api/org_paths');
            const data = await response.json();
            orgPathsList.innerHTML = '';
            data.forEach(path => { const li = document.createElement('li'); li.textContent = path; orgPathsList.appendChild(li); });
        } catch (error) { console.error('Error fetching org paths:', error); }
    }
    async function fetchGlobalTags() {
        try {
            const response = await fetch('/api/tags');
            const data = await response.json();
            globalTagsList.innerHTML = '';
            data.forEach(tag => { const li = document.createElement('li'); li.textContent = tag.name; li.dataset.tagId = tag.id; globalTagsList.appendChild(li); });
        } catch (error) { console.error('Error fetching global tags:', error); }
    }

    // --- Event Listeners for Menu Controls ---
    sizeInput.addEventListener('change', () => {
        const newSize = parseInt(sizeInput.value);
        if (newSize > 0) {
            photosPerRow = newSize;
            clearSelectionsAndUndoHistory();
            fetchMedia(1);
        } else { sizeInput.value = photosPerRow; }
    });
    sortBySelect.addEventListener('change', () => {
        currentSortBy = sortBySelect.value;
        clearSelectionsAndUndoHistory(); fetchMedia(1);
    });
    sortOrderSelect.addEventListener('change', () => {
        currentSortOrder = sortOrderSelect.value;
        clearSelectionsAndUndoHistory(); fetchMedia(1);
    });
    refreshBtn.addEventListener('click', () => {
        clearSelectionsAndUndoHistory();
        fetchMedia(currentPage);
        fetchOrgPaths(); fetchGlobalTags();
    });

    // --- Pagination Event Listeners ---
    prevPageBtn.addEventListener('click', () => { if (currentPage > 1) { clearSelectionsAndUndoHistory(); fetchMedia(currentPage - 1); }});
    nextPageBtn.addEventListener('click', () => { if (currentPage < totalPages) { clearSelectionsAndUndoHistory(); fetchMedia(currentPage + 1); }});

    function clearSelectionsAndUndoHistory() {
        selectedMediaIds.clear();
        // TODO: Clear undo history
        console.log("Selections and undo history cleared.");
        // Re-render to remove visual selection from currently displayed items if any
        // This check ensures photoWall is available and has content before trying to re-render.
        if (photoWall && (document.readyState === 'complete' || document.readyState === 'interactive')) {
             renderPhotoWall(currentMediaItems); // Re-render with current items to clear selection visuals
        }
    }

    // --- Modal Handling ---
    const modals = document.querySelectorAll('.modal');
    const closeButtons = document.querySelectorAll('.close-modal-btn');
    const imageViewerModal = document.getElementById('image-viewer-modal');
    const fullImage = document.getElementById('full-image');
    const modalCaption = document.querySelector('.modal-caption');
    const modalPrev = document.querySelector('.modal-prev');
    const modalNext = document.querySelector('.modal-next');
    let currentViewIndex = -1;

    function openModal(modalId) { const modal = document.getElementById(modalId); if(modal) modal.style.display = 'block'; }
    function closeModal(modalElement) { if(modalElement) modalElement.style.display = 'none'; }
    closeButtons.forEach(button => { button.onclick = function() { closeModal(button.closest('.modal')); }});
    window.onclick = function(event) { modals.forEach(modal => { if (event.target == modal) closeModal(modal); }); }
    document.getElementById('filter-config-btn').onclick = () => openModal('filter-config-modal');
    document.getElementById('tag-management-btn').onclick = () => openModal('tag-management-modal');

    // --- Image Viewer Logic ---
    function openImageViewer(mediaId) {
        const itemIndex = currentMediaItems.findIndex(m => m.id === mediaId);
        if (itemIndex === -1) return;
        currentViewIndex = itemIndex;
        updateImageViewerContent();
        openModal('image-viewer-modal');
    }
    function updateImageViewerContent() {
        if (currentViewIndex < 0 || currentViewIndex >= currentMediaItems.length) return;
        const item = currentMediaItems[currentViewIndex];
        fullImage.src = `/api/media/file/${item.id}`;
        modalCaption.textContent = item.filename;
        modalPrev.style.display = currentViewIndex > 0 ? 'block' : 'none';
        modalNext.style.display = currentViewIndex < currentMediaItems.length - 1 ? 'block' : 'none';
    }
    modalPrev.onclick = () => { if(currentViewIndex > 0) { currentViewIndex--; updateImageViewerContent(); }};
    modalNext.onclick = () => { if(currentViewIndex < currentMediaItems.length - 1) { currentViewIndex++; updateImageViewerContent(); }};

    // Specific keydown listener for the image viewer modal
    document.addEventListener('keydown', (event) => {
        if (imageViewerModal.style.display === 'block') { // Only act if viewer is open
            if (event.key === 'ArrowLeft') { modalPrev.click(); }
            else if (event.key === 'ArrowRight') { modalNext.click(); }
            else if (event.key === 'Escape') { closeModal(imageViewerModal); }
        }
    });

    // --- Initial Data Load ---
    fetchMedia(currentPage, currentSortBy, currentSortOrder);
    fetchOrgPaths();
    fetchGlobalTags();

    window.appContext = { refreshPhotoWall: () => fetchMedia(currentPage, currentSortBy, currentSortOrder), clearSelections: clearSelectionsAndUndoHistory };
});
