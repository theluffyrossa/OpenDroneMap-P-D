let selectedFiles = [];
let uploadedImages = [];

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    uploadBtn.addEventListener('click', uploadAndProcess);
});

function handleFiles(files) {
    const fileArray = Array.from(files);
    const imageFiles = fileArray.filter(file => file.type.startsWith('image/'));

    if (imageFiles.length === 0) {
        showError('Por favor, selecione apenas arquivos de imagem');
        return;
    }

    const maxFiles = 50;
    if (selectedFiles.length + imageFiles.length > maxFiles) {
        showError(`Máximo de ${maxFiles} imagens permitidas`);
        return;
    }

    selectedFiles = [...selectedFiles, ...imageFiles];
    displayFileList();
    displayImagePreviews();
    updateUploadButton();
}

function displayFileList() {
    const fileListDiv = document.getElementById('file-list');

    if (selectedFiles.length === 0) {
        fileListDiv.innerHTML = '';
        return;
    }

    fileListDiv.innerHTML = `
        <h6>Arquivos selecionados (${selectedFiles.length}):</h6>
        <div class="file-items">
            ${selectedFiles.map((file, index) => `
                <div class="file-item">
                    <div>
                        <i class="fas fa-image"></i>
                        <span>${file.name}</span>
                        <span class="file-size">(${formatFileSize(file.size)})</span>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="removeFile(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `).join('')}
        </div>
        <div class="mt-2">
            <button class="btn btn-sm btn-warning" onclick="clearFiles()">
                <i class="fas fa-trash"></i> Limpar Tudo
            </button>
        </div>
    `;
}

function displayImagePreviews() {
    const previewGrid = document.getElementById('image-preview');

    if (selectedFiles.length === 0) {
        previewGrid.innerHTML = '<p class="text-muted text-center">Nenhuma imagem selecionada</p>';
        return;
    }

    previewGrid.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const reader = new FileReader();

        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.className = 'image-thumbnail';
            img.title = file.name;
            img.onclick = () => viewImage(e.target.result, file.name);
            previewGrid.appendChild(img);
        };

        reader.readAsDataURL(file);
    });
}

function viewImage(src, name) {
    const modal = new bootstrap.Modal(document.getElementById('successModal'));
    document.getElementById('success-message').innerHTML = `
        <img src="${src}" style="max-width: 100%; max-height: 400px;" alt="${name}">
        <p class="mt-2 text-center"><strong>${name}</strong></p>
    `;
    modal.show();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    displayFileList();
    displayImagePreviews();
    updateUploadButton();
}

function clearFiles() {
    selectedFiles = [];
    document.getElementById('file-input').value = '';
    displayFileList();
    displayImagePreviews();
    updateUploadButton();
}

function updateUploadButton() {
    const uploadBtn = document.getElementById('upload-btn');
    uploadBtn.disabled = selectedFiles.length === 0;

    if (selectedFiles.length > 0) {
        uploadBtn.innerHTML = `
            <i class="fas fa-rocket"></i>
            Processar ${selectedFiles.length} ${selectedFiles.length === 1 ? 'imagem' : 'imagens'}
        `;
    } else {
        uploadBtn.innerHTML = '<i class="fas fa-rocket"></i> Iniciar Upload e Processamento';
    }
}

async function uploadAndProcess() {
    if (selectedFiles.length === 0) {
        showError('Selecione pelo menos uma imagem');
        return;
    }

    if (selectedFiles.length < 3) {
        showError('Mínimo de 3 imagens necessárias para processamento');
        return;
    }

    const uploadBtn = document.getElementById('upload-btn');
    const originalBtnText = uploadBtn.innerHTML;

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando imagens...';

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });

    try {
        const uploadResponse = await fetch(`${API_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Erro no upload');
        }

        const uploadResult = await uploadResponse.json();
        currentTaskId = uploadResult.task_id;

        showSuccess(`${uploadResult.total_files} imagens enviadas com sucesso!`);

        const quality = document.getElementById('quality-select').value;
        const dsm = document.getElementById('dsm-check').checked;
        const dtm = document.getElementById('dtm-check').checked;
        const resolution = parseFloat(document.getElementById('resolution-input').value);

        const processingOptions = {
            quality: quality,
            dsm: dsm,
            dtm: dtm,
            orthophoto_resolution: resolution,
            auto_boundary: true
        };

        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Iniciando processamento...';

        const processResponse = await fetch(`${API_URL}/api/process/${currentTaskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processingOptions)
        });

        if (!processResponse.ok) {
            const error = await processResponse.json();
            throw new Error(error.detail || 'Erro ao iniciar processamento');
        }

        const processResult = await processResponse.json();

        const statusDiv = document.getElementById('processing-status');
        statusDiv.innerHTML = `
            <p class="text-info">
                <strong>Processamento iniciado!</strong><br>
                Task ID: ${currentTaskId}<br>
                Tempo estimado: ${Math.round(processResult.estimated_time / 60)} minutos
            </p>
        `;

        document.getElementById('progress-bar-container').style.display = 'block';
        document.getElementById('console-output').style.display = 'block';

        connectWebSocket(currentTaskId);

        clearFiles();

        startStatusPolling(currentTaskId);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalBtnText;
        updateUploadButton();
    }
}

async function startStatusPolling(taskId) {
    const pollInterval = setInterval(async () => {
        try {
            const status = await apiRequest(`/status/${taskId}`);

            updateProcessingStatus({
                task_id: taskId,
                status: status.status,
                progress: status.progress,
                console_output: status.console_output,
                error: status.message
            });

            if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                clearInterval(pollInterval);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 3000);
}