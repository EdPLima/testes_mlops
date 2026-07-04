# src/pipeline/ - Pipeline de Retreino MLOps

Scripts executáveis que implementam a esteira de retreino automatizado.

## Ordem de Execução

### 01_process_data.py

Primeiro passo: Processa e valida dados.

O que faz:
- Carrega dados brutos (iris_raw) do Unity Catalog
- Valida qualidade (valores nulos, tipos, ranges)
- Divide em treino (70%) e teste (30%)
- Salva iris_train e iris_test no Unity Catalog

Parâmetros:
- --catalog: Nome do catálogo UC (padrão: study)
- --schema: Nome do schema UC (padrão: mlops_iris)

Execução:
```bash
python -m src.pipeline.01_process_data --catalog study --schema mlops_iris
```

Saída:
- Tabela: catalog.schema.iris_train
- Tabela: catalog.schema.iris_test

### 02_train_model.py

Segundo passo: Treina novo modelo.

O que faz:
- Carrega dados de treino e teste
- Treina LogisticRegression com hiperparâmetros
- Registra modelo no MLflow Registry
- Define alias baseado no contexto:
  - Se não existe Champion: alias "BaseLine"
  - Se existe Champion: alias "Challenger"

Parâmetros:
- --catalog: Catálogo UC
- --schema: Schema UC
- --max-iter: Máximo de iterações (padrão: 200)
- --solver: Algoritmo solver (padrão: lbfgs)
- --run-name: Nome do run MLflow (padrão: iris_training)

Execução:
```bash
python -m src.pipeline.02_train_model \
    --catalog study \
    --schema mlops_iris \
    --max-iter 200
```

Saída:
- Modelo registrado no MLflow
- Alias: "BaseLine" ou "Challenger"
- Métricas: train_accuracy, test_accuracy

### 03_evaluate_model.py

Terceiro passo: Teste A/B entre Challenger e Champion.

O que faz:
- Carrega Challenger do MLflow
- Carrega Champion do MLflow
- Avalia ambos em dados de teste
- Compara métricas:
  - Accuracy
  - Precision
  - Recall
  - F1-Score
- Decide vencedor (maior accuracy)
- Recomenda promoção ou não

Parâmetros:
- --catalog: Catálogo UC
- --schema: Schema UC

Execução:
```bash
python -m src.pipeline.03_evaluate_model --catalog study --schema mlops_iris
```

Saída (exemplo):
```
VENCEDOR: Challenger
Melhoria: 0.0234

RECOMENDAÇÃO: Promover Challenger para Champion
Execute: python -m src.pipeline.04_promote_model
```

Quando executar:
- Após 02_train_model.py criar Challenger
- Antes de promover para produção

### 04_promote_model.py

Quarto passo: Promove Challenger para Champion.

O que faz:
- Verifica se existe Challenger
- Define alias "Champion" para versão do Challenger
- Remove alias "Challenger"
- Modelo promovido está pronto para produção

Parâmetros:
- --catalog: Catálogo UC
- --schema: Schema UC

Execução:
```bash
python -m src.pipeline.04_promote_model --catalog study --schema mlops_iris
```

Importante:
- Execute apenas se 03_evaluate_model.py recomendar promoção
- Após execução, Challenger vira Champion
- Champion anterior permanece no registro (sem alias)

### 05_monitor_drift.py

Quinto passo: Monitora modelo em produção.

O que faz:
- Carrega Champion (modelo em produção)
- Monitora performance em dados de produção
- Detecta drift de features
- Detecta drift de predições
- Aciona alertas se necessário
- Se drift crítico: dispara retreino

Parâmetros:
- --catalog: Catálogo UC
- --schema: Schema UC

Execução:
```bash
python -m src.pipeline.05_monitor_drift --catalog study --schema mlops_iris
```

Frequência recomendada:
- A cada 6 horas (configurado em resources/monitoring_job.yml)
- Ou após cada batch de inferências

## Fluxo Completo

```
01_process_data
    |
    | Dados processados e salvos
    v
02_train_model
    |
    | Modelo treinado
    | Alias: BaseLine (primeira vez) ou Challenger (próximas vezes)
    v
03_evaluate_model
    |
    | Compara Challenger vs Champion
    | Calcula métricas
    v
    Challenger venceu?
    |
    +-- SIM --> 04_promote_model
    |               |
    |               | Challenger vira Champion
    |               v
    |           Produção atualizada
    |
    +-- NÃO --> Mantém Champion atual
                    |
                    v
                Descarta Challenger
    
05_monitor_drift (loop contínuo)
    |
    | Monitora Champion em produção
    | Detecta drift
    v
    Drift detectado?
    |
    +-- SIM --> Aciona retreino (volta para 01_process_data)
    |
    +-- NÃO --> Continua monitorando
```

## Automação via Databricks Jobs

Configurado em resources/:

training_job.yml:
- Executa: 01 → 02
- Frequência: Diariamente às 2h

evaluation_job.yml:
- Executa: 03 → 04 (se recomendado)
- Trigger: Após training_job

monitoring_job.yml:
- Executa: 05
- Frequência: A cada 6 horas

## Integração com Notebooks

Os notebooks em notebooks/ usam as mesmas funções de src/utils/:

```python
# Em notebooks/04_model_evaluation.ipynb
from src.utils.model_evaluation import ModelEvaluator

evaluator = ModelEvaluator("study.mlops_iris.logistic_regression_iris")
results = evaluator.evaluate_challenger_vs_champion(X_test, y_test)
```

Diferença:
- Notebooks: Exploração interativa, visualizações
- Scripts pipeline: Automação, execução por Jobs
