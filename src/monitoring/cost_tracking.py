"""
Cost Tracking Module
====================

Tracks API usage and estimated costs for monitoring and budgeting.

Features:
1. Token usage tracking
2. Cost estimation per request
3. Daily/monthly cost aggregation
4. Budget alerts
5. Cost breakdown by operation type

OpenAI Pricing (as of 2024):
- GPT-4 Turbo: $0.01/1K input tokens, $0.03/1K output tokens
- GPT-4: $0.03/1K input tokens, $0.06/1K output tokens
- GPT-3.5 Turbo: $0.0005/1K input tokens, $0.0015/1K output tokens

Usage:
    from monitoring.cost_tracking import cost_tracker

    # Track API call
    cost_tracker.track_api_call(
        operation="intent_classification",
        model="gpt-4-turbo-preview",
        input_tokens=150,
        output_tokens=50
    )

    # Get cost summary
    summary = cost_tracker.get_cost_summary()
    print(f"Total cost today: ${summary['today_cost']:.4f}")
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from .logger import app_logger


# OpenAI pricing (per 1K tokens)
PRICING = {
    "gpt-4-turbo-preview": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-4": {
        "input": 0.03,
        "output": 0.06
    },
    "gpt-3.5-turbo": {
        "input": 0.0005,
        "output": 0.0015
    },
    "gpt-4-turbo": {  # Alias
        "input": 0.01,
        "output": 0.03
    }
}


@dataclass
class APICall:
    """
    Single API call record

    Attributes:
        timestamp: When the call was made
        operation: Type of operation (intent_classification, rag_qa, etc.)
        model: Model used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Estimated cost in USD
        metadata: Additional context
    """
    timestamp: datetime
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """
    Tracks API costs and usage

    Monitors token usage and estimates costs for budgeting.
    Persists data to disk for historical analysis.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize cost tracker

        Args:
            data_dir: Directory to store cost data (default: ./data/costs)
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data" / "costs"

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self.calls: List[APICall] = []

        # Budget settings
        self.daily_budget = float(os.getenv("COST_DAILY_BUDGET", "10.0"))  # $10/day
        self.monthly_budget = float(os.getenv("COST_MONTHLY_BUDGET", "200.0"))  # $200/month

        # Load today's data
        self._load_today_data()

        app_logger.info(
            "CostTracker initialized",
            daily_budget=self.daily_budget,
            monthly_budget=self.monthly_budget,
            data_dir=str(self.data_dir)
        )

    def track_api_call(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        **metadata
    ) -> float:
        """
        Track an API call and return estimated cost

        Args:
            operation: Type of operation
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            **metadata: Additional context

        Returns:
            Estimated cost in USD
        """
        # Get pricing for model
        model_normalized = model.lower()
        pricing = PRICING.get(model_normalized)

        if not pricing:
            # Try to match partial model name
            for key in PRICING.keys():
                if key in model_normalized:
                    pricing = PRICING[key]
                    break

        if not pricing:
            app_logger.warning(
                f"Unknown model pricing: {model}, using GPT-4 pricing",
                model=model
            )
            pricing = PRICING["gpt-4"]

        # Calculate cost
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Create API call record
        call = APICall(
            timestamp=datetime.now(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            metadata=metadata
        )

        # Store in memory
        self.calls.append(call)

        # Persist to disk
        self._save_call(call)

        # Log the call
        app_logger.info(
            "API call tracked",
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost
        )

        # Check budget alerts
        self._check_budget_alerts()

        return total_cost

    def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get cost summary for date range

        Args:
            start_date: Start of date range (default: today)
            end_date: End of date range (default: today)

        Returns:
            Dictionary with cost summary
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()

        # Filter calls in date range
        calls_in_range = [
            call for call in self.calls
            if start_date <= call.timestamp <= end_date
        ]

        if not calls_in_range:
            return {
                "total_cost": 0.0,
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "by_operation": {},
                "by_model": {},
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }

        # Calculate totals
        total_cost = sum(call.cost for call in calls_in_range)
        total_input_tokens = sum(call.input_tokens for call in calls_in_range)
        total_output_tokens = sum(call.output_tokens for call in calls_in_range)

        # Break down by operation
        by_operation = defaultdict(lambda: {"cost": 0.0, "calls": 0, "tokens": 0})
        for call in calls_in_range:
            by_operation[call.operation]["cost"] += call.cost
            by_operation[call.operation]["calls"] += 1
            by_operation[call.operation]["tokens"] += call.input_tokens + call.output_tokens

        # Break down by model
        by_model = defaultdict(lambda: {"cost": 0.0, "calls": 0, "tokens": 0})
        for call in calls_in_range:
            by_model[call.model]["cost"] += call.cost
            by_model[call.model]["calls"] += 1
            by_model[call.model]["tokens"] += call.input_tokens + call.output_tokens

        return {
            "total_cost": total_cost,
            "total_calls": len(calls_in_range),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "by_operation": dict(by_operation),
            "by_model": dict(by_model),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    def get_today_cost(self) -> float:
        """Get total cost for today"""
        summary = self.get_cost_summary()
        return summary["total_cost"]

    def get_month_cost(self) -> float:
        """Get total cost for current month"""
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Load all data for the month
        month_calls = self._load_month_data(now.year, now.month)

        total = sum(call.cost for call in month_calls)
        return total

    def get_budget_status(self) -> Dict[str, Any]:
        """
        Get budget status

        Returns:
            Dictionary with budget information
        """
        today_cost = self.get_today_cost()
        month_cost = self.get_month_cost()

        return {
            "daily": {
                "budget": self.daily_budget,
                "spent": today_cost,
                "remaining": self.daily_budget - today_cost,
                "percentage_used": (today_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0,
                "exceeded": today_cost > self.daily_budget
            },
            "monthly": {
                "budget": self.monthly_budget,
                "spent": month_cost,
                "remaining": self.monthly_budget - month_cost,
                "percentage_used": (month_cost / self.monthly_budget * 100) if self.monthly_budget > 0 else 0,
                "exceeded": month_cost > self.monthly_budget
            }
        }

    def _check_budget_alerts(self):
        """Check if budget thresholds are exceeded"""
        status = self.get_budget_status()

        # Daily budget alert
        if status["daily"]["percentage_used"] > 80 and not hasattr(self, "_daily_alert_sent"):
            app_logger.warning(
                "Daily budget alert: 80% spent",
                spent=status["daily"]["spent"],
                budget=status["daily"]["budget"]
            )
            self._daily_alert_sent = True

        if status["daily"]["exceeded"] and not hasattr(self, "_daily_exceeded_alert_sent"):
            app_logger.error(
                "Daily budget EXCEEDED",
                spent=status["daily"]["spent"],
                budget=status["daily"]["budget"]
            )
            self._daily_exceeded_alert_sent = True

        # Monthly budget alert
        if status["monthly"]["percentage_used"] > 80 and not hasattr(self, "_monthly_alert_sent"):
            app_logger.warning(
                "Monthly budget alert: 80% spent",
                spent=status["monthly"]["spent"],
                budget=status["monthly"]["budget"]
            )
            self._monthly_alert_sent = True

        if status["monthly"]["exceeded"] and not hasattr(self, "_monthly_exceeded_alert_sent"):
            app_logger.error(
                "Monthly budget EXCEEDED",
                spent=status["monthly"]["spent"],
                budget=status["monthly"]["budget"]
            )
            self._monthly_exceeded_alert_sent = True

    def _save_call(self, call: APICall):
        """Save API call to disk"""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.data_dir / f"costs_{today}.jsonl"

        with open(file_path, "a") as f:
            json.dump({
                "timestamp": call.timestamp.isoformat(),
                "operation": call.operation,
                "model": call.model,
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "cost": call.cost,
                "metadata": call.metadata
            }, f)
            f.write("\n")

    def _load_today_data(self):
        """Load today's cost data from disk"""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = self.data_dir / f"costs_{today}.jsonl"

        if not file_path.exists():
            return

        with open(file_path, "r") as f:
            for line in f:
                data = json.loads(line)
                call = APICall(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    operation=data["operation"],
                    model=data["model"],
                    input_tokens=data["input_tokens"],
                    output_tokens=data["output_tokens"],
                    cost=data["cost"],
                    metadata=data.get("metadata", {})
                )
                self.calls.append(call)

    def _load_month_data(self, year: int, month: int) -> List[APICall]:
        """Load all cost data for a specific month"""
        month_calls = []

        # Get all days in the month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)

        current_day = datetime(year, month, 1)

        while current_day < next_month:
            date_str = current_day.strftime("%Y-%m-%d")
            file_path = self.data_dir / f"costs_{date_str}.jsonl"

            if file_path.exists():
                with open(file_path, "r") as f:
                    for line in f:
                        data = json.loads(line)
                        call = APICall(
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            operation=data["operation"],
                            model=data["model"],
                            input_tokens=data["input_tokens"],
                            output_tokens=data["output_tokens"],
                            cost=data["cost"],
                            metadata=data.get("metadata", {})
                        )
                        month_calls.append(call)

            current_day += timedelta(days=1)

        return month_calls

    def print_cost_report(self):
        """Print formatted cost report to console"""
        summary = self.get_cost_summary()
        budget_status = self.get_budget_status()

        print("\n" + "=" * 80)
        print("COST TRACKING REPORT")
        print("=" * 80)
        print()

        print("TODAY'S COSTS:")
        print(f"  Total: ${summary['total_cost']:.4f}")
        print(f"  Calls: {summary['total_calls']}")
        print(f"  Tokens: {summary['total_tokens']:,} ({summary['total_input_tokens']:,} in / {summary['total_output_tokens']:,} out)")
        print()

        print("BUDGET STATUS:")
        print(f"  Daily: ${budget_status['daily']['spent']:.4f} / ${budget_status['daily']['budget']:.2f} ({budget_status['daily']['percentage_used']:.1f}%)")
        if budget_status['daily']['exceeded']:
            print(f"    ⚠️  BUDGET EXCEEDED by ${abs(budget_status['daily']['remaining']):.4f}")
        print()

        month_cost = self.get_month_cost()
        print(f"  Monthly: ${month_cost:.4f} / ${budget_status['monthly']['budget']:.2f} ({budget_status['monthly']['percentage_used']:.1f}%)")
        if budget_status['monthly']['exceeded']:
            print(f"    ⚠️  BUDGET EXCEEDED by ${abs(budget_status['monthly']['remaining']):.4f}")
        print()

        if summary['by_operation']:
            print("BY OPERATION:")
            for operation, stats in sorted(summary['by_operation'].items(), key=lambda x: x[1]['cost'], reverse=True):
                print(f"  {operation}: ${stats['cost']:.4f} ({stats['calls']} calls, {stats['tokens']:,} tokens)")
            print()

        if summary['by_model']:
            print("BY MODEL:")
            for model, stats in sorted(summary['by_model'].items(), key=lambda x: x[1]['cost'], reverse=True):
                print(f"  {model}: ${stats['cost']:.4f} ({stats['calls']} calls, {stats['tokens']:,} tokens)")
            print()

        print("=" * 80)


# Global cost tracker instance
cost_tracker = CostTracker()


if __name__ == "__main__":
    # Standalone usage example
    print("Cost Tracking Module - Standalone Test")
    print()

    # Simulate some API calls
    cost_tracker.track_api_call(
        operation="intent_classification",
        model="gpt-4-turbo-preview",
        input_tokens=150,
        output_tokens=50
    )

    cost_tracker.track_api_call(
        operation="rag_qa",
        model="gpt-4-turbo-preview",
        input_tokens=800,
        output_tokens=200
    )

    # Print report
    cost_tracker.print_cost_report()
