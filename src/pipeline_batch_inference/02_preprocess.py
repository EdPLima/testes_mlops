#!/usr/bin/env python
"""
Pipeline Batch Inference - Etapa 2: Pré-processar Dados

RESPONSABILIDADE:
    Aplicar transformações necessárias nos dados
    Garantir que dados estão no formato esperado pelo modelo
    
ENTRADA:
    - {catalog}.{schema}.batch_inference_staging (tabela Delta)
    
SAÍDA:
    - {catalog}.{schema}.batch_inference_features_normalized (features normalizadas)
    - {catalog}.{schema}.batch_inference_features_original (dados originais)
    
TRANSFORMAÇÕES:
    Usa data_utils.preprocess_inference_data() que:
    - Aplica StandardScaler (fit nos dados de treino)
    - Normaliza dados de inferência
    - Garante mesma escala do treino
    
NOTA SOBRE CONVERSÕES:
    A função preprocess_inference_data() do data_utils usa sklearn,
    que requer pandas DataFrame. Por isso fazemos:
    Spark → pandas (processar) → Spark
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Setup de path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.data_utils import get_spark_session, preprocess_inference_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    """Processa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description='Preprocessar dados para inferência')
    parser.add_argument('--catalog', type=str, required=True, help='UC Catalog')
    parser.add_argument('--schema', type=str, required=True, help='UC Schema')
    return parser.parse_args()


def main():
    """Executa pré-processamento usando funções do data_utils."""
    args = parse_args()
    
    logger.info("=" * 60)
    logger.info("ETAPA 2: PRE-PROCESSAR DADOS")
    logger.info("=" * 60)
    
    # Setup Spark
    spark = get_spark_session()
    
    # Carregar dados da etapa anterior (tabela staging)
    staging_table = f"{args.catalog}.{args.schema}.batch_inference_staging"
    logger.info(f"Carregando dados de: {staging_table}")
    
    spark_df = spark.table(staging_table)
    
    # Cachear informações antes de conversões (evita múltiplas RPCs)
    count = spark_df.count()
    columns = spark_df.columns
    
    logger.info(f"Carregados {count} registros")
    logger.info(f"Colunas: {columns}")
    
    # Converter para pandas (necessário para sklearn StandardScaler)
    df_all = spark_df.toPandas()
    
    # Selecionar apenas as 4 features para normalização
    feature_cols = [
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm'
    ]
    df_features = df_all[feature_cols].copy()
    
    # Pré-processar (normalizar) as features usando data_utils
    # NOTA: Esta função usa sklearn que requer pandas
    logger.info("Aplicando pre-processamento (StandardScaler)...")
    df_processed = preprocess_inference_data(spark, df_features, args.catalog, args.schema)
    logger.info(f"Pre-processamento concluido: {len(df_processed)} registros validos")
    
    # Salvar features NORMALIZADAS em tabela Delta
    normalized_table = f"{args.catalog}.{args.schema}.batch_inference_features_normalized"
    logger.info(f"Salvando features normalizadas em: {normalized_table}")
    
    spark_df_processed = spark.createDataFrame(df_processed)
    spark_df_processed.write.mode("overwrite").saveAsTable(normalized_table)
    logger.info(f"Features normalizadas salvas: {count} registros")
    
    # Salvar dados ORIGINAIS (incluindo target se existir) em tabela Delta
    original_table = f"{args.catalog}.{args.schema}.batch_inference_features_original"
    logger.info(f"Salvando dados originais em: {original_table}")
    
    spark_df_original = spark.createDataFrame(df_all)
    spark_df_original.write.mode("overwrite").saveAsTable(original_table)
    logger.info(f"Dados originais salvos: {count} registros")


if __name__ == "__main__":
    main()
