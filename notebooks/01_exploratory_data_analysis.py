# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Análise Exploratória de Dados - Iris Dataset
# MAGIC %md
# MAGIC  Análise Exploratória de Dados - Iris Dataset
# MAGIC
# MAGIC Este notebook tem como objetivo:
# MAGIC
# MAGIC 1. Carregar o dataset Iris do sklearn
# MAGIC 2. Entender a estrutura dos dados
# MAGIC 3. Realizar análise estatística descritiva
# MAGIC 4. Visualizar distribuições e correlações
# MAGIC 5. Identificar padrões e insights
# MAGIC 6. Preparar o terreno para feature engineering
# MAGIC
# MAGIC Este é o primeiro passo do pipeline MLOps.

# COMMAND ----------

# DBTITLE 1,Imports e Configuração
 from sklearn.datasets import load_iris
 import pandas as pd
 import numpy as np
 import matplotlib.pyplot as plt
 import seaborn as sns

 sns.set_style('whitegrid')
 plt.rcParams['figure.figsize'] = (12, 6)

# COMMAND ----------

# DBTITLE 1,Carregar Dataset

iris = load_iris()
df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
df['target'] = iris.target
df['species'] = df['target'].map({0: 'setosa', 1: 'versicolor', 2: 'virginica'})

display(df.head())

# COMMAND ----------

# DBTITLE 1,Análise Estatística Descritiva
print("Shape do dataset:", df.shape)
print("\nInformações do dataset:")
print(df.info())
print("\nEstatísticas descritivas:")
display(df.describe())
print("\nDistribuição das classes:")
print(df['species'].value_counts())
