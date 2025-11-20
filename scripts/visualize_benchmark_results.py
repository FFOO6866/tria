#!/usr/bin/env python3
"""
Benchmark Results Visualization
================================

Generate charts and visualizations from benchmark results.

Usage:
    python scripts/visualize_benchmark_results.py data/benchmark_results.json
    python scripts/visualize_benchmark_results.py data/benchmark_results.json --output charts/
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Optional matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("matplotlib not available. Install with: pip install matplotlib")


def load_results(json_path: Path) -> Dict[str, Any]:
    """Load benchmark results from JSON"""
    with open(json_path, 'r') as f:
        return json.load(f)


def plot_latency_comparison(results: Dict[str, Any], output_dir: Path):
    """
    Create latency comparison chart

    Shows P50, P95, P99 for before/after scenarios
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    before = results['latency_before_uncached']
    after_uncached = results['latency_after_uncached']
    after_cached = results['latency_after_cached']

    # Convert to seconds
    scenarios = ['Before\n(Sync, No Cache)', 'After\n(Async, No Cache)', 'After\n(Async, Cached)']
    p50_values = [
        before['p50'] / 1000,
        after_uncached['p50'] / 1000,
        after_cached['p50'] / 1000
    ]
    p95_values = [
        before['p95'] / 1000,
        after_uncached['p95'] / 1000,
        after_cached['p95'] / 1000
    ]
    p99_values = [
        before['p99'] / 1000,
        after_uncached['p99'] / 1000,
        after_cached['p99'] / 1000
    ]

    x = range(len(scenarios))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    bars1 = ax.bar([i - width for i in x], p50_values, width, label='P50', color='#2ecc71')
    bars2 = ax.bar(x, p95_values, width, label='P95', color='#f39c12')
    bars3 = ax.bar([i + width for i in x], p99_values, width, label='P99', color='#e74c3c')

    ax.set_xlabel('Scenario', fontsize=12)
    ax.set_ylabel('Latency (seconds)', fontsize=12)
    ax.set_title('Latency Comparison: Before vs After Optimizations', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{height:.1f}s',
                ha='center',
                va='bottom',
                fontsize=9
            )

    plt.tight_layout()
    plt.savefig(output_dir / 'latency_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'latency_comparison.png'}")
    plt.close()


def plot_cache_hit_rates(results: Dict[str, Any], output_dir: Path):
    """
    Create cache hit rate chart

    Shows hit rates for L1, L2, L3, L4, and overall
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    cache = results['cache_metrics']

    levels = ['L1\n(Exact)', 'L2\n(Semantic)', 'L3\n(Intent)', 'L4\n(RAG)', 'Overall']
    hit_rates = [
        cache['l1_hit_rate'],
        cache['l2_hit_rate'],
        cache['l3_hit_rate'],
        cache['l4_hit_rate'],
        cache['overall_hit_rate']
    ]

    colors = ['#3498db', '#9b59b6', '#1abc9c', '#e67e22', '#2ecc71']

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(levels, hit_rates, color=colors, edgecolor='black', linewidth=1.2)

    ax.set_ylabel('Hit Rate (%)', fontsize=12)
    ax.set_title('Cache Hit Rates by Level', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)

    # Add target line at 75%
    ax.axhline(y=75, color='red', linestyle='--', linewidth=2, label='Target: 75%')
    ax.legend()

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'{height:.1f}%',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )

    plt.tight_layout()
    plt.savefig(output_dir / 'cache_hit_rates.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'cache_hit_rates.png'}")
    plt.close()


def plot_cost_comparison(results: Dict[str, Any], output_dir: Path):
    """
    Create cost comparison chart

    Shows cost per 1K requests before/after with cache
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    cost = results['cost_analysis']

    scenarios = ['Before\n(Uncached)', 'After\n(Uncached)', 'After\n(Cached)']
    costs = [
        cost['before_cost_uncached'],
        cost['after_cost_uncached'],
        cost['after_cost_cached']
    ]

    colors = ['#e74c3c', '#f39c12', '#2ecc71']

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(scenarios, costs, color=colors, edgecolor='black', linewidth=1.2)

    ax.set_ylabel('Cost per 1K Requests ($)', fontsize=12)
    ax.set_title('Cost Comparison: Before vs After Optimizations', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'${height:.2f}',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )

    # Add savings annotation
    savings_pct = cost['savings_pct']
    ax.text(
        0.5, 0.95,
        f'Total Savings: {savings_pct:.0f}%',
        transform=ax.transAxes,
        fontsize=14,
        fontweight='bold',
        color='green',
        ha='center',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    )

    plt.tight_layout()
    plt.savefig(output_dir / 'cost_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'cost_comparison.png'}")
    plt.close()


def plot_streaming_comparison(results: Dict[str, Any], output_dir: Path):
    """
    Create streaming vs non-streaming comparison

    Shows first token latency vs total latency
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    stream = results['streaming_metrics']

    categories = ['Streaming\n(Perceived)', 'Non-Streaming\n(Actual)']
    latencies = [
        stream['perceived_latency_ms'] / 1000,
        stream['actual_latency_ms'] / 1000
    ]

    colors = ['#2ecc71', '#e74c3c']

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(categories, latencies, color=colors, edgecolor='black', linewidth=1.2)

    ax.set_ylabel('Latency (seconds)', fontsize=12)
    ax.set_title('Streaming vs Non-Streaming Response Latency', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'{height:.2f}s',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )

    # Add improvement annotation
    improvement_pct = stream['improvement_pct']
    ax.text(
        0.5, 0.95,
        f'Perceived Latency Improvement: {improvement_pct:.0f}%',
        transform=ax.transAxes,
        fontsize=14,
        fontweight='bold',
        color='green',
        ha='center',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    )

    plt.tight_layout()
    plt.savefig(output_dir / 'streaming_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'streaming_comparison.png'}")
    plt.close()


def plot_dspy_comparison(results: Dict[str, Any], output_dir: Path):
    """
    Create DSPy vs Manual comparison chart

    Shows accuracy, tokens, and cost
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    dspy = results.get('dspy_metrics')
    if not dspy:
        print("Skipping DSPy comparison chart (no DSPy metrics)")
        return

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

    # Accuracy comparison
    accuracies = [dspy['manual_accuracy'] * 100, dspy['dspy_accuracy'] * 100]
    ax1.bar(['Manual', 'DSPy'], accuracies, color=['#e74c3c', '#2ecc71'])
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_title('Accuracy', fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', alpha=0.3)
    for i, v in enumerate(accuracies):
        ax1.text(i, v, f'{v:.1f}%', ha='center', va='bottom', fontweight='bold')

    # Token comparison
    tokens = [dspy['manual_tokens_avg'], dspy['dspy_tokens_avg']]
    ax2.bar(['Manual', 'DSPy'], tokens, color=['#e74c3c', '#2ecc71'])
    ax2.set_ylabel('Tokens per Request')
    ax2.set_title('Token Usage', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    for i, v in enumerate(tokens):
        ax2.text(i, v, f'{v:.0f}', ha='center', va='bottom', fontweight='bold')

    # Cost comparison
    costs = [dspy['manual_cost_per_request'], dspy['dspy_cost_per_request']]
    ax3.bar(['Manual', 'DSPy'], costs, color=['#e74c3c', '#2ecc71'])
    ax3.set_ylabel('Cost per Request ($)')
    ax3.set_title('Cost', fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    for i, v in enumerate(costs):
        ax3.text(i, v, f'${v:.4f}', ha='center', va='bottom', fontweight='bold')

    plt.suptitle('DSPy vs Manual Prompts Comparison', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'dspy_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'dspy_comparison.png'}")
    plt.close()


def create_summary_dashboard(results: Dict[str, Any], output_dir: Path):
    """
    Create a summary dashboard with all key metrics

    Single page overview of all improvements
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Title
    fig.suptitle(
        'Performance Benchmark Summary Dashboard',
        fontsize=20,
        fontweight='bold',
        y=0.98
    )

    # 1. Latency P50 comparison (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    before_p50 = results['latency_before_uncached']['p50'] / 1000
    after_p50 = results['latency_after_cached']['p50'] / 1000
    ax1.bar(['Before', 'After'], [before_p50, after_p50], color=['#e74c3c', '#2ecc71'])
    ax1.set_ylabel('Seconds')
    ax1.set_title('P50 Latency', fontweight='bold')
    ax1.text(0, before_p50, f'{before_p50:.1f}s', ha='center', va='bottom')
    ax1.text(1, after_p50, f'{after_p50:.1f}s', ha='center', va='bottom')

    # 2. Cache hit rate (top center)
    ax2 = fig.add_subplot(gs[0, 1])
    cache_hit = results['cache_metrics']['overall_hit_rate']
    ax2.pie(
        [cache_hit, 100 - cache_hit],
        labels=['Cache Hit', 'Cache Miss'],
        autopct='%1.1f%%',
        colors=['#2ecc71', '#ecf0f1'],
        startangle=90
    )
    ax2.set_title(f'Cache Hit Rate\n{cache_hit:.0f}%', fontweight='bold')

    # 3. Cost savings (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    before_cost = results['cost_analysis']['before_cost_uncached']
    after_cost = results['cost_analysis']['after_cost_cached']
    ax3.bar(['Before', 'After'], [before_cost, after_cost], color=['#e74c3c', '#2ecc71'])
    ax3.set_ylabel('$ per 1K requests')
    ax3.set_title('Cost per 1K Requests', fontweight='bold')
    ax3.text(0, before_cost, f'${before_cost:.2f}', ha='center', va='bottom')
    ax3.text(1, after_cost, f'${after_cost:.2f}', ha='center', va='bottom')

    # 4. All latency percentiles (middle row, spans 2 columns)
    ax4 = fig.add_subplot(gs[1, :2])
    scenarios = ['Before', 'After\n(Uncached)', 'After\n(Cached)']
    p50 = [
        results['latency_before_uncached']['p50'] / 1000,
        results['latency_after_uncached']['p50'] / 1000,
        results['latency_after_cached']['p50'] / 1000
    ]
    p95 = [
        results['latency_before_uncached']['p95'] / 1000,
        results['latency_after_uncached']['p95'] / 1000,
        results['latency_after_cached']['p95'] / 1000
    ]
    p99 = [
        results['latency_before_uncached']['p99'] / 1000,
        results['latency_after_uncached']['p99'] / 1000,
        results['latency_after_cached']['p99'] / 1000
    ]
    x = range(len(scenarios))
    width = 0.25
    ax4.bar([i - width for i in x], p50, width, label='P50', color='#2ecc71')
    ax4.bar(x, p95, width, label='P95', color='#f39c12')
    ax4.bar([i + width for i in x], p99, width, label='P99', color='#e74c3c')
    ax4.set_ylabel('Latency (seconds)')
    ax4.set_title('Latency Percentiles Comparison', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(scenarios)
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)

    # 5. Cache levels breakdown (middle right)
    ax5 = fig.add_subplot(gs[1, 2])
    levels = ['L1', 'L2', 'L3', 'L4']
    hit_rates = [
        results['cache_metrics']['l1_hit_rate'],
        results['cache_metrics']['l2_hit_rate'],
        results['cache_metrics']['l3_hit_rate'],
        results['cache_metrics']['l4_hit_rate']
    ]
    ax5.barh(levels, hit_rates, color=['#3498db', '#9b59b6', '#1abc9c', '#e67e22'])
    ax5.set_xlabel('Hit Rate (%)')
    ax5.set_title('Cache Levels', fontweight='bold')
    ax5.set_xlim(0, 100)
    ax5.grid(axis='x', alpha=0.3)
    for i, v in enumerate(hit_rates):
        ax5.text(v, i, f'{v:.0f}%', va='center', fontweight='bold')

    # 6. Key metrics summary (bottom row)
    ax6 = fig.add_subplot(gs[2, :])
    ax6.axis('off')

    improvement_pct = results['latency_improvement_pct']
    savings_pct = results['cost_analysis']['savings_pct']
    stream_improvement = results['streaming_metrics']['improvement_pct']

    summary_text = f"""
    KEY IMPROVEMENTS

    Latency:        {improvement_pct:.0f}% faster (P50)
    Cache Hit Rate: {cache_hit:.0f}%
    Cost Savings:   {savings_pct:.0f}% cheaper
    Streaming:      {stream_improvement:.0f}% faster perceived latency

    Timestamp:      {results['timestamp']}
    Test Queries:   {results['test_queries']}
    """

    ax6.text(
        0.5, 0.5,
        summary_text,
        transform=ax6.transAxes,
        fontsize=14,
        ha='center',
        va='center',
        family='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    )

    plt.savefig(output_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir / 'summary_dashboard.png'}")
    plt.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Visualize Benchmark Results")
    parser.add_argument(
        'json_file',
        type=str,
        help='Path to benchmark results JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='charts',
        help='Output directory for charts (default: charts/)'
    )

    args = parser.parse_args()

    if not MATPLOTLIB_AVAILABLE:
        print("\n[ERROR] matplotlib is required for visualization")
        print("Install with: pip install matplotlib")
        sys.exit(1)

    # Load results
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"\n[ERROR] File not found: {json_path}")
        sys.exit(1)

    print(f"\nLoading results from: {json_path}")
    results = load_results(json_path)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Generate charts
    print("\nGenerating charts...")

    plot_latency_comparison(results, output_dir)
    plot_cache_hit_rates(results, output_dir)
    plot_cost_comparison(results, output_dir)
    plot_streaming_comparison(results, output_dir)
    plot_dspy_comparison(results, output_dir)
    create_summary_dashboard(results, output_dir)

    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)
    print(f"\nCharts saved to: {output_dir.absolute()}")
    print("\nGenerated files:")
    print("  - latency_comparison.png")
    print("  - cache_hit_rates.png")
    print("  - cost_comparison.png")
    print("  - streaming_comparison.png")
    print("  - dspy_comparison.png (if available)")
    print("  - summary_dashboard.png")
    print()


if __name__ == '__main__':
    main()
