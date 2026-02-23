"""
API endpoints for advanced transaction analytics
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from accounts.mongo_models import MongoConnection
from ml.analytics import (
    TransactionCategorizer, SpendingPatternAnalyzer, 
    CashFlowForecaster, get_transaction_insights
)
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def transaction_insights_api(request):
    """GET /api/analytics/insights - Get comprehensive transaction insights"""
    try:
        days = int(request.GET.get('days', 30))
        current_balance = float(request.GET.get('balance', 0))
        
        # Fetch user's transactions
        pred_coll = MongoConnection.get_collection(settings.MONGO_COLLECTIONS.get('fraud_predictions', 'fraud_predictions'))
        transactions = list(pred_coll.find(
            {'user_id': str(request.user.id)},
            {'transaction_amount': 1, 'timestamp': 1, 'channel': 1, 'created_at': 1}
        ).limit(1000))
        
        if not transactions:
            return JsonResponse({
                'status': 'success',
                'message': 'No transactions found',
                'insights': {}
            })
        
        # Generate insights
        insights = get_transaction_insights(transactions, current_balance)
        
        return JsonResponse({
            'status': 'success',
            'insights': insights
        })
    
    except Exception as e:
        logger.error(f"Insights API error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def spending_analysis_api(request):
    """GET /api/analytics/spending - Analyze spending patterns"""
    try:
        days = int(request.GET.get('days', 30))
        
        # Fetch user's transactions
        pred_coll = MongoConnection.get_collection(settings.MONGO_COLLECTIONS.get('fraud_predictions', 'fraud_predictions'))
        transactions = list(pred_coll.find(
            {'user_id': str(request.user.id)},
            {'transaction_amount': 1, 'timestamp': 1, 'channel': 1, 'created_at': 1}
        ).limit(1000))
        
        analyzer = SpendingPatternAnalyzer()
        analysis = analyzer.analyze_spending_trends(transactions, days=days)
        
        return JsonResponse({
            'status': 'success',
            'analysis': analysis
        })
    
    except Exception as e:
        logger.error(f"Spending analysis error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def anomalies_api(request):
    """GET /api/analytics/anomalies - Detect unusual transactions"""
    try:
        threshold = float(request.GET.get('threshold', 2.0))
        
        # Fetch user's transactions
        pred_coll = MongoConnection.get_collection(settings.MONGO_COLLECTIONS.get('fraud_predictions', 'fraud_predictions'))
        transactions = list(pred_coll.find(
            {'user_id': str(request.user.id)},
            {'transaction_amount': 1, 'timestamp': 1, 'channel': 1, 'created_at': 1, 'transaction_id': 1}
        ).limit(1000))
        
        analyzer = SpendingPatternAnalyzer()
        anomalies = analyzer.detect_anomalies(transactions, threshold_std=threshold)
        
        return JsonResponse({
            'status': 'success',
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    
    except Exception as e:
        logger.error(f"Anomaly detection error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def cash_flow_forecast_api(request):
    """GET /api/analytics/forecast - Forecast cash flow"""
    try:
        days = int(request.GET.get('days', 30))
        current_balance = float(request.GET.get('balance', 0))
        
        # Fetch user's transactions
        pred_coll = MongoConnection.get_collection(settings.MONGO_COLLECTIONS.get('fraud_predictions', 'fraud_predictions'))
        transactions = list(pred_coll.find(
            {'user_id': str(request.user.id)},
            {'transaction_amount': 1, 'timestamp': 1, 'created_at': 1}
        ).limit(1000))
        
        forecaster = CashFlowForecaster()
        forecast = forecaster.forecast_balance(transactions, current_balance, days_ahead=days)
        
        return JsonResponse({
            'status': 'success',
            'forecast': forecast
        })
    
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def overdraft_risk_api(request):
    """GET /api/analytics/overdraft-risk - Assess overdraft risk"""
    try:
        current_balance = float(request.GET.get('balance', 0))
        
        # Fetch user's transactions
        pred_coll = MongoConnection.get_collection(settings.MONGO_COLLECTIONS.get('fraud_predictions', 'fraud_predictions'))
        transactions = list(pred_coll.find(
            {'user_id': str(request.user.id)},
            {'transaction_amount': 1, 'timestamp': 1, 'created_at': 1}
        ).limit(1000))
        
        forecaster = CashFlowForecaster()
        risk = forecaster.predict_overdraft_risk(transactions, current_balance)
        
        return JsonResponse({
            'status': 'success',
            'risk_assessment': risk
        })
    
    except Exception as e:
        logger.error(f"Overdraft risk error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def categorize_transactions_api(request):
    """POST /api/analytics/categorize - Categorize transactions"""
    try:
        try:
            body = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        transactions = body.get('transactions', [])
        if not transactions:
            return JsonResponse({'error': 'No transactions provided'}, status=400)
        
        categorizer = TransactionCategorizer()
        categorized = []
        
        for txn in transactions:
            merchant = txn.get('merchant_name') or txn.get('channel', '')
            amount = txn.get('transaction_amount')
            category = categorizer.categorize(merchant, amount)
            
            categorized.append({
                'transaction_id': txn.get('transaction_id'),
                'merchant': merchant,
                'amount': amount,
                'category': category
            })
        
        return JsonResponse({
            'status': 'success',
            'categorized_transactions': categorized
        })
    
    except Exception as e:
        logger.error(f"Categorization error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
