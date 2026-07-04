# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Load test data
# Load test dataset from Delta table
df_test = spark.sql("SELECT * FROM study.mlops_iris.iris_test").toPandas()

# COMMAND ----------

import mlflow

mlflow.set_registry_uri("databricks-uc")
client = mlflow.MlflowClient()

# COMMAND ----------

# DBTITLE 1,Load model as Spark UDF
model_name = "study.mlops_iris.logistic_regression_iris"

# Obtém a versão do modelo marcada como BaseLine
latest_model_version = client.get_model_version_by_alias(
    name=model_name, 
    alias="BaseLine"
).version

model_uri = f"models:/{model_name}/{latest_model_version}"

# Cria Spark UDF para batch inference 
predict_func = mlflow.pyfunc.spark_udf(spark, model_uri)

# COMMAND ----------

# DBTITLE 1,Make predictions on test set
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    classification_report, confusion_matrix
)

# Separate features and target
feature_cols = ['sepal_length_cm', 'sepal_width_cm', 'petal_length_cm', 'petal_width_cm']
X_test = df_test[feature_cols]
y_test = df_test['target']

# Enable autolog for sklearn
mlflow.sklearn.autolog(
    log_input_examples=True,
    log_model_signatures=True,
    log_models=False,  # We already have the model registered
    disable=False,
    exclusive=False,
    disable_for_unsupported_versions=False,
    silent=False
)

# Start MLflow run for evaluation
with mlflow.start_run(run_name="baseline_evaluation") as run:
    
    # Load the model and make predictions
    loaded_model = mlflow.pyfunc.load_model(model_uri)
    y_pred = loaded_model.predict(X_test)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Log evaluation metrics
    mlflow.log_metric("test_accuracy", accuracy)
    mlflow.log_metric("test_precision", precision)
    mlflow.log_metric("test_recall", recall)
    mlflow.log_metric("test_f1_score", f1)
    
    # Log model metadata
    mlflow.log_param("model_name", model_name)
    mlflow.log_param("model_version", latest_model_version)
    mlflow.log_param("model_alias", "BaseLine")
    mlflow.log_param("test_samples", len(y_test))
    
    # Generate and log confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    cm_fig = plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Setosa', 'Versicolor', 'Virginica'],
                yticklabels=['Setosa', 'Versicolor', 'Virginica'],
                cbar_kws={'label': 'Count'})
    plt.xlabel('Predicted Label', fontsize=12)
    plt.ylabel('True Label', fontsize=12)
    plt.title('Confusion Matrix - Iris Classification', fontsize=14, fontweight='bold')
    plt.tight_layout()
    mlflow.log_figure(cm_fig, "confusion_matrix.png")
    plt.show()
    plt.close()
    
    # Generate and log classification report
    class_report = classification_report(
        y_test, y_pred, 
        target_names=['Setosa', 'Versicolor', 'Virginica'],
        output_dict=True
    )
    
    # Log per-class metrics
    for class_name, metrics in class_report.items():
        if isinstance(metrics, dict):
            for metric_name, value in metrics.items():
                mlflow.log_metric(f"{class_name}_{metric_name}", value)
    
    # Save classification report as text artifact
    report_text = classification_report(
        y_test, y_pred,
        target_names=['Setosa', 'Versicolor', 'Virginica']
    )
    with open("/tmp/classification_report.txt", "w") as f:
        f.write("="*70 + "\n")
        f.write("MODEL EVALUATION REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Version: {latest_model_version}\n")
        f.write(f"Alias: BaseLine\n\n")
        f.write("Overall Metrics:\n")
        f.write(f"  Accuracy:  {accuracy:.4f}\n")
        f.write(f"  Precision: {precision:.4f}\n")
        f.write(f"  Recall:    {recall:.4f}\n")
        f.write(f"  F1-Score:  {f1:.4f}\n\n")
        f.write("Per-Class Metrics:\n")
        f.write(report_text)
    mlflow.log_artifact("/tmp/classification_report.txt")
    
    # Log prediction distribution
    unique, counts = np.unique(y_pred, return_counts=True)
    pred_dist = dict(zip(unique.astype(int), counts.astype(int)))
    for class_label, count in pred_dist.items():
        mlflow.log_metric(f"predictions_class_{class_label}", count)
    
    run_id = run.info.run_id
    experiment_id = run.info.experiment_id
    
    # Print summary
    print("Test Set Evaluation Results:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-Score:  {f1:.4f}")
    print(f"\nPrediction Distribution:")
    for label, count in zip(unique, counts):
        print(f"  Class {int(label)}: {count} samples")
    print(f"\nMLflow tracking:")
    print(f"  Experiment ID: {experiment_id}")
    print(f"  Run ID: {run_id}")
