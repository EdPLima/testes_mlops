"""
MLflow Utility Functions

Este módulo fornece funções reutilizáveis para interação com o MLflow Model Registry.
Todas as funções aqui são usadas pelos scripts do pipeline e podem ser importadas em notebooks.

Conceito: Model Registry é onde os modelos treinados são armazenados e versionados.
Cada modelo tem um nome (catalog.schema.model_name) e versões numeradas (1, 2, 3...).
Aliases são tags que apontam para versões específicas (Champion, Challenger, BaseLine).
"""

from typing import Optional
import mlflow
from mlflow.tracking import MlflowClient


def setup_mlflow(experiment_path: str = "/Shared/mlops_experiments"):
    """
    Configura MLflow para usar Unity Catalog como Model Registry e define o experimento.
    
    Unity Catalog Registry permite:
    - Governança centralizada de modelos
    - Controle de acesso por catálogo/schema
    - Versionamento automático
    - Integração com notebooks e jobs
    
    Args:
        experiment_path: Caminho do experimento MLflow (padrão: "/Shared/mlops_experiments")
    
    Returns:
        MlflowClient: Cliente configurado para Unity Catalog
    
    Exemplo:
        client = setup_mlflow()
        # Agora client pode fazer operações no registry
    """
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(experiment_path)
    return MlflowClient()


def get_latest_model_version(client: MlflowClient, model_name: str) -> int:
    """
    Obtém o número da versão mais recente de um modelo registrado.
    
    Cada vez que um modelo é registrado (mlflow.sklearn.log_model), 
    uma nova versão é criada automaticamente: v1, v2, v3, etc.
    
    Args:
        client: Cliente MLflow configurado
        model_name: Nome completo do modelo (catalog.schema.model_name)
        
    Returns:
        int: Versão mais recente (ex: 5 se última versão é v5)
    
    Exemplo:
        latest = get_latest_model_version(client, "study.mlops_iris.logistic_regression_iris")
        # Se modelo tem v1, v2, v3 -> retorna 3
    """
    # Busca todas as versões do modelo
    versions = client.search_model_versions(f"name = '{model_name}'")
    
    # Retorna o maior número de versão
    return max([int(v.version) for v in versions])


def get_model_version_by_alias(
    client: MlflowClient,
    model_name: str,
    alias: str
) -> Optional[int]:
    """
    Busca a versão de um modelo que possui determinado alias.
    
    Aliases são tags semânticas que apontam para versões específicas:
    - "Champion": Modelo em produção (servindo tráfego real)
    - "Challenger": Modelo candidato (recém-treinado, aguardando avaliação)
    - "BaseLine": Primeiro modelo ou modelo de referência
    
    Args:
        client: Cliente MLflow
        model_name: Nome completo do modelo
        alias: Alias a buscar ("Champion", "Challenger", "BaseLine")
        
    Returns:
        int ou None: Versão do modelo com esse alias, ou None se não existir
    
    Exemplo:
        version = get_model_version_by_alias(client, "study.mlops.lr", "Champion")
        if version:
            print(f"Champion é a versão {version}")
        else:
            print("Nenhum Champion encontrado")
    """
    try:
        # Tenta buscar modelo por alias
        model_version = client.get_model_version_by_alias(model_name, alias)
        return int(model_version.version)
    except Exception:
        # Se alias não existe, retorna None em vez de erro
        return None


def set_model_alias(
    client: MlflowClient,
    model_name: str,
    alias: str,
    version: int
) -> None:
    """
    Define um alias para uma versão específica de modelo.
    
    Se o alias já existir em outra versão, ele é movido para a nova versão.
    Exemplo: Se v5 é "Champion" e você define v6 como "Champion",
    v5 perde o alias e v6 se torna o novo "Champion".
    
    Args:
        client: Cliente MLflow
        model_name: Nome completo do modelo
        alias: Alias a definir
        version: Versão do modelo que receberá o alias
    
    Exemplo:
        # Promover versão 6 para Champion
        set_model_alias(client, "study.mlops.lr", "Champion", 6)
    """
    client.set_registered_model_alias(model_name, alias, version)


def load_model_by_alias(model_name: str, alias: str):
    """
    Carrega um modelo pronto para inferência usando seu alias.
    
    Esta é a forma recomendada de carregar modelos em produção.
    Em vez de versão hardcoded (v5), usa alias ("Champion") que aponta
    sempre para o modelo correto, mesmo quando versões mudam.
    
    Args:
        model_name: Nome completo do modelo
        alias: Alias do modelo a carregar
        
    Returns:
        sklearn model: Modelo sklearn nativo com todos os métodos (.predict, .predict_proba, etc)
    
    Exemplo:
        # Carregar modelo em produção
        model = load_model_by_alias("study.mlops_iris.lr", "Champion")
        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)  # Disponível!
        
        # Carregar modelo candidato
        challenger = load_model_by_alias("study.mlops_iris.lr", "Challenger")
    """
    # Formato URI: models:/<nome>@<alias>
    model_uri = f"models:/{model_name}@{alias}"
    # Usar sklearn.load_model para preservar métodos como predict_proba()
    return mlflow.sklearn.load_model(model_uri)


def delete_model_alias(
    client: MlflowClient,
    model_name: str,
    alias: str
) -> None:
    """
    Remove um alias de modelo.
    
    Usado após promoção: quando Challenger vira Champion,
    removemos o alias "Challenger" para limpar.
    A versão continua existindo, apenas perde o alias.
    
    Args:
        client: Cliente MLflow
        model_name: Nome completo do modelo
        alias: Alias a remover
    
    Exemplo:
        # Após promover Challenger para Champion
        delete_model_alias(client, "study.mlops.lr", "Challenger")
        # Agora essa versão não tem mais alias
    """
    try:
        client.delete_registered_model_alias(model_name, alias)
    except Exception:
        # Se alias não existir, não faz nada (evita erro)
        pass
