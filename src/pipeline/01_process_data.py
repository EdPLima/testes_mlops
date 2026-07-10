#!/usr/bin/env python
"""
Script 01: Data Processing Pipeline

Transforma o dataset Iris bruto em dados prontos para treinamento.

O que este script faz:
1. Carrega dataset Iris do sklearn
2. Normaliza features com StandardScaler
3. Divide em treino/teste com seed fixo (reprodutibilidade)
4. Salva no Unity Catalog como Delta tables

Por que isso é diferente do notebook?
- Parametrizável: pode mudar catalog/schema via CLI
- Automático: pode rodar em Jobs sem intervenção
- Testável: funções separadas podem ter unit tests
- Reproduzível: mesmo seed sempre gera mesmo split

Exemplo de uso:
    python 01_process_data.py \
        --catalog study \
        --schema mlops_iris \
        --test-size 0.2
"""

import argparse
import logging
from typing import Tuple

import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from pyspark.sql import SparkSession


# =============================================================================
# SETUP DE LOGGING
# =============================================================================
# Por que logging ao invés de print?
# - Logs têm níveis (INFO, WARNING, ERROR)
# - Podem ser capturados por sistemas de monitoring
# - Incluem timestamp automaticamente
# - Em produção, você precisa saber O QUE aconteceu e QUANDO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# FUNÇÕES DE PROCESSAMENTO
# =============================================================================

def load_raw_data() -> pd.DataFrame:
    """
    Carrega dataset Iris do sklearn.
    
    Returns:
        DataFrame com features e target
        
    """
    logger.info("Loading Iris dataset from sklearn")
    
    iris = load_iris()
    df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    df['target'] = iris.target
    
    # Normalizar nomes de colunas: remover espaços e parênteses
    # sklearn usa "sepal length (cm)" mas Delta precisa de "sepal_length_cm"
    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '') for col in df.columns]
    
    logger.info(f"Loaded {len(df)} samples with {len(df.columns)} columns")
    return df


