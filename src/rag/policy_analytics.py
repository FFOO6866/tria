"""
Policy Usage Analytics
=======================

Track and analyze policy retrieval patterns to understand:
- Which policies are accessed most frequently
- What intents trigger policy lookups
- How effective policies are in answering queries

NO MOCKING - Production-ready analytics
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict


class PolicyUsageTracker:
    """
    Track policy usage and generate analytics

    Features:
    - Logs every policy retrieval
    - Tracks which collections are used
    - Records intent-to-policy mappings
    - Generates usage reports
    """

    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize policy usage tracker

        Args:
            log_file: Optional path to log file (defaults to data/policy_usage.jsonl)
        """
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "data"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "policy_usage.jsonl"

        self.log_file = log_file
        self.session_stats = defaultdict(int)

    def log_retrieval(
        self,
        intent: str,
        query: str,
        collection: str,
        results_count: int,
        top_similarity: float = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Log a policy retrieval event

        Args:
            intent: Intent that triggered the retrieval
            query: Search query used
            collection: Collection searched (policies_en, faqs_en, etc.)
            results_count: Number of results returned
            top_similarity: Similarity score of top result
            metadata: Additional metadata
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "query": query[:200],  # Truncate for privacy
            "collection": collection,
            "results_count": results_count,
            "top_similarity": top_similarity,
            "metadata": metadata or {}
        }

        # Append to log file (JSONL format)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')

            # Update session stats
            self.session_stats[f"{collection}_{intent}"] += 1

        except Exception as e:
            # Log error but don't fail the request
            print(f"[WARNING] Failed to log policy usage: {e}")

    def log_tone_retrieval(
        self,
        intent: str,
        sentiment: str,
        results_count: int,
        metadata: Dict[str, Any] = None
    ):
        """
        Log a tone guideline retrieval event

        Args:
            intent: Intent that triggered tone retrieval
            sentiment: Detected sentiment
            results_count: Number of tone guidelines retrieved
            metadata: Additional metadata
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "tone_retrieval",
            "intent": intent,
            "sentiment": sentiment,
            "results_count": results_count,
            "metadata": metadata or {}
        }

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            print(f"[WARNING] Failed to log tone retrieval: {e}")

    def log_validation(
        self,
        intent: str,
        validation_passed: bool,
        confidence: float,
        issues_count: int,
        metadata: Dict[str, Any] = None
    ):
        """
        Log a response validation event

        Args:
            intent: Intent being validated
            validation_passed: Whether validation passed
            confidence: Validation confidence score
            issues_count: Number of issues found
            metadata: Additional metadata
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "validation",
            "intent": intent,
            "validation_passed": validation_passed,
            "confidence": confidence,
            "issues_count": issues_count,
            "metadata": metadata or {}
        }

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            print(f"[WARNING] Failed to log validation: {e}")

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session usage

        Returns:
            Dictionary with session statistics
        """
        return dict(self.session_stats)

    def generate_usage_report(
        self,
        days: int = 7,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate usage report from log file

        Args:
            days: Number of days to analyze
            output_file: Optional file to save report

        Returns:
            Dictionary with usage statistics
        """
        if not self.log_file.exists():
            return {
                "error": "No usage data available",
                "log_file": str(self.log_file)
            }

        # Read all events
        events = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            return {"error": f"Failed to read log file: {e}"}

        # Filter by date range
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        recent_events = [
            e for e in events
            if datetime.fromisoformat(e['timestamp']).timestamp() > cutoff
        ]

        # Analyze events
        report = {
            "period_days": days,
            "total_events": len(recent_events),
            "by_collection": defaultdict(int),
            "by_intent": defaultdict(int),
            "by_type": defaultdict(int),
            "avg_similarity": [],
            "avg_results_count": [],
            "validation_stats": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "avg_confidence": []
            }
        }

        for event in recent_events:
            # Count by collection
            if 'collection' in event:
                report['by_collection'][event['collection']] += 1

            # Count by intent
            if 'intent' in event:
                report['by_intent'][event['intent']] += 1

            # Count by type
            event_type = event.get('type', 'retrieval')
            report['by_type'][event_type] += 1

            # Similarity scores
            if 'top_similarity' in event and event['top_similarity'] is not None:
                report['avg_similarity'].append(event['top_similarity'])

            # Results counts
            if 'results_count' in event:
                report['avg_results_count'].append(event['results_count'])

            # Validation stats
            if event_type == 'validation':
                report['validation_stats']['total'] += 1
                if event.get('validation_passed'):
                    report['validation_stats']['passed'] += 1
                else:
                    report['validation_stats']['failed'] += 1
                if 'confidence' in event:
                    report['validation_stats']['avg_confidence'].append(event['confidence'])

        # Calculate averages
        if report['avg_similarity']:
            report['avg_similarity_score'] = sum(report['avg_similarity']) / len(report['avg_similarity'])
            del report['avg_similarity']

        if report['avg_results_count']:
            report['avg_results_per_query'] = sum(report['avg_results_count']) / len(report['avg_results_count'])
            del report['avg_results_count']

        if report['validation_stats']['avg_confidence']:
            report['validation_stats']['avg_confidence_score'] = sum(
                report['validation_stats']['avg_confidence']
            ) / len(report['validation_stats']['avg_confidence'])
            del report['validation_stats']['avg_confidence']

        # Convert defaultdicts to regular dicts
        report['by_collection'] = dict(report['by_collection'])
        report['by_intent'] = dict(report['by_intent'])
        report['by_type'] = dict(report['by_type'])

        # Save report if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

        return report


# Global tracker instance
_global_tracker = None


def get_tracker() -> PolicyUsageTracker:
    """Get or create global policy usage tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = PolicyUsageTracker()
    return _global_tracker
