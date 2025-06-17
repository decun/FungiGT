"""
Paquete de Visualizadores Especializados para FungiGT
====================================================

Este paquete contiene múltiples visualizadores especializados para diferentes
tipos de archivos genómicos y bioinformáticos.

Visualizadores disponibles:
- BinDashVisualizer: Análisis genómico comparativo y filogenético

Visualizadores en desarrollo:
- AnnotationsVisualizer: Visualización de anotaciones funcionales
- HMMERVisualizer: Análisis de dominios proteicos
- SeedOrthologsVisualizer: Análisis de ortólogos y filogenética
- QualityControlVisualizer: Métricas de calidad genómica
- PhylogenyVisualizer: Construcción de árboles filogenéticos
- GeneralGenomicsVisualizer: Visualizaciones genómicas generales
"""

from .base_visualizer import BaseVisualizer
from .bindash_visualizer import BinDashVisualizer

# TODO: Implementar estos visualizadores
# from .annotations_visualizer import AnnotationsVisualizer
# from .hmmer_visualizer import HMMERVisualizer
# from .seed_orthologs_visualizer import SeedOrthologsVisualizer
# from .quality_control_visualizer import QualityControlVisualizer
# from .phylogeny_visualizer import PhylogenyVisualizer
# from .general_genomics_visualizer import GeneralGenomicsVisualizer

__all__ = [
    'BaseVisualizer',
    'BinDashVisualizer'
    # 'AnnotationsVisualizer', 
    # 'HMMERVisualizer',
    # 'SeedOrthologsVisualizer',
    # 'QualityControlVisualizer',
    # 'PhylogenyVisualizer',
    # 'GeneralGenomicsVisualizer'
]

__version__ = '1.0.0'
__author__ = 'FungiGT Team' 