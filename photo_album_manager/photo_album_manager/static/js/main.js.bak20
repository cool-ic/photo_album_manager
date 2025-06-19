document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded. Initializing application features. Displaying tags on thumbnails.');

    // Cache DOM elements
    const photoWall = document.getElementById('photo-wall');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const pageInfoSpan = document.getElementById('page-info');
    const orgPathsList = document.getElementById('org-paths-list');
    const globalTagsListUl = document.getElementById('global-tags-list');
    const sizeInput = document.getElementById('size-input');
    const sortBySelect = document.getElementById('sort-by');
    const sortOrderSelect = document.getElementById('sort-order');
    const refreshBtn = document.getElementById('refresh-btn');
    const filterConfigBtn = document.getElementById('filter-config-btn');
    const filterConfigModal = document.getElementById('filter-config-modal');
    const filterFunctionInput = document.getElementById('filter-function-input');
    const applyFilterBtn = document.getElementById('apply-filter-btn');
    const clearFilterBtn = document.getElementById('clear-filter-btn');
    const filterStatusDiv = document.getElementById('filter-status');
    const tagManagementBtn = document.getElementById('tag-management-btn');
    const tagManagementModal = document.getElementById('tag-management-modal');
    const newTagInput = document.getElementById('new-tag-input');
    const addNewTagBtn = document.getElementById('add-new-tag-btn');
    const manageTagsListUl = document.getElementById('manage-tags-list');
    const tagManagementStatusDiv = document.getElementById('tag-management-status');
    const batchTagBtn = document.getElementById('batch-tag-btn');
    const undoBtn = document.getElementById('undo-btn');
    const imageViewerModal = document.getElementById('image-viewer-modal');
    const fullImage = document.getElementById('full-image');
    const modalCaption = document.querySelector('.modal-caption');
    const modalPrev = document.querySelector('.modal-prev');
    const modalNext = document.querySelector('.modal-next');

    // Application State
    let currentPage = 1, totalPages = 1;
    let photosPerRow = parseInt(sizeInput.value) || 5;
    if (photoWall) photoWall.style.setProperty('--photos-per-row', photosPerRow);
    let currentSortBy = sortBySelect.value, currentSortOrder = sortOrderSelect.value;
    const selectedMediaIds = new Set();
    const activeTagNamesForOperations = new Set();
    let currentMediaItems = [], isXKeyPressed = false, resizeTimeout, lastCalculatedPerPage = 0;
    let lastTaggingAction = null;

    function updateUndoButtonState() { if (undoBtn) { undoBtn.disabled = !lastTaggingAction; undoBtn.title = lastTaggingAction ? `Undo last tagging action` : 'Nothing to undo'; } }
    document.addEventListener('keydown', (event) => { if (event.key === 'x' || event.key === 'X') isXKeyPressed = true; });
    document.addEventListener('keyup', (event) => { if (event.key === 'x' || event.key === 'X') isXKeyPressed = false; });

    // --- Core Functions (some minified for focus) ---
    function getCalculatedPerPage() { const c=(parseInt(photoWall.style.getPropertyValue('--photos-per-row'))||photosPerRow),w=photoWall.clientWidth,a=photoWall.parentElement?photoWall.parentElement.clientHeight:window.innerHeight,g=10;if(w===0||a===0||c===0)return c>0?c*4:20;const cl=(w-(c-1)*g)/c,t=cl,s=t+g;if(s<=g)return c;const n=Math.max(1,Math.floor(a/s)),p=c*n;return Math.max(c,p); }
    async function fetchMedia(page = 1, sortBy = currentSortBy, sortOrder = currentSortOrder) { if(photoWall)void photoWall.offsetHeight;const cp=getCalculatedPerPage();lastCalculatedPerPage=cp;const u=`/api/media?page=${page}&per_page=${cp}&sort_by=${sortBy}&sort_order=${sortOrder}`;console.log(`Fetching: ${u}`);try{const r=await fetch(u);if(!r.ok)throw new Error(`${r.status}: ${await r.text()}`);const d=await r.json();currentMediaItems=d.media;renderPhotoWall(currentMediaItems);currentPage=d.current_page;totalPages=d.total_pages;updatePaginationControls()}catch(e){console.error('Fetch error:',e);photoWall.innerHTML=`<p>Error: ${e.message}</p>`} }

    function renderPhotoWall(mediaItems) {
        console.log(`Rendering photo wall with ${mediaItems ? mediaItems.length : 0} items.`);
        if (!photoWall) { console.error("photoWall element not found during render."); return; }
        photoWall.innerHTML = '';
        if (!mediaItems || mediaItems.length === 0) {
            photoWall.innerHTML = '<p>No media found matching your criteria.</p>';
            return;
        }
        console.log(`Photo wall using CSS Grid with '--photos-per-row': ${photoWall.style.getPropertyValue('--photos-per-row')}`);

        mediaItems.forEach(item => {
            const thumbItem = document.createElement('div');
            thumbItem.classList.add('thumbnail-item');
            thumbItem.dataset.id = String(item.id); // Ensure dataset.id is a string
            thumbItem.style.backgroundImage = `url(/api/media/thumbnail/${item.id})`;

            if (selectedMediaIds.has(item.id)) { // Check if item.id is in selectedMediaIds
                thumbItem.classList.add('selected');
            }

            // --- Add Tags Overlay ---
            if (item.tags && item.tags.length > 0) {
                const tagsOverlay = document.createElement('div');
                tagsOverlay.classList.add('thumbnail-tags-overlay');
                // Display a limited number of tags, e.g., first 3
                item.tags.slice(0, 3).forEach(tagName => {
                    const tagSpan = document.createElement('span');
                    tagSpan.classList.add('thumbnail-tag');
                    tagSpan.textContent = tagName;
                    tagsOverlay.appendChild(tagSpan);
                });
                if (item.tags.length > 3) {
                    const moreTagsSpan = document.createElement('span');
                    moreTagsSpan.classList.add('thumbnail-tag-more');
                    moreTagsSpan.textContent = '...';
                    tagsOverlay.appendChild(moreTagsSpan);
                }
                thumbItem.appendChild(tagsOverlay);
            }
            // --- End Tags Overlay ---

            thumbItem.addEventListener('click', (event) => {
                if (isXKeyPressed) { event.preventDefault(); openImageViewer(item.id); }
                else { toggleSelection(thumbItem, item.id); }
            });

            thumbItem.addEventListener('contextmenu', async (event) => {
                event.preventDefault();
                const mediaId = parseInt(item.id);
                const activeTags = Array.from(activeTagNamesForOperations);
                if (activeTags.length === 0) { console.warn('[QuickTag] No active tags selected for tagging.'); return; }

                console.log(`[QuickTag] Right-click on media ID: ${mediaId}. Active tags to apply:`, activeTags);
                try {
                    const response = await fetch(`/api/media/${mediaId}/tags`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({tag_names: activeTags})});
                    const result = await response.json();
                    if (response.ok) {
                        console.log(`[QuickTag] Media ID ${mediaId} tagged. API response tags:`, result.tags);
                        const updatedItemIndex = currentMediaItems.findIndex(m => m.id === mediaId);
                        if (updatedItemIndex > -1) {
                            const previousTags = [...(currentMediaItems[updatedItemIndex].tags || [])];
                            currentMediaItems[updatedItemIndex].tags = result.tags; // Update with tags from server
                            lastTaggingAction = {type: 'add_quick', mediaIds: [mediaId], tagNamesApplied: [...activeTags], previousTagsMap: new Map([[mediaId, previousTags]])};
                            updateUndoButtonState();
                            console.log('[Undo] Stored last action for quick tag:', lastTaggingAction);
                            renderPhotoWall(currentMediaItems); // Re-render to show updated tags on this item
                        }
                        // Visual feedback for the specific item can be tricky if full re-render happens immediately.
                        // The re-render will include the new tags.
                        // For a brief highlight *before* re-render, it would need to be applied and then cleared,
                        // but renderPhotoWall clears the slate.
                    } else {
                        console.error('[QuickTag] Error tagging media:', result.error);
                        alert(`Error tagging media: ${result.error || 'Unknown server error'}`);
                    }
                } catch (error) {
                    console.error('[QuickTag] Network error or other issue during quick tagging:', error);
                    alert('Failed to apply tags due to a network or server issue.');
                }
            });
            photoWall.appendChild(thumbItem);
        });
    }

    function toggleSelection(el, id) { // id is already a number from item.id
        const numId = parseInt(id); // Ensure it's a number if dataset.id was string
        if(selectedMediaIds.has(numId)){selectedMediaIds.delete(numId);el.classList.remove('selected')}
        else{selectedMediaIds.add(numId);el.classList.add('selected')}
        console.log('Current selection IDs:',Array.from(selectedMediaIds));
    }
    function updatePaginationControls() { pageInfoSpan.textContent=`Page ${currentPage} of ${totalPages}`;prevPageBtn.disabled=currentPage<=1;nextPageBtn.disabled=currentPage>=totalPages }
    async function fetchOrgPaths() { try{const r=await fetch('/api/org_paths');const d=await r.json();orgPathsList.innerHTML='';d.forEach(p=>{const l=document.createElement('li');l.textContent=p;orgPathsList.appendChild(l)})}catch(e){} }
    async function fetchGlobalTags() { if(!globalTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();globalTagsListUl.innerHTML='';if(d.length===0)globalTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const l=document.createElement('li');l.textContent=t.name;l.dataset.tagId=t.id;l.dataset.tagName=t.name;if(activeTagNamesForOperations.has(t.name))l.classList.add('active-for-tagging');l.addEventListener('click',()=>{if(activeTagNamesForOperations.has(t.name)){activeTagNamesForOperations.delete(t.name);l.classList.remove('active-for-tagging')}else{activeTagNamesForOperations.add(t.name);l.classList.add('active-for-tagging')}});globalTagsListUl.appendChild(l)})}catch(e){globalTagsListUl.innerHTML='<li>Error tags.</li>'} }
    async function handleDeleteTag(tagId, tagName) { if(!confirm(`Delete '${tagName}'?`))return;try{const r=await fetch(`/api/tags/${tagId}`,{method:'DELETE'});const rs=await r.json();if(r.ok){populateManageTagsList();fetchGlobalTags();window.appContext.refreshPhotoWall()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} }
    async function populateManageTagsList() { if(!manageTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();manageTagsListUl.innerHTML='';if(d.length===0)manageTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const li=document.createElement('li');const s=document.createElement('span');s.textContent=t.name;li.appendChild(s);li.dataset.tagId=t.id;const b=document.createElement('button');b.textContent='Delete';b.style.cssText='margin-left:10px;padding:2px 5px;font-size:0.8em;background-color:#dc3545;color:white;border:none;cursor:pointer;';b.onclick=(e)=>{e.stopPropagation();handleDeleteTag(t.id,t.name)};li.appendChild(b);manageTagsListUl.appendChild(li)})}catch(e){manageTagsListUl.innerHTML='<li>Error tags.</li>'} }
    if(addNewTagBtn){addNewTagBtn.addEventListener('click', async () => { const tn=newTagInput.value.trim();if(!tn){alert('Empty tag.');return}try{const r=await fetch('/api/tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:tn})});const rs=await r.json();if(r.ok){newTagInput.value='';populateManageTagsList();fetchGlobalTags()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} });}
    if(batchTagBtn) batchTagBtn.addEventListener('click', async () => { const mIds=Array.from(selectedMediaIds);const tApply=Array.from(activeTagNamesForOperations);if(mIds.length===0||tApply.length===0){alert('Select photos & active tags.');return}const o=batchTagBtn.textContent;batchTagBtn.textContent='Tagging...';batchTagBtn.disabled=true;let sC=0,eC=0;const pTagsMap=new Map();for(const mId of mIds){try{const idx=currentMediaItems.findIndex(m=>m.id===mId);if(idx>-1){pTagsMap.set(mId,[...(currentMediaItems[idx].tags||[])])}else{pTagsMap.set(mId,[])}const r=await fetch(`/api/media/${mId}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:tApply})});const rs=await r.json();if(r.ok){sC++;if(idx>-1)currentMediaItems[idx].tags=rs.tags}else{eC++}}catch(e){eC++}}batchTagBtn.textContent=o;batchTagBtn.disabled=false;alert(`Batch: ${sC} success, ${eC} failed.`);if(sC>0){lastTaggingAction={type:'add_batch',mediaIds:[...mIds],tagNamesApplied:[...tApply],previousTagsMap:pTagsMap};updateUndoButtonState();renderPhotoWall(currentMediaItems);}});
    if(undoBtn) undoBtn.addEventListener('click', async () => { if(!lastTaggingAction){alert('Nothing to undo.');return}const{type,mediaIds,tagNamesApplied,previousTagsMap}=lastTaggingAction;let uS=true,uEC=0;const o=undoBtn.textContent;undoBtn.textContent='Undoing...';undoBtn.disabled=true;if(type==='add_quick'||type==='add_batch'){for(const mId of mediaIds){const tRestore=previousTagsMap.get(mId);if(tRestore===undefined)continue;try{const r=await fetch(`/api/media/${mId}/tags`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:tRestore})});const rs=await r.json();if(r.ok){const idx=currentMediaItems.findIndex(m=>m.id===mId);if(idx>-1)currentMediaItems[idx].tags=rs.tags}else{uS=false;uEC++}}catch(e){uS=false;uEC++}}}else{uS=false}undoBtn.textContent=o;if(uS&&uEC===0){alert('Undo successful.');lastTaggingAction=null}else if(uEC>0){alert(`Undo partially failed for ${uEC} items.`)}else{alert('Undo failed.')}updateUndoButtonState();renderPhotoWall(currentMediaItems)});
    function clearSelectionsAndUndoHistory() { selectedMediaIds.clear(); activeTagNamesForOperations.clear(); lastTaggingAction = null; updateUndoButtonState(); fetchGlobalTags(); console.log("FRONTEND: Cleared selections, active tags, undo history.");if(document.readyState==='complete'||document.readyState==='interactive')renderPhotoWall(currentMediaItems) }

    // --- Event Listeners for Menu Controls & Modals (rest are largely unchanged) ---
    sizeInput.addEventListener('change', () => { const newSize=parseInt(sizeInput.value);if(newSize>0){photosPerRow=newSize;photoWall.style.setProperty('--photos-per-row',photosPerRow);clearSelectionsAndUndoHistory();fetchMedia(1)}else{sizeInput.value=photosPerRow} });
    sortBySelect.addEventListener('change', () => { currentSortBy=sortBySelect.value;clearSelectionsAndUndoHistory();fetchMedia(1) });
    sortOrderSelect.addEventListener('change', () => { currentSortOrder=sortOrderSelect.value;clearSelectionsAndUndoHistory();fetchMedia(1) });
    refreshBtn.addEventListener('click', async () => {const o=refreshBtn.textContent;refreshBtn.textContent='Scanning...';refreshBtn.disabled=true;let s=false;try{const r=await fetch('/api/scan/trigger',{method:'POST'});const t=await r.json().catch(()=>({error:"JSON Error"}));if(!r.ok){alert(`Scan Error: ${t.error||'Unknown'}`);s=true}else{alert('Scan complete.')}}catch(e){alert('Scan Network Error.');s=true}refreshBtn.textContent=o;refreshBtn.disabled=false;if(!s){clearSelectionsAndUndoHistory();fetchMedia(1);fetchOrgPaths();fetchGlobalTags();if(tagManagementModal && tagManagementModal.style.display==='block')populateManageTagsList()}});
    prevPageBtn.addEventListener('click', () => { if(currentPage>1){clearSelectionsAndUndoHistory();fetchMedia(currentPage-1)} });
    nextPageBtn.addEventListener('click', () => { if(currentPage<totalPages){clearSelectionsAndUndoHistory();fetchMedia(currentPage+1)} });
    const allModals=document.querySelectorAll('.modal');const closeButtons=document.querySelectorAll('.close-modal-btn');function openModal(modalId){const modal=document.getElementById(modalId);if(modal)modal.style.display='block'}function closeModal(modalElement){if(modalElement)modalElement.style.display='none'}closeButtons.forEach(b=>{b.onclick=function(){closeModal(b.closest('.modal'))}});window.onclick=function(event){allModals.forEach(m=>{if(event.target==m)closeModal(m)})};let currentViewIndex=-1;function openImageViewer(mediaId){const i=currentMediaItems.findIndex(m=>m.id===mediaId);if(i===-1)return;currentViewIndex=i;updateImageViewerContent();openModal('image-viewer-modal')}function updateImageViewerContent(){if(currentViewIndex<0||currentViewIndex>=currentMediaItems.length)return;const item=currentMediaItems[currentViewIndex];fullImage.src=`/api/media/file/${item.id}`;modalCaption.textContent=item.filename;modalPrev.style.display=currentViewIndex>0?'block':'none';modalNext.style.display=currentViewIndex<currentMediaItems.length-1?'block':'none'}modalPrev.onclick=()=>{if(currentViewIndex>0){currentViewIndex--;updateImageViewerContent()}};modalNext.onclick=()=>{if(currentViewIndex<currentMediaItems.length-1){currentViewIndex++;updateImageViewerContent()}};document.addEventListener('keydown',(event)=>{if(imageViewerModal.style.display==='block'){if(event.key==='ArrowLeft')modalPrev.click();else if(event.key==='ArrowRight')modalNext.click();else if(event.key==='Escape')closeModal(imageViewerModal)}});filterConfigBtn.onclick=()=>{filterStatusDiv.textContent='';openModal('filter-config-modal')};applyFilterBtn.addEventListener('click',async()=>{const fc=filterFunctionInput.value;try{const r=await fetch('/api/media/filter_config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filter_code:fc})});const rs=await r.json();if(r.ok){filterStatusDiv.textContent='Filter applied!';filterStatusDiv.style.color='green';closeModal(filterConfigModal);clearSelectionsAndUndoHistory();fetchMedia(1)}else{filterStatusDiv.textContent=`Error: ${rs.error||'Filter error'}`;filterStatusDiv.style.color='red'}}catch(e){filterStatusDiv.textContent='Network error.';filterStatusDiv.style.color='red'}});clearFilterBtn.addEventListener('click',async()=>{try{const r=await fetch('/api/media/filter_config',{method:'DELETE'});const rs=await r.json();if(r.ok){filterFunctionInput.value='';filterStatusDiv.textContent='Filter cleared!';filterStatusDiv.style.color='green';clearSelectionsAndUndoHistory();fetchMedia(1)}else{filterStatusDiv.textContent=`Error: ${rs.error||'Filter clear error'}`;filterStatusDiv.style.color='red'}}catch(e){filterStatusDiv.textContent='Network error.';filterStatusDiv.style.color='red'}});
    if(tagManagementBtn){tagManagementBtn.onclick=()=>{tagManagementStatusDiv.textContent='';openModal('tag-management-modal');populateManageTagsList()};}

    // Initial Data Load
    fetchMedia(currentPage, currentSortBy, currentSortOrder);
    fetchOrgPaths();
    fetchGlobalTags();
    updateUndoButtonState(); // Initialize undo button state

    window.appContext = { refreshPhotoWall: () => fetchMedia(currentPage, currentSortBy, currentSortOrder), clearSelections: clearSelectionsAndUndoHistory, getActiveTagNames: () => Array.from(activeTagNamesForOperations), getSelectedMediaIds: () => Array.from(selectedMediaIds), getLastTaggingAction: () => lastTaggingAction, setLastTaggingAction: (action) => { lastTaggingAction = action; updateUndoButtonState(); } };
});