def preprocess_data(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Preprocessa dados: normaliza e divide em treino/teste.
    
    Args:
        df: DataFrame bruto
        test_size: Proporção de dados para teste (0.0-1.0)
        random_state: Seed para reprodutibilidade
        
    Returns:
        Tuple com (train_df, test_df)
        
    O que é normalização?
        StandardScaler transforma features para ter:
        - Média = 0
        - Desvio padrão = 1
        
        Por que? Algoritmos como LogisticRegression convergem mais rápido
        quando features estão na mesma escala.
        
        Exemplo:
        Feature A: 0-1 (já normalizada)
        Feature B: 0-1000 (precisa normalizar)
        
        Se não normalizar, Feature B domina o modelo.
    
    Train/Test Split:
        Por que dividir?
        - Treino: Modelo aprende padrões
        - Teste: Validação em dados nunca vistos
        
        Se não dividir, modelo pode "decorar" dados (overfitting)
        e falhar em dados novos.
        
        random_state=42: Garante que sempre divide da mesma forma.
        Importante para reprodutibilidade e comparação entre runs.
    """
    logger.info(f"Preprocessing data (test_size={test_size})")
    
    # Separar features (X) e target (y)
    X = df.drop('target', axis=1)
    y = df['target']
    
    # Train/test split com seed fixo
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,  # CRÍTICO: Reprodutibilidade
        stratify=y  # Mantém proporção de classes em treino e teste
    )
    
    logger.info(f"Split: {len(X_train)} train, {len(X_test)} test")
    
    # Normalizar features
    # Importante: Fit apenas no treino, transform em ambos
    # Por que? Para simular produção, onde modelo nunca viu dados de teste
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    logger.info("Features normalized with StandardScaler")
    
    # Converter de volta para DataFrame (mantém nomes de colunas)
    train_df = pd.DataFrame(X_train_scaled, columns=X.columns)
    train_df['target'] = y_train.values
    
    test_df = pd.DataFrame(X_test_scaled, columns=X.columns)
    test_df['target'] = y_test.values
    
    return train_df, test_df


def save_to_catalog(
    spark: SparkSession,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    catalog: str,
    schema: str
) -> None:
    """
    Salva DataFrames no Unity Catalog como Delta tables.
    
    Args:
        spark: SparkSession ativa
        train_df: Dados de treino
        test_df: Dados de teste
        catalog: Catálogo UC
        schema: Schema UC
        
    Por que Delta Lake?
        - ACID transactions: Leituras/escritas atômicas
        - Time travel: Pode voltar a versões anteriores
        - Schema evolution: Pode adicionar colunas depois
        - Otimizações: Z-ordering, data skipping
        - Padrão no Databricks
        
    Por que Unity Catalog?
        - Governança centralizada
        - Controle de acesso fino
        - Auditoria de uso
        - Compatível com Databricks Jobs
    """
    logger.info(f"Saving data to {catalog}.{schema}")
    
    train_table = f"{catalog}.{schema}.iris_train"
    test_table = f"{catalog}.{schema}.iris_test"
    
    # Converter Pandas → Spark → Delta
    # mode="overwrite": Substitui se já existir
    # format="delta": Usa Delta Lake (transacional, versionado)
    logger.info(f"Saving train data to {train_table}")
    train_spark_df = spark.createDataFrame(train_df)
    train_spark_df.write.format("delta").mode("overwrite").saveAsTable(train_table)
    
    logger.info(f"Saving test data to {test_table}")
    test_spark_df = spark.createDataFrame(test_df)
    test_spark_df.write.format("delta").mode("overwrite").saveAsTable(test_table)
    
    logger.info(f"Data saved successfully to {catalog}.{schema}")


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================
# Por que separar a lógica principal?
# - Permite importar este arquivo em outros scripts sem executar
# - Facilita testes (pode chamar main() com argumentos customizados)

def main(catalog: str, schema: str, test_size: float) -> None:
    """
    Orquestra o pipeline completo de processamento.
    
    Args:
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog  
        test_size: Proporção do conjunto de teste
    """
    logger.info("Starting data processing pipeline")
    logger.info(f"Target: {catalog}.{schema}")
    
    # Obter SparkSession
    # Em Databricks, spark já está disponível
    # Localmente, você criaria com SparkSession.builder
    try:
        spark = SparkSession.getActiveSession()
        if spark is None:
            raise RuntimeError("No active Spark session found")
    except Exception as e:
        logger.error(f"Failed to get Spark session: {e}")
        raise
    
    # Pipeline
    try:
        # 1. Carregar dados
        raw_df = load_raw_data()
        
        # 2. Preprocessar
        train_df, test_df = preprocess_data(raw_df, test_size=test_size)
        
        # 3. Salvar
        save_to_catalog(spark, train_df, test_df, catalog, schema)
        
        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def cli_main() -> None:
    """
    Entry point para execução via linha de comando ou Python wheel.
    
    Esta função processa argumentos CLI com argparse e chama main().
    É usada quando o script é executado via:
    - python 01_process_data.py --catalog study --schema mlops_iris
    - Databricks Jobs via python_wheel_task
    """
    parser = argparse.ArgumentParser(
        description="Process Iris dataset and save to Unity Catalog"
    )
    
    parser.add_argument(
        "--catalog",
        type=str,
        default="study",
        help="Unity Catalog name (default: study)"
    )
    
    parser.add_argument(
        "--schema",
        type=str,
        default="mlops_iris",
        help="Schema name (default: mlops_iris)"
    )
    
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test set proportion (0.0 to 1.0, default: 0.2)"
    )
    
    args = parser.parse_args()
    
    # Chamar função main com argumentos processados
    main(
        catalog=args.catalog,
        schema=args.schema,
        test_size=args.test_size
    )


if __name__ == "__main__":
    cli_main()
