"""
Model Evaluation Module

Orquestração de teste A/B entre modelos challenger e production.

Conceito: Em MLOps, não basta treinar um modelo novo. Precisamos comparar
objetivamente com o modelo atual (production) antes de promover para produção.

Esta classe encapsula toda a lógica de comparação, tornando-a reutilizável
tanto em scripts automatizados quanto em notebooks exploratórios.
"""

import logging
from typing import Dict, Optional
import pandas as pd
import mlflow

from src.utils.mlflow_utils import load_model_by_alias, get_model_version_by_alias, setup_mlflow
from src.utils.evaluation_utils import evaluate_model, compare_models

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Avaliador de modelos para teste A/B.
    
    Responsabilidades:
    - Carregar modelos por alias (production, challenger)
    - Avaliar modelos em dados de teste
    - Comparar métricas
    - Recomendar promoção ou não
    
    Uso em scripts:
        evaluator = ModelEvaluator("study.mlops_iris.logistic_regression_iris")
        results = evaluator.evaluate_challenger_vs_production(X_test, y_test)
        if results['should_promote']:
            # Promover challenger
    
    Uso em notebooks:
        from src.utils.model_evaluation import ModelEvaluator
        
        evaluator = ModelEvaluator(model_name)
        results = evaluator.evaluate_challenger_vs_production(X_test, y_test)
        
        # Explorar resultados interativamente
        print(results['production'])
        print(results['challenger'])
        
        # Visualizar confusion matrix
        import matplotlib.pyplot as plt
        cm = results['challenger']['confusion_matrix']
        plt.imshow(cm)
    """
    
    def __init__(self, model_name: str):
        """
        Inicializa avaliador para um modelo específico.
        
        Args:
            model_name: Nome completo do modelo no formato catalog.schema.model_name
                       Exemplo: "study.mlops_iris.logistic_regression_iris"
        """
        self.model_name = model_name
        self.client = setup_mlflow()
    
    def evaluate_challenger_vs_production(
        self, 
        X_test: pd.DataFrame, 
        y_test: pd.Series
    ) -> Dict:
        """
        Executa teste A/B completo entre challenger e production.
        
        Fluxo:
        1. Verifica se ambos os modelos existem no registry
        2. Carrega challenger e production
        3. Avalia ambos nos mesmos dados de teste
        4. Compara métricas
        5. Decide vencedor
        6. Recomenda promoção ou não
        
        Args:
            X_test: Features de teste (mesmo conjunto para ambos os modelos)
            y_test: Labels de teste
            
        Returns:
            Dict com estrutura:
            {
                'status': str,  # 'evaluated', 'no_production', 'no_challenger'
                'production_version': int,  # Versão do production
                'challenger_version': int,  # Versão do challenger
                'production': dict,  # Métricas do production
                'challenger': dict,  # Métricas do challenger
                'winner': str,  # 'production' ou 'challenger'
                'improvement': float,  # Diferença de accuracy
                'should_promote': bool,  # Recomendação de promoção
                'message': str  # Explicação da decisão
            }
        
        Casos especiais:
        - Se não existe production: Retorna status='no_production'
          (Isso acontece quando nenhum modelo foi promovido ainda)
        
        - Se não existe challenger: Retorna status='no_challenger'
          (Isso acontece se você não treinou um modelo novo)
        
        Decisão de promoção:
            challenger vence SE accuracy(challenger) > accuracy(production)
            Nesse caso, should_promote=True
        
        Exemplo de resultado quando challenger vence:
        {
            'status': 'evaluated',
            'production_version': 5,
            'challenger_version': 6,
            'production': {'accuracy': 0.9500, ...},
            'challenger': {'accuracy': 0.9734, ...},
            'winner': 'challenger',
            'improvement': 0.0234,
            'should_promote': True,
            'message': 'challenger venceu com 0.0234 de melhoria em accuracy'
        }
        """
        # Verificar se existe production (modelo em produção)
        production_version = get_model_version_by_alias(self.client, self.model_name, "production")
        
        if not production_version:
            logger.warning("Nenhum production encontrado. Avaliação não pode ser executada.")
            return {
                'status': 'no_production',
                'message': 'Nenhum modelo production encontrado para comparação'
            }
        
        # Verificar se existe challenger (modelo candidato)
        challenger_version = get_model_version_by_alias(self.client, self.model_name, "challenger")
        
        if not challenger_version:
            logger.warning("Nenhum challenger encontrado. Avaliação não pode ser executada.")
            return {
                'status': 'no_challenger',
                'message': 'Nenhum modelo challenger encontrado para comparação'
            }
        
        logger.info(f"Iniciando avaliação: production v{production_version} vs challenger v{challenger_version}")
        
        # Carregar ambos os modelos do MLflow Registry
        model_production = load_model_by_alias(self.model_name, "production")
        model_challenger = load_model_by_alias(self.model_name, "challenger")
        
        # Comparar modelos usando mesmos dados de teste
        # Isso garante comparação justa (apple-to-apple)
        comparison = compare_models(model_production, model_challenger, X_test, y_test)
        
        # Adicionar informações de versão ao resultado
        comparison['production_version'] = production_version
        comparison['challenger_version'] = challenger_version
        comparison['status'] = 'evaluated'
        
        # Decisão de promoção baseada no vencedor
        if comparison['winner'] == 'challenger':
            comparison['should_promote'] = True
            comparison['message'] = (
                f"challenger venceu com {comparison['improvement']:.4f} "
                f"de melhoria em accuracy"
            )
        else:
            comparison['should_promote'] = False
            comparison['message'] = (
                f"production permanece. "
                f"challenger não superou o modelo atual."
            )
        
        return comparison
    
    def evaluate_single_model(
        self,
        alias: str,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict:
        """
        Avalia um único modelo por alias.
        
        Útil para:
        - Avaliar baseline (primeiro modelo de referência)
        - Avaliar production isoladamente
        - Avaliar challenger isoladamente
        
        Args:
            alias: Alias do modelo ("production", "challenger", "baseline")
            X_test: Features de teste
            y_test: Labels de teste
            
        Returns:
            Dict com métricas + informações do modelo:
            {
                'version': int,
                'alias': str,
                'accuracy': float,
                'precision': float,
                'recall': float,
                'f1_score': float,
                'confusion_matrix': np.ndarray,
                'classification_report': str
            }
        
        Raises:
            ValueError: Se modelo com alias especificado não existir
        """
        version = get_model_version_by_alias(self.client, self.model_name, alias)
        
        if not version:
            raise ValueError(f"Modelo com alias '{alias}' não encontrado: {self.model_name}")
        
        logger.info(f"Avaliando modelo: {alias} v{version}")
        
        # Carregar modelo
        model = load_model_by_alias(self.model_name, alias)
        
        # Avaliar
        metrics = evaluate_model(model, X_test, y_test)
        
        # Adicionar metadados
        metrics['version'] = version
        metrics['alias'] = alias
        
        return metrics
