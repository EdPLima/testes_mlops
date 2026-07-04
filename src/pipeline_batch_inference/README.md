# 📊 Pipeline de Inferência Batch

## 🎯 Objetivo

Pipeline **INDEPENDENTE** do pipeline de retreino (`src/pipeline/`) para fazer predições em lote usando o modelo "production".

## 🆚 Diferença dos Pipelines

| Pipeline de Retreino | Pipeline de Inferência |
|---------------------|------------------------|
| `src/pipeline/` | `src/pipeline_batch_inference/` |
| Treina modelos | Usa modelo existente |
| Mensal / sob demanda | Diário / sob demanda |
| Output: Modelo no Registry | Output: Predições em Delta |

## 📂 Estrutura

```
src/pipeline_batch_inference/
├── 01_load_new_data.py      # Carrega dados de dataset_drift
├── 02_preprocess.py          # Pré-processa features
├── 03_run_inference.py       # Carrega modelo + prediz
├── 04_save_predictions.py    # Salva em batch_predictions
└── 05_save_metadata.py       # Registra metadados
```

## 🔄 Fluxo

```
Novos dados
    ↓
[1] Carregar de dataset_drift
    ↓
[2] Pré-processar
    ↓
[3] Carregar "production" + Inferir
    ↓
[4] Salvar em batch_predictions
    ↓
[5] Salvar metadados
```

## ▶️ Como Executar

```bash
# Executar pipeline completo
python -m src.pipeline_batch_inference.01_load_new_data --catalog study --schema mlops_iris
python -m src.pipeline_batch_inference.02_preprocess
python -m src.pipeline_batch_inference.03_run_inference --catalog study --schema mlops_iris
python -m src.pipeline_batch_inference.04_save_predictions --catalog study --schema mlops_iris
python -m src.pipeline_batch_inference.05_save_metadata
```

## 📋 Pré-requisitos

1. **Modelo production existe** no MLflow Registry
2. **Tabela dataset_drift populada:**
   ```sql
   INSERT INTO study.mlops_iris.dataset_drift 
   VALUES (5.1, 3.5, 1.4, 0.2);
   ```

## 📊 Tabelas

**INPUT:** `study.mlops_iris.dataset_drift`  
**OUTPUT:** `study.mlops_iris.batch_predictions`

## 🔍 Queries de Monitoramento

```sql
-- Predições de hoje
SELECT * FROM study.mlops_iris.batch_predictions
WHERE data_carga = CURRENT_DATE();

-- Predições incertas
SELECT * FROM study.mlops_iris.batch_predictions
WHERE prediction_probability < 0.7;

-- Drift temporal
SELECT data_carga, AVG(sepal_length_cm)
FROM study.mlops_iris.batch_predictions
GROUP BY data_carga;
```

## ⚠️ Quando Retreinar

Execute `src/pipeline/` se:
- Confiança média < 75%
- % predições incertas > 15%
- Drift de features > 20%
