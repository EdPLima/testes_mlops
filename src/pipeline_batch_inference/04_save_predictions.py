#!/usr/bin/env python
"""
Pipeline Batch Inference - Etapa 4: Salvar Predições

RESPONSABILIDADE:
    Salvar predições em tabela Delta com metadados completos
    
ENTRADA:
    - {catalog}.{schema}.batch_inference_features_original (tabela Delta)
    - {catalog}.{schema}.batch_inference_predictions_raw (tabela Delta)
    
SAÍDA:
    - {catalog}.{schema}.batch_predictions (tabela Delta final)
    
ESTRUTURA DA TABELA:
    - batch_id: UUID do lote
    - prediction_timestamp: Quando rodou
    - data_carga: Data do processamento
    - Features ORIGINAIS (não normalizadas)
    - predicted_class: Resultado
    - prediction_probability: Confiança
    - probability_class_0/1/2: Prob. individuais
    - model_version: Versão usada
    - model_alias: Sempre "production"
    
MODE: APPEND
    Cada execução ADICIONA registros (nunca sobrescreve)
    Histórico completo de predições
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import uuid

import pandas as pd
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DateType, IntegerType, DoubleType

# Setup de path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.data_utils import get_spark_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_table_if_not_exists(spark, catalog: str, schema: str):
    """Cria tabela de predições se não existir."""
    table_name = f"{catalog}.{schema}.batch_predictions"
    logger.info(f"Verificando tabela: {table_name}")
    
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        batch_id STRING COMMENT 'UUID único do batch',
        prediction_timestamp TIMESTAMP COMMENT 'Timestamp da predição',
        data_carga DATE COMMENT 'Data de processamento',
        model_version INT COMMENT 'Versão do modelo MLflow',
        model_alias STRING COMMENT 'Alias do modelo (production)',
        
        sepal_length_cm DOUBLE COMMENT 'Sepal length (original)',
        sepal_width_cm DOUBLE COMMENT 'Sepal width (original)',
        petal_length_cm DOUBLE COMMENT 'Petal length (original)',
        petal_width_cm DOUBLE COMMENT 'Petal width (original)',
        
        predicted_class INT COMMENT 'Classe predita (0, 1, 2)',
        prediction_probability DOUBLE COMMENT 'Confiança da predição',
        probability_class_0 DOUBLE COMMENT 'Prob. Setosa',
        probability_class_1 DOUBLE COMMENT 'Prob. Versicolor',
        probability_class_2 DOUBLE COMMENT 'Prob. Virginica'
    )
    USING DELTA
    COMMENT 'Predições batch para monitoramento'
    PARTITIONED BY (data_carga)
    """
    
    spark.sql(create_sql)
    logger.info(f"Tabela {table_name} pronta")


