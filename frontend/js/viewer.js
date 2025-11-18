let map = null;
let currentLayer = null;
let currentProjectData = null;

document.addEventListener('DOMContentLoaded', () => {
    const projectSelect = document.getElementById('project-select');

    if (projectSelect) {
        projectSelect.addEventListener('change', async (e) => {
            const taskId = e.target.value;
            if (taskId) {
                await loadProjectResults(taskId);
            } else {
                clearMap();
            }
        });
    }

    initializeMap();
});

function initializeMap() {
    if (!document.getElementById('map')) {
        return;
    }

    map = L.map('map').setView([-15.7801, -47.9292], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 22,
        maxNativeZoom: 19
    }).addTo(map);

    L.control.scale({
        metric: true,
        imperial: false
    }).addTo(map);
}

async function loadProjectsForViewer() {
    try {
        const projects = await apiRequest('/projects');
        const projectSelect = document.getElementById('project-select');

        const completedProjects = projects.filter(p => p.status === 'completed');

        if (completedProjects.length === 0) {
            projectSelect.innerHTML = '<option value="">Nenhum projeto concluído</option>';
            return;
        }

        projectSelect.innerHTML = `
            <option value="">Selecione um projeto...</option>
            ${completedProjects.map(project => `
                <option value="${project.task_id}">
                    ${project.name} - ${formatDate(project.created_at)}
                </option>
            `).join('')}
        `;
    } catch (error) {
        console.error('Error loading projects for viewer:', error);
    }
}

async function loadProjectResults(taskId) {
    try {
        const downloadButtons = document.getElementById('download-buttons');
        downloadButtons.style.display = 'none';

        clearMap();

        const results = await apiRequest(`/results/${taskId}`);
        currentProjectData = results;

        if (results.orthophoto_url) {
            await loadOrthophoto(taskId);
            setupDownloadButtons(results);
            downloadButtons.style.display = 'block';
        } else {
            showError('Este projeto não possui ortomosaico disponível');
        }

        const status = await apiRequest(`/status/${taskId}`);
        displayProjectInfo(status, results);

    } catch (error) {
        console.error('Error loading project results:', error);
        showError('Erro ao carregar resultados do projeto');
    }
}

async function loadOrthophoto(taskId) {
    try {
        const orthophotoUrl = `${API_URL}/api/download/${taskId}/orthophoto.tif`;

        const bounds = [
            [-15.8, -48.0],
            [-15.7, -47.9]
        ];

        currentLayer = L.imageOverlay(orthophotoUrl, bounds, {
            opacity: 0.9,
            interactive: true
        });

        currentLayer.addTo(map);

        map.fitBounds(bounds);

        const baseLayers = {
            "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }),
            "Satélite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Tiles © Esri'
            })
        };

        const overlays = {
            "Ortomosaico": currentLayer
        };

        L.control.layers(baseLayers, overlays).addTo(map);

        setTimeout(() => {
            map.invalidateSize();
        }, 100);

    } catch (error) {
        console.error('Error loading orthophoto:', error);
        showError('Erro ao carregar ortomosaico');
    }
}

function clearMap() {
    if (currentLayer && map) {
        map.removeLayer(currentLayer);
        currentLayer = null;
    }

    if (map) {
        map.eachLayer((layer) => {
            if (layer instanceof L.ImageOverlay) {
                map.removeLayer(layer);
            }
        });

        const layerControl = document.querySelector('.leaflet-control-layers');
        if (layerControl) {
            layerControl.remove();
        }
    }
}

function setupDownloadButtons(results) {
    const orthophotoBtn = document.getElementById('download-orthophoto');
    const demBtn = document.getElementById('download-dem');
    const pointcloudBtn = document.getElementById('download-pointcloud');
    const allBtn = document.getElementById('download-all');

    orthophotoBtn.style.display = results.orthophoto_url ? 'inline-block' : 'none';
    demBtn.style.display = results.dem_url ? 'inline-block' : 'none';
    pointcloudBtn.style.display = results.pointcloud_url ? 'inline-block' : 'none';

    if (results.orthophoto_url) {
        orthophotoBtn.onclick = () => downloadFile(results.orthophoto_url, 'orthophoto.tif');
    }

    if (results.dem_url) {
        demBtn.onclick = () => downloadFile(results.dem_url, 'dsm.tif');
    }

    if (results.pointcloud_url) {
        pointcloudBtn.onclick = () => downloadFile(results.pointcloud_url, 'pointcloud.laz');
    }

    if (results.download_all_url) {
        allBtn.onclick = () => downloadFile(results.download_all_url, `${results.task_id}_results.zip`);
    }
}

function downloadFile(url, filename) {
    const fullUrl = `${API_URL}${url}`;

    const link = document.createElement('a');
    link.href = fullUrl;
    link.download = filename;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showSuccess(`Download iniciado: ${filename}`);
}

function displayProjectInfo(status, results) {
    const infoHtml = `
        <div class="alert alert-info mt-3">
            <h6>Informações do Projeto</h6>
            <ul class="mb-0">
                <li><strong>Task ID:</strong> ${status.task_id}</li>
                <li><strong>Status:</strong> ${getStatusBadge(status.status)}</li>
                <li><strong>Data de criação:</strong> ${formatDate(status.created_at)}</li>
                ${results.processed_area ? `
                    <li><strong>Área processada:</strong> ${results.processed_area.toFixed(2)} m²</li>
                ` : ''}
                ${results.processing_time ? `
                    <li><strong>Tempo de processamento:</strong> ${Math.round(results.processing_time / 60)} minutos</li>
                ` : ''}
            </ul>
        </div>
    `;

    const mapContainer = document.getElementById('map');
    const infoDiv = document.createElement('div');
    infoDiv.innerHTML = infoHtml;
    mapContainer.parentElement.insertBefore(infoDiv, mapContainer.nextSibling);
}

window.addEventListener('resize', () => {
    if (map) {
        setTimeout(() => {
            map.invalidateSize();
        }, 200);
    }
});