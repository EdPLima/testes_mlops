# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Setup MLflow client
import mlflow
import pandas as pd

mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()

model_name = "study.mlops_iris.logistic_regression_iris"

# COMMAND ----------

# DBTITLE 1,Check model evaluation metrics
# Obtém a versão atual marcada como BaseLine
# Em produção, este passo deveria incluir validação automática de thresholds
# (ex: accuracy > 0.95, precision > 0.90, etc)

baseline_version = client.get_model_version_by_alias(
    name=model_name, 
    alias="BaseLine"
).version

print(f"Model: {model_name}")
print(f"Current BaseLine version: {baseline_version}")
print("\nBefore promoting to Production, review evaluation metrics in MLflow.")
print("If metrics meet your requirements, proceed to the next cell.")

# COMMAND ----------

# DBTITLE 1,Promote model to Production
# Promove o modelo para Production
# O alias "Production" indica que este modelo está aprovado para uso em ambiente produtivo
# Serving endpoints e batch inference devem referenciar este alias

client.set_registered_model_alias(
    name=model_name,
    alias="Production",
    version=baseline_version
)

print(f"Model promoted to Production: {model_name}")
print(f"Version: {baseline_version}")
print(f"\nTo load this model in production code:")
print(f"  mlflow.pyfunc.load_model('models:/{model_name}@Production')")

# COMMAND ----------

# DBTITLE 1,Test production model inference
# Testa o modelo em produção com alguns exemplos
# Valida que o carregamento via alias "Production" funciona corretamente

production_model = mlflow.pyfunc.load_model(f"models:/{model_name}@Production")

# Dados de exemplo representando cada classe do Iris
test_data = pd.DataFrame({
    'sepal_length_cm': [5.1, 6.7, 4.9],
    'sepal_width_cm': [3.5, 3.0, 2.5],
    'petal_length_cm': [1.4, 5.2, 4.5],
    'petal_width_cm': [0.2, 2.3, 1.7]
})

predictions = production_model.predict(test_data)
class_names = {0: 'Setosa', 1: 'Versicolor', 2: 'Virginica'}

print("Production model inference test:")
for i, pred in enumerate(predictions):
    pred_class = int(pred)
    print(f"Sample {i+1}: predicted class {pred_class} ({class_names[pred_class]})")

print("\nModel is ready for production use.")

# COMMAND ----------

# DBTITLE 1,Next steps: Serving Endpoint (optional)
# MAGIC %md
# MAGIC ## Próximos Passos
# MAGIC
# MAGIC Com o modelo promovido para Production, existem algumas opções de deploy:
# MAGIC
# MAGIC ### 1. Model Serving Endpoint (Real-time inference)
# MAGIC
# MAGIC Cria um endpoint REST para inferência em tempo real com escalabilidade automática:
# MAGIC
# MAGIC ```python
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
# MAGIC
# MAGIC w = WorkspaceClient()
# MAGIC
# MAGIC w.serving_endpoints.create(
# MAGIC     name="iris-classifier-endpoint",
# MAGIC     config=EndpointCoreConfigInput(
# MAGIC         served_entities=[
# MAGIC             ServedEntityInput(
# MAGIC                 entity_name=model_name,
# MAGIC                 entity_version=baseline_version,
# MAGIC                 scale_to_zero_enabled=True,
# MAGIC                 workload_size="Small"
# MAGIC             )
# MAGIC         ]
# MAGIC     )
# MAGIC )
# MAGIC ```
# MAGIC
# MAGIC ### 2. Batch Inference (Spark UDF)
# MAGIC
# MAGIC Para predições em lote, carregue o modelo como UDF do Spark:
# MAGIC
# MAGIC ```python
# MAGIC from pyspark.sql.functions import struct
# MAGIC
# MAGIC loaded_model = mlflow.pyfunc.spark_udf(
# MAGIC     spark, 
# MAGIC     model_uri=f"models:/{model_name}@Production",
# MAGIC     result_type="integer"
# MAGIC )
# MAGIC
# MAGIC df_with_predictions = df.withColumn(
# MAGIC     "prediction",
# MAGIC     loaded_model(struct(*feature_columns))
# MAGIC )
# MAGIC ```
# MAGIC
# MAGIC ### 3. Monitoramento e Retraining
# MAGIC
# MAGIC - Configure Databricks Jobs para executar os notebooks de treino periodicamente
# MAGIC - Monitore drift de features e performance do modelo
# MAGIC - Use MLflow para comparar versões e decidir quando retreinar
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Pipeline MLOps Implementado
# MAGIC
# MAGIC 1. `01_load_data` - Carregamento de dados brutos
# MAGIC 2. `02_data_processing` - Preparação de features e split train/test
# MAGIC 3. `03_model_training` - Treinamento e registro no Unity Catalog
# MAGIC 4. `04_model_evaluation` - Avaliação no conjunto de teste
# MAGIC 5. `05_model_deployment` - Promoção para produção
