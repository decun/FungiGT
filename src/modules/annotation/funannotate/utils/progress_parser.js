/**
 * Utilidad para parsear logs de Funannotate y estimar progreso
 * Basado en los patrones específicos de salida de Funannotate
 */

class FunannotateProgressParser {
    constructor() {
        this.currentProgress = 0;
        this.workflow = 'unknown';
        this.stages = {
            predict: [
                { pattern: /loading genome|parsing.*fasta/i, progress: 5, stage: 'Cargando genoma' },
                { pattern: /training.*data|parsed.*training/i, progress: 10, stage: 'Preparando datos de entrenamiento' },
                { pattern: /running.*augustus|ab-initio.*gene.*predictors/i, progress: 25, stage: 'Ejecutando Augustus' },
                { pattern: /running.*glimmerhmm/i, progress: 35, stage: 'Ejecutando GlimmerHMM' },
                { pattern: /running.*snap/i, progress: 45, stage: 'Ejecutando SNAP' },
                { pattern: /running.*genemark/i, progress: 50, stage: 'Ejecutando GeneMark' },
                { pattern: /running.*codingquarry/i, progress: 55, stage: 'Ejecutando CodingQuarry' },
                { pattern: /evidence.*modeler|running.*evm/i, progress: 70, stage: 'Combinando predicciones (EVM)' },
                { pattern: /filtering.*gene.*models/i, progress: 80, stage: 'Filtrando modelos génicos' },
                { pattern: /generating.*gff3|writing.*output/i, progress: 90, stage: 'Generando archivos de salida' },
                { pattern: /funannotate.*predict.*complete/i, progress: 100, stage: 'Predicción completada' }
            ],
            annotate: [
                { pattern: /loading.*annotations|parsing.*input/i, progress: 10, stage: 'Cargando anotaciones' },
                { pattern: /running.*interproscan|iprscan/i, progress: 30, stage: 'Ejecutando InterProScan' },
                { pattern: /running.*antismash/i, progress: 50, stage: 'Ejecutando antiSMASH' },
                { pattern: /running.*phobius/i, progress: 60, stage: 'Ejecutando Phobius' },
                { pattern: /running.*signalp/i, progress: 70, stage: 'Ejecutando SignalP' },
                { pattern: /functional.*annotation|adding.*functional/i, progress: 85, stage: 'Agregando anotaciones funcionales' },
                { pattern: /writing.*output|generating.*final/i, progress: 95, stage: 'Generando salida final' },
                { pattern: /funannotate.*annotate.*complete/i, progress: 100, stage: 'Anotación completada' }
            ],
            compare: [
                { pattern: /loading.*genomes|parsing.*input/i, progress: 15, stage: 'Cargando genomas' },
                { pattern: /ortholog.*analysis|running.*orthofinder/i, progress: 40, stage: 'Análisis de ortólogos' },
                { pattern: /phylogenetic.*analysis/i, progress: 70, stage: 'Análisis filogenético' },
                { pattern: /comparative.*analysis/i, progress: 85, stage: 'Análisis comparativo' },
                { pattern: /generating.*report|writing.*output/i, progress: 95, stage: 'Generando reporte' },
                { pattern: /funannotate.*compare.*complete/i, progress: 100, stage: 'Comparación completada' }
            ]
        };
    }

    /**
     * Establece el workflow actual (predict, annotate, compare)
     * @param {string} workflow - Tipo de workflow de Funannotate
     */
    setWorkflow(workflow) {
        this.workflow = workflow.toLowerCase();
        this.currentProgress = 0;
    }

