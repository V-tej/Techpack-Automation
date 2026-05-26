document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const dropContent = document.querySelector('.drop-content');
    const removeFileBtn = document.getElementById('removeFile');
    const submitBtn = document.getElementById('submitBtn');
    const uploadForm = document.getElementById('uploadForm');
    const brandInput = document.getElementById('brand');
    const styleInput = document.getElementById('style');

    // Status elements
    const statusBadge = document.getElementById('statusBadge');
    const logsContainer = document.getElementById('logsContainer');
    const logList = document.getElementById('logList');
    const logsEmpty = document.getElementById('logsEmpty');
    const btnSpinner = document.getElementById('btnSpinner');
    const btnText = submitBtn.querySelector('span');

    // Results elements
    const resultsContainer = document.getElementById('resultsContainer');
    const statPages = document.getElementById('statPages');
    const statClassified = document.getElementById('statClassified');
    const statImages = document.getElementById('statImages');
    const statUnclassified = document.getElementById('statUnclassified');
    const categoriesList = document.getElementById('categoriesList');
    const outputPath = document.getElementById('outputPath');

    // Enhanced elements
    const headerInfo = document.getElementById('headerInfo');
    const artworkBody = document.getElementById('artworkBody');
    const vendorsSection = document.getElementById('vendorsSection');
    const vendorTags = document.getElementById('vendorTags');

    let currentFile = null;
    let pollInterval = null;

    // --- Drag and Drop Handling ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function () {
        handleFiles(this.files);
    });

    // Handle selected file
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type !== 'application/pdf') {
                alert('Please upload a PDF file.');
                return;
            }
            // Limit to 100MB
            const maxSize = 100 * 1024 * 1024;
            if (file.size > maxSize) {
                alert('File is too large. Maximum allowed size is 100MB.');
                return;
            }
            currentFile = file;

            // Auto-fill brand if empty
            if (!brandInput.value) brandInput.value = "BRAND";

            dropContent.style.display = 'none';
            fileInfo.style.display = 'flex';
            fileInfo.querySelector('.file-name').textContent = file.name;
            checkFormValidity();
        }
    }

    // Remove selected file
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        currentFile = null;
        fileInput.value = '';
        dropContent.style.display = 'block';
        fileInfo.style.display = 'none';
        checkFormValidity();
    });

    // Form Validation — style is optional now (auto-detected)
    function checkFormValidity() {
        if (currentFile && brandInput.value.trim()) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
    }

    brandInput.addEventListener('input', checkFormValidity);
    styleInput.addEventListener('input', checkFormValidity);

    // --- Form Submission ---
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!currentFile) return;

        // UI updates for processing
        submitBtn.disabled = true;
        btnText.textContent = 'Processing...';
        btnSpinner.style.display = 'block';
        statusBadge.textContent = 'Processing';
        statusBadge.className = 'badge badge-processing';
        resultsContainer.style.display = 'none';

        logList.innerHTML = '';
        logsEmpty.style.display = 'none';

        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('brand', brandInput.value.trim());
        formData.append('style', styleInput.value.trim() || 'STYLE');

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (response.status === 413) {
                handleError('File is too large for the server. Maximum allowed size is 100MB.');
                return;
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                if (response.ok) {
                    pollJobStatus(data.job_id);
                } else {
                    handleError(data.error || 'Upload failed');
                }
            } else {
                handleError(`Server error (${response.status})`);
            }
        } catch (error) {
            handleError('Network error occurred. The file might be too large.');
        }
    });

    // --- Polling Job Status ---
    function pollJobStatus(jobId) {
        let lastLogCount = 0;

        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/job/${jobId}`);
                const data = await response.json();

                // Update logs
                if (data.logs && data.logs.length > lastLogCount) {
                    for (let i = lastLogCount; i < data.logs.length; i++) {
                        const log = data.logs[i];
                        const li = document.createElement('li');
                        li.innerHTML = `<span class="log-time">[${log.time}]</span> ${log.msg}`;
                        logList.appendChild(li);
                    }
                    lastLogCount = data.logs.length;
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }

                // Check status
                if (data.status === 'done') {
                    clearInterval(pollInterval);
                    handleSuccess(data.result);
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    handleError(data.error);
                }
            } catch (error) {
                console.error("Polling error:", error);
            }
        }, 1000);
    }

    function handleSuccess(result) {
        // Reset button
        submitBtn.disabled = false;
        btnText.textContent = 'Process Another';
        btnSpinner.style.display = 'none';

        statusBadge.textContent = 'Complete';
        statusBadge.className = 'badge badge-done';

        // Update stats
        statPages.textContent = result.total_pages;
        statClassified.textContent = result.classified;
        statUnclassified.textContent = result.unclassified;
        statImages.textContent = result.images_extracted || 0;

        // Show header info if available
        if (result.header && (result.header.style_no || result.header.buyer)) {
            headerInfo.style.display = 'block';
            document.getElementById('infoStyle').textContent = result.header.style_no || '—';
            document.getElementById('infoBuyer').textContent = result.header.buyer || '—';
            document.getElementById('infoSeason').textContent = result.header.season || '—';
            document.getElementById('infoGarment').textContent = result.header.garment_type || '—';
        } else {
            headerInfo.style.display = 'none';
        }

        // Update categories grid — COLOR CODED
        categoriesList.innerHTML = '';
        for (const [cat, info] of Object.entries(result.categories)) {
            const colorHex = info.color_hex || '#8b5cf6';
            const count = info.count || info;
            const colorName = info.color_name || '';

            const el = document.createElement('div');
            el.className = 'cat-badge';
            el.style.background = `${colorHex}15`;
            el.style.border = `1px solid ${colorHex}40`;
            el.innerHTML = `
                <div class="cat-count" style="color: ${colorHex}">${count}</div>
                <div class="cat-name" style="color: ${colorHex}">${cat.replace(/_/g, ' ')}</div>
            `;
            categoriesList.appendChild(el);
        }

        // Populate artwork table
        artworkBody.innerHTML = '';
        if (result.entries && result.entries.length > 0) {
            result.entries.forEach(entry => {
                const row = document.createElement('tr');
                const colorHex = entry.color_hex || '#8b5cf6';
                const statusClass = `status-${entry.status.toLowerCase()}`;

                row.innerHTML = `
                    <td><strong>${entry.id}</strong></td>
                    <td><span class="type-dot" style="background: ${colorHex}"></span>${entry.category.replace(/_/g, ' ')}</td>
                    <td>${entry.artwork_name || '—'}</td>
                    <td>${entry.placement || '—'}</td>
                    <td title="${entry.color}">${truncate(entry.color, 25)}</td>
                    <td>${entry.size || '—'}</td>
                    <td>${entry.page || '—'}</td>
                    <td><span class="status-badge ${statusClass}">${entry.status}</span></td>
                    <td>
                        <button class="action-btn approve" onclick="approveArtwork('${entry.id}')" title="Approve">✓</button>
                        <button class="action-btn reject" onclick="rejectArtwork('${entry.id}')" title="Reject">✗</button>
                    </td>
                `;
                artworkBody.appendChild(row);
            });
        }

        // Show vendors
        if (result.vendors && result.vendors.length > 0) {
            vendorsSection.style.display = 'block';
            vendorTags.innerHTML = '';
            result.vendors.forEach(v => {
                const tag = document.createElement('span');
                tag.className = 'vendor-tag';
                tag.textContent = v;
                vendorTags.appendChild(tag);
            });
        } else {
            vendorsSection.style.display = 'none';
        }

        outputPath.textContent = result.output_dir;

        // Show results with animation
        resultsContainer.style.display = 'block';
        resultsContainer.style.animation = 'fadeIn 0.5s ease';
    }

    function handleError(errorMsg) {
        submitBtn.disabled = false;
        btnText.textContent = 'Try Again';
        btnSpinner.style.display = 'none';

        statusBadge.textContent = 'Error';
        statusBadge.className = 'badge badge-error';

        const li = document.createElement('li');
        li.style.color = '#ef4444';
        li.innerHTML = `❌ Error: ${errorMsg}`;
        logList.appendChild(li);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    function truncate(text, max) {
        if (!text) return '—';
        return text.length > max ? text.substring(0, max) + '...' : text;
    }

    // --- Auto-Reconnect to Active/Queued Jobs on Page Load ---
    async function checkActiveJobs() {
        try {
            const response = await fetch('/api/jobs');
            const jobsList = await response.json();
            if (jobsList && jobsList.length > 0) {
                const latestJob = jobsList[0]; // Since reversed in list_jobs, latest is first
                if (latestJob.status === 'queued' || latestJob.status === 'processing') {
                    console.log("Found active/queued job on load, reconnecting:", latestJob.id);
                    
                    // UI updates to show processing
                    submitBtn.disabled = true;
                    btnText.textContent = 'Processing...';
                    btnSpinner.style.display = 'block';
                    
                    // Set correct badge style
                    statusBadge.textContent = latestJob.status === 'queued' ? 'Queued' : 'Processing';
                    statusBadge.className = `badge badge-${latestJob.status}`;
                    resultsContainer.style.display = 'none';
                    
                    logList.innerHTML = '';
                    logsEmpty.style.display = 'none';
                    
                    // Pre-fill inputs if available
                    brandInput.value = latestJob.brand || 'BRAND';
                    styleInput.value = latestJob.style || 'STYLE';
                    
                    pollJobStatus(latestJob.id);
                }
            }
        } catch (error) {
            console.error("Error checking active jobs:", error);
        }
    }

    // Start auto-reconnect check on startup
    checkActiveJobs();
});

// --- Global approval functions ---
async function approveArtwork(artworkId) {
    try {
        const res = await fetch(`/api/artworks/${artworkId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'Approved' })
        });
        if (res.ok) {
            // Update the badge in the table
            updateStatusInTable(artworkId, 'Approved');
        }
    } catch (err) {
        console.error('Approval failed:', err);
    }
}

async function rejectArtwork(artworkId) {
    try {
        const res = await fetch(`/api/artworks/${artworkId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'Rejected' })
        });
        if (res.ok) {
            updateStatusInTable(artworkId, 'Rejected');
        }
    } catch (err) {
        console.error('Rejection failed:', err);
    }
}

function updateStatusInTable(artworkId, newStatus) {
    const rows = document.querySelectorAll('#artworkBody tr');
    rows.forEach(row => {
        const idCell = row.querySelector('td:first-child strong');
        if (idCell && idCell.textContent === artworkId) {
            const badge = row.querySelector('.status-badge');
            if (badge) {
                badge.textContent = newStatus;
                badge.className = `status-badge status-${newStatus.toLowerCase()}`;
            }
        }
    });
}
