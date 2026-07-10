#!/usr/bin/env python
"""
Pipeline Batch Inference - Etapa 5: Salvar Metadados

RESPONSABILIDADE:
    Registrar metadados do batch para monitoramento
    
ENTRADA:
    - {catalog}.{schema}.batch_predictions (tabela Delta)
    - {catalog}.{schema}.batch_inference_metadata_temp (batch_id)
    
SAÍDA:
    - Logs estruturados
    - Métricas do batch
    - Estatísticas de confiança
    
METADADOS IMPORTANTES:
    - Distribuição de classes preditas
    - Confiança média das predições
    - % de predições incertas (<70%)
    - Volume de dados processados
    - Timestamp de execução
    
FUTURO:
    Salvar em tabela batch_inference_metadata para histórico
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# Setup de path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.data_utils import get_spark_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def calculate_batch_statistics(df: pd.DataFrame) -> dict:
    """
    Calcula estatísticas do batch.
    
    Args:
        df: DataFrame com predições
        
    Returns:
        Dicionário com estatísticas
    """
    stats = {}
    
    # Distribuição de classes
    class_dist = df['predicted_class'].value_counts().to_dict()
    stats['class_distribution'] = class_dist
    
    # Confiança
    stats['avg_confidence'] = df['prediction_probability'].mean()
    stats['min_confidence'] = df['prediction_probability'].min()
    stats['max_confidence'] = df['prediction_probability'].max()
    
    # Predições incertas
    low_confidence_count = (df['prediction_probability'] < 0.7).sum()
    stats['low_confidence_count'] = int(low_confidence_count)
    stats['low_confidence_pct'] = (low_confidence_count / len(df)) * 100
    
    # Volume
    stats['total_predictions'] = len(df)
    
    return stats


def log_batch_metadata(
    batch_id: str,
    model_version: int,
    stats: dict
):
    """
    Registra metadados do batch nos logs.
    
    Args:
        batch_id: UUID do batch
        model_version: Versão do modelo
        stats: Estatísticas calculadas
    """
    logger.info("\n" + "=" * 60)
    logger.info("METADADOS DO BATCH")
    logger.info("=" * 60)
    
    logger.info(f"\nBatch ID: {batch_id}")
    logger.info(f"Model Version: {model_version}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Total Predictions: {stats['total_predictions']}")
    
    logger.info("\nDistribuição de Classes:")
    class_names = {0: 'Setosa', 1: 'Versicolor', 2: 'Virginica'}
    for class_id, count in stats['class_distribution'].items():
        pct = (count / stats['total_predictions']) * 100
        class_name = class_names.get(class_id, f"Classe {class_id}")
        logger.info(f"  {class_name}: {count} ({pct:.1f}%)")
    
    logger.info(f"\nConfiança das Predições:")
    logger.info(f"  Média: {stats['avg_confidence']:.4f} ({stats['avg_confidence']*100:.2f}%)")
    logger.info(f"  Mínima: {stats['min_confidence']:.4f}")
    logger.info(f"  Máxima: {stats['max_confidence']:.4f}")
    
    if stats['low_confidence_count'] > 0:
        logger.warning(f"\nALERTA: {stats['low_confidence_count']} predições com baixa confiança (<70%)")
        logger.warning(f"   {stats['low_confidence_pct']:.1f}% do total")
        logger.warning("   Considere revisar esses casos")
    else:
        logger.info("\nTodas as predições têm alta confiança (>70%)")


def main(catalog: str = 'study', schema: str = 'mlops_iris'):
    """Executa salvamento de metadados."""
    logger.info("=" * 60)
    logger.info("ETAPA 5: SALVAR METADADOS")
    logger.info("=" * 60)
    
    spark = get_spark_session()
    
    # Buscar batch_id da etapa anterior
    metadata_table = f"{catalog}.{schema}.batch_inference_metadata_temp"
    logger.info(f"Buscando batch ID de: {metadata_table}")
    
    batch_metadata = spark.table(metadata_table).collect()
    if not batch_metadata:
        raise ValueError("Batch ID não encontrado. Execute etapas anteriores primeiro.")
    
    batch_id = batch_metadata[0]['batch_id']
    logger.info(f"Batch ID encontrado: {batch_id}")
    
    # Carregar predições da tabela final
    predictions_table = f"{catalog}.{schema}.batch_predictions"
    logger.info(f"Carregando predições de: {predictions_table}")
    
    # Filtrar apenas o batch atual
    spark_df = spark.table(predictions_table).filter(f"batch_id = '{batch_id}'")
    df = spark_df.toPandas()
    
    if len(df) == 0:
        raise ValueError(f"Nenhuma predição encontrada para batch_id: {batch_id}")
    
    logger.info(f"Carregadas {len(df)} predições do batch atual")
    
    # Calcular estatísticas
    stats = calculate_batch_statistics(df)
    
    # Pegar versão do modelo
    model_version = df['model_version'].iloc[0]
    
    # Registrar metadados
    log_batch_metadata(batch_id, model_version, stats)
    
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE BATCH INFERENCE CONCLUIDO")
    logger.info("=" * 60)
    
    logger.info("\nPROXIMOS PASSOS:")
    logger.info("\n1. Consultar predições:")
    logger.info(f"   SELECT * FROM {catalog}.{schema}.batch_predictions")
    logger.info(f"   WHERE batch_id = '{batch_id}'")
    
    logger.info("\n2. Analisar drift:")
    logger.info("   Comparar features com dados de treino")
    
    logger.info("\n3. Monitorar confiança:")
    logger.info("   Se muitas predições incertas, considere retreinar")


def cli_main() -> None:
    """Entry point para execução via linha de comando ou Python wheel."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='study')
    parser.add_argument('--schema', default='mlops_iris')
    args = parser.parse_args()
    main(args.catalog, args.schema)


if __name__ == "__main__":
    cli_main()
