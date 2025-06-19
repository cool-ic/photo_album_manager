document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded. Initializing application features. Implementing Undo for Tagging.');

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
    let lastTaggingAction = null; // { type: 'add_quick'/'add_batch', mediaIds: [], tagNamesApplied: [], previousTagsMap: Map<mediaId, oldTagsList> }

    // --- Utility to update Undo Button State ---
    function updateUndoButtonState() {
        if (undoBtn) {
            undoBtn.disabled = !lastTaggingAction;
            if (lastTaggingAction) {
                const actionType = lastTaggingAction.type === 'add_quick' ? 'Quick Tag' : 'Batch Tag';
                const mediaCount = lastTaggingAction.mediaIds.length;
                undoBtn.title = `Undo last action: ${actionType} on ${mediaCount} item(s)`;
            } else {
                undoBtn.title = 'Nothing to undo';
            }
        }
    }

    document.addEventListener('keydown', (event) => { if (event.key === 'x' || event.key === 'X') isXKeyPressed = true; });
    document.addEventListener('keyup', (event) => { if (event.key === 'x' || event.key === 'X') isXKeyPressed = false; });

    // --- Minified/Unchanged Core Functions ---
    function getCalculatedPerPage() { const currentPhotosPerRowVal=parseInt(photoWall.style.getPropertyValue('--photos-per-row'))||photosPerRow;const wallWidth=photoWall.clientWidth;const availableHeight=photoWall.parentElement?photoWall.parentElement.clientHeight:window.innerHeight;const gap=10;if(wallWidth===0||availableHeight===0||currentPhotosPerRowVal===0){return currentPhotosPerRowVal>0?currentPhotosPerRowVal*4:20}const columnWidth=(wallWidth-(currentPhotosPerRowVal-1)*gap)/currentPhotosPerRowVal;const thumbHeight=columnWidth;const singleRowTotalHeight=thumbHeight+gap;if(singleRowTotalHeight<=gap){return currentPhotosPerRowVal}const numRows=Math.max(1,Math.floor(availableHeight/singleRowTotalHeight));const calculatedPerPage=currentPhotosPerRowVal*numRows;return Math.max(currentPhotosPerRowVal,calculatedPerPage); }
    async function fetchMedia(page = 1, sortBy = currentSortBy, sortOrder = currentSortOrder) { if(photoWall)void photoWall.offsetHeight;const calculatedPerPage=getCalculatedPerPage();lastCalculatedPerPage=calculatedPerPage;const apiUrl=`/api/media?page=${page}&per_page=${calculatedPerPage}&sort_by=${sortBy}&sort_order=${sortOrder}`;console.log(`Fetching media from: ${apiUrl}`);try{const response=await fetch(apiUrl);if(!response.ok)throw new Error(`HTTP error! status: ${response.status}, message: ${await response.text()}`);const data=await response.json();currentMediaItems=data.media;renderPhotoWall(currentMediaItems);currentPage=data.current_page;totalPages=data.total_pages;updatePaginationControls()}catch(error){console.error('Error fetching media:',error);photoWall.innerHTML=`<p>Error loading media: ${error.message}. Please try again.</p>`} }

    function renderPhotoWall(mediaItems) {
        if(!photoWall)return; photoWall.innerHTML='';
        if(!mediaItems||mediaItems.length===0){photoWall.innerHTML='<p>No media found.</p>';return}
        mediaItems.forEach(item=>{
            const thumbItem=document.createElement('div');thumbItem.classList.add('thumbnail-item');thumbItem.dataset.id=item.id;thumbItem.style.backgroundImage=`url(/api/media/thumbnail/${item.id})`;
            if(selectedMediaIds.has(item.id))thumbItem.classList.add('selected');
            thumbItem.addEventListener('click',(event)=>{if(isXKeyPressed){event.preventDefault();openImageViewer(item.id)}else{toggleSelection(thumbItem,item.id)}});
            thumbItem.addEventListener('contextmenu',async(event)=>{
                event.preventDefault();const mediaId=parseInt(item.id);const activeTags=Array.from(activeTagNamesForOperations);
                if(activeTags.length===0){console.warn('[QuickTag] No active tags.');return}
                try{
                    const response=await fetch(`/api/media/${mediaId}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:activeTags})});
                    const result=await response.json();
                    if(response.ok){
                        const updatedItemIndex=currentMediaItems.findIndex(m=>m.id===mediaId);
                        if(updatedItemIndex>-1){
                            const previousTags=[...(currentMediaItems[updatedItemIndex].tags || [])]; // Ensure previousTags is always an array
                            currentMediaItems[updatedItemIndex].tags=result.tags;
                            lastTaggingAction={type:'add_quick',mediaIds:[mediaId],tagNamesApplied:[...activeTags],previousTagsMap:new Map([[mediaId, previousTags]])};
                            updateUndoButtonState();
                            console.log('[Undo] Stored last action for quick tag:',lastTaggingAction);
                        }
                        thumbItem.style.outline='3px solid limegreen'; thumbItem.style.outlineOffset='-2px';
                        setTimeout(()=>{thumbItem.style.outline='';thumbItem.style.outlineOffset='';},1200);
                    }else{alert(`Error: ${result.error||'Unknown'}`)}
                }catch(err){alert('Network error.')}
            });
            photoWall.appendChild(thumbItem);
        });
    }

    function toggleSelection(el, id) { if(selectedMediaIds.has(id)){selectedMediaIds.delete(id);el.classList.remove('selected')}else{selectedMediaIds.add(id);el.classList.add('selected')} }
    function updatePaginationControls() { pageInfoSpan.textContent=`Page ${currentPage} of ${totalPages}`;prevPageBtn.disabled=currentPage<=1;nextPageBtn.disabled=currentPage>=totalPages }
    async function fetchOrgPaths() { try{const r=await fetch('/api/org_paths');const d=await r.json();orgPathsList.innerHTML='';d.forEach(p=>{const l=document.createElement('li');l.textContent=p;orgPathsList.appendChild(l)})}catch(e){} }
    async function fetchGlobalTags() { if(!globalTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();globalTagsListUl.innerHTML='';if(d.length===0)globalTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const l=document.createElement('li');l.textContent=t.name;l.dataset.tagId=t.id;l.dataset.tagName=t.name;if(activeTagNamesForOperations.has(t.name))l.classList.add('active-for-tagging');l.addEventListener('click',()=>{if(activeTagNamesForOperations.has(t.name)){activeTagNamesForOperations.delete(t.name);l.classList.remove('active-for-tagging')}else{activeTagNamesForOperations.add(t.name);l.classList.add('active-for-tagging')}});globalTagsListUl.appendChild(l)})}catch(e){globalTagsListUl.innerHTML='<li>Error tags.</li>'} }
    async function handleDeleteTag(tagId, tagName) { if(!confirm(`Delete '${tagName}'?`))return;try{const r=await fetch(`/api/tags/${tagId}`,{method:'DELETE'});const rs=await r.json();if(r.ok){populateManageTagsList();fetchGlobalTags();window.appContext.refreshPhotoWall()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} }
    async function populateManageTagsList() { if(!manageTagsListUl)return;try{const r=await fetch('/api/tags');const d=await r.json();manageTagsListUl.innerHTML='';if(d.length===0)manageTagsListUl.innerHTML='<li>No tags.</li>';d.forEach(t=>{const li=document.createElement('li');const s=document.createElement('span');s.textContent=t.name;li.appendChild(s);li.dataset.tagId=t.id;const b=document.createElement('button');b.textContent='Delete';b.style.cssText='margin-left:10px;padding:2px 5px;font-size:0.8em;background-color:#dc3545;color:white;border:none;cursor:pointer;';b.onclick=(e)=>{e.stopPropagation();handleDeleteTag(t.id,t.name)};li.appendChild(b);manageTagsListUl.appendChild(li)})}catch(e){manageTagsListUl.innerHTML='<li>Error tags.</li>'} }
    if(addNewTagBtn){addNewTagBtn.addEventListener('click', async () => { const tn=newTagInput.value.trim();if(!tn){alert('Empty tag.');return}try{const r=await fetch('/api/tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:tn})});const rs=await r.json();if(r.ok){newTagInput.value='';populateManageTagsList();fetchGlobalTags()}else{alert(`Error: ${rs.error||'Unknown'}`)}}catch(e){alert('Network error.')} });}
    if (batchTagBtn) {
        batchTagBtn.addEventListener('click', async () => {
            const mediaIdsToTag = Array.from(selectedMediaIds);
            const tagsToApply = Array.from(activeTagNamesForOperations);
            if(mediaIdsToTag.length===0||tagsToApply.length===0){alert('Select photos and active tags.');return}
            const originalButtonText=batchTagBtn.textContent;batchTagBtn.textContent='Tagging...';batchTagBtn.disabled=true;let successCount=0,errorCount=0;
            const previousTagsMap = new Map();
            for(const mediaId of mediaIdsToTag){try{const itemIndex=currentMediaItems.findIndex(m=>m.id===mediaId);if(itemIndex>-1){previousTagsMap.set(mediaId,[...(currentMediaItems[itemIndex].tags || [])])}else{previousTagsMap.set(mediaId,[])}const response=await fetch(`/api/media/${mediaId}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag_names:tagsToApply})});const result=await response.json();if(response.ok){successCount++;if(itemIndex>-1)currentMediaItems[itemIndex].tags=result.tags}else{errorCount++}}catch(e){errorCount++}}
            batchTagBtn.textContent=originalButtonText;batchTagBtn.disabled=false;alert(`Batch tag: ${successCount} success, ${errorCount} failed.`);
            if(successCount>0){lastTaggingAction={type:'add_batch',mediaIds:[...mediaIdsToTag],tagNamesApplied:[...tagsToApply],previousTagsMap:previousTagsMap};updateUndoButtonState();}
        });
    }

    // --- Undo Button Logic ---
    if (undoBtn) {
        undoBtn.addEventListener('click', async () => {
            if (!lastTaggingAction) {
                alert('Nothing to undo.');
                return;
            }
            console.log('[Undo] Clicked. Action to undo:', JSON.stringify(lastTaggingAction, (key, value) => value instanceof Map ? Object.fromEntries(value) : value));
            const { type, mediaIds, tagNamesApplied, previousTagsMap } = lastTaggingAction;
            let undoSuccess = true;
            let undoErrorCount = 0;

            const originalButtonText = undoBtn.textContent;
            undoBtn.textContent = 'Undoing...';
            undoBtn.disabled = true;

            if (type === 'add_quick' || type === 'add_batch') {
                for (const mediaId of mediaIds) {
                    const tagsToRestore = previousTagsMap.get(mediaId);
                    if (tagsToRestore === undefined) {
                        console.warn(`[Undo] No previous tags found for media ID ${mediaId}. Cannot restore precisely for this item.`);
                        undoErrorCount++; // Count as an error if we can't find previous state
                        continue;
                    }
                    try {
                        console.log(`[Undo] Restoring tags for media ID ${mediaId} to:`, tagsToRestore);
                        const response = await fetch(`/api/media/${mediaId}/tags`, {
                            method: 'PUT', // Use PUT to set the tags to the exact previous state
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ tag_names: tagsToRestore })
                        });
                        const result = await response.json();
                        if (response.ok) {
                            console.log(`[Undo] Successfully restored tags for media ID ${mediaId}. New tags:`, result.tags);
                            const itemIndex = currentMediaItems.findIndex(m => m.id === mediaId);
                            if (itemIndex > -1) {
                                currentMediaItems[itemIndex].tags = result.tags;
                            }
                        } else {
                            console.error(`[Undo] Error restoring tags for media ID ${mediaId}:`, result.error);
                            undoSuccess = false; undoErrorCount++;
                        }
                    } catch (error) {
                        console.error(`[Undo] Network error restoring tags for media ID ${mediaId}:`, error);
                        undoSuccess = false; undoErrorCount++;
                    }
                }
            } else {
                console.warn('[Undo] Unknown lastTaggingAction type:', type);
                undoSuccess = false; // Mark as not fully successful if type is unknown
            }

            undoBtn.textContent = originalButtonText;
            // Button state will be updated by updateUndoButtonState() below

            if (undoSuccess && undoErrorCount === 0) {
                alert('Undo successful.');
                lastTaggingAction = null;
            } else if (undoErrorCount > 0) {
                alert(`Undo partially failed. ${undoErrorCount} item(s) could not be restored.`);
                // Decide whether to clear lastTaggingAction. For now, let's clear it to prevent repeated partial undo.
                lastTaggingAction = null;
            } else { // Generic failure if undoSuccess is false but no specific item errors counted
                alert('Undo failed or no specific action taken (e.g. unknown type).');
                lastTaggingAction = null; // Clear it in this case too
            }
            updateUndoButtonState();
            renderPhotoWall(currentMediaItems); // Re-render to show updated tags
            // Consider also calling fetchGlobalTags() if undoing a tag deletion could re-create a tag (not current scope)
        });
    }

    // --- Event Listeners & Other Functions (unchanged, minified for subtask focus) ---
    function clearSelectionsAndUndoHistory() { selectedMediaIds.clear(); activeTagNamesForOperations.clear(); lastTaggingAction = null; updateUndoButtonState(); fetchGlobalTags(); console.log("FRONTEND: Selections, active tags, and undo history cleared.");if(document.readyState==='complete'||document.readyState==='interactive')renderPhotoWall(currentMediaItems) }
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
