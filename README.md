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

## Architecture

- **Environments**: dev, staging, prod
- **Unity Catalog**: Catálogos separados por ambiente
- **MLflow**: Rastreamento de experimentos e modelo registry
- **Databricks Jobs**: 4 jobs principais (training, inference, evaluation, monitoring)