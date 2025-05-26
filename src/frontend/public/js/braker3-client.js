// BRAKER3 Client
// Funciones para interactuar con el servidor BRAKER3

const BRAKER3_API_URL = 'http://localhost:3003';

class Braker3Client {
    constructor() {
        this.currentJobId = null;
        this.progressInterval = null;
        this.uploadedFiles = [];
    }

    // Inicializar el cliente
    init() {
        // Event listeners para el formulario de BRAKER3
        const braker3Form = document.getElementById('braker3Form');
        if (braker3Form) {
            braker3Form.addEventListener('submit', this.executeBraker3.bind(this));
        }

        // Event listener para el botón de subida de archivos
        const uploadButton = document.getElementById('uploadBRAKER3Button');
        if (uploadButton) {
            uploadButton.addEventListener('click', this.uploadFiles.bind(this));
        }

        console.log('Cliente BRAKER3 inicializado');
    }

    // Subir archivos al servidor
    async uploadFiles() {
        const fileInput = document.getElementById('fnaFilesBRAKER3');
        const inputFolderPath = document.getElementById('braker3InputFolderPath').value;
        const outputFolderPath = document.getElementById('braker3OutputFolderPath').value;

        if (!fileInput || !inputFolderPath) {
            alert('Por favor, selecciona archivos y especifica una carpeta de entrada válida');
            return;
        }

        if (fileInput.files.length === 0) {
            alert('Por favor, selecciona al menos un archivo para subir');
            return;
        }

        // Crear FormData para enviar archivos
        const formData = new FormData();
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('fnaFiles', fileInput.files[i]);
        }
        formData.append('inputFolderPath', inputFolderPath);
        
        if (outputFolderPath) {
            formData.append('outputFolderPath', outputFolderPath);
        }