def save_to_delta(
    spark,
    df_original: pd.DataFrame,
    df_predictions: pd.DataFrame,
    catalog: str,
    schema: str,
    batch_id: str
):
    """
    Salva predições em Delta table.
    
    Args:
        spark: SparkSession
        df_original: DataFrame com dados ORIGINAIS (não normalizados)
        df_predictions: DataFrame com predições
        catalog: Catálogo UC
        schema: Schema UC
        batch_id: UUID do batch
    """
    table_name = f"{catalog}.{schema}.batch_predictions"
    logger.info(f"Salvando predições em: {table_name}")
    
    # Pegar features ORIGINAIS (não normalizadas)
    feature_cols = [
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm'
    ]
    df_features = df_original[feature_cols].copy()
    
    # Adicionar predições - garantir tipos corretos
    df_features['predicted_class'] = df_predictions['predicted_class'].astype('int32').values
    df_features['prediction_probability'] = df_predictions['prediction_probability'].values
    df_features['probability_class_0'] = df_predictions['probability_class_0'].values
    df_features['probability_class_1'] = df_predictions['probability_class_1'].values
    df_features['probability_class_2'] = df_predictions['probability_class_2'].values
    df_features['model_version'] = df_predictions['model_version'].astype('int32').values
    
    # Adicionar metadados
    df_features['batch_id'] = batch_id
    df_features['prediction_timestamp'] = datetime.now()
    df_features['data_carga'] = datetime.now().date()
    df_features['model_alias'] = 'production'
    
    # Selecionar colunas da tabela na ordem correta
    output_cols = [
        'batch_id',
        'prediction_timestamp',
        'data_carga',
        'model_version',
        'model_alias',
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm',
        'predicted_class',
        'prediction_probability',
        'probability_class_0',
        'probability_class_1',
        'probability_class_2'
    ]
    
    output_df = df_features[output_cols]
    
    # Definir schema explícito para garantir tipos corretos
    output_schema = StructType([
        StructField("batch_id", StringType(), True),
        StructField("prediction_timestamp", TimestampType(), True),
        StructField("data_carga", DateType(), True),
        StructField("model_version", IntegerType(), True),
        StructField("model_alias", StringType(), True),
        StructField("sepal_length_cm", DoubleType(), True),
        StructField("sepal_width_cm", DoubleType(), True),
        StructField("petal_length_cm", DoubleType(), True),
        StructField("petal_width_cm", DoubleType(), True),
        StructField("predicted_class", IntegerType(), True),
        StructField("prediction_probability", DoubleType(), True),
        StructField("probability_class_0", DoubleType(), True),
        StructField("probability_class_1", DoubleType(), True),
        StructField("probability_class_2", DoubleType(), True),
    ])
    
    # Converter para Spark com schema explícito
    spark_df = spark.createDataFrame(output_df, schema=output_schema)
    
    spark_df.write \
        .format("delta") \
        .mode("append") \
        .saveAsTable(table_name)
    
    logger.info(f"Salvos {len(output_df)} registros")
    logger.info(f"  Batch ID: {batch_id}")
    
    return batch_id


def main(catalog: str, schema: str):
    """Executa salvamento de predições."""
    logger.info("=" * 60)
    logger.info("ETAPA 4: SALVAR PREDICOES")
    logger.info("=" * 60)
    
    spark = get_spark_session()
    
    # Criar tabela se não existe
    create_table_if_not_exists(spark, catalog, schema)
    
    # Carregar dados ORIGINAIS (não normalizados) da tabela Delta
    original_table = f"{catalog}.{schema}.batch_inference_features_original"
    logger.info(f"Carregando dados originais de: {original_table}")
    
    spark_df_original = spark.table(original_table)
    df_original = spark_df_original.toPandas()
    logger.info(f"Carregados {len(df_original)} registros originais")
    
    # Carregar predições da tabela Delta
    predictions_table = f"{catalog}.{schema}.batch_inference_predictions_raw"
    logger.info(f"Carregando predições de: {predictions_table}")
    
    spark_df_predictions = spark.table(predictions_table)
    df_predictions = spark_df_predictions.toPandas()
    logger.info(f"Carregadas {len(df_predictions)} predições")
    
    # Gerar batch ID
    batch_id = str(uuid.uuid4())
    
    # Salvar em Delta com features ORIGINAIS + predições
    batch_id = save_to_delta(spark, df_original, df_predictions, catalog, schema, batch_id)
    
    # Salvar batch_id em tabela temporária para próxima etapa
    metadata_table = f"{catalog}.{schema}.batch_inference_metadata_temp"
    batch_metadata = spark.createDataFrame([{
        'batch_id': batch_id,
        'timestamp': datetime.now()
    }])
    batch_metadata.write.mode("overwrite").saveAsTable(metadata_table)
    
    logger.info(f"Predições salvas com sucesso")
    logger.info(f"Batch ID: {batch_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='study')
    parser.add_argument('--schema', default='mlops_iris')
    args = parser.parse_args()
    
    main(args.catalog, args.schema)
