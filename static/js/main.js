document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded. Initializing. Implementing Delete Photo UI.');

    // Cache DOM elements
    const photoWall = document.getElementById('photo-wall');
    const globalTagsListUl = document.getElementById('global-tags-list');
    const sizeInput = document.getElementById('size-input');
    const sortBySelect = document.getElementById('sort-by');
    const sortOrderSelect = document.getElementById('sort-order');
    const refreshBtn = document.getElementById('refresh-btn');
    const tagManagementBtn = document.getElementById('tag-management-btn');
    const batchTagBtn = document.getElementById('batch-tag-btn');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn'); // Added

    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const pageInfoSpan = document.getElementById('page-info');
    const orgPathsList = document.getElementById('org-paths-list');
    const filterConfigBtn = document.getElementById('filter-config-btn');
    const imageViewerModal = document.getElementById('image-viewer-modal');
    const tagManagementModal = document.getElementById('tag-management-modal');
    const newTagInput = document.getElementById('new-tag-input');
    const addNewTagBtn = document.getElementById('add-new-tag-btn');
    const manageTagsListUl = document.getElementById('manage-tags-list');
    const tagManagementStatusDiv = document.getElementById('tag-management-status');
    const filterConfigModal = document.getElementById('filter-config-modal');
    const filterFunctionInput = document.getElementById('filter-function-input');
    const applyFilterBtn = document.getElementById('apply-filter-btn');
    const clearFilterBtn = document.getElementById('clear-filter-btn');
    const filterStatusDiv = document.getElementById('filter-status');
    const fullImage = document.getElementById('full-image');
    const modalCaption = document.querySelector('.modal-caption');
    const modalPrev = document.querySelector('.modal-prev');
    const modalNext = document.querySelector('.modal-next');

    // Favorite Filters elements
    const saveFilterFavoriteBtn = document.getElementById('save-filter-favorite-btn');
    const favoriteFiltersListUl = document.getElementById('favorite-filters-list');
    const noFavoriteFiltersMessage = document.getElementById('no-favorite-filters-message');
    const LOCALSTORAGE_FILTER_FAVORITES_KEY = 'photoAlbumManagerFilterFavorites';

    // CodeMirror instance for filter input
    let filterCodeEditor = null;

    // --- Filter Favorites Functions ---
    function loadFilterFavorites() {
        const favoritesJson = localStorage.getItem(LOCALSTORAGE_FILTER_FAVORITES_KEY);
        try {
            const favorites = JSON.parse(favoritesJson);
            return Array.isArray(favorites) ? favorites : [];
        } catch (e) {
            return [];
        }
    }

    function saveFilterFavorites(favoritesArray) {
        localStorage.setItem(LOCALSTORAGE_FILTER_FAVORITES_KEY, JSON.stringify(favoritesArray));
    }

    function addFilterFavorite(snippet) {
        if (!snippet || !snippet.trim()) {
            alert("Cannot save an empty filter snippet.");
            return;
        }
        const favorites = loadFilterFavorites();
        // Optional: Prevent duplicates
        if (favorites.includes(snippet)) {
            // alert("This filter snippet is already in your favorites.");
            // return;
            // Or allow duplicates, current behavior allows duplicates.
        }
        favorites.push(snippet);
        saveFilterFavorites(favorites);
        renderFilterFavorites(); // Re-render the list
    }

    function deleteFilterFavorite(indexToDelete) {
        let favorites = loadFilterFavorites();
        if (indexToDelete >= 0 && indexToDelete < favorites.length) {
            favorites.splice(indexToDelete, 1);
            saveFilterFavorites(favorites);
            renderFilterFavorites();
        }
    }

    function renderFilterFavorites() {
        if (!favoriteFiltersListUl || !noFavoriteFiltersMessage) return;

        const favorites = loadFilterFavorites();
        favoriteFiltersListUl.innerHTML = ''; // Clear existing items

        if (favorites.length === 0) {
            noFavoriteFiltersMessage.style.display = 'block';
            return;
        }

        noFavoriteFiltersMessage.style.display = 'none';

        favorites.forEach((snippet, index) => {
            const li = document.createElement('li');
            li.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; border-bottom: 1px solid #eee; margin-bottom: 4px; background-color: #fff; border-radius: 3px;';

            const snippetText = document.createElement('span');
            snippetText.textContent = snippet.length > 60 ? snippet.substring(0, 57) + '...' : snippet; // Truncate if long
            snippetText.title = snippet; // Show full snippet on hover
            snippetText.style.cssText = 'flex-grow: 1; margin-right: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: default;';

            const btnContainer = document.createElement('div');
            btnContainer.style.cssText = 'display: flex; gap: 5px;';

            const loadBtn = document.createElement('button');
            loadBtn.textContent = 'Load';
            loadBtn.className = 'load-favorite-btn'; // Added class
            // loadBtn.style.cssText = 'padding: 3px 6px; font-size: 0.8em; background-color: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px;'; // CSS will handle
            loadBtn.onclick = () => {
                if (filterCodeEditor) {
                    filterCodeEditor.setValue(snippet);
                    filterCodeEditor.refresh(); // Ensure it's rendered correctly
                } else if (filterFunctionInput) { // Fallback if CodeMirror not init
                    filterFunctionInput.value = snippet;
                }
            };

            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = 'Del';
            deleteBtn.className = 'delete-favorite-btn'; // Added class
            // deleteBtn.style.cssText = 'padding: 3px 6px; font-size: 0.8em; background-color: #dc3545; color: white; border: none; cursor: pointer; border-radius: 3px;'; // CSS will handle
            deleteBtn.onclick = () => deleteFilterFavorite(index);

            btnContainer.appendChild(loadBtn);
            btnContainer.appendChild(deleteBtn);
            li.appendChild(snippetText);
            li.appendChild(btnContainer);
            favoriteFiltersListUl.appendChild(li);
        });
    }
    // --- End Filter Favorites Functions ---

    // Application State
    let currentPage = 1, totalPages = 1;
    let photosPerRow = parseInt(sizeInput.value) || 5;
    if (photoWall) photoWall.style.setProperty('--photos-per-row', photosPerRow);
    let currentSortBy = sortBySelect.value, currentSortOrder = sortOrderSelect.value;
    const selectedMediaIds = new Set();
    const activeTagNamesForOperations = new Set();
    let currentMediaItems = [], isXKeyPressed = false, isTKeyPressed = false, isDKeyPressed = false, isShiftKeyPressed = false, resizeTimeout, lastCalculatedPerPage = 0;
    let lastClickedPhotoIndex = -1; // For Shift-click range selection

    document.addEventListener('keydown', (event) => {
        if(event.key==='x'||event.key==='X')isXKeyPressed=true;
        if(event.key==='t'||event.key==='T')isTKeyPressed=true;
        if(event.key==='d'||event.key==='D')isDKeyPressed=true;
        if(event.key==='Shift') isShiftKeyPressed = true;
    });
    document.addEventListener('keyup', (event) => {
        if(event.key==='x'||event.key==='X')isXKeyPressed=false;
        if(event.key==='t'||event.key==='T')isTKeyPressed=false;
        if(event.key==='d'||event.key==='D')isDKeyPressed=false;
        if(event.key==='Shift') isShiftKeyPressed = false;
    });

    // --- Core Functions (some minified for focus) ---
    function getCalculatedPerPage() { const c=(parseInt(photoWall.style.getPropertyValue('--photos-per-row'))||photosPerRow),w=photoWall.clientWidth,a=photoWall.parentElement?photoWall.parentElement.clientHeight:window.innerHeight,g=10;if(w===0||a===0||c===0)return c>0?c*4:20;const cl=(w-(c-1)*g)/c,th=cl,s=th+g;if(s<=g)return c;const n=Math.max(1,Math.floor(a/s)),p=c*n;return Math.max(c,p); }
    async function fetchMedia(page = 1, sortBy = currentSortBy, sortOrder = currentSortOrder) { if(photoWall)void photoWall.offsetHeight;const cp=getCalculatedPerPage();lastCalculatedPerPage=cp;const u=`/api/media?page=${page}&per_page=${cp}&sort_by=${sortBy}&sort_order=${sortOrder}`;console.log(`Fetching: ${u}`);try{const r=await fetch(u);if(!r.ok)throw new Error(`${r.status}: ${await r.text()}`);const d=await r.json();currentMediaItems=d.media;renderPhotoWall(d.media);currentPage=d.current_page;totalPages=d.total_pages;if(updatePaginationControls)updatePaginationControls()}catch(e){console.error('Fetch error:',e);if(photoWall)photoWall.innerHTML=`<p>Error: ${e.message}</p>`} }
    async function handleQuickTagging(mediaId, thumbItem) { const aT=Array.from(activeTagNamesForOperations);if(aT.length===0){console.warn('[QuickTag] No active tags.');return}try{const r=await fetch(`/api/media/${mediaId}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:aT})});const rs=await r.json();if(r.ok){const idx=currentMediaItems.findIndex(m=>m.id===mediaId);if(idx>-1)currentMediaItems[idx].tags=rs.tags;renderPhotoWall(currentMediaItems);if(thumbItem)thumbItem.style.outline='2px solid green';setTimeout(()=>{if(thumbItem)thumbItem.style.outline=''},1000)}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} }
    function renderPhotoWall(mediaItems) {
        if (!photoWall) return;
        photoWall.innerHTML = '';
        if (!mediaItems || mediaItems.length === 0) {
            photoWall.innerHTML = '<p>No media.</p>';
            return;
        }
        mediaItems.forEach((item, index) => { // Added index here
            const ti = document.createElement('div');
            ti.classList.add('thumbnail-item');
            ti.dataset.id = String(item.id);
            ti.dataset.index = index; // Store index for easy retrieval
            ti.style.backgroundImage = `url(/api/media/thumbnail/${item.id})`;

            if (selectedMediaIds.has(item.id)) ti.classList.add('selected');

            if (item.tags && item.tags.length > 0) {
                const o = document.createElement('div');
                o.className = 'thumbnail-tags-overlay';
                item.tags.slice(0, 3).forEach(tn => {
                    const s = document.createElement('span');
                    s.className = 'thumbnail-tag';
                    s.textContent = tn;
                    s.dataset.tagName = tn;
                    o.appendChild(s);
                    s.addEventListener('click', (tagEvent) => {
                        if (isDKeyPressed) {
                            tagEvent.preventDefault();
                            tagEvent.stopPropagation();
                            handleRemoveTagFromMedia(item.id, tn, s);
                        }
                    });
                });
                if (item.tags.length > 3) {
                    const m = document.createElement('span');
                    m.className = 'thumbnail-tag-more';
                    m.textContent = '...';
                    o.appendChild(m);
                }
                ti.appendChild(o);
            }

            ti.addEventListener('click', (e) => {
                e.preventDefault();
                const clickedItemId = parseInt(item.id);
                const currentIndex = parseInt(ti.dataset.index); // Get current index

                if (isShiftKeyPressed && lastClickedPhotoIndex !== -1 && lastClickedPhotoIndex < currentMediaItems.length) {
                    const start = Math.min(lastClickedPhotoIndex, currentIndex);
                    const end = Math.max(lastClickedPhotoIndex, currentIndex);

                    // For range selection, we typically want to ensure all items in the range get selected.
                    // The behavior for items outside the range can vary (e.g. keep their state, or deselect).
                    // This implementation will select everything in the range.
                    // It does not explicitly deselect items outside the range that were previously selected.
                    for (let i = start; i <= end; i++) {
                        const itemInRange = currentMediaItems[i];
                        if (itemInRange) {
                            selectedMediaIds.add(itemInRange.id);
                            // Update visual state for all items in range
                            const thumbElementInRange = photoWall.querySelector(`.thumbnail-item[data-id='${itemInRange.id}']`);
                            if (thumbElementInRange) {
                                thumbElementInRange.classList.add('selected');
                            }
                        }
                    }
                    // Note: lastClickedPhotoIndex is NOT updated here, so the anchor remains for further shift-clicks.
                } else if (isTKeyPressed) {
                    handleQuickTagging(clickedItemId, ti);
                    lastClickedPhotoIndex = currentIndex; // Update anchor on T+click as well
                } else if (isXKeyPressed) {
                    openImageViewer(clickedItemId);
                    lastClickedPhotoIndex = currentIndex; // Update anchor
                } else {
                    // Normal click: toggle selection and set as anchor
                    toggleSelection(ti, clickedItemId);
                    lastClickedPhotoIndex = currentIndex;
                }
                console.log('Selected IDs:', Array.from(selectedMediaIds), 'Last clicked index:', lastClickedPhotoIndex);
            });
            photoWall.appendChild(ti);
        });
    }
    function toggleSelection(el, id) { const numId = parseInt(id); if(selectedMediaIds.has(numId)){selectedMediaIds.delete(numId);el.classList.remove('selected')}else{selectedMediaIds.add(numId);el.classList.add('selected')} console.log('Current selection IDs:',Array.from(selectedMediaIds)); }
    function updatePaginationControls() { if(pageInfoSpan)pageInfoSpan.textContent=`Page ${currentPage} of ${totalPages}`;if(prevPageBtn)prevPageBtn.disabled=currentPage<=1;if(nextPageBtn)nextPageBtn.disabled=currentPage>=totalPages }
    async function fetchOrgPaths() { try{const r=await fetch('/api/org_paths');const d=await r.json();if(orgPathsList){orgPathsList.innerHTML='';d.forEach(p=>{const l=document.createElement('li');l.textContent=p;orgPathsList.appendChild(l)})}}catch(e){} }
    async function fetchGlobalTags() { if(!globalTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();globalTagsListUl.innerHTML='';if(d.length===0)globalTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const l=document.createElement('li');l.textContent=t.name;l.dataset.tagId=t.id;l.dataset.tagName=t.name;if(activeTagNamesForOperations.has(t.name))l.classList.add('active-for-tagging');l.addEventListener('click',()=>{if(activeTagNamesForOperations.has(t.name)){activeTagNamesForOperations.delete(t.name);l.classList.remove('active-for-tagging')}else{activeTagNamesForOperations.add(t.name);l.classList.add('active-for-tagging')}});globalTagsListUl.appendChild(l)})}catch(e){globalTagsListUl.innerHTML='<li>Error tags.</li>'} }

    async function handleRemoveTagFromMedia(mediaId, tagName, tagSpanElement) {
        console.log(`Attempting to remove tag '${tagName}' from media ID ${mediaId}`);
        // Optional: Visual feedback before API call (e.g., dimming the tag)
        if (tagSpanElement) tagSpanElement.style.opacity = '0.5';

        try {
            const response = await fetch(`/api/media/${mediaId}/tags/${encodeURIComponent(tagName)}`, {
                method: 'DELETE',
            });
            const result = await response.json();

            if (response.ok) {
                console.log(`Successfully removed tag '${tagName}' from media ID ${mediaId}. Server response:`, result);
                // Update currentMediaItems
                const mediaIndex = currentMediaItems.findIndex(item => item.id === mediaId);
                if (mediaIndex > -1) {
                    currentMediaItems[mediaIndex].tags = result.tags; // Assuming backend returns updated tags list
                }
                renderPhotoWall(currentMediaItems); // Re-render the photo wall
            } else {
                console.error(`Error removing tag: ${result.error || 'Unknown server error'}`);
                alert(`Failed to remove tag '${tagName}': ${result.error || 'Unknown server error'}`);
                if (tagSpanElement) tagSpanElement.style.opacity = '1'; // Restore opacity on failure
            }
        } catch (error) {
            console.error('Network or other error removing tag:', error);
            alert(`Network error removing tag '${tagName}'.`);
            if (tagSpanElement) tagSpanElement.style.opacity = '1'; // Restore opacity on failure
        }
    }

    async function handleDeleteTag(tagId, tagName) { if(!confirm(`Delete '${tagName}'?`))return;try{const r=await fetch(`/api/tags/${tagId}`,{method:'DELETE'});const rs=await r.json();if(r.ok){if(populateManageTagsList)populateManageTagsList();fetchGlobalTags();if(window.appContext)window.appContext.refreshPhotoWall()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} }
    async function populateManageTagsList() { if(!manageTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();manageTagsListUl.innerHTML='';if(d.length===0)manageTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const li=document.createElement('li');const s=document.createElement('span');s.textContent=t.name;li.appendChild(s);li.dataset.tagId=t.id;const b=document.createElement('button');b.textContent='Delete';b.style.cssText='margin-left:10px;padding:2px 5px;font-size:0.8em;background-color:#dc3545;color:white;border:none;cursor:pointer;';b.onclick=(e)=>{e.stopPropagation();handleDeleteTag(t.id,t.name)};li.appendChild(b);manageTagsListUl.appendChild(li)})}catch(e){manageTagsListUl.innerHTML='<li>Error tags.</li>'} }
    if(addNewTagBtn) addNewTagBtn.addEventListener('click', async () => { const tn=newTagInput.value.trim();if(!tn){alert('Empty tag.');return}try{const r=await fetch('/api/tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:tn})});const rs=await r.json();if(r.ok){newTagInput.value='';populateManageTagsList();fetchGlobalTags()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} });
    if(batchTagBtn) batchTagBtn.addEventListener('click', async () => { const mIds=Array.from(selectedMediaIds);const tApply=Array.from(activeTagNamesForOperations);if(mIds.length===0||tApply.length===0){alert('Select photos & active tags.');return}const o=batchTagBtn.textContent;batchTagBtn.textContent='Tagging...';batchTagBtn.disabled=true;let sC=0,eC=0;for(const mId of mIds){try{const idx=currentMediaItems.findIndex(m=>m.id===mId);const r=await fetch(`/api/media/${mId}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:tApply})});const rs=await r.json();if(r.ok){sC++;if(idx>-1)currentMediaItems[idx].tags=rs.tags}else{eC++}}catch(e){eC++}}batchTagBtn.textContent=o;batchTagBtn.disabled=false;alert(`Batch: ${sC} success, ${eC} failed.`);if(sC>0){renderPhotoWall(currentMediaItems);}});

    function clearSelectionsAndActiveTags() {
        selectedMediaIds.clear();
        activeTagNamesForOperations.clear();
        if(fetchGlobalTags)fetchGlobalTags();
        console.log("FRONTEND: Cleared selections and active tags.");
        if(photoWall && (document.readyState==='complete'||document.readyState==='interactive')) renderPhotoWall(currentMediaItems);
    }

    // --- Delete Selected Photos Logic ---
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', async () => {
            const mediaIdsToDelete = Array.from(selectedMediaIds);
            console.log('[DeletePhotos] Clicked. Media IDs to delete:', mediaIdsToDelete);

            if (mediaIdsToDelete.length === 0) {
                alert('No photos selected for deletion. Please select photos (left-click) first.');
                return;
            }

            if (!confirm(`Are you sure you want to delete ${mediaIdsToDelete.length} selected photo(s)? This will move them to the archive.`)) {
                console.log('[DeletePhotos] Deletion cancelled by user.');
                return;
            }

            const originalButtonText = deleteSelectedBtn.textContent;
            deleteSelectedBtn.textContent = 'Deleting...';
            deleteSelectedBtn.disabled = true;

            try {
                const response = await fetch('/api/media/delete_selected', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ media_ids: mediaIdsToDelete })
                });
                const result = await response.json(); // Expect summary: {message, success_count, failures: [{id, reason}]}

                alert(result.message || 'Deletion process completed.'); // Show summary message from server
                console.log('[DeletePhotos] Server response:', result);

                // Refresh view only if some items were successfully processed or if the response indicates an OK status
                // (e.g. 207 Multi-Status means some actions, possibly successful, were performed)
                if (result.success_count > 0 || response.ok) {
                    clearSelectionsAndActiveTags(); // Clear selections

                    // Trigger a "deep refresh": scan backend then reload UI from page 1
                    console.log('[DeletePhotos] Initiating deep refresh after deletion...');
                    if (refreshBtn && typeof refreshBtn.click === 'function') {
                        refreshBtn.click(); // Simulate a click on the main refresh button
                    } else {
                        // Fallback if refreshBtn isn't available or click simulation is problematic
                        console.warn('[DeletePhotos] refreshBtn not found or not clickable, attempting manual deep refresh sequence.');
                        fetch('/api/scan/trigger', { method: 'POST' })
                           .then(scanRes => scanRes.json())
                           .then(scanData => {
                               console.log('[DeletePhotos] Post-delete scan complete:', scanData.message);
                               fetchMedia(1); // Fetch page 1
                               if(fetchGlobalTags) fetchGlobalTags(); // Refresh info panel tags
                               if(fetchOrgPaths) fetchOrgPaths();   // Refresh info panel org paths
                           })
                           .catch(err => {
                               console.error('[DeletePhotos] Post-delete scan trigger failed:', err);
                               // Still try to refresh basic view even if scan trigger fails
                               fetchMedia(1);
                               if(fetchGlobalTags) fetchGlobalTags();
                               if(fetchOrgPaths) fetchOrgPaths();
                           });
                    }
                }
            } catch (error) {
                console.error('[DeletePhotos] Network error or other issue during deletion:', error);
                alert('Failed to delete photos due to a network or server issue. Please check console for details.');
            }
            deleteSelectedBtn.textContent = originalButtonText;
            deleteSelectedBtn.disabled = false;
        });
    } else {
        console.warn("deleteSelectedBtn not found.");
    }

    // --- Event Listeners & Other Functions (unchanged, minified for subtask focus) ---
    if(sizeInput) sizeInput.addEventListener('change', () => { const newSize=parseInt(sizeInput.value);if(newSize>0){photosPerRow=newSize;photoWall.style.setProperty('--photos-per-row',photosPerRow);clearSelectionsAndActiveTags();fetchMedia(1)}else{sizeInput.value=photosPerRow} });
    if(sortBySelect) sortBySelect.addEventListener('change', () => { currentSortBy=sortBySelect.value;clearSelectionsAndActiveTags();fetchMedia(1) });
    if(sortOrderSelect) sortOrderSelect.addEventListener('change', () => { currentSortOrder=sortOrderSelect.value;clearSelectionsAndActiveTags();fetchMedia(1) });
    if(refreshBtn) refreshBtn.addEventListener('click', async () => {const o=refreshBtn.textContent;refreshBtn.textContent='Scanning...';refreshBtn.disabled=true;let s=false;try{const r=await fetch('/api/scan/trigger',{method:'POST'});const t=await r.json().catch(()=>({error:"JSON Error"}));if(!r.ok){alert(`Scan Error: ${t.error||'Unknown'}`);s=true}else{/* Alert removed */}}catch(e){alert('Scan Network Error.');s=true}refreshBtn.textContent=o;refreshBtn.disabled=false;if(!s){clearSelectionsAndActiveTags();fetchMedia(1);if(fetchOrgPaths)fetchOrgPaths();if(fetchGlobalTags)fetchGlobalTags();if(tagManagementModal && tagManagementModal.style.display==='block' && populateManageTagsList)populateManageTagsList()}});
    if(prevPageBtn) prevPageBtn.addEventListener('click', () => { if(currentPage>1){clearSelectionsAndActiveTags();fetchMedia(currentPage-1)} });
    if(nextPageBtn) nextPageBtn.addEventListener('click', () => { if(currentPage<totalPages){clearSelectionsAndActiveTags();fetchMedia(currentPage+1)} });
    const allModals=document.querySelectorAll('.modal');const closeButtons=document.querySelectorAll('.close-modal-btn');function openModal(modalId){const modal=document.getElementById(modalId);if(modal)modal.style.display='block'}function closeModal(modalElement){if(modalElement)modalElement.style.display='none'}if(closeButtons)closeButtons.forEach(b=>{b.onclick=function(){closeModal(b.closest('.modal'))}});window.onclick=function(event){allModals.forEach(m=>{if(event.target==m)closeModal(m)})};let currentViewIndex=-1;function openImageViewer(mediaId){const i=currentMediaItems.findIndex(m=>m.id===mediaId);if(i===-1)return;currentViewIndex=i;updateImageViewerContent();openModal('image-viewer-modal')}function updateImageViewerContent(){if(currentViewIndex<0||currentViewIndex>=currentMediaItems.length)return;const item=currentMediaItems[currentViewIndex];if(fullImage)fullImage.src=`/api/media/file/${item.id}`;if(modalCaption)modalCaption.textContent=item.filename;if(modalPrev)modalPrev.style.display=currentViewIndex>0?'block':'none';if(modalNext)modalNext.style.display=currentViewIndex<currentMediaItems.length-1?'block':'none'}if(modalPrev)modalPrev.onclick=()=>{if(currentViewIndex>0){currentViewIndex--;updateImageViewerContent()}};if(modalNext)modalNext.onclick=()=>{if(currentViewIndex<currentMediaItems.length-1){currentViewIndex++;updateImageViewerContent()}};document.addEventListener('keydown',(event)=>{if(imageViewerModal && imageViewerModal.style.display==='block'){if(event.key==='ArrowLeft')modalPrev.click();else if(event.key==='ArrowRight')modalNext.click();else if(event.key==='Escape')closeModal(imageViewerModal)}});
    if(filterConfigBtn) filterConfigBtn.onclick=()=>{
        if(filterStatusDiv)filterStatusDiv.textContent='';
        openModal('filter-config-modal');
        // Refresh CodeMirror instance if it exists and modal is opened,
        // as it might not render correctly if initialized while hidden.
        if (filterCodeEditor) {
            setTimeout(() => filterCodeEditor.refresh(), 0);
        }
        renderFilterFavorites(); // Load and display favorites when modal opens
    };

    if (saveFilterFavoriteBtn) {
        saveFilterFavoriteBtn.addEventListener('click', () => {
            const snippetToSave = filterCodeEditor ? filterCodeEditor.getValue() : filterFunctionInput.value;
            addFilterFavorite(snippetToSave);
        });
    }

    if(applyFilterBtn) applyFilterBtn.addEventListener('click',async()=>{
        const fc = filterCodeEditor ? filterCodeEditor.getValue() : filterFunctionInput.value; // Get value from CodeMirror if available
        try{
            const r=await fetch('/api/media/filter_config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filter_code:fc})});
            const rs=await r.json();
            if(r.ok){
                if(filterStatusDiv){filterStatusDiv.textContent='Filter applied!';filterStatusDiv.style.color='green'}
                if(filterConfigModal)closeModal(filterConfigModal);
                clearSelectionsAndActiveTags();
                fetchMedia(1);
            }else{
                if(filterStatusDiv){filterStatusDiv.textContent=`Error: ${rs.error||'Filter error'}`;filterStatusDiv.style.color='red'}
            }
        }catch(e){
            if(filterStatusDiv){filterStatusDiv.textContent='Network error.';filterStatusDiv.style.color='red'}
        }
    });
    if(clearFilterBtn) clearFilterBtn.addEventListener('click',async()=>{try{const r=await fetch('/api/media/filter_config',{method:'DELETE'});const rs=await r.json();if(r.ok){
        if(filterCodeEditor) {
            filterCodeEditor.setValue(''); // Clear CodeMirror instance
        } else if (filterFunctionInput) {
            filterFunctionInput.value=''; // Fallback for plain textarea
        }
        if(filterStatusDiv){filterStatusDiv.textContent='Filter cleared!';filterStatusDiv.style.color='green'}clearSelectionsAndActiveTags();fetchMedia(1)}else{if(filterStatusDiv){filterStatusDiv.textContent=`Error: ${rs.error||'Filter clear error'}`;filterStatusDiv.style.color='red'}}}catch(e){if(filterStatusDiv){filterStatusDiv.textContent='Network error.';filterStatusDiv.style.color='red'}}});
    if(tagManagementBtn) tagManagementBtn.onclick=()=>{if(tagManagementStatusDiv)tagManagementStatusDiv.textContent='';openModal('tag-management-modal');if(populateManageTagsList)populateManageTagsList()};

    // Initialize CodeMirror for the filter function input
    if (filterFunctionInput && typeof CodeMirror !== 'undefined') {
        filterCodeEditor = CodeMirror.fromTextArea(filterFunctionInput, {
            mode: "python",
            theme: "material", // Make sure you included material.css or choose another theme
            lineNumbers: true,
            indentUnit: 4,
            smartIndent: true,
            tabSize: 4,
            indentWithTabs: false, // Use spaces for tabs, common Python practice
            // extraKeys: {"Tab": "indentMore", "Shift-Tab": "indentLess"} // Usually default
        });
        // Adjust size if needed, e.g., when modal is shown or based on content
        // filterCodeEditor.setSize(null, "auto"); // Example: auto height based on content
    } else if (!filterFunctionInput) {
        console.warn("filterFunctionInput textarea not found for CodeMirror initialization.");
    } else if (typeof CodeMirror === 'undefined') {
        console.warn("CodeMirror library not loaded. Filter input will be a plain textarea.");
    }


    fetchMedia(currentPage, currentSortBy, currentSortOrder);
    if(fetchOrgPaths)fetchOrgPaths();
    if(fetchGlobalTags)fetchGlobalTags();
    // updateUndoButtonState(); // Removed

    window.appContext = { refreshPhotoWall: () => fetchMedia(currentPage, currentSortBy, currentSortOrder), clearSelectionsAndActiveTags: clearSelectionsAndActiveTags, getActiveTagNames: () => Array.from(activeTagNamesForOperations), getSelectedMediaIds: () => Array.from(selectedMediaIds) };
});
