"""Lead scoring engine for Kiro AI chatbot.

Calculates lead quality based on:
- Pages visited
- Time spent on site
- Engagement patterns
- Urgency level
- Message frequency (spam detection)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class LeadScoringConfig:
    """Configuration for lead scoring algorithm."""
    base_score: int = 50
    pages_threshold: int = 5
    pages_bonus: int = 15
    time_threshold_seconds: int = 300  # 5 minutes
    time_bonus: int = 10
    urgency_high_bonus: int = 10
    urgency_medium_bonus: int = 5
    spam_penalty: int = 20
    hot_threshold: int = 75
    warm_threshold: int = 50


class LeadScorer:
    """Main lead scoring engine."""

    def __init__(self, config: Optional[LeadScoringConfig] = None):
        self.config = config or LeadScoringConfig()

    def calculate_score(self, lead_data: Dict) -> Dict:
        """Calculate lead score based on engagement metrics.
        
        Args:
            lead_data: Dict with lead information
            {
                'name': str,
                'email': str,
                'phone': str,
                'business_type': str,
                'requirement': str,
                'urgency': 'High' | 'Medium' | 'Low',
                'pages_visited': List[str],
                'time_on_site_seconds': int,
                'message_count': int,
                'message_frequency': float,  # messages/second
                'first_message_time': datetime,
                'last_message_time': datetime
            }
        
        Returns:
            Dict with score and qualification level
        """
        score = self.config.base_score
        breakdown = {}

        # Bonus for pages visited
        pages_visited = len(lead_data.get('pages_visited', []))
        if pages_visited >= self.config.pages_threshold:
            score += self.config.pages_bonus
            breakdown['pages_bonus'] = self.config.pages_bonus

        # Bonus for time on site
        time_on_site = lead_data.get('time_on_site_seconds', 0)
        if time_on_site >= self.config.time_threshold_seconds:
            score += self.config.time_bonus
            breakdown['time_bonus'] = self.config.time_bonus

        # Bonus for urgency
        urgency = lead_data.get('urgency', 'Low')
        if urgency == 'High':
            score += self.config.urgency_high_bonus
            breakdown['urgency_bonus'] = self.config.urgency_high_bonus
        elif urgency == 'Medium':
            score += self.config.urgency_medium_bonus
            breakdown['urgency_bonus'] = self.config.urgency_medium_bonus

        # Penalty for spam behavior
        if self._is_spam(lead_data):
            score -= self.config.spam_penalty
            breakdown['spam_penalty'] = -self.config.spam_penalty

        # Ensure score stays in 0-100 range
        score = max(0, min(100, score))

        return {
            'score': score,
            'qualification': self._get_qualification(score),
            'breakdown': breakdown,
            'contact_within_hours': self._get_contact_window(score),
            'pages_count': pages_visited,
            'time_on_site_seconds': time_on_site
        }

    def _is_spam(self, lead_data: Dict) -> bool:
        """Detect spam/bot behavior."""
        # Check message frequency (messages/sec > 0.5 is suspicious)
        message_freq = lead_data.get('message_frequency', 0)
        if message_freq > 0.5:
            return True

        # Check message count (too many too quickly)
        message_count = lead_data.get('message_count', 0)
        if message_count > 20:
            return True

        # Check if requirement text is nonsense
        requirement = lead_data.get('requirement', '')
        if self._is_nonsense(requirement):
            return True

        return False

    def _is_nonsense(self, text: str) -> bool:
        """Check if text looks like spam/nonsense."""
        if not text or len(text) < 3:
            return True

        # All caps + lots of special chars
        special_char_ratio = sum(1 for c in text if c in '!@#$%^&*')
        if special_char_ratio / len(text) > 0.5 and text.isupper():
            return True

        # Too many repeated characters
        for char in text:
            if text.count(char) / len(text) > 0.7:
                return True

        return False

    def _get_qualification(self, score: int) -> str:
        """Get qualification level based on score."""
        if score >= self.config.hot_threshold:
            return 'Hot'
        elif score >= self.config.warm_threshold:
            return 'Warm'
        return 'Cold'

    def _get_contact_window(self, score: int) -> int:
        """Get recommended contact window in hours."""
        if score >= self.config.hot_threshold:
            return 2  # Contact within 2 hours
        elif score >= self.config.warm_threshold:
            return 24  # Contact within 24 hours
        return 48  # Cold leads: contact within 48 hours


class IntentDetector:
    """Detects user intent and routes to appropriate team."""

    KEYWORDS = {
        'Sales': [
            'need', 'pricing', 'quote', 'demo', 'features', 'interested',
            'cost', 'price', 'buy', 'purchase', 'subscription', 'plan',
            'solution', 'help me set up'
        ],
        'Billing': [
            'invoice', 'payment', 'refund', 'charge', 'subscription',
            'bill', 'credit card', 'transaction', 'receipt', 'pricing'
        ],
        'Support': [
            'error', 'bug', 'not working', 'issue', 'problem', 'help',
            'broken', 'crash', 'failing', 'stopped', 'down', 'issue'
        ],
        'Technical': [
            'integration', 'api', 'setup', 'deploy', 'crash', 'timeout',
            'database', 'server', 'logs', 'webhook', 'authentication',
            'ssl', 'certificate', 'connection'
        ],
        'FAQ': [
            'how', 'where', 'what', 'can i', 'do you', 'why', 'when'
        ]
    }

    def detect(self, message: str) -> Dict:
        """Detect intent from user message.
        
        Returns:
            Dict with detected team, confidence, and keywords found
        """
        message_lower = message.lower()
        intent_scores = {}

        for team, keywords in self.KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if matches > 0:
                intent_scores[team] = matches

        if not intent_scores:
            return {'team': 'Support', 'confidence': 0.5, 'matched_keywords': []}

        top_team = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[top_team] / len(message_lower.split())
        confidence = min(1.0, confidence)

        return {
            'team': top_team,
            'confidence': confidence,
            'all_scores': intent_scores,
            'matched_keywords': [kw for team in intent_scores for kw in self.KEYWORDS[team] if kw in message_lower]
        }


class RoutingEngine:
    """Routes leads to internal teams with priority."""

    def __init__(self):
        self.intent_detector = IntentDetector()

    def create_routing_payload(self, lead_data: Dict, lead_score: Dict) -> Dict:
        """Create internal routing payload for team assignment.
        
        Args:
            lead_data: Lead information
            lead_score: Result from LeadScorer.calculate_score()
        
        Returns:
            Routing payload for internal system
        """
        # Detect intent
        intent = self.intent_detector.detect(lead_data.get('requirement', ''))
        team = intent['team']

        # Determine priority
        if lead_score['qualification'] == 'Hot':
            priority = 'High'
        elif lead_score['qualification'] == 'Warm':
            priority = 'Medium'
        else:
            priority = 'Low'

        context = f"""
