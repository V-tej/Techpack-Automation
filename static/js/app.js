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
    const statUnclassified = document.getElementById('statUnclassified');
    const categoriesList = document.getElementById('categoriesList');
    const outputPath = document.getElementById('outputPath');

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

    fileInput.addEventListener('change', function() {
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
            currentFile = file;
            
            // Auto-fill inputs if empty
            if(!brandInput.value) brandInput.value = "BRAND";
            if(!styleInput.value) {
                // Try to extract style from filename
                const nameMatch = file.name.match(/^([a-zA-Z0-9-]+)/);
                styleInput.value = nameMatch ? nameMatch[1].toUpperCase() : "STYLE001";
            }

            dropContent.style.display = 'none';
            fileInfo.style.display = 'flex';
            fileInfo.querySelector('.file-name').textContent = file.name;
            checkFormValidity();
        }
    }

    // Remove selected file
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent opening file dialog
        currentFile = null;
        fileInput.value = '';
        dropContent.style.display = 'block';
        fileInfo.style.display = 'none';
        checkFormValidity();
    });

    // Form Validation
    function checkFormValidity() {
        if (currentFile && brandInput.value.trim() && styleInput.value.trim()) {
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
        formData.append('style', styleInput.value.trim());

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                // Start polling for status
                pollJobStatus(data.job_id);
            } else {
                handleError(data.error || 'Upload failed');
            }
        } catch (error) {
            handleError('Network error occurred');
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
        
        // Update categories grid
        categoriesList.innerHTML = '';
        for (const [cat, count] of Object.entries(result.categories)) {
            const el = document.createElement('div');
            el.className = 'cat-badge';
            el.innerHTML = `
                <div class="cat-count">${count}</div>
                <div class="cat-name">${cat.replace('_', ' ')}</div>
            `;
            categoriesList.appendChild(el);
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
});
