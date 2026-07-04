# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Load train and test data
# Load training and test datasets from Delta tables
df_train = spark.sql("SELECT * FROM study.mlops_iris.iris_train").toPandas()
df_test = spark.sql("SELECT * FROM study.mlops_iris.iris_test").toPandas()

# COMMAND ----------

def split(df):
  X = df.drop('target', axis=1)
  y = df['target']
  return X, y

X_train, y_train = split(df_train)
X_test, y_test = split(df_test)

# COMMAND ----------

import mlflow

mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()

# COMMAND ----------

def get_latest_model_version(model_name):
    model_version_infos = client.search_model_versions("name = '%s'" % model_name)
    return max([model_version_info.version for model_version_info in model_version_infos])

# COMMAND ----------

# DBTITLE 1,MLOps: Experiment Tracking e Model Registry
# ============================================================================
# MLOPS: Experiment Tracking e Model Registry
# ============================================================================
from sklearn.linear_model import LogisticRegression
from mlflow.models import infer_signature

# Nome qualificado do modelo no Unity Catalog: catalog.schema.model_name
model_name = "study.mlops_iris.logistic_regression_iris"

# ============================================================================
# MLflow Run: Rastreia TODO o ciclo de vida do experimento
# ============================================================================
with mlflow.start_run(run_name="Model-Batch-Deployment-Demo") as mlflow_run:
    
    # AUTOLOG: Captura automaticamente métricas, parâmetros e artefatos
    # Benefícios MLOps:
    # - log_input_examples: Salva exemplos de entrada para validação futura
    # - log_post_training_metrics: Registra accuracy, precision, recall, etc.
    # - Documentação automática do experimento
    mlflow.sklearn.autolog(
        log_input_examples=True, 
        log_models=False,  # Vamos fazer log manual para mais controle
        log_post_training_metrics=True,
        silent=True
    )

    # Inicializa modelo com hiperparâmetros fixos
    # random_state=42 garante REPRODUTIBILIDADE
    clf = LogisticRegression(max_iter=200, random_state=42, solver='lbfgs')
    
    # Treina o modelo
    clf.fit(X_train, y_train)

    # ========================================================================
    # MODEL SIGNATURE: Contrato de entrada/saída do modelo
    # ========================================================================
    # Define tipos de dados esperados (input) e retornados (output)
    # ESSENCIAL em MLOps para:
    # - Validar dados em produção antes de fazer inferência
    # - Prevenir erros de tipo em runtime
    # - Documentar interface do modelo
    signature = infer_signature(X_train, y_train)

    # ========================================================================
    # MODEL REGISTRY: Salva modelo no Unity Catalog
    # ========================================================================
    mlflow.sklearn.log_model(
        clf, 
        artifact_path="logistic_regression",
        signature=signature,  # Validação de input/output
        registered_model_name=model_name  # Registra automaticamente no UC
    )

    # ========================================================================
    # MODEL ALIAS: Sistema de tags para gerenciar modelos
    # ========================================================================
    # Aliases são fundamentais em MLOps:
    # - "BaseLine": Modelo base de referência
    # - "Champion": Modelo atual em produção
    # - "Challenger": Modelo candidato sendo testado
    # Permite atualizar modelos sem mudar código de inferência
    client.set_registered_model_alias(model_name, "BaseLine", get_latest_model_version(model_name))
    
    print("✓ Modelo registrado com sucesso no Unity Catalog")
    print(f"✓ Model Name: {model_name}")
    print(f"✓ Alias 'BaseLine' configurado para versão {get_latest_model_version(model_name)}")