Lead: {lead_data.get('name', 'Unknown')}
Email: {lead_data.get('email', '')}
Phone: {lead_data.get('phone', '')}
Business: {lead_data.get('business_type', 'Not specified')}
Requirement: {lead_data.get('requirement', '')}
Urgency: {lead_data.get('urgency', 'Not specified')}
Lead Score: {lead_score['score']}/100 ({lead_score['qualification']})
Pages Visited: {lead_score['pages_count']}
Time on Site: {lead_score['time_on_site_seconds']}s
Intent Confidence: {intent['confidence']:.1%}
        """.strip()

        return {
            'team': team,
            'priority': priority,
            'context': context,
            'actions': [
                'Create ticket',
                'Notify agent',
                f"Contact within {lead_score['contact_within_hours']} hours"
            ],
            'lead_data': lead_data,
            'lead_score': lead_score,
            'intent': intent
        }


# Example usage
if __name__ == '__main__':
    # Sample lead data
    sample_lead = {
        'name': 'Prithivi Raj',
        'email': 'prithivi@example.com',
        'phone': '+91-9876543210',
        'business_type': 'E-commerce',
        'requirement': 'Need WhatsApp bot for customer support',
        'urgency': 'High',
        'pages_visited': ['/pricing', '/features/whatsapp', '/case-studies', '/faq', '/integration'],
        'time_on_site_seconds': 420,
        'message_count': 3,
        'message_frequency': 0.01
    }

    # Calculate score
    scorer = LeadScorer()
    score_result = scorer.calculate_score(sample_lead)
    print(f"Lead Score: {json.dumps(score_result, indent=2)}\n")

    # Create routing
    router = RoutingEngine()
    routing = router.create_routing_payload(sample_lead, score_result)
    print(f"Routing Payload: {json.dumps(routing, indent=2, default=str)}")
