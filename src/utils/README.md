# src/utils/ - Funções Reutilizáveis

Biblioteca de utilitários para o pipeline MLOps.

## mlflow_utils.py

Gerenciamento do MLflow Model Registry.

Funções principais:

setup_mlflow()
- Configura MLflow para Unity Catalog
- Retorna MlflowClient configurado
- Uso: client = setup_mlflow()

get_latest_model_version(client, model_name)
- Retorna versão mais recente de um modelo
- Parâmetros: client (MlflowClient), model_name (str)
- Retorna: int (versão)

get_model_version_by_alias(client, model_name, alias)
- Busca modelo por alias (Champion, Challenger, BaseLine)
- Retorna None se não existir
- Uso: version = get_model_version_by_alias(client, "study.mlops.lr", "Champion")

set_model_alias(client, model_name, alias, version)
- Define alias para versão específica
- Uso: set_model_alias(client, "study.mlops.lr", "Champion", 5)

load_model_by_alias(model_name, alias)
- Carrega modelo pronto para inferência
- Retorna mlflow.pyfunc.PyFuncModel
- Uso: model = load_model_by_alias("study.mlops.lr", "Champion")

delete_model_alias(client, model_name, alias)
- Remove alias de modelo
- Uso: delete_model_alias(client, "study.mlops.lr", "Challenger")

## data_utils.py

Carregamento de dados do Unity Catalog.

Funções principais:

get_spark_session()
- Obtém SparkSession ativa
- Lança RuntimeError se não houver sessão
- Retorna: SparkSession

load_data_from_catalog(spark, catalog, schema, table_name)
- Carrega tabela do Unity Catalog como pandas DataFrame
- Parâmetros: spark, catalog (str), schema (str), table_name (str)
- Retorna: pd.DataFrame

load_train_test_data(spark, catalog, schema)
- Carrega iris_train e iris_test do Unity Catalog
- Retorna: Tuple[X_train, X_test, y_train, y_test]
- Features são todas as colunas exceto 'target'

## evaluation_utils.py

Cálculo de métricas de classificação.

Funções principais:

evaluate_model(model, X_test, y_test)
- Avalia modelo em dados de teste
- Retorna dicionário com métricas:
  - accuracy: float
  - precision: float (weighted)
  - recall: float (weighted)
  - f1_score: float (weighted)
  - confusion_matrix: list[list]
  - classification_report: str

compare_models(model_champion, model_challenger, X_test, y_test)
- Compara dois modelos
- Retorna dicionário com:
  - champion: dict (métricas)
  - challenger: dict (métricas)
  - winner: str ('Champion' ou 'Challenger')
  - improvement: float (diferença de accuracy)

## model_evaluation.py

Orquestração de teste A/B.

Classe ModelEvaluator:

Construtor: __init__(model_name)
- model_name: nome completo do modelo (catalog.schema.model_name)
- Inicializa MlflowClient

evaluate_challenger_vs_champion(X_test, y_test)
- Executa teste A/B completo
- Verifica existência de Champion e Challenger
- Compara métricas
- Retorna dict com:
  - status: str ('evaluated', 'no_champion', 'no_challenger')
  - champion_version: int
  - challenger_version: int
  - champion: dict (métricas)
  - challenger: dict (métricas)
  - winner: str
  - improvement: float
  - should_promote: bool
  - message: str

evaluate_single_model(alias, X_test, y_test)
- Avalia um único modelo por alias
- Retorna métricas + version + alias

Exemplo de uso:
```python
from src.utils.model_evaluation import ModelEvaluator

evaluator = ModelEvaluator("study.mlops_iris.logistic_regression_iris")
results = evaluator.evaluate_challenger_vs_champion(X_test, y_test)

if results['should_promote']:
    print(f"{results['winner']} venceu")
    print(f"Melhoria: {results['improvement']:.4f}")
```
