#!/usr/bin/env python3
"""
Módulo de Visualizadores Especializados para FungiGT
==================================================

Este módulo contiene visualizadores especializados para diferentes tipos de análisis genómicos:

- BinDashVisualizer: Análisis genómico comparativo y filogenético
- AnnotationsVisualizer: Visualización de anotaciones funcionales  
- SeedOrthologsVisualizer: Análisis de seed orthologs
- HitsVisualizer: Visualización de hits de homología
- CheckMVisualizer: Control de calidad genómica (pendiente)
- HmmerVisualizer: Análisis de dominios proteicos (pendiente)
"""

from pathlib import Path
from typing import Dict, Any

# Importar visualizadores especializados
from .bindash_visualizer import BinDashVisualizer
from .checkm_visualizer import CheckMVisualizer
from .annotations_visualizer import AnnotationsVisualizer
from .seed_orthologs_visualizer import SeedOrthologsVisualizer
from .hits_visualizer import HitsVisualizer
from .base_visualizer import BaseVisualizer
from .dna_features_visualizer import DNAFeaturesVisualizer

# Lista de visualizadores disponibles
AVAILABLE_VISUALIZERS = [
    'BinDashVisualizer',
    'CheckMVisualizer',
    'AnnotationsVisualizer', 
    'SeedOrthologsVisualizer',
    'HitsVisualizer',
    'BaseVisualizer',
    'DNAFeaturesVisualizer'
]

# Diccionario de mapeo para facilitar acceso dinámico
VISUALIZER_MAP = {
    'bindash': BinDashVisualizer,
    'checkm': CheckMVisualizer,
    'annotations': AnnotationsVisualizer,
    'seed_orthologs': SeedOrthologsVisualizer,
    'hits': HitsVisualizer,
    'dna_features': DNAFeaturesVisualizer
}

# Exportar todo lo necesario
__all__ = AVAILABLE_VISUALIZERS + ['VISUALIZER_MAP']

__version__ = '1.0.0'
__author__ = 'FungiGT Team' 