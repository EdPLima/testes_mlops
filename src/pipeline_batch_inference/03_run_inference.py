#!/usr/bin/env python
"""
Pipeline Batch Inference - Etapa 3: Executar Inferência

RESPONSABILIDADE:
    Carregar modelo "production" do MLflow Registry
    Fazer predições em batch nos dados pré-processados
    
ENTRADA:
    - {catalog}.{schema}.batch_inference_features_normalized (tabela Delta)
    - Modelo "production" do MLflow Registry
    
SAÍDA:
    - {catalog}.{schema}.batch_inference_predictions_raw (tabela Delta)
    
IMPORTANTE:
    SEMPRE usa modelo com alias "production"
    Nunca versão hardcoded!
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Tuple

import pandas as pd
import numpy as np

# Setup de path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.mlflow_utils import (
    setup_mlflow,
    load_model_by_alias,
    get_model_version_by_alias
)
from src.utils.data_utils import get_spark_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_production_model(catalog: str, schema: str) -> Tuple[object, int]:
    """
    Carrega modelo production do MLflow Registry.
    
    Args:
        catalog: Catálogo UC
        schema: Schema UC
        
    Returns:
        Tupla (modelo, versão)
    """
    client = setup_mlflow()
    model_name = f"{catalog}.{schema}.logistic_regression_iris"
    
    logger.info(f"Carregando modelo: {model_name}@production")
    
    # Carregar modelo
    model = load_model_by_alias(model_name, "production")
    
    # Buscar versão
    version = get_model_version_by_alias(client, model_name, "production")
    
    if not version:
        raise ValueError("Modelo 'production' não encontrado. Execute pipeline de treino.")
    
    logger.info(f"Modelo carregado: v{version}")
    
    return model, version


def run_inference(model, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Executa inferência batch.
    
    Args:
        model: Modelo MLflow
        df: DataFrame com features
        
    Returns:
        Tupla (predições, probabilidades)
    """
    logger.info("Executando inferência batch...")
    
    feature_cols = [
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm'
    ]
    
    X = df[feature_cols]
    
    # Predições
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    
    logger.info(f"Inferência concluída: {len(predictions)} predições")
    
    # Log distribuição
    unique, counts = np.unique(predictions, return_counts=True)
    for class_id, count in zip(unique, counts):
        pct = (count / len(predictions)) * 100
        logger.info(f"  Classe {class_id}: {count} ({pct:.1f}%)")
    
    return predictions, probabilities


def main(catalog: str, schema: str):
    """Executa inferência."""
    logger.info("=" * 60)
    logger.info("ETAPA 3: EXECUTAR INFERENCIA")
    logger.info("=" * 60)
    
    # Setup Spark
    spark = get_spark_session()
    
    # Carregar modelo
    model, model_version = load_production_model(catalog, schema)
    
    # Carregar dados pré-processados da tabela Delta
    normalized_table = f"{catalog}.{schema}.batch_inference_features_normalized"
    logger.info(f"Carregando features normalizadas de: {normalized_table}")
    
    spark_df = spark.table(normalized_table)
    df = spark_df.toPandas()
    logger.info(f"Carregados {len(df)} registros")
    
    # Executar inferência
    predictions, probabilities = run_inference(model, df)
    
    # Adicionar resultados ao DataFrame
    df['predicted_class'] = predictions
    df['prediction_probability'] = np.max(probabilities, axis=1)
    df['probability_class_0'] = probabilities[:, 0]
    df['probability_class_1'] = probabilities[:, 1]
    df['probability_class_2'] = probabilities[:, 2]
    df['model_version'] = model_version
    
    # Salvar predições em tabela Delta
    predictions_table = f"{catalog}.{schema}.batch_inference_predictions_raw"
    logger.info(f"Salvando predições em: {predictions_table}")
    
    spark_df_predictions = spark.createDataFrame(df)
    spark_df_predictions.write.mode("overwrite").saveAsTable(predictions_table)
    
    logger.info(f"Predições salvas: {spark_df_predictions.count()} registros")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='study')
    parser.add_argument('--schema', default='mlops_iris')
    args = parser.parse_args()
    
    main(args.catalog, args.schema)
