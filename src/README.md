# src/ - Código Fonte do Projeto MLOps

Contém todo o código Python organizado em duas categorias.

## Estrutura

```
src/
├── utils/       Funções reutilizáveis
└── pipeline/    Scripts executáveis
```

## utils/ - Funções Reutilizáveis

Biblioteca de funções que podem ser importadas em qualquer lugar.

Módulos:
- mlflow_utils.py: Operações MLflow Registry
- data_utils.py: Carregamento de dados
- evaluation_utils.py: Cálculo de métricas
- model_evaluation.py: Lógica de teste A/B

Uso em notebooks:
```python
from src.utils.mlflow_utils import load_model_by_alias
model = load_model_by_alias("study.mlops_iris.lr", "Champion")
```

Uso em testes:
```python
from src.utils.evaluation_utils import evaluate_model
metrics = evaluate_model(model, X_test, y_test)
```

## pipeline/ - Scripts Executáveis

Scripts CLI que executam o pipeline MLOps em ordem.

Scripts (ordem de execução):
1. 01_process_data.py: Processa dados
2. 02_train_model.py: Treina modelo
3. 03_evaluate_model.py: Teste A/B
4. 04_promote_model.py: Promoção
5. 05_monitor_drift.py: Monitoramento

Execução:
```bash
python -m src.pipeline.01_process_data --catalog study --schema mlops_iris
python -m src.pipeline.02_train_model --catalog study --schema mlops_iris
```

## Diferença Fundamental

utils/ = Biblioteca (importável)
- Apenas funções
- Sem CLI
- Testável com pytest

pipeline/ = Executáveis (CLI)
- Com argparse e main()
- Executados por Jobs
- Orquestram funções de utils/
