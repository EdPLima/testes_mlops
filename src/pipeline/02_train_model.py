#!/usr/bin/env python
"""
Script 02: Model Training Pipeline

Treina modelo de classificação Iris e registra no MLflow Registry.

Este script implementa a lógica de treinamento automatizado com versionamento inteligente:
- Primeira execução: Cria modelo "baseline" (modelo de referência)
- Execuções seguintes: Cria modelo "challenger" (candidato a substituir o production)

A decisão é baseada na existência de um modelo "production" (modelo em produção).

Fluxo:
1. Carrega dados de treino/teste
2. Verifica se existe production
3. Treina LogisticRegression
4. Registra no MLflow
5. Define alias apropriado (baseline ou challenger)

Uso:
    python -m src.pipeline.02_train_model --catalog study --schema mlops_iris
"""

import argparse
import logging
import sys
from pathlib import Path

# Adicionar diretório src ao path (compatível com Databricks Jobs)
try:
    # Tenta usar __file__ (disponível em execução normal Python)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    # __file__ não disponível (Databricks Jobs) - usar caminho absoluto
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

import mlflow
from mlflow.models import infer_signature
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from src.utils.mlflow_utils import (
    setup_mlflow,
    get_latest_model_version,
    get_model_version_by_alias,
    set_model_alias
)
from src.utils.data_utils import get_spark_session, load_train_test_data

# Configurar logging para exibir informações durante execução
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """
    Processa argumentos da linha de comando.
    
    Argumentos:
        --catalog: Catálogo Unity Catalog onde estão os dados (padrão: study)
        --schema: Schema Unity Catalog onde estão as tabelas (padrão: mlops_iris)
        --max-iter: Número máximo de iterações do algoritmo (padrão: 200)
        --solver: Algoritmo de otimização (padrão: lbfgs)
        --run-name: Nome do run no MLflow para organização (padrão: iris_training)
    
    Returns:
        Namespace com argumentos parseados
    
    Nota:
        Argumentos têm valores padrão para permitir execução interativa.
        Em Jobs, passe os argumentos explicitamente.
    """
    parser = argparse.ArgumentParser(description='Model Training Pipeline')
    parser.add_argument('--catalog', type=str, default='study', help='UC Catalog name (default: study)')
    parser.add_argument('--schema', type=str, default='mlops_iris', help='UC Schema name (default: mlops_iris)')
    parser.add_argument('--max-iter', type=int, default=200, help='Max iterations (default: 200)')
    parser.add_argument('--solver', type=str, default='lbfgs', help='Solver algorithm (default: lbfgs)')
    parser.add_argument('--run-name', type=str, default='iris_training', help='MLflow run name (default: iris_training)')
    return parser.parse_args()


