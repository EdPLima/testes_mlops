#!/usr/bin/env python
"""
Pipeline Batch Inference - Etapa 1: Carregar Novos Dados

RESPONSABILIDADE:
    Carregar e validar dados novos da tabela dataset_drift
    
ENTRADA:
    - {catalog}.{schema}.dataset_drift
    
SAÍDA:
    - {catalog}.{schema}.batch_inference_staging (tabela Delta)
    
IMPORTANTE:
    Preserva TODAS as colunas, incluindo target se existir.
    Trabalha direto com Spark DataFrame (sem conversões desnecessárias).
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup de path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.data_utils import get_spark_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main(catalog: str, schema: str):
    """Executa carga e validação de dados."""
    logger.info("=" * 60)
    logger.info("ETAPA 1: CARREGAR NOVOS DADOS")
    logger.info("=" * 60)
    
    spark = get_spark_session()
    
    # Carregar dados da tabela (trabalha direto com Spark DataFrame)
    source_table = f"{catalog}.{schema}.dataset_drift"
    logger.info(f"Carregando dados de: {source_table}")
    
    spark_df = spark.table(source_table)
    
    # Validar features obrigatórias (cache schema para performance)
    columns = spark_df.columns
    required_features = [
        'sepal_length_cm',
        'sepal_width_cm',
        'petal_length_cm',
        'petal_width_cm'
    ]
    
    missing = [f for f in required_features if f not in columns]
    if missing:
        raise ValueError(f"Features obrigatórias faltando: {missing}")
    
    # Validar se há dados
    count = spark_df.count()
    if count == 0:
        raise ValueError(f"Tabela {source_table} está vazia")
    
    logger.info(f"Dados carregados e validados: {count} registros")
    logger.info(f"Colunas: {columns}")
    
    # Salvar em tabela staging (Spark → Spark, sem conversões)
    staging_table = f"{catalog}.{schema}.batch_inference_staging"
    logger.info(f"Salvando dados em tabela Delta: {staging_table}")
    
    spark_df.write.mode("overwrite").saveAsTable(staging_table)
    
    logger.info(f"Dados salvos com sucesso: {staging_table}")
    logger.info(f"Registros: {count}")


def cli_main() -> None:
    """Entry point para execução via linha de comando ou Python wheel."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', default='study')
    parser.add_argument('--schema', default='mlops_iris')
    args = parser.parse_args()
    main(args.catalog, args.schema)


if __name__ == "__main__":
    cli_main()