    /**
     * Parsea una línea de log y actualiza el progreso
     * @param {string} logLine - Línea de log de Funannotate
     * @returns {Object} - {progress: number, stage: string, updated: boolean}
     */
    parseLogLine(logLine) {
        if (!logLine || typeof logLine !== 'string') {
            return { progress: this.currentProgress, stage: 'Procesando...', updated: false };
        }

        const line = logLine.trim();
        
        // Detectar errores críticos
        if (this.isErrorLine(line)) {
            return { 
                progress: -1, 
                stage: 'Error detectado', 
                error: this.extractError(line),
                updated: true 
            };
        }

        // Usar las etapas del workflow actual
        const stages = this.stages[this.workflow] || this.stages.predict;
        
        for (const stage of stages) {
            if (stage.pattern.test(line)) {
                // Solo actualizar si el progreso es mayor al actual
                if (stage.progress > this.currentProgress) {
                    this.currentProgress = stage.progress;
                    return {
                        progress: this.currentProgress,
                        stage: stage.stage,
                        updated: true,
                        logLine: line
                    };
                }
                break;
            }
        }

        // Si no hay match específico, buscar patrones generales
        const generalProgress = this.parseGeneralPatterns(line);
        if (generalProgress.updated) {
            return generalProgress;
        }

        // No hay actualización
        return { 
            progress: this.currentProgress, 
            stage: this.getCurrentStage(), 
            updated: false 
        };
    }

    /**
     * Detecta líneas de error críticas
     * @param {string} line - Línea de log
     * @returns {boolean}
     */
    isErrorLine(line) {
        const errorPatterns = [
            /error:/i,
            /failed/i,
            /genome.*assembly.*error/i,
            /headers.*contain.*more.*characters/i,
            /cannot.*find/i,
            /permission.*denied/i,
            /no.*such.*file/i
        ];

        return errorPatterns.some(pattern => pattern.test(line));
    }

    /**
     * Extrae información de error de una línea
     * @param {string} line - Línea de error
     * @returns {string}
     */
    extractError(line) {
        if (line.includes('headers contain more characters')) {
            return 'Headers FASTA demasiado largos (>16 caracteres)';
        }
        if (line.includes('GeneMark not found')) {
            return 'GeneMark no disponible (opcional)';
        }
        if (line.includes('permission denied')) {
            return 'Error de permisos de archivo';
        }
        if (line.includes('no such file')) {
            return 'Archivo no encontrado';
        }
        
        // Error genérico
        return line.length > 100 ? line.substring(0, 100) + '...' : line;
    }

    /**
     * Parsea patrones generales de progreso
     * @param {string} line - Línea de log
     * @returns {Object}
     */
    parseGeneralPatterns(line) {
        const patterns = [
            { pattern: /preparing|initializing/i, progress: 5, stage: 'Inicializando' },
            { pattern: /loading|reading/i, progress: 10, stage: 'Cargando datos' },
            { pattern: /processing|running/i, progress: 30, stage: 'Procesando' },
            { pattern: /analyzing|computing/i, progress: 50, stage: 'Analizando' },
            { pattern: /finalizing|finishing/i, progress: 90, stage: 'Finalizando' },
            { pattern: /complete|done|finished/i, progress: 100, stage: 'Completado' }
        ];

        for (const pattern of patterns) {
            if (pattern.pattern.test(line) && pattern.progress > this.currentProgress) {
                this.currentProgress = pattern.progress;
                return {
                    progress: this.currentProgress,
                    stage: pattern.stage,
                    updated: true
                };
            }
        }

        return { progress: this.currentProgress, stage: this.getCurrentStage(), updated: false };
    }

    /**
     * Obtiene la etapa actual basada en el progreso
     * @returns {string}
     */
    getCurrentStage() {
        const stages = this.stages[this.workflow] || this.stages.predict;
        
        // Encontrar la etapa más cercana al progreso actual
        let currentStage = 'Procesando...';
        for (const stage of stages) {
            if (this.currentProgress >= stage.progress) {
                currentStage = stage.stage;
            } else {
                break;
            }
        }
        
        return currentStage;
    }

    /**
     * Reinicia el progreso
     */
    reset() {
        this.currentProgress = 0;
        this.workflow = 'unknown';
    }

    /**
     * Obtiene estadísticas del progreso actual
     * @returns {Object}
     */
    getStats() {
        return {
            progress: this.currentProgress,
            workflow: this.workflow,
            stage: this.getCurrentStage(),
            isComplete: this.currentProgress >= 100,
            hasError: this.currentProgress === -1
        };
    }
}

module.exports = FunannotateProgressParser;