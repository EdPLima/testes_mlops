# Iris Classification MLOps Pipeline

Pipeline MLOps completo para classificação de Iris com CI/CD, retreino automático e monitoramento.

## Features

- **Training Pipeline**: Treina modelos automaticamente e registra no MLflow
- **Batch Inference**: Executa inferência em lote usando modelo em produção
- **Model Evaluation**: Compara modelos Challenger vs Champion
- **Monitoring**: Monitora drift do modelo em produção
- **CI/CD**: Deploy automatizado via GitHub Actions (staging/prod)

## Quick Start

```bash
# Deploy to dev environment
databricks bundle deploy --target dev

# Run training pipeline
databricks bundle run mlops_training_pipeline --target dev
```

## Documentation

- [Bundle Guide](BUNDLE_GUIDE.md) - Como usar Databricks Bundles
- [CI/CD Guide](CI_CD_GUIDE.md) - Como configurar CI/CD com GitHub Actions

## 📁 Estrutura do Projeto

```
testes_mlops/
├── src/teste_mlops/          # Código Python do projeto
│   ├── pipelines/            # Pipelines de MLOps
│   │   ├── training.py       # Pipeline de treinamento
│   │   ├── inference.py      # Pipeline de inferência em lote
│   │   ├── evaluation.py     # Avaliação Challenger vs Champion
│   │   └── monitoring.py     # Monitoramento de drift
│   └── utils/                # Utilitários compartilhados
├── resources/                # Definições de Jobs (YAML)
│   ├── training_job.yml      # Job de treinamento
│   ├── batch_inference_job.yml
│   ├── evaluation_job.yml
│   └── monitoring_job.yml
├── notebooks/                # Notebooks exploratórios
├── tests/                    # Testes unitários
├── databricks.yml            # Configuração do Bundle
└── pyproject.toml            # Dependências Python
```

## 🏗️ Arquitetura MLOps

### Ambientes
- **dev**: Desenvolvimento local/exploratório
- **staging**: Testes antes de produção
- **prod**: Ambiente de produção

### Unity Catalog
Cada ambiente tem seu próprio schema:
- `study.mlops_iris_dev`
- `study.mlops_iris_staging` 
- `study.mlops_iris_prod`

### MLflow Registry
- **Challenger**: Modelo recém-treinado aguardando validação
- **Champion**: Modelo atual em produção
- **Aliases**: `@challenger`, `@champion` para versionamento

### 4 Pipelines Principais

1. **Training Pipeline** (Diário às 2AM)
   - Carrega dados de treino
   - Treina modelo (LogisticRegression)
   - Registra como `Challenger` no MLflow
   - Salva métricas de validação

2. **Evaluation Pipeline** (Manual/On-demand)
   - Compara métricas: Challenger vs Champion
   - Se Challenger for melhor → Promove para Champion
   - Registra decisão no MLflow

3. **Batch Inference Pipeline** (Diário às 3:30AM)
   - Carrega modelo Champion
   - Processa novos dados
   - Salva predições em batch_predictions

4. **Monitoring Pipeline** (A cada 6 horas)
   - Calcula drift de dados (statistical tests)
   - Calcula drift de modelo (accuracy degradation)
   - Gera alertas se drift > threshold

## 🚀 Conceitos Importantes

### Serverless Compute
Todos os jobs usam **Serverless** (não precisa criar clusters):
```yaml
environments:
  - environment_key: "default"
    spec:
      dependencies:
        - "../dist/*.whl"  # Seu pacote Python
        - "scikit-learn"
        - "mlflow"
```

### Python Wheel Package
O código é empacotado como `.whl` (wheel) para distribuição:
- Build: `python -m build`
- Deploy: Databricks Bundle copia para workspace
- Jobs: Instalam o wheel automaticamente

### Databricks Asset Bundles (DABs)
Infraestrutura como código para Databricks:
- `databricks.yml`: Define recursos (jobs, pipelines, dashboards)
- `resources/*.yml`: Configuração de cada job
- `databricks bundle deploy`: Cria/atualiza recursos
- `databricks bundle run`: Executa jobs

## 🔄 Fluxo de Trabalho Completo

```mermaid
grafo TD
    A[Push to main] --> B[GitHub Actions]
    B --> C[Build Wheel]
    C --> D[Deploy Bundle]
    D --> E[Run Training]
    E --> F[Modelo Challenger]
    F --> G[Evaluation]
    G -->|Melhor| H[Promove para Champion]
    G -->|Pior| I[Mantém Champion atual]
    H --> J[Batch Inference]
    J --> K[Monitoring]
    K -->|Drift detectado| L[Alerta + Re-treino]
```

## 🎓 Para Estudar

1. **Databricks Bundles**: Leia [BUNDLE_GUIDE.md](BUNDLE_GUIDE.md)
2. **CI/CD**: Leia [CI_CD_GUIDE.md](CI_CD_GUIDE.md)
3. **MLflow**: Explore notebooks em `notebooks/`
4. **Serverless**: Veja `resources/*.yml` para exemplos

## 🐛 Troubleshooting

### "Cannot launch the cluster"
- **Causa**: Capacidade serverless indisponível (comum em Free Edition)
- **Solução**: Retry em horário diferente ou upgrade para Standard

### Wheel não encontrado
- **Causa**: Path errado em `dependencies`
- **Solução**: Use `../dist/*.whl` (relativo ao YAML)

### Job não atualiza após deploy
- **Causa**: Deploy sem `--force` mantém job antigo
- **Solução**: `databricks bundle deploy --target staging --force`