"""
DCA Service - Suggestions d'achat échelonné (Dollar Cost Averaging)
"""

from typing import List, Dict
from datetime import datetime, timedelta
from core.models import MarketData, Prediction, OpportunityScore


class DCAService:
    """Service de suggestions DCA"""
    
    def generate_dca_plan(self, 
                         symbol: str,
                         total_investment: float,
                         current_price: float,
                         market_data: MarketData,
                         prediction: Prediction,
                         opportunity: OpportunityScore) -> Dict:
        """
        Génère un plan d'achat échelonné
        
        Args:
            symbol: Symbole crypto
            total_investment: Montant total à investir
            current_price: Prix actuel
            market_data: Données de marché
            prediction: Prédiction
            opportunity: Score d'opportunité
        
        Returns:
            Plan DCA avec recommandations
        """
        
        # Déterminer la stratégie selon le score d'opportunité
        if opportunity.score >= 8:
            # Excellente opportunité - investir rapidement
            strategy = "aggressive"
            entries = 2
            timeframe_days = 3
        elif opportunity.score >= 6:
            # Bonne opportunité - investir progressivement
            strategy = "moderate"
            entries = 3
            timeframe_days = 7
        elif opportunity.score >= 4:
            # Opportunité correcte - investir très progressivement
            strategy = "conservative"
            entries = 5
            timeframe_days = 14
        else:
            # Mauvaise opportunité - attendre ou investir très lentement
            strategy = "wait"
            entries = 7
            timeframe_days = 21
        
        # Calculer les entrées
        amount_per_entry = total_investment / entries
        entries_list = []
        
        for i in range(entries):
            # Prix d'entrée suggéré (avec légère décote progressive)
            discount_pct = i * 1.5  # 0%, 1.5%, 3%, etc.
            target_price = current_price * (1 - discount_pct / 100)
            
            entry = {
                "entry_number": i + 1,
                "amount_eur": amount_per_entry,
                "target_price": target_price,
                "estimated_date": datetime.now() + timedelta(days=i * (timeframe_days // entries)),
                "condition": self._get_entry_condition(i, opportunity, prediction)
            }
            entries_list.append(entry)
        
        return {
            "symbol": symbol,
            "strategy": strategy,
            "total_investment": total_investment,
            "entries": entries_list,
            "timeframe_days": timeframe_days,
            "recommendation": self._get_strategy_description(strategy),
            "risk_level": self._calculate_risk_level(market_data, prediction),
            "expected_avg_price": sum(e["target_price"] for e in entries_list) / entries
        }
    
    def _get_entry_condition(self, entry_index: int, 
                            opportunity: OpportunityScore,
                            prediction: Prediction) -> str:
        """Génère la condition d'entrée"""
        
        if entry_index == 0:
            return "Immédiatement"
        
        conditions = [
            f"Si prix baisse de {entry_index * 1.5:.1f}%",
            f"Dans {entry_index * 2} jours",
            "Si RSI < 35" if entry_index > 2 else "",
            "Si opportunité score >= 7" if opportunity.score < 7 else ""
        ]
        
        return " OU ".join([c for c in conditions if c])
    
    def _get_strategy_description(self, strategy: str) -> str:
        """Description de la stratégie"""
        
        descriptions = {
            "aggressive": "🚀 Investir rapidement sur 3 jours - excellente opportunité",
            "moderate": "📊 Investir progressivement sur 1 semaine - bonne opportunité",
            "conservative": "🐢 Investir lentement sur 2 semaines - opportunité correcte",
            "wait": "⏸️ Attendre une meilleure opportunité ou investir très lentement"
        }
        
        return descriptions.get(strategy, "Stratégie personnalisée")
    
    def _calculate_risk_level(self, market_data: MarketData, 
                              prediction: Prediction) -> str:
        """Calcule le niveau de risque"""
        
        risk_score = 0
        
        # Volatilité
        if abs(market_data.current_price.change_24h) > 10:
            risk_score += 2
        elif abs(market_data.current_price.change_24h) > 5:
            risk_score += 1
        
        # RSI
        rsi = market_data.technical_indicators.rsi
        if rsi > 70 or rsi < 30:
            risk_score += 1
        
        # Prédiction
        if prediction.confidence < 60:
            risk_score += 1
        
        if risk_score >= 4:
            return "🔴 Risque élevé"
        elif risk_score >= 2:
            return "🟡 Risque moyen"
        else:
            return "🟢 Risque faible"
    
    def suggest_entry_now(self, dca_plan: Dict, current_price: float) -> bool:
        """Suggère si c'est le moment d'entrer"""
        
        for entry in dca_plan["entries"]:
            if entry["target_price"] >= current_price * 0.98:  # Marge de 2%
                return True
        
        return False
    
    def format_dca_message(self, dca_plan: Dict, simple: bool = False) -> str:
        """Formate le plan DCA pour affichage"""
        
        if simple:
            msg = f"💰 PLAN D'ACHAT ÉCHELONNÉ - {dca_plan['symbol']}\n\n"
            msg += f"{dca_plan['recommendation']}\n\n"
            msg += f"Budget total : {dca_plan['total_investment']:.2f}€\n"
            msg += f"Nombre d'achats : {len(dca_plan['entries'])}\n\n"
            
            for entry in dca_plan['entries'][:3]:
                msg += f"#{entry['entry_number']}: {entry['amount_eur']:.2f}€ "
                msg += f"quand prix ~ {entry['target_price']:.2f}€\n"
            
        else:
            msg = f"💰 PLAN DCA - {dca_plan['symbol']}\n\n"
            msg += f"Stratégie : {dca_plan['strategy'].upper()}\n"
            msg += f"Risque : {dca_plan['risk_level']}\n"
            msg += f"Budget : {dca_plan['total_investment']:.2f}€\n"
            msg += f"Prix moyen cible : {dca_plan['expected_avg_price']:.2f}€\n\n"
            msg += f"📋 ENTRÉES :\n"
            
            for entry in dca_plan['entries']:
                msg += f"\n#{entry['entry_number']} - {entry['amount_eur']:.2f}€\n"
                msg += f"  Prix cible : {entry['target_price']:.2f}€\n"
                msg += f"  Condition : {entry['condition']}\n"
        
        return msg