        try {
            // Mostrar indicador de carga
            this.setUploadStatus('Subiendo archivos...', 'uploading');

            // Enviar archivos al servidor
            const response = await fetch(`${BRAKER3_API_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.uploadedFiles = data.files;
                this.setUploadStatus(`Subida exitosa: ${data.files.length} archivos`, 'success');
                console.log('Archivos subidos:', data.files);
                
                // Actualizar el selector de genoma con el primer archivo subido si no hay selección previa
                if (data.files.length > 0 && (!document.getElementById('brakerGenomeFile').value || document.getElementById('brakerGenomeFile').value === '')) {
                    document.getElementById('brakerGenomeFile').value = data.files[0].name;
                }
            } else {
                this.setUploadStatus(`Error al subir archivos: ${data.error}`, 'error');
                console.error('Error al subir archivos:', data.error);
            }
        } catch (error) {
            this.setUploadStatus('Error de conexión al subir archivos', 'error');
            console.error('Error en la subida de archivos:', error);
        }
    }

    // Mostrar estado de subida de archivos
    setUploadStatus(message, status) {
        const uploadButton = document.getElementById('uploadBRAKER3Button');
        
        if (!uploadButton) return;
        
        // Resetear clases
        uploadButton.classList.remove('bg-green-600', 'bg-red-600', 'bg-yellow-600', 'hover:bg-green-700', 'hover:bg-red-700', 'hover:bg-yellow-700');
        
        // Aplicar estilo según estado
        switch(status) {
            case 'uploading':
                uploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
                break;
            case 'error':
                uploadButton.classList.add('bg-red-600', 'hover:bg-red-700');
                break;
            case 'success':
            default:
                uploadButton.classList.add('bg-green-600', 'hover:bg-green-700');
                break;
        }
        
        // Actualizar texto
        uploadButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 17v-2a4 4 0 014-4h2m4 0h2a4 4 0 014 4v2m-4-6l-4-4m0 0l-4 4m4-4v12" />
            </svg>
            ${message}
        `;
        
        // Resetear a texto normal después de un tiempo si es exitoso
        if (status === 'success') {
            setTimeout(() => {
                uploadButton.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 17v-2a4 4 0 014-4h2m4 0h2a4 4 0 014 4v2m-4-6l-4-4m0 0l-4 4m4-4v12" />
                    </svg>
                    Subir Archivos
                `;
            }, 3000);
        }
    }

    // Ejecutar BRAKER3
    async executeBraker3(event) {
        event.preventDefault();
        
        // Obtener valores del formulario
        const species = document.getElementById('brakerSpecies').value;
        const genome = document.getElementById('brakerGenomeFile').value;
        const bam = document.getElementById('brakerBamFile')?.value || null;
        const prot_seq = document.getElementById('brakerProtSeqFile')?.value || null;
        const threads = document.getElementById('brakerThreads').value;
        const inputFolderPath = document.getElementById('braker3InputFolderPath').value;
        const outputFolderPath = document.getElementById('braker3OutputFolderPath').value;
        
        // Recopilar flags seleccionados
        const flagCheckboxes = document.querySelectorAll('input[name="flagsBRAKER3"]:checked');
        const flags = Array.from(flagCheckboxes).map(cb => cb.value).join(' ');
        
        // Validar datos obligatorios localmente antes de enviar
        if (!species || !genome || !threads || !inputFolderPath || !outputFolderPath) {
            alert('Por favor, completa todos los campos obligatorios.');
            return;
        }
        
        console.log('Datos a enviar:', {
            species, genome, bam, prot_seq, threads, flags, inputFolderPath, outputFolderPath
        });
        
        // Datos para enviar
        const data = {
            species,
            genome,
            bam,
            prot_seq: prot_seq,
            threads,
            flags,
            inputFolderPath,
            outputFolderPath
        };
        
        try {
            // Crear entrada en la tabla de análisis
            const analysisId = window.addAnalysisToTable({
                type: 'BRAKER3',
                status: 'Iniciando',
                progress: '0%'
            });
            
            // Ejecutar BRAKER3
            const response = await fetch(`${BRAKER3_API_URL}/execute-braker3`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error HTTP:', response.status, errorText);
                throw new Error(`Error HTTP: ${response.status} - ${errorText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.currentJobId = result.jobId;
                
                // Iniciar monitoreo de progreso
                this.startProgressMonitoring(analysisId);
                
                alert('BRAKER3 iniciado correctamente. El análisis puede tardar varias horas.');
            } else {
                // Actualizar estado en tabla
                if (typeof this.updateAnalysisStatus === 'function') {
                    this.updateAnalysisStatus(analysisId, 'Error', 0);
                } else {
                    console.error('updateAnalysisStatus no está definido');
                }
                alert(`Error al iniciar BRAKER3: ${result.error}`);
            }
        } catch (error) {
            console.error('Error al ejecutar BRAKER3:', error);
            alert('Error de conexión al intentar ejecutar BRAKER3: ' + error.message);
        }
    }

    // Iniciar monitoreo de progreso
    startProgressMonitoring(analysisId) {
        // Limpiar intervalo anterior si existe
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        // Crear elemento para logs
        const tableRow = document.querySelector(`tr[data-id="${analysisId}"]`);
        const progressCell = tableRow.querySelector(`td:nth-child(3)`);
        
        let logsContainer = progressCell.querySelector('.logs-container');
        if (!logsContainer) {
            logsContainer = document.createElement('div');
            logsContainer.classList.add('logs-container', 'mt-4', 'p-2', 'bg-gray-100', 'rounded', 'text-xs', 'font-mono', 'max-h-40', 'overflow-y-auto');
            progressCell.appendChild(logsContainer);
        }

        // Consultar progreso periódicamente
        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`${BRAKER3_API_URL}/progress?id=${this.currentJobId}`);
                const data = await response.json();

                if (data.success) {
                    // Actualizar progreso en la tabla
                    this.updateAnalysisStatus(analysisId, data.status, data.progress);
                    
                    // Actualizar logs
                    if (data.logs && data.logs.length > 0) {
                        this.updateLogs(logsContainer, data.logs);
                    }
                    
                    // Si el proceso está completo, detener el monitoreo
                    if (data.completed) {
                        clearInterval(this.progressInterval);
                        this.progressInterval = null;
                        
                        // Añadir botones de acción para ver/descargar resultados
                        this.addActionButtons(analysisId, document.getElementById('braker3OutputFolderPath').value);
                    }
                } else {
                    // En caso de error, mostrar mensaje en logs
                    const errorLog = document.createElement('div');
                    errorLog.className = 'text-red-600 font-bold py-1';
                    errorLog.textContent = `Error: ${data.error}`;
                    logsContainer.appendChild(errorLog);
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }
            } catch (error) {
                console.error('Error al monitorear progreso:', error);
                
                // Intentar unas cuantas veces más antes de rendirse
                this.monitoringErrors = (this.monitoringErrors || 0) + 1;
                if (this.monitoringErrors > 5) {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                    
                    const errorLog = document.createElement('div');
                    errorLog.className = 'text-red-600 font-bold py-1';
                    errorLog.textContent = 'Error de conexión al monitorear progreso. Refresca la página para reintentar.';
                    logsContainer.appendChild(errorLog);
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }
            }
        }, 3000); // Consultar cada 3 segundos
    }

    // Actualizar logs en el contenedor
    updateLogs(container, logs) {
        // Mantener solo un número razonable de logs en la interfaz
        if (container.children.length > 30) {
            // Eliminar los logs más antiguos si hay demasiados
            while (container.children.length > 20) {
                container.removeChild(container.firstChild);
            }
        }
        
        // Añadir nuevos logs
        for (const log of logs) {
            // Evitar duplicados al comparar con el último log
            const lastLog = container.lastChild ? container.lastChild.textContent : '';
            if (lastLog === log.text) continue;
            
            const logElement = document.createElement('div');
            
            // Aplicar estilo según el tipo de log
            switch(log.type) {
                case 'stdout':
                    logElement.className = 'text-gray-700 py-1';
                    break;
                case 'stderr':
                    // No todos los errores son errores reales, algunos son solo información
                    logElement.className = log.text.includes('Error') || log.text.includes('error') || log.text.includes('failed') 
                        ? 'text-red-600 py-1'
                        : 'text-yellow-600 py-1';
                    break;
                case 'warning':
                    logElement.className = 'text-yellow-600 py-1';
                    break;
                case 'error':
                    logElement.className = 'text-red-600 font-bold py-1';
                    break;
                case 'success':
                    logElement.className = 'text-green-600 font-bold py-1';
                    break;
                default:
                    logElement.className = 'text-gray-600 py-1';
            }
            
            logElement.textContent = log.text;
            container.appendChild(logElement);
        }
        
        // Auto-scroll hacia abajo
        container.scrollTop = container.scrollHeight;
    }

    // Actualizar estado en la tabla
    updateAnalysisStatus(analysisId, status, progress) {
        const tableRow = document.querySelector(`tr[data-id="${analysisId}"]`);
        if (!tableRow) return;
        
        const statusCell = tableRow.querySelector('td:nth-child(2) span');
        const progressBar = document.getElementById(`progressBar-${analysisId}`);
        const progressText = document.getElementById(`progressText-${analysisId}`);
        
        // Actualizar texto de estado
        statusCell.textContent = status;
        
        // Aplicar clase según estado
        if (status.includes('Error') || status.includes('error')) {
            statusCell.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800';
        } else if (status === 'Completado') {
            statusCell.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800';
        } else if (status === 'Cancelado') {
            statusCell.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800';
        } else {
            statusCell.className = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800';
        }
        
        // Actualizar barra de progreso
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
    }

    // Añadir botones de acción para ver/descargar resultados
    addActionButtons(analysisId, outputFolder) {
        const tableRow = document.querySelector(`tr[data-id="${analysisId}"]`);
        if (!tableRow) return;
        
        const actionsCell = tableRow.querySelector(`td:nth-child(4)`);
        
        actionsCell.innerHTML = `
            <div class="flex space-x-2">
                <button class="view-results-btn bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs" data-output="${outputFolder}">
                    Ver resultados
                </button>
                <button class="download-results-btn bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded text-xs" data-output="${outputFolder}">
                    Descargar
                </button>
            </div>
        `;
        
        // Agregar event listeners a los nuevos botones
        actionsCell.querySelector('.view-results-btn').addEventListener('click', function() {
            window.open(`${BRAKER3_API_URL}/results?path=${encodeURIComponent(outputFolder)}`, '_blank');
        });
        
        actionsCell.querySelector('.download-results-btn').addEventListener('click', function() {
            window.location.href = `${BRAKER3_API_URL}/download?path=${encodeURIComponent(outputFolder)}`;
        });
    }
}

// Crear instancia e inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.braker3Client = new Braker3Client();
    window.braker3Client.init();
}); 