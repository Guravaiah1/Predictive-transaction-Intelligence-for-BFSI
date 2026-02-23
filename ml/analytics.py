"""
Advanced Analytics Module for Transaction Intelligence
Provides transaction categorization, spending pattern analysis, and forecasting
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class TransactionCategorizer:
    """Categorizes transactions based on merchant names and transaction details"""
    
    # Default category mappings based on merchant keywords
    CATEGORY_KEYWORDS = {
        'Groceries': ['grocery', 'supermarket', 'whole foods', 'trader joe', 'safeway', 'kroger', 'walmart', 'costco', 'market'],
        'Restaurants': ['restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'dining', 'food delivery', 'doordash', 'ubereats', 'grubhub'],
        'Utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'utility', 'verizon', 'at&t', 'comcast'],
        'Transportation': ['uber', 'lyft', 'taxi', 'gas station', 'parking', 'transit', 'airline', 'hotel', 'airbnb'],
        'Shopping': ['amazon', 'target', 'mall', 'store', 'shop', 'retail', 'clothing', 'apparel', 'ebay', 'etsy'],
        'Entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'gaming', 'concert', 'theater', 'hulu', 'disney', 'youtube'],
        'Healthcare': ['pharmacy', 'doctor', 'hospital', 'clinic', 'dental', 'medical', 'cvs', 'walgreens', 'health'],
        'Salary': ['payroll', 'salary', 'wage', 'employer', 'direct deposit'],
        'Transfer': ['transfer', 'payment', 'wire', 'atm', 'cash withdrawal'],
        'Insurance': ['insurance', 'premium', 'geico', 'state farm', 'allstate'],
        'Subscription': ['subscription', 'membership', 'recurring', 'annual', 'monthly'],
    }
    
    def __init__(self):
        self.category_keywords = self.CATEGORY_KEYWORDS
    
    def categorize(self, merchant_name: str, amount: float = None, transaction_type: str = None) -> str:
        """
        Categorize a transaction based on merchant name and optional metadata.
        
        Args:
            merchant_name: Name of the merchant
            amount: Transaction amount (optional)
            transaction_type: Type of transaction (optional)
        
        Returns:
            Category name
        """
        if not merchant_name:
            return 'Other'
        
        merchant_lower = str(merchant_name).lower()
        
        # Check for exact matches first
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in merchant_lower:
                    return category
        
        return 'Other'
    
    def categorize_batch(self, transactions: List[Dict[str, Any]]) -> List[str]:
        """Categorize multiple transactions"""
        categories = []
        for txn in transactions:
            merchant = txn.get('merchant_name') or txn.get('channel') or ''
            amount = txn.get('transaction_amount')
            txn_type = txn.get('transaction_type')
            category = self.categorize(merchant, amount, txn_type)
            categories.append(category)
        return categories


class SpendingPatternAnalyzer:
    """Analyzes spending patterns and identifies anomalies"""
    
    def __init__(self):
        self.categorizer = TransactionCategorizer()
    
    def analyze_spending_trends(self, transactions: List[Dict[str, Any]], days: int = 30) -> Dict[str, Any]:
        """
        Analyze spending trends over a specified period.
        
        Args:
            transactions: List of transaction records
            days: Number of days to analyze
        
        Returns:
            Dictionary with spending analysis
        """
        if not transactions:
            return {'error': 'No transactions provided'}
        
        df = pd.DataFrame(transactions)
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'created_at' in df.columns:
            df['timestamp'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Filter to recent transactions
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'timestamp' in df.columns:
            df = df[df['timestamp'] >= cutoff_date]
        
        # Categorize transactions
        df['category'] = df.apply(
            lambda row: self.categorizer.categorize(
                row.get('channel') or row.get('merchant_name', ''),
                row.get('transaction_amount')
            ),
            axis=1
        )
        
        # Calculate spending by category
        spending_by_category = df.groupby('category')['transaction_amount'].agg(['sum', 'count', 'mean']).to_dict()
        
        # Daily spending trend
        if 'timestamp' in df.columns:
            df['date'] = df['timestamp'].dt.date
            daily_spending = df.groupby('date')['transaction_amount'].sum().to_dict()
            daily_spending = {str(k): v for k, v in daily_spending.items()}
        else:
            daily_spending = {}
        
        # Calculate statistics
        total_spent = df['transaction_amount'].sum()
        avg_transaction = df['transaction_amount'].mean()
        max_transaction = df['transaction_amount'].max()
        min_transaction = df['transaction_amount'].min()
        transaction_count = len(df)
        
        return {
            'period_days': days,
            'total_spent': float(total_spent) if not pd.isna(total_spent) else 0,
            'avg_transaction': float(avg_transaction) if not pd.isna(avg_transaction) else 0,
            'max_transaction': float(max_transaction) if not pd.isna(max_transaction) else 0,
            'min_transaction': float(min_transaction) if not pd.isna(min_transaction) else 0,
            'transaction_count': int(transaction_count),
            'spending_by_category': {
                cat: {
                    'total': float(stats['sum']) if not pd.isna(stats['sum']) else 0,
                    'count': int(stats['count']),
                    'average': float(stats['mean']) if not pd.isna(stats['mean']) else 0,
                }
                for cat, stats in spending_by_category.items()
            },
            'daily_spending': daily_spending,
        }
    
    def detect_anomalies(self, transactions: List[Dict[str, Any]], threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect unusual spending patterns (anomalies).
        
        Args:
            transactions: List of transaction records
            threshold_std: Number of standard deviations for anomaly detection
        
        Returns:
            List of anomalous transactions
        """
        if len(transactions) < 3:
            return []
        
        df = pd.DataFrame(transactions)
        
        # Calculate statistics
        mean_amount = df['transaction_amount'].mean()
        std_amount = df['transaction_amount'].std()
        
        if std_amount == 0:
            return []
        
        # Identify anomalies
        anomalies = []
        for idx, row in df.iterrows():
            z_score = abs((row['transaction_amount'] - mean_amount) / std_amount)
            if z_score > threshold_std:
                anomalies.append({
                    'transaction_id': row.get('transaction_id'),
                    'amount': float(row['transaction_amount']),
                    'merchant': row.get('channel') or row.get('merchant_name', 'Unknown'),
                    'z_score': float(z_score),
                    'reason': f"Amount is {z_score:.1f}x standard deviations from mean (${mean_amount:.2f})",
                    'timestamp': str(row.get('timestamp', row.get('created_at', 'Unknown'))),
                })
        
        return sorted(anomalies, key=lambda x: x['z_score'], reverse=True)


