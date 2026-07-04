"""
Data Utility Functions

Funções para carregamento e manipulação de dados do Unity Catalog.

Conceito: Unity Catalog é o sistema de governança de dados do Databricks.
Dados são organizados em: Catálogo > Schema > Tabela
Exemplo: study.mlops_iris.iris_train
         ^^^^^ ^^^^^^^^^ ^^^^^^^^^^
         cat   schema    tabela
"""

from typing import Tuple
import pandas as pd
from pyspark.sql import SparkSession
from sklearn.preprocessing import StandardScaler


def get_spark_session() -> SparkSession:
    """
    Obtém a SparkSession ativa no ambiente Databricks.
    
    SparkSession é o ponto de entrada para trabalhar com Spark.
    No Databricks, uma sessão já está ativa automaticamente.
    
    Returns:
        SparkSession: Sessão Spark ativa
        
    Raises:
        RuntimeError: Se não houver sessão ativa (raro no Databricks)
    
    Exemplo:
        spark = get_spark_session()
        df = spark.sql("SELECT * FROM catalog.schema.table")
    """
    spark = SparkSession.getActiveSession()
    if spark is None:
        raise RuntimeError("No active Spark session found")
    return spark


def load_data_from_catalog(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str
) -> pd.DataFrame:
    """
    Carrega uma tabela do Unity Catalog e converte para pandas DataFrame.
    
    Processo:
    1. Spark lê tabela do Unity Catalog (distribuída)
    2. Converte para pandas (memória local)
    
    Atenção: Só use para tabelas pequenas que cabem em memória.
    Para tabelas grandes, trabalhe com Spark DataFrame.
    
    Args:
        spark: SparkSession ativa
        catalog: Nome do catálogo Unity Catalog
        schema: Nome do schema
        table_name: Nome da tabela
        
    Returns:
        pd.DataFrame: Dados da tabela em pandas
    
    Exemplo:
        # Carregar dados de treino
        df = load_data_from_catalog(spark, "study", "mlops_iris", "iris_train")
        # df é um pandas DataFrame pronto para ML
    """
    # Montar nome completo da tabela
    full_table_name = f"{catalog}.{schema}.{table_name}"
    
    # Ler com Spark SQL e converter para pandas
    return spark.sql(f"SELECT * FROM {full_table_name}").toPandas()


def load_train_test_data(
    spark: SparkSession,
    catalog: str,
    schema: str
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Carrega conjuntos de treino e teste prontos para machine learning.
    
    Assume que as tabelas já foram criadas por 01_process_data.py:
    - catalog.schema.iris_train: Dados de treino
    - catalog.schema.iris_test: Dados de teste
    
    Ambas as tabelas têm:
    - Features: sepal_length_cm, sepal_width_cm, petal_length_cm, petal_width_cm
    - Target: target (0, 1 ou 2 representando espécies de iris)
    
    Args:
        spark: SparkSession ativa
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
        
    Returns:
        Tuple com 4 elementos:
        - X_train: Features de treino (pd.DataFrame)
        - X_test: Features de teste (pd.DataFrame)
        - y_train: Labels de treino (pd.Series)
        - y_test: Labels de teste (pd.Series)
    
    Exemplo:
        spark = get_spark_session()
        X_train, X_test, y_train, y_test = load_train_test_data(
            spark, "study", "mlops_iris"
        )
        
        # Pronto para treinar
        model.fit(X_train, y_train)
    """
    # Carregar tabela de treino
    df_train = load_data_from_catalog(spark, catalog, schema, "iris_train")
    
    # Carregar tabela de teste
    df_test = load_data_from_catalog(spark, catalog, schema, "iris_test")
    
    # Separar features (X) de target (y)
    # Features: todas as colunas exceto 'target'
    X_train = df_train.drop('target', axis=1)
    y_train = df_train['target']
    
    X_test = df_test.drop('target', axis=1)
    y_test = df_test['target']
    
    return X_train, X_test, y_train, y_test


def load_inference_data(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str = "dataset_drift"
) -> pd.DataFrame:
    """
    Carrega dados para inferência batch e valida features.
    
    Esta função carrega dados da tabela de inferência (ex: dataset_drift)
    e valida que contém todas as features necessárias.
    
    Features obrigatórias:
        - sepal_length_cm
        - sepal_width_cm
        - petal_length_cm
        - petal_width_cm
    
    Args:
        spark: SparkSession ativa
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
        table_name: Nome da tabela (default: "dataset_drift")
        
    Returns:
        pd.DataFrame: Dados validados com features
        
    Raises:
        ValueError: Se tabela vazia ou features faltando
        
    Exemplo:
        spark = get_spark_session()
        data = load_inference_data(spark, "study", "mlops_iris")
        # data tem as 4 features necessárias
    """
    # Carregar dados
    df = load_data_from_catalog(spark, catalog, schema, table_name)
    
    # Verificar se tem dados
    if len(df) == 0:
        raise ValueError(
            f"Tabela {catalog}.{schema}.{table_name} está vazia. "
            "Popule a tabela antes de rodar inferência."
        )
    
    # Validar features obrigatórias
    required_features = [
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm'
    ]
    
    missing = [f for f in required_features if f not in df.columns]
    if missing:
        raise ValueError(
            f"Features obrigatórias faltando: {missing}\n"
            f"Tabela deve ter: {required_features}"
        )
    
    # Selecionar apenas features necessárias
    return df[required_features]


def preprocess_inference_data(
    spark: SparkSession,
    inference_data: pd.DataFrame,
    catalog: str,
    schema: str
) -> pd.DataFrame:
    """
    Aplica pré-processamento aos dados de inferência.
    
    IMPORTANTE: Aplica MESMA transformação usada no treino!
    
    O modelo foi treinado com dados normalizados (StandardScaler).
    Para predições corretas, DEVEMOS aplicar a mesma normalização.
    
    Processo:
        1. Carrega dados de TREINO (para calcular mean/std)
        2. Fit StandardScaler nos dados de treino
        3. Transform dados de inferência usando mesmo scaler
    
    Por que fit no treino e não nos dados de inferência?
        - Evita data leakage
        - Mantém consistência com modelo treinado
        - Simula ambiente de produção real
    
    Args:
        spark: SparkSession ativa
        inference_data: Dados brutos de inferência
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
        
    Returns:
        pd.DataFrame: Dados normalizados (mesma escala do treino)
        
    Exemplo:
        # Carregar dados de inferência
        raw_data = load_inference_data(spark, "study", "mlops_iris")
        
        # Pré-processar (normalizar)
        processed_data = preprocess_inference_data(
            spark, raw_data, "study", "mlops_iris"
        )
        
        # Agora pode usar no modelo
        predictions = model.predict(processed_data)
    
    Nota:
        Em produção, você salvaria o scaler como artefato MLflow.
        Aqui recarregamos dados de treino por simplicidade.
    """
    # Carregar dados de TREINO para calcular estatísticas
    df_train = load_data_from_catalog(spark, catalog, schema, "iris_train")
    X_train = df_train.drop('target', axis=1)
    
    # Fit scaler nos dados de TREINO (não nos dados de inferência!)
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    # Transform dados de INFERÊNCIA usando scaler do treino
    scaled_data = scaler.transform(inference_data)
    
    # Converter de volta para DataFrame (mantém nomes de colunas)
    return pd.DataFrame(scaled_data, columns=inference_data.columns)
