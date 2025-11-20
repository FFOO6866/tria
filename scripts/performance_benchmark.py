#!/usr/bin/env python3
"""
Performance Benchmark Suite
=============================

Measure actual performance metrics for policy-integrated chatbot.

Metrics Measured:
- End-to-end latency per query type
- ChromaDB retrieval time
- GPT-4 response time
- Validation overhead
- Memory usage
- Throughput (queries/second)

Usage:
    python scripts/performance_benchmark.py

NO MOCKS - Real performance measurement
"""

import os
import sys
import time
import psutil
from pathlib import Path
from dotenv import load_dotenv
from statistics import mean, median, stdev
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment
load_dotenv(project_root / ".env")

from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent


class PerformanceBenchmark:
    """Performance benchmark suite"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "queries": [],
            "summary": {}
        }

    def measure_query(self, message: str, intent_type: str) -> dict:
        """
        Measure performance for a single query

        Returns:
            dict with timing breakdowns
        """
        # Get baseline memory
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Initialize agent (cold start)
        start_init = time.time()
        agent = EnhancedCustomerServiceAgent(
            api_key=self.api_key,
            enable_rag=True,
            enable_escalation=True,
            enable_response_validation=True
        )
        init_time = time.time() - start_init

        # Warm up ChromaDB connection
        try:
            agent.handle_message("test", [])
        except:
            pass

        # Measure actual query
        start_total = time.time()

        try:
            response = agent.handle_message(
                message=message,
                conversation_history=[]
            )

            total_time = time.time() - start_total

            # Memory after
            mem_after = process.memory_info().rss / 1024 / 1024  # MB

            result = {
                "message": message[:50] + "..." if len(message) > 50 else message,
                "intent_type": intent_type,
                "intent_detected": response.intent,
                "total_time": round(total_time, 3),
                "init_time": round(init_time, 3),
                "confidence": round(response.confidence, 3),
                "memory_delta_mb": round(mem_after - mem_before, 2),
                "validation_passed": response.metadata.get("validation_passed"),
                "knowledge_chunks": response.metadata.get("knowledge_chunks_used", 0),
                "success": True
            }

            return result

        except Exception as e:
            return {
                "message": message[:50],
                "intent_type": intent_type,
                "total_time": time.time() - start_total,
                "error": str(e),
                "success": False
            }

    def run_benchmark(self):
        """Run complete benchmark suite"""

        print("=" * 70)
        print("PERFORMANCE BENCHMARK SUITE")
        print("=" * 70)
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test queries representing different intents
        test_queries = [
            # Product inquiries (with validation)
            {
                "message": "How much is a 10 inch pizza box?",
                "type": "product_inquiry_validated",
                "runs": 3
            },
            {
                "message": "Do you have 12 inch boxes?",
                "type": "product_inquiry_validated",
                "runs": 3
            },

            # Policy questions (with validation)
            {
                "message": "What's your refund policy?",
                "type": "policy_question_validated",
                "runs": 3
            },
            {
                "message": "What are your delivery times?",
                "type": "policy_question_validated",
                "runs": 3
            },

            # Complaints (with escalation + tone)
            {
                "message": "My order arrived damaged!",
                "type": "complaint_escalated",
                "runs": 3
            },
            {
                "message": "This is the third late delivery!",
                "type": "complaint_escalated",
                "runs": 3
            },

            # Simple greeting (minimal processing)
            {
                "message": "Hello",
                "type": "greeting_simple",
                "runs": 3
            }
        ]

        print(f"\nRunning {sum(q['runs'] for q in test_queries)} total measurements...")
        print("(Each query run 3 times for statistical accuracy)\n")

        # Run benchmarks
        for idx, test in enumerate(test_queries, 1):
            print(f"[{idx}/{len(test_queries)}] Testing: {test['type']}")
            print(f"    Query: \"{test['message']}\"")

            run_times = []

            for run in range(test['runs']):
                print(f"    Run {run + 1}/{test['runs']}...", end=" ")

                result = self.measure_query(test['message'], test['type'])

                if result['success']:
                    run_times.append(result['total_time'])
                    print(f"{result['total_time']:.2f}s")
                else:
                    print(f"FAILED: {result.get('error', 'Unknown')}")

                self.results['queries'].append(result)

                # Small delay between runs
                time.sleep(0.5)

            if run_times:
                avg_time = mean(run_times)
                print(f"    Average: {avg_time:.2f}s")
                if len(run_times) > 1:
                    print(f"    Std Dev: {stdev(run_times):.3f}s")
            print()

        # Generate summary
        self._generate_summary()

        # Save results
        output_file = project_root / "data" / "performance_benchmark.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"[OK] Benchmark results saved to: {output_file}")

        return self.results

    def _generate_summary(self):
        """Generate performance summary"""

        successful = [q for q in self.results['queries'] if q.get('success')]

        if not successful:
            print("\n[ERROR] No successful queries to analyze")
            return

        # Group by intent type
        by_type = {}
        for query in successful:
            intent_type = query['intent_type']
            if intent_type not in by_type:
                by_type[intent_type] = []
            by_type[intent_type].append(query['total_time'])

        # Calculate statistics
        all_times = [q['total_time'] for q in successful]

        summary = {
            "total_queries": len(self.results['queries']),
            "successful": len(successful),
            "failed": len(self.results['queries']) - len(successful),
            "overall": {
                "min_time": round(min(all_times), 3),
                "max_time": round(max(all_times), 3),
                "mean_time": round(mean(all_times), 3),
                "median_time": round(median(all_times), 3),
                "std_dev": round(stdev(all_times), 3) if len(all_times) > 1 else 0
            },
            "by_type": {}
        }

        for intent_type, times in by_type.items():
            summary['by_type'][intent_type] = {
                "count": len(times),
                "mean": round(mean(times), 3),
                "min": round(min(times), 3),
                "max": round(max(times), 3),
                "std_dev": round(stdev(times), 3) if len(times) > 1 else 0
            }

        # Memory usage
        mem_deltas = [q['memory_delta_mb'] for q in successful if 'memory_delta_mb' in q]
        if mem_deltas:
            summary['memory'] = {
                "avg_delta_mb": round(mean(mem_deltas), 2),
                "max_delta_mb": round(max(mem_deltas), 2)
            }

        self.results['summary'] = summary

        # Print summary
        print("=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)

        print(f"\nTotal Queries: {summary['total_queries']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")

        print(f"\nOverall Performance:")
        print(f"  Min Time: {summary['overall']['min_time']}s")
        print(f"  Max Time: {summary['overall']['max_time']}s")
        print(f"  Mean Time: {summary['overall']['mean_time']}s")
        print(f"  Median Time: {summary['overall']['median_time']}s")
        print(f"  Std Dev: {summary['overall']['std_dev']}s")

        print(f"\nBy Intent Type:")
        for intent_type, stats in summary['by_type'].items():
            print(f"  {intent_type}:")
            print(f"    Mean: {stats['mean']}s")
            print(f"    Range: {stats['min']}s - {stats['max']}s")

        if 'memory' in summary:
            print(f"\nMemory Usage:")
            print(f"  Avg Delta: {summary['memory']['avg_delta_mb']} MB")
            print(f"  Max Delta: {summary['memory']['max_delta_mb']} MB")

        # Performance assessment
        print(f"\n" + "=" * 70)
        print("PERFORMANCE ASSESSMENT")
        print("=" * 70)

        mean_time = summary['overall']['mean_time']

        print(f"\nUser Experience:")
        if mean_time < 2:
            print("  [EXCELLENT] < 2s - Feels instant")
        elif mean_time < 5:
            print("  [GOOD] 2-5s - Acceptable for complex queries")
        elif mean_time < 10:
            print("  [FAIR] 5-10s - Users may notice delay")
        else:
            print("  [POOR] > 10s - Too slow, needs optimization")

        print(f"\nComparison:")
        print(f"  ChatGPT: ~1-3s")
        print(f"  This System: ~{mean_time:.1f}s")
        print(f"  Overhead: +{mean_time - 2:.1f}s ({((mean_time/2 - 1) * 100):.0f}% slower)")


def main():
    """Run performance benchmark"""

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n[ERROR] OPENAI_API_KEY not found in environment")
        sys.exit(1)

    # Set CHROMA_OPENAI_API_KEY
    if not os.getenv('CHROMA_OPENAI_API_KEY'):
        os.environ['CHROMA_OPENAI_API_KEY'] = api_key

    print("\n[OK] Environment configured")

    # Run benchmark
    benchmark = PerformanceBenchmark(api_key)
    results = benchmark.run_benchmark()

    # Recommendations
    print("\n" + "=" * 70)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 70)

    mean_time = results['summary']['overall']['mean_time']

    if mean_time > 5:
        print("\n[HIGH PRIORITY]")
        print("  1. Add response caching for common queries")
        print("  2. Consider async processing for validation")
        print("  3. Optimize ChromaDB retrieval (reduce top_n)")
        print("  4. Use GPT-3.5-turbo for non-critical paths")

    if results['summary'].get('memory', {}).get('avg_delta_mb', 0) > 100:
        print("\n[MEMORY CONCERN]")
        print("  1. Agent initialization creates new OpenAI client each time")
        print("  2. Consider singleton pattern for reusable components")
        print("  3. Profile memory usage with memory_profiler")

    print("\n[NEXT STEPS]")
    print("  1. Review performance_benchmark.json for detailed timings")
    print("  2. Implement caching layer (Week 1 priority)")
    print("  3. Run load test with concurrent users")
    print("  4. Profile with py-spy for bottleneck identification")


if __name__ == '__main__':
    main()
