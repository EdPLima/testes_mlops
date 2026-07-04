# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
 from sklearn.datasets import load_iris
 import pandas as pd

# COMMAND ----------

iris = load_iris()
df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
df['target'] = iris.target
df['species'] = df['target'].map({0: 'setosa', 1: 'versicolor', 2: 'virginica'})
df = df.drop('species', axis = 1)

# COMMAND ----------

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# 1. Separar features e target
X = df.drop('target', axis=1)
y = df['target']

# COMMAND ----------

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size= 0.2, random_state= 42)

# COMMAND ----------

print("X_train shape:", X_train.shape)
print("y_train shape:", y_train.shape)
print("X_test shape:", X_test.shape)
print("y_test shape:", y_test.shape)

# COMMAND ----------

padronizer = StandardScaler()
X_train = padronizer.fit_transform(X_train)
X_test = padronizer.transform(X_test)

# COMMAND ----------

# DBTITLE 1,Create DataFrames with proper column names
feature_names = ['sepal_length_cm', 'sepal_width_cm', 'petal_length_cm', 'petal_width_cm']

X_train_df = pd.DataFrame(X_train, columns=feature_names)
X_test_df = pd.DataFrame(X_test, columns=feature_names)

X_train_df['target'] = y_train.values
X_test_df['target'] = y_test.values

# COMMAND ----------

X_train_df

# COMMAND ----------

# DBTITLE 1,Save processed data to Delta tables
# Convert to Spark DataFrames and save as Delta tables
train_spark_df = spark.createDataFrame(X_train_df)
test_spark_df = spark.createDataFrame(X_test_df)

train_spark_df.write.format("delta").mode("overwrite").saveAsTable("study.mlops_iris.iris_train")
test_spark_df.write.format("delta").mode("overwrite").saveAsTable("study.mlops_iris.iris_test")

print(f"Training data saved to: study.mlops_iris.iris_train ({len(X_train_df)} rows)")
print(f"Test data saved to: study.mlops_iris.iris_test ({len(X_test_df)} rows)")

# COMMAND ----------

# DBTITLE 1,Verify saved tables
# Verify the tables were created successfully
spark.sql("SHOW TABLES IN study.mlops_iris").display()
