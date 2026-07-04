# Monitoramento de Modelos

Dashboard de monitoramento da saúde dos modelos em produção.

## Dashboard: model_health_monitoring

**Fonte de dados**: `study.mlops_iris.batch_predictions`

### Métricas Monitoradas

* **Performance**:
  - Precision, Recall, F1-Score, Acurácia
  - Distribuição de confiança das predições
  - Taxa de predições com baixa confiança

* **Versão do Modelo**:
  - Versão atual em produção
  - Histórico de versões
  - Alias do modelo (production)

* **Distribuição de Features**:
  - Comparativo treino vs batch
  - Detecção de drift
  - Análise estatística das features

* **Volume**:
  - Total de predições
  - Predições por data
  - Predições por classe

## Estrutura

```
monitoring/
├── model_health_monitoring.lvdash.json  # Dashboard principal
└── README.md                            # Esta documentação
```

## Acesso

O dashboard está disponível em:
`/Workspace/Users/<seu-user>/teste_mlops/src/monitoring/model_health_monitoring.lvdash.json`

## Atualização

O dashboard é atualizado automaticamente conforme novos dados são inseridos na tabela `batch_predictions` pelo job de batch inference.
