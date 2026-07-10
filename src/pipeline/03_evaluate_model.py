#!/usr/bin/env python
"""
Script 03: Model Evaluation (A/B Testing)

Executa teste A/B entre challenger e production para decidir se o novo modelo
deve ser promovido para produção.

Conceito de Teste A/B em MLOps:
    Ao invés de deployar cegamente um modelo novo, comparamos objetivamente:
    - Mesmos dados de teste
    - Mesmas métricas
    - Decisão baseada em números, não intuição
    
    Se challenger > production: Recomenda promoção
    Se production >= challenger: Mantém atual

Este script não promove automaticamente. Apenas recomenda.
A promoção é feita por 04_promote_model.py após confirmação.

Uso:
    python -m src.pipeline.03_evaluate_model --catalog study --schema mlops_iris
"""

import argparse
import logging
import sys
from pathlib import Path

# Adicionar diretório src ao path (compatível com Databricks Jobs)
try:
    # Tenta usar __file__ (disponível em execução normal Python)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
except NameError:
    # __file__ não disponível (Databricks Jobs) - usar caminho absoluto
    sys.path.insert(0, '/Workspace/Users/eduardolimaofficial410@gmail.com/teste_mlops')

from src.utils.model_evaluation import ModelEvaluator
from src.utils.data_utils import get_spark_session, load_train_test_data

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """
    Processa argumentos da linha de comando.
    
    Returns:
        Namespace com argumentos parseados
    """
    parser = argparse.ArgumentParser(description='Model Evaluation Pipeline')
    parser.add_argument('--catalog', type=str, default='study', help='UC Catalog name (default: study)')
    parser.add_argument('--schema', type=str, default='mlops_iris', help='UC Schema name (default: mlops_iris)')
    return parser.parse_args()


def main(catalog: str, schema: str):
    """
    Executa avaliação A/B entre challenger e production.
    
    Fluxo:
    1. Carrega dados de teste
    2. Inicializa ModelEvaluator
    3. Carrega challenger e production do MLflow
    4. Avalia ambos nos mesmos dados
    5. Compara métricas
    6. Exibe resultados detalhados
    7. Recomenda ação (promover ou manter)
    
    Args:
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
    
    Métricas comparadas:
    - Accuracy: % de acertos totais
    - Precision: % de positivos preditos corretos
    - Recall: % de positivos reais detectados
    - F1-Score: Balanço entre precision e recall
    
    Decisão:
        Vencedor = modelo com MAIOR accuracy
        
        Em produção real, você pode usar critérios mais complexos:
        - Múltiplas métricas (precision + recall)
        - Métricas de negócio (revenue, custo)
        - Latência de inferência
        - Tamanho do modelo
    
    Conceitos:
    
    Por que não promover automaticamente?
        Separamos avaliação (03) de promoção (04) para:
        - Revisão humana se necessário
        - Validações adicionais
        - Aprovações de negócio
        - Rollback mais seguro
    
    Threshold de melhoria:
        Você pode adicionar threshold mínimo:
        "Só promove se challenger for X% melhor"
        Isso evita trocas por melhorias insignificantes.
    """
    logger.info("=" * 60)
    logger.info("MLOPS: MODEL EVALUATION PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Target: {catalog}.{schema}")
    
    # =========================================================================
    # 1. CARREGAR DADOS DE TESTE
    # =========================================================================
    # Usar dados de teste (nunca vistos durante treino)
    # Garante avaliação justa de ambos os modelos
    logger.info("\nCarregando dados de teste...")
    spark = get_spark_session()
    _, X_test, _, y_test = load_train_test_data(spark, catalog, schema)
    logger.info(f"Teste: {len(X_test)} registros")
    
    # =========================================================================
    # 2. INICIALIZAR AVALIADOR
    # =========================================================================
    # ModelEvaluator encapsula toda lógica de comparação
    model_name = f"{catalog}.{schema}.logistic_regression_iris"
    evaluator = ModelEvaluator(model_name)
    
    # =========================================================================
    # 3. EXECUTAR TESTE A/B
    # =========================================================================
    logger.info("\nExecutando teste A/B: challenger vs production...")
    logger.info("Carregando modelos do MLflow...")
    
    results = evaluator.evaluate_challenger_vs_production(X_test, y_test)
    
    # =========================================================================
    # 4. VERIFICAR SE AVALIAÇÃO FOI EXECUTADA
    # =========================================================================
    # Casos especiais:
    # - status='no_production': Nenhum modelo em produção ainda
    # - status='no_challenger': Nenhum candidato para avaliar
    if results['status'] != 'evaluated':
        logger.warning(f"Avaliação não executada: {results['message']}")
        logger.warning("\nAções necessárias:")
        if results['status'] == 'no_production':
            logger.warning("  1. Execute 02_train_model.py para criar baseline")
            logger.warning("  2. Execute 04_promote_model.py para promover baseline → production")
        elif results['status'] == 'no_challenger':
            logger.warning("  1. Execute 02_train_model.py para criar challenger")
        return
    
    # =========================================================================
    # 5. EXIBIR RESULTADOS
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("RESULTADOS DO TESTE A/B")
    logger.info("=" * 60)
    
    # Informações das versões
    logger.info(f"\nproduction: v{results['production_version']}")
    logger.info(f"challenger: v{results['challenger_version']}")
    
    # Métricas do production
    logger.info("\n--- PRODUCTION (Modelo Atual) ---")
    prod_metrics = results['production']
    logger.info(f"Accuracy:  {prod_metrics['accuracy']:.4f}")
    logger.info(f"Precision: {prod_metrics['precision']:.4f}")
    logger.info(f"Recall:    {prod_metrics['recall']:.4f}")
    logger.info(f"F1-Score:  {prod_metrics['f1_score']:.4f}")
    
    # Métricas do challenger
    logger.info("\n--- CHALLENGER (Modelo Novo) ---")
    chal_metrics = results['challenger']
    logger.info(f"Accuracy:  {chal_metrics['accuracy']:.4f}")
    logger.info(f"Precision: {chal_metrics['precision']:.4f}")
    logger.info(f"Recall:    {chal_metrics['recall']:.4f}")
    logger.info(f"F1-Score:  {chal_metrics['f1_score']:.4f}")
    
    # Comparação
    logger.info("\n" + "=" * 60)
    logger.info("DECISÃO")
    logger.info("=" * 60)
    logger.info(f"\nVencedor: {results['winner']}")
    logger.info(f"Melhoria em accuracy: {results['improvement']:+.4f}")
    
    # Recomendação
    if results['should_promote']:
        logger.info("\n✅ RECOMENDAÇÃO: PROMOVER challenger → production")
        logger.info("\nNovo modelo apresentou melhoria significativa.")
        logger.info("Execute o próximo passo para promover:")
        logger.info(f"  python -m src.pipeline.04_promote_model --catalog {catalog} --schema {schema}")
    else:
        logger.info("\n❌ RECOMENDAÇÃO: MANTER production")
        logger.info("\nModelo atual ainda é superior ou equivalente.")
        logger.info("Considere:")
        logger.info("  1. Ajustar hiperparâmetros do modelo")
        logger.info("  2. Adicionar mais features")
        logger.info("  3. Coletar mais dados de treino")
    
    logger.info("\n" + "=" * 60)
    logger.info("AVALIAÇÃO CONCLUÍDA")
    logger.info("=" * 60)


def cli_main() -> None:
    """Entry point para execução via linha de comando ou Python wheel."""
    args = parse_args()
    main(args.catalog, args.schema)


if __name__ == "__main__":
    cli_main()
