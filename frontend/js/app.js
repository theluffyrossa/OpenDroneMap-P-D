const API_URL = window.location.origin;
let currentTaskId = null;
let ws = null;

function showSection(sectionName) {
    const sections = document.querySelectorAll('.section');
    sections.forEach(section => {
        section.style.display = 'none';
    });

    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.style.display = 'block';
    }

    if (sectionName === 'projects') {
        loadProjects();
    } else if (sectionName === 'viewer') {
        loadProjectsForViewer();
    }
}

async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_URL}/api${endpoint}`, {
            ...options,
            headers: {
                ...options.headers,
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.detail || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        showError(error.message);
        throw error;
    }
}

function showError(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('error-message').textContent = message;
    errorModal.show();
}

function showSuccess(message) {
    const successModal = new bootstrap.Modal(document.getElementById('successModal'));
    document.getElementById('success-message').textContent = message;
    successModal.show();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

function getStatusBadge(status) {
    const statusClasses = {
        'pending': 'status-pending',
        'uploading': 'status-processing',
        'processing': 'status-processing',
        'completed': 'status-completed',
        'failed': 'status-failed',
        'cancelled': 'status-cancelled'
    };

    const statusTexts = {
        'pending': 'Pendente',
        'uploading': 'Enviando',
        'processing': 'Processando',
        'completed': 'Concluído',
        'failed': 'Falhou',
        'cancelled': 'Cancelado'
    };

    return `<span class="status-badge ${statusClasses[status] || 'status-pending'}">
        ${statusTexts[status] || status}
    </span>`;
}

async function loadProjects() {
    try {
        const projects = await apiRequest('/projects');
        const tableBody = document.getElementById('projects-table-body');

        if (projects.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum projeto encontrado</td></tr>';
            return;
        }

        tableBody.innerHTML = projects.map(project => `
            <tr>
                <td>${project.task_id}</td>
                <td>${project.name}</td>
                <td>${getStatusBadge(project.status)}</td>
                <td>${project.total_images}</td>
                <td>${project.quality}</td>
                <td>${formatDate(project.created_at)}</td>
                <td>
                    ${project.status === 'completed' ? `
                        <button class="btn btn-sm btn-primary" onclick="viewProject('${project.task_id}')">
                            <i class="fas fa-eye"></i> Ver
                        </button>
                    ` : ''}
                    ${project.status === 'processing' ? `
                        <button class="btn btn-sm btn-info" onclick="checkStatus('${project.task_id}')">
                            <i class="fas fa-sync"></i> Status
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteProject('${project.task_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

async function checkStatus(taskId) {
    try {
        const status = await apiRequest(`/status/${taskId}`);

        const statusHtml = `
            <div>
                <p><strong>Status:</strong> ${getStatusBadge(status.status)}</p>
                <p><strong>Progresso:</strong> ${status.progress}%</p>
                <p><strong>Tempo de processamento:</strong> ${Math.round(status.processing_time || 0)} segundos</p>
                ${status.console_output ? `
                    <div class="console-output mt-3">
                        ${status.console_output.join('\n')}
                    </div>
                ` : ''}
            </div>
        `;

        const modal = new bootstrap.Modal(document.getElementById('successModal'));
        document.getElementById('success-message').innerHTML = statusHtml;
        modal.show();
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

async function deleteProject(taskId) {
    if (!confirm(`Tem certeza que deseja excluir o projeto ${taskId}?`)) {
        return;
    }

    try {
        await apiRequest(`/projects/${taskId}`, {
            method: 'DELETE'
        });
        showSuccess('Projeto excluído com sucesso');
        loadProjects();
    } catch (error) {
        console.error('Error deleting project:', error);
    }
}

function viewProject(taskId) {
    showSection('viewer');
    setTimeout(() => {
        const projectSelect = document.getElementById('project-select');
        projectSelect.value = taskId;
        projectSelect.dispatchEvent(new Event('change'));
    }, 100);
}

function connectWebSocket(taskId) {
    if (ws) {
        ws.close();
    }

    const wsUrl = `ws://${window.location.host}/ws/${taskId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateProcessingStatus(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };
}

function updateProcessingStatus(data) {
    const statusDiv = document.getElementById('processing-status');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-bar-container');
    const consoleOutput = document.getElementById('console-output');

    if (data.status === 'processing') {
        progressContainer.style.display = 'block';
        progressBar.style.width = `${data.progress}%`;
        progressBar.textContent = `${data.progress}%`;

        statusDiv.innerHTML = `
            <p><strong>Status:</strong> Processando...</p>
            <p><strong>Progresso:</strong> ${data.progress}%</p>
        `;

        if (data.console_output && data.console_output.length > 0) {
            consoleOutput.style.display = 'block';
            consoleOutput.textContent = data.console_output.join('\n');
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    } else if (data.status === 'completed') {
        progressBar.style.width = '100%';
        progressBar.textContent = '100%';
        progressBar.classList.remove('progress-bar-animated');
        progressBar.classList.add('bg-success');

        statusDiv.innerHTML = `
            <p class="text-success"><strong>Processamento concluído com sucesso!</strong></p>
            <button class="btn btn-primary" onclick="viewProject('${data.task_id}')">
                <i class="fas fa-eye"></i> Visualizar Resultados
            </button>
        `;
    } else if (data.status === 'failed') {
        progressBar.classList.remove('progress-bar-animated');
        progressBar.classList.add('bg-danger');

        statusDiv.innerHTML = `
            <p class="text-danger"><strong>Erro no processamento:</strong> ${data.error || 'Erro desconhecido'}</p>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    showSection('upload');

    const errorModal = document.getElementById('errorModal');
    const successModal = document.getElementById('successModal');

    if (errorModal) {
        errorModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('error-message').textContent = '';
        });
    }

    if (successModal) {
        successModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('success-message').textContent = '';
        });
    }
});