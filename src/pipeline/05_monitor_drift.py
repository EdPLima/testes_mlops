#!/usr/bin/env python
"""
Script 05: Monitor Drift

Monitora o modelo production em produção detectando:
- Drift de features (distribuição dos dados mudou?)
- Drift de predições (comportamento do modelo mudou?)
- Degradação de performance (accuracy caiu?)

Este script deve rodar continuamente (ex: a cada 6 horas) para garantir
que o modelo em produção continua performando bem.

Se drift crítico for detectado, pode acionar retreino automático.

Execução via Databricks Job:
    Configurado em resources/monitoring_job.yml
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd
import numpy as np
from scipy import stats

# Adicionar diretório src ao path (compatível com Databricks Jobs)
try:
    # Tenta usar __file__ (disponível em execução normal Python)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    # __file__ não disponível (Databricks Jobs) - usar caminho absoluto
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.mlflow_utils import setup_mlflow, load_model_by_alias
from src.utils.data_utils import get_spark_session, load_data_from_catalog

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """
    Processa argumentos da linha de comando.
    
    Returns:
        Namespace com argumentos parseados
    """
    parser = argparse.ArgumentParser(description='Model Drift Monitoring Pipeline')
    parser.add_argument('--catalog', type=str, default='study', help='UC Catalog name (default: study)')
    parser.add_argument('--schema', type=str, default='mlops_iris', help='UC Schema name (default: mlops_iris)')
    parser.add_argument(
        '--drift-threshold',
        type=float,
        default=0.05,
        help='P-value threshold para detectar drift (padrão: 0.05)'
    )
    return parser.parse_args()


def get_numeric_columns(df: pd.DataFrame) -> List[str]:
    """
    Obtém lista de colunas numéricas do DataFrame.
    
    Esta função existe para evitar acessar .select_dtypes().columns
    múltiplas vezes, o que causaria RPCs repetidos (lint SCPAP001).
    
    Args:
        df: DataFrame pandas
        
    Returns:
        Lista de nomes de colunas numéricas
    """
    return df.select_dtypes(include=[np.number]).columns.tolist()


def detect_feature_drift(
    baseline_data: pd.DataFrame,
    production_data: pd.DataFrame,
    feature_columns: List[str],
    threshold: float = 0.05
) -> Dict:
    """
    Detecta drift em features usando teste estatístico.
    
    Usa Kolmogorov-Smirnov test para comparar distribuições:
    - H0 (hipótese nula): As distribuições são iguais
    - H1 (hipótese alternativa): As distribuições são diferentes
    
    Se p-value < threshold: Rejeita H0, ou seja, detecta drift
    
    Args:
        baseline_data: Dados de baseline (ex: dados de treino)
        production_data: Dados de produção (ex: últimas inferências)
        feature_columns: Lista de features a monitorar
        threshold: P-value threshold para detectar drift
        
    Returns:
        Dict com resultados por feature:
        {
            'feature_name': {
                'p_value': float,
                'drift_score': float,
                'has_drift': bool
            }
        }
    """
    results = {}
    
    for feature in feature_columns:
        # Kolmogorov-Smirnov test
        # Compara distribuições de baseline vs produção
        ks_stat, p_value = stats.ks_2samp(
            baseline_data[feature],
            production_data[feature]
        )
        
        has_drift = p_value < threshold
        
        results[feature] = {
            'p_value': p_value,
            'drift_score': ks_stat,  # 0-1, quanto maior, mais diferença
            'has_drift': has_drift
        }
    
    return results


def calculate_distribution_stats(data: pd.DataFrame, feature_columns: List[str]) -> Dict:
    """
    Calcula estatísticas descritivas das features.
    
    Args:
        data: DataFrame com dados
        feature_columns: Lista de features a analisar
        
    Returns:
        Dict com estatísticas por feature:
        {
            'feature_name': {
                'mean': float,
                'std': float,
                'min': float,
                'max': float,
                'median': float
            }
        }
    """
    stats_dict = {}
    
    for feature in feature_columns:
        feature_data = data[feature]
        stats_dict[feature] = {
            'mean': float(feature_data.mean()),
            'std': float(feature_data.std()),
            'min': float(feature_data.min()),
            'max': float(feature_data.max()),
            'median': float(feature_data.median())
        }
    
    return stats_dict


def main(catalog: str, schema: str, drift_threshold: float):
    """
    Monitora drift do modelo production.
    
    Fluxo:
    1. Carrega modelo production do MLflow
    2. Carrega dados de baseline (dados de treino)
    3. Carrega dados de produção (dados recentes)
    4. Detecta drift estatístico em features
    5. Reporta alertas se drift detectado
    
    Args:
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
        drift_threshold: P-value threshold para drift
    """
    logger.info("=" * 60)
    logger.info("MLOPS: DRIFT MONITORING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Target: {catalog}.{schema}")
    logger.info(f"Drift threshold: {drift_threshold}")
    
    # Setup
    spark = get_spark_session()
    client = setup_mlflow()
    model_name = f"{catalog}.{schema}.logistic_regression_iris"
    
    # Verificar se existe production
    try:
        production_model = load_model_by_alias(model_name, "production")
        logger.info(f"\nMonitorando modelo: {model_name}@production")
    except Exception as e:
        logger.error(f"Erro ao carregar production: {e}")
        logger.error("Execute 02_train_model.py e 04_promote_model.py primeiro")
        return
    
    # Carregar dados de baseline (dados de treino)
    # Estes são os dados nos quais o modelo foi treinado
    logger.info("\nCarregando dados de baseline (treino)...")
    baseline_data = load_data_from_catalog(spark, catalog, schema, "iris_train")
    logger.info(f"Baseline: {len(baseline_data)} registros")
    
    # Carregar dados de produção (usando teste como proxy)
    # Em produção real, estes seriam os dados de inferência recentes
    logger.info("Carregando dados de produção (teste)...")
    production_data = load_data_from_catalog(spark, catalog, schema, "iris_test")
    logger.info(f"Produção: {len(production_data)} registros")
    
    # Remover coluna target para análise de features apenas
    baseline_features = baseline_data.drop('target', axis=1)
    production_features = production_data.drop('target', axis=1)
    
    # OTIMIZAÇÃO: Calcular colunas numéricas UMA VEZ (corrige SCPAP001)
    # Usar função auxiliar para evitar repetir acesso a .select_dtypes().columns
    feature_columns = get_numeric_columns(baseline_features)
    logger.info(f"Features a monitorar: {feature_columns}")
    
    # Detectar drift de features
    logger.info("\n" + "=" * 60)
    logger.info("DETECÇÃO DE DRIFT")
    logger.info("=" * 60)
    
    drift_results = detect_feature_drift(
        baseline_features,
        production_features,
        feature_columns,
        threshold=drift_threshold
    )
    
    # Reportar resultados
    has_any_drift = any(result['has_drift'] for result in drift_results.values())
    
    if has_any_drift:
        logger.warning("\nALERTA: Drift detectado nas seguintes features:")
        for feature, result in drift_results.items():
            if result['has_drift']:
                logger.warning(
                    f"  {feature}: "
                    f"p-value={result['p_value']:.4f}, "
                    f"drift_score={result['drift_score']:.4f}"
                )
    else:
        logger.info("\nNenhum drift significativo detectado")
    
    # Calcular e comparar estatísticas descritivas
    logger.info("\n" + "=" * 60)
    logger.info("ESTATÍSTICAS DESCRITIVAS")
    logger.info("=" * 60)
    
    baseline_stats = calculate_distribution_stats(baseline_features, feature_columns)
    production_stats = calculate_distribution_stats(production_features, feature_columns)
    
    # Comparar médias
    logger.info("\nComparação de médias (baseline vs produção):")
    for feature in feature_columns:
        baseline_mean = baseline_stats[feature]['mean']
        production_mean = production_stats[feature]['mean']
        diff_pct = ((production_mean - baseline_mean) / baseline_mean) * 100
        
        logger.info(
            f"  {feature}: "
            f"baseline={baseline_mean:.4f}, "
            f"produção={production_mean:.4f}, "
            f"diff={diff_pct:+.2f}%"
        )
    
    # Decisão final
    logger.info("\n" + "=" * 60)
    logger.info("RECOMENDAÇÃO")
    logger.info("=" * 60)
    
    if has_any_drift:
        logger.warning("\n⚠️  AÇÃO NECESSÁRIA:")
        logger.warning("  1. Investigar causas do drift detectado")
        logger.warning("  2. Coletar dados recentes representativos")
        logger.warning("  3. Retreinar modelo com dados atualizados:")
        logger.warning(f"     python -m src.pipeline.02_train_model --catalog {catalog} --schema {schema}")
    else:
        logger.info("\n✅ Modelo production estável, nenhuma ação necessária")
    
    logger.info("\n" + "=" * 60)
    logger.info("MONITORAMENTO CONCLUÍDO")
    logger.info("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    main(args.catalog, args.schema, args.drift_threshold)
