"""
Evaluation Utility Functions

Funções para cálculo de métricas de classificação.

Conceito: Após treinar um modelo, precisamos avaliar sua performance.
Métricas comuns para classificação:
- Accuracy: % de acertos totais
- Precision: % de positivos preditos que são realmente positivos
- Recall: % de positivos reais que foram detectados
- F1-Score: Média harmônica entre precision e recall
"""

from typing import Dict
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


def evaluate_model(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict:
    """
    Avalia modelo de classificação e retorna métricas completas.
    
    Processo:
    1. Faz predições em dados de teste
    2. Compara predições com labels reais
    3. Calcula múltiplas métricas
    
    Args:
        model: Modelo treinado com método .predict()
        X_test: Features de teste
        y_test: Labels reais de teste
        
    Returns:
        Dict com métricas:
        {
            'accuracy': float (0-1),
            'precision': float (0-1),
            'recall': float (0-1),
            'f1_score': float (0-1),
            'confusion_matrix': list[list[int]],
            'classification_report': str (tabela formatada)
        }
    
    Explicação das métricas:
    
    Accuracy = (TP + TN) / Total
    - Mede acertos totais
    - Problema: não funciona bem com classes desbalanceadas
    
    Precision = TP / (TP + FP)
    - Dos que previ como positivo, quantos acertei?
    - Importante quando False Positive é caro
    
    Recall = TP / (TP + FN)
    - Dos positivos reais, quantos detectei?
    - Importante quando False Negative é caro
    
    F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
    - Balanço entre precision e recall
    
    Onde:
    TP = True Positive (acertou positivo)
    TN = True Negative (acertou negativo)
    FP = False Positive (errou, previu positivo mas era negativo)
    FN = False Negative (errou, previu negativo mas era positivo)
    
    Exemplo:
        from src.utils.evaluation_utils import evaluate_model
        
        model = LogisticRegression()
        model.fit(X_train, y_train)
        
        metrics = evaluate_model(model, X_test, y_test)
        print(f"Accuracy: {metrics['accuracy']:.2f}")
    """
    # Fazer predições
    y_pred = model.predict(X_test)
    
    # Calcular métricas
    # average='weighted': Média ponderada por número de samples de cada classe
    # zero_division=0: Se precision/recall for 0/0, retorna 0 em vez de erro
    return {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(
            y_test, y_pred,
            average='weighted',
            zero_division=0
        )),
        'recall': float(recall_score(
            y_test, y_pred,
            average='weighted',
            zero_division=0
        )),
        'f1_score': float(f1_score(
            y_test, y_pred,
            average='weighted',
            zero_division=0
        )),
        # Confusion Matrix: Tabela de confusão
        # Linhas = Label real, Colunas = Label predito
        # confusion_matrix[i][j] = Quantas vezes classe i foi predita como j
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        
        # Classification Report: Tabela formatada com todas as métricas
        'classification_report': classification_report(y_test, y_pred)
    }


def compare_models(
    model_production,
    model_challenger,
    X_test: pd.DataFrame,
    y_test: pd.Series
) -> Dict:
    """
    Compara dois modelos lado a lado (teste A/B).
    
    Usado para decidir se um novo modelo (challenger) deve substituir
    o modelo atual em produção (production).
    
    Decisão de promoção: challenger vence se accuracy for maior que production.
    
    Args:
        model_production: Modelo atual em produção
        model_challenger: Modelo candidato (recém-treinado)
        X_test: Features de teste
        y_test: Labels de teste
        
    Returns:
        Dict com:
        {
            'production': dict (métricas do production),
            'challenger': dict (métricas do challenger),
            'winner': str ('production' ou 'challenger'),
            'improvement': float (diferença de accuracy)
        }
    
    Conceito de Teste A/B:
        Ao invés de simplesmente deployar um modelo novo, comparamos
        objetivamente com o modelo atual usando as mesmas métricas e dados.
        
        Se challenger for melhor: promove
        Se production for melhor: mantém atual
        
        Isso garante que produção nunca piora.
    
    Exemplo:
        from src.utils.evaluation_utils import compare_models
        
        # production é o modelo atual (v5)
        production = load_model_by_alias("model", "production")
        
        # challenger é o novo modelo (v6)
        challenger = load_model_by_alias("model", "challenger")
        
        # Comparar
        results = compare_models(production, challenger, X_test, y_test)
        
        if results['winner'] == 'challenger':
            print(f"Novo modelo venceu! Melhoria: {results['improvement']:.4f}")
            # Promover challenger para production
        else:
            print("Modelo atual continua sendo o melhor")
    """
    # Avaliar production
    metrics_production = evaluate_model(model_production, X_test, y_test)
    
    # Avaliar challenger
    metrics_challenger = evaluate_model(model_challenger, X_test, y_test)
    
    # Decidir vencedor baseado em accuracy
    # Em produção real, você pode usar múltiplas métricas
    # ou critérios de negócio (ex: latência, custo)
    winner = 'challenger' if metrics_challenger['accuracy'] > metrics_production['accuracy'] else 'production'
    
    # Calcular melhoria (pode ser negativa se challenger for pior)
    improvement = metrics_challenger['accuracy'] - metrics_production['accuracy']
    
    return {
        'production': metrics_production,
        'challenger': metrics_challenger,
        'winner': winner,
        'improvement': float(improvement)
    }