class CashFlowForecaster:
    """Predicts future cash flow based on historical patterns"""
    
    def __init__(self):
        pass
    
    def forecast_balance(self, transactions: List[Dict[str, Any]], 
                        current_balance: float, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Forecast account balance for future days.
        
        Args:
            transactions: Historical transaction records
            current_balance: Current account balance
            days_ahead: Number of days to forecast
        
        Returns:
            Forecast data with predicted daily balances
        """
        if not transactions:
            return {'error': 'No historical data for forecasting'}
        
        df = pd.DataFrame(transactions)
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'created_at' in df.columns:
            df['timestamp'] = pd.to_datetime(df['created_at'], errors='coerce')
        
        # Group by date and calculate net daily change
        df['date'] = df['timestamp'].dt.date
        daily_changes = df.groupby('date')['transaction_amount'].sum()
        
        # Calculate average daily spending
        avg_daily_spending = daily_changes.mean()
        std_daily_spending = daily_changes.std()
        
        # Generate forecast
        forecast = []
        predicted_balance = current_balance
        
        for day in range(1, days_ahead + 1):
            future_date = datetime.now() + timedelta(days=day)
            
            # Simple forecast: use average daily spending
            predicted_balance -= avg_daily_spending
            
            forecast.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'predicted_balance': float(predicted_balance),
                'confidence_interval_lower': float(predicted_balance - (2 * std_daily_spending)),
                'confidence_interval_upper': float(predicted_balance + (2 * std_daily_spending)),
            })
        
        return {
            'current_balance': float(current_balance),
            'avg_daily_spending': float(avg_daily_spending),
            'std_daily_spending': float(std_daily_spending),
            'forecast_days': days_ahead,
            'forecast': forecast,
        }
    
    def predict_overdraft_risk(self, transactions: List[Dict[str, Any]], 
                              current_balance: float, threshold: float = 0) -> Dict[str, Any]:
        """
        Predict if account is at risk of overdraft.
        
        Args:
            transactions: Historical transaction records
            current_balance: Current account balance
            threshold: Balance threshold for overdraft alert
        
        Returns:
            Overdraft risk assessment
        """
        if not transactions:
            return {'error': 'No historical data'}
        
        df = pd.DataFrame(transactions)
        
        # Calculate average daily spending
        avg_daily_spending = df['transaction_amount'].mean()
        
        # Estimate days until overdraft
        if avg_daily_spending > 0:
            days_until_overdraft = current_balance / avg_daily_spending
        else:
            days_until_overdraft = float('inf')
        
        risk_level = 'LOW'
        if days_until_overdraft < 7:
            risk_level = 'HIGH'
        elif days_until_overdraft < 14:
            risk_level = 'MEDIUM'
        
        return {
            'current_balance': float(current_balance),
            'avg_daily_spending': float(avg_daily_spending),
            'days_until_overdraft': float(days_until_overdraft) if days_until_overdraft != float('inf') else None,
            'risk_level': risk_level,
            'recommendation': self._get_overdraft_recommendation(risk_level, days_until_overdraft),
        }
    
    def _get_overdraft_recommendation(self, risk_level: str, days: float) -> str:
        """Generate recommendation based on overdraft risk"""
        if risk_level == 'HIGH':
            return f"⚠️ High risk: Only {days:.0f} days of spending remaining. Consider reducing expenses or depositing funds."
        elif risk_level == 'MEDIUM':
            return f"⚠️ Medium risk: {days:.0f} days of spending remaining. Monitor your spending closely."
        else:
            return "✓ Low risk: Your account balance is healthy."


class CustomerSegmentation:
    """Segments customers based on spending behavior"""
    
    def __init__(self):
        self.categorizer = TransactionCategorizer()
    
    def segment_customers(self, customer_transactions: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        Segment customers into groups based on spending behavior.
        
        Args:
            customer_transactions: Dictionary mapping customer_id to list of transactions
        
        Returns:
            Dictionary with customer segments and characteristics
        """
        segments = {}
        
        for customer_id, transactions in customer_transactions.items():
            if not transactions:
                continue
            
            df = pd.DataFrame(transactions)
            
            # Calculate spending metrics
            total_spent = df['transaction_amount'].sum()
            avg_transaction = df['transaction_amount'].mean()
            transaction_count = len(df)
            
            # Determine segment
            if total_spent > 10000:
                segment = 'High-Value'
            elif total_spent > 5000:
                segment = 'Mid-Tier'
            else:
                segment = 'Budget-Conscious'
            
            segments[customer_id] = {
                'segment': segment,
                'total_spent': float(total_spent),
                'avg_transaction': float(avg_transaction),
                'transaction_count': int(transaction_count),
                'spending_frequency': int(transaction_count / max(1, (datetime.now() - pd.to_datetime(df['timestamp'].min())).days)),
            }
        
        return segments


def get_transaction_insights(transactions: List[Dict[str, Any]], 
                            current_balance: float = None) -> Dict[str, Any]:
    """
    Generate comprehensive insights from transaction data.
    
    Args:
        transactions: List of transaction records
        current_balance: Current account balance (optional)
    
    Returns:
        Dictionary with comprehensive insights
    """
    analyzer = SpendingPatternAnalyzer()
    forecaster = CashFlowForecaster()
    
    insights = {
        'spending_analysis': analyzer.analyze_spending_trends(transactions, days=30),
        'anomalies': analyzer.detect_anomalies(transactions),
    }
    
    if current_balance is not None:
        insights['cash_flow_forecast'] = forecaster.forecast_balance(transactions, current_balance, days_ahead=30)
        insights['overdraft_risk'] = forecaster.predict_overdraft_risk(transactions, current_balance)
    
    return insights
