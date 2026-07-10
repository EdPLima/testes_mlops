#!/usr/bin/env python
"""
Script 04: Model Promotion

Promove modelo challenger para production (produção).

Este é o último passo do processo de retreino:
- 01_process_data: Prepara dados
- 02_train_model: Treina modelo challenger
- 03_evaluate_model: Compara challenger vs production
- 04_promote_model: Promove challenger → production (ESTE SCRIPT)

Após promoção:
- challenger vira production (modelo em produção)
- Alias "challenger" é removido
- production anterior mantém sua versão mas perde alias

Uso:
    python -m src.pipeline.04_promote_model --catalog study --schema mlops_iris
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

from src.utils.mlflow_utils import (
    setup_mlflow,
    get_model_version_by_alias,
    set_model_alias,
    delete_model_alias
)

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
    parser = argparse.ArgumentParser(description='Model Promotion Pipeline')
    parser.add_argument('--catalog', type=str, default='study', help='UC Catalog name (default: study)')
    parser.add_argument('--schema', type=str, default='mlops_iris', help='UC Schema name (default: mlops_iris)')
    return parser.parse_args()


def main(catalog: str, schema: str):
    """
    Promove challenger para production.
    
    Fluxo:
    1. Verifica se existe challenger
    2. Busca versão do challenger
    3. Define essa versão como novo production
    4. Remove alias challenger
    5. Confirma promoção
    
    Args:
        catalog: Catálogo Unity Catalog
        schema: Schema Unity Catalog
    
    Conceitos:
    
    Por que separar avaliação de promoção?
        - Revisão humana: Permite análise antes de deploy
        - Aprovações: Permite workflow de aprovação
        - Rollback: Facilita voltar atrás se necessário
        - Auditoria: Promoção é ação explícita e rastreável
    
    O que acontece com versões antigas?
        - Continuam existindo no registry (versionamento completo)
        - Apenas perdem o alias "production"
        - Podem ser carregadas por número de versão
        - Útil para rollback: basta reatribuir alias production
    
    Rollback de emergência:
        Se novo production tem problema em produção:
        
        from src.utils.mlflow_utils import set_model_alias, setup_mlflow
        
        client = setup_mlflow()
        model_name = "study.mlops_iris.logistic_regression_iris"
        
        # Voltar para versão 5 (por exemplo)
        set_model_alias(client, model_name, "production", 5)
    
    Promoção idempotente:
        Se você executar este script múltiplas vezes, não há problema.
        Ele simplesmente redefine o alias production.
    """
    logger.info("=" * 60)
    logger.info("MLOPS: MODEL PROMOTION PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Target: {catalog}.{schema}")
    
    # =========================================================================
    # 1. SETUP
    # =========================================================================
    client = setup_mlflow()
    model_name = f"{catalog}.{schema}.logistic_regression_iris"
    
    # =========================================================================
    # 2. VERIFICAR SE EXISTE CHALLENGER
    # =========================================================================
    logger.info("\nVerificando challenger...")
    challenger_version = get_model_version_by_alias(client, model_name, "challenger")
    
    if not challenger_version:
        logger.error("Nenhum challenger encontrado para promoção")
        logger.error("\nPRÉ-REQUISITOS:")
        logger.error("  1. Execute 02_train_model.py para criar challenger")
        logger.error("  2. Execute 03_evaluate_model.py para avaliar")
        logger.error("  3. Execute este script apenas se recomendado")
        return
    
    logger.info(f"challenger encontrado: v{challenger_version}")
    
    # Verificar production atual (informativo)
    current_production_version = get_model_version_by_alias(client, model_name, "production")
    if current_production_version:
        logger.info(f"production atual: v{current_production_version}")
    else:
        logger.info("Nenhum production atual (primeira promoção)")
    
    # =========================================================================
    # 3. CONFIRMAÇÃO (em produção, você pode adicionar input do usuário)
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("INICIANDO PROMOÇÃO")
    logger.info("=" * 60)
    
    # Em ambiente interativo, você poderia adicionar:
    # confirm = input(f"Promover v{challenger_version} para production? (yes/no): ")
    # if confirm.lower() != 'yes':
    #     logger.info("Promoção cancelada")
    #     return
    
    # =========================================================================
    # 4. PROMOÇÃO
    # =========================================================================
    logger.info(f"\nPromovendo v{challenger_version} para production...")
    
    # Define challenger como novo production
    # Se já existe production, ele é movido automaticamente
    set_model_alias(client, model_name, "production", challenger_version)
    logger.info("Alias 'production' atualizado com sucesso")
    
    # Remove alias challenger (limpeza)
    # A versão continua existindo, apenas perde a tag "challenger"
    logger.info("Removendo alias 'challenger'...")
    delete_model_alias(client, model_name, "challenger")
    logger.info("Alias 'challenger' removido com sucesso")
    
    # =========================================================================
    # 5. CONFIRMAÇÃO FINAL
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PROMOÇÃO CONCLUÍDA COM SUCESSO")
    logger.info("=" * 60)
    logger.info(f"\nModelo promovido:")
    logger.info(f"  Versão: v{challenger_version}")
    logger.info(f"  Alias: production")
    logger.info(f"  Nome: {model_name}")
    
    # =========================================================================
    # 6. PRÓXIMOS PASSOS
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PRÓXIMOS PASSOS")
    logger.info("=" * 60)
    logger.info("\n1. Monitorar modelo em produção:")
    logger.info(f"   python -m src.pipeline.05_monitor_drift --catalog {catalog} --schema {schema}")
    logger.info("\n2. Em caso de problema, fazer rollback:")
    logger.info("   from src.utils.mlflow_utils import set_model_alias, setup_mlflow")
    logger.info("   client = setup_mlflow()")
    logger.info(f"   set_model_alias(client, '{model_name}', 'production', {current_production_version or 'VERSION_ANTERIOR'})")
    logger.info("\n3. Retreinar modelo periodicamente:")
    logger.info("   - Execute novamente 01_process_data.py com dados atualizados")
    logger.info("   - Execute 02_train_model.py para criar novo challenger")
    logger.info("   - Repita ciclo de avaliação → promoção")


def cli_main() -> None:
    """Entry point para execução via linha de comando ou Python wheel."""
    args = parse_args()
    main(args.catalog, args.schema)


if __name__ == "__main__":
    cli_main()