def main(catalog: str, schema: str, max_iter: int, solver: str, run_name: str):
    """
    Executa pipeline de treinamento de modelo.
    
    Processo completo:
    1. Setup: Configura MLflow e obtém SparkSession
    2. Contexto: Verifica se existe modelo production (em produção)
    3. Dados: Carrega dados de treino e teste
    4. Treinamento: Treina LogisticRegression
    5. Avaliação básica: Calcula accuracy em treino e teste
    6. Registro: Salva modelo no MLflow Registry
    7. Alias: Define baseline ou challenger conforme contexto
    
    Args:
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
        max_iter: Máximo de iterações
        solver: Algoritmo solver
        run_name: Nome do run MLflow
    
    Conceitos importantes:
    
    MLflow Run:
        Representa uma execução de treinamento.
        Dentro de um run, você pode logar:
        - Parâmetros (hiperparâmetros)
        - Métricas (accuracy, loss, etc)
        - Artefatos (modelo, gráficos, etc)
        - Tags (metadados)
    
    Model Signature:
        Define o contrato de entrada/saída do modelo.
        Exemplo: signature = infer_signature(X_train, y_train)
        Informa que modelo espera features com shape de X_train
        e retorna predições com shape de y_train.
        
        Benefícios:
        - Validação automática em inferência
        - Documentação clara do modelo
        - Prevenção de erros de tipo
    
    Model Aliases:
        Tags semânticas que apontam para versões:
        - baseline: Primeiro modelo ou referência
        - challenger: Candidato a substituir production
        - production: Modelo em produção
    """
    logger.info("=" * 60)
    logger.info("MLOPS: MODEL TRAINING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Target: {catalog}.{schema}")
    logger.info(f"Model: LogisticRegression (max_iter={max_iter}, solver={solver})")
    
    # =========================================================================
    # 1. SETUP: Configurar MLflow e Spark
    # =========================================================================
    spark = get_spark_session()
    client = setup_mlflow()
    
    # Nome completo do modelo no formato UC: catalog.schema.model_name
    model_name = f"{catalog}.{schema}.logistic_regression_iris"
    
    # =========================================================================
    # 2. CONTEXTO: Verificar se existe modelo em produção
    # =========================================================================
    # Lógica de versionamento:
    # - Se não existe production: Estamos criando o primeiro modelo → baseline
    # - Se existe production: Estamos criando candidato → challenger
    production_version = get_model_version_by_alias(client, model_name, "production")
    
    if production_version:
        logger.info(f"\nModelo em produção detectado: production v{production_version}")
        logger.info("Novo modelo será registrado como CHALLENGER")
        alias_to_set = "challenger"
    else:
        logger.info("\nNenhum modelo em produção detectado")
        logger.info("Novo modelo será registrado como BASELINE")
        alias_to_set = "baseline"
    
    # =========================================================================
    # 3. DADOS: Carregar dados de treino e teste
    # =========================================================================
    logger.info("\nCarregando dados...")
    X_train, X_test, y_train, y_test = load_train_test_data(spark, catalog, schema)
    logger.info(f"Treino: {len(X_train)} registros")
    logger.info(f"Teste: {len(X_test)} registros")
    
    # =========================================================================
    # 4. TREINAMENTO: Treinar modelo com MLflow tracking
    # =========================================================================
    logger.info("\nIniciando treinamento...")
    
    # MLflow Run: Contexto que rastreia todo o experimento
    with mlflow.start_run(run_name=run_name) as run:
        
        # ----------------------------------------------------------------
        # 4.1. AUTOLOG: Rastreamento automático
        # ----------------------------------------------------------------
        # MLflow autolog captura automaticamente:
        # - Hiperparâmetros do modelo
        # - Métricas de treino
        # - Modelo treinado
        # - Exemplos de entrada (para validação)
        mlflow.sklearn.autolog(
            log_input_examples=True,  # Salva exemplos de X_train para documentação
            log_models=False,  # Não logar automaticamente (vamos fazer manual)
            log_post_training_metrics=True,  # Logar métricas após treino
            silent=True  # Não exibir warnings do autolog
        )
        
        # ----------------------------------------------------------------
        # 4.2. TREINAR MODELO
        # ----------------------------------------------------------------
        # LogisticRegression: Algoritmo de classificação linear
        # - Simples e interpretável
        # - Funciona bem para problemas linearmente separáveis
        # - random_state=42: Garante reprodutibilidade (sempre mesmo resultado)
        clf = LogisticRegression(
            max_iter=max_iter,
            random_state=42,  # IMPORTANTE: Reprodutibilidade
            solver=solver
        )
        
        # Treinar modelo
        clf.fit(X_train, y_train)
        logger.info("Modelo treinado com sucesso")
        
        # ----------------------------------------------------------------
        # 4.3. AVALIAÇÃO BÁSICA
        # ----------------------------------------------------------------
        # Calcular accuracy em treino e teste
        # Objetivo: Validar que modelo treinou corretamente
        # Avaliação DETALHADA será feita em 03_evaluate_model.py
        train_accuracy = accuracy_score(y_train, clf.predict(X_train))
        test_accuracy = accuracy_score(y_test, clf.predict(X_test))
        
        logger.info(f"\nTrain Accuracy: {train_accuracy:.4f}")
        logger.info(f"Test Accuracy:  {test_accuracy:.4f}")
        
        # Logar métricas no MLflow
        mlflow.log_metric("train_accuracy", train_accuracy)
        mlflow.log_metric("test_accuracy", test_accuracy)
        
        # ----------------------------------------------------------------
        # 4.4. MODEL SIGNATURE: Contrato de entrada/saída
        # ----------------------------------------------------------------
        # Signature documenta:
        # - Tipos de dados esperados (input)
        # - Tipos de dados retornados (output)
        # 
        # Benefício: MLflow valida automaticamente em inferência
        # Se você passar dados com shape errado, MLflow rejeita antes
        # de chamar o modelo (previne erros em produção)
        signature = infer_signature(X_train, y_train)
        
        # ----------------------------------------------------------------
        # 4.5. REGISTRAR MODELO NO MLFLOW REGISTRY
        # ----------------------------------------------------------------
        logger.info(f"\nRegistrando modelo: {model_name}")
        
        # log_model faz 2 coisas:
        # 1. Salva modelo como artefato do run
        # 2. Registra no Model Registry (por causa de registered_model_name)
        mlflow.sklearn.log_model(
            clf,
            artifact_path="logistic_regression",  # Caminho dentro do run
            signature=signature,  # Validação de input/output
            registered_model_name=model_name  # Registra automaticamente no UC
        )
        
        # ----------------------------------------------------------------
        # 4.6. DEFINIR ALIAS
        # ----------------------------------------------------------------
        # Após registro, a versão mais recente é criada automaticamente
        # Precisamos definir o alias apropriado para essa versão
        latest_version = get_latest_model_version(client, model_name)
        set_model_alias(client, model_name, alias_to_set, latest_version)
        
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETED")
        logger.info(f"Modelo registrado: v{latest_version} com alias '{alias_to_set}'")
        logger.info(f"MLflow Run ID: {run.info.run_id}")
        logger.info("=" * 60)
        
        # ----------------------------------------------------------------
        # 4.7. PRÓXIMO PASSO
        # ----------------------------------------------------------------
        if alias_to_set == "challenger":
            logger.info("\nPRÓXIMO PASSO: Execute 03_evaluate_model.py para comparar modelos")
            logger.info(f"  python -m src.pipeline.03_evaluate_model --catalog {catalog} --schema {schema}")
        else:
            logger.info("\nPRIMEIRO MODELO CRIADO!")
            logger.info("Execute este script novamente para criar um challenger")


def cli_main() -> None:
    """Entry point para execução via linha de comando ou Python wheel."""
    args = parse_args()
    main(args.catalog, args.schema, args.max_iter, args.solver, args.run_name)


if __name__ == "__main__":
    cli_main()
