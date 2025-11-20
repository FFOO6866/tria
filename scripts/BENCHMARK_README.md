# Performance Benchmark Suite

Comprehensive before/after performance benchmarking for the Tria AIBPO customer service chatbot.

## Overview

This benchmark suite measures performance improvements across 5 key dimensions:

1. **Latency** - P50, P95, P99 response times (sync vs async, cached vs uncached)
2. **Cache Efficiency** - 4-tier cache hit rates (L1, L2, L3, L4)
3. **Streaming** - First token latency and perceived vs actual latency
4. **DSPy Optimization** - Accuracy, token usage, and cost comparison
5. **Cost Analysis** - Token usage and API costs per 1K requests

## Prerequisites

### Required
- OpenAI API key set in `.env` file
- Python 3.8+
- Dependencies: `pip install -r requirements.txt`

### Optional (for full benchmarks)
- Redis running locally (for multilevel cache benchmarks)
- ChromaDB initialized with knowledge base
- Trained DSPy models (run `scripts/optimize_dspy_example.py` first)
- `tqdm` for progress bars: `pip install tqdm`

## Quick Start

### Basic Usage

```bash
# Run all benchmarks (basic)
python scripts/benchmark_performance.py

# Export results to JSON
python scripts/benchmark_performance.py --export-json results.json

# Export results to CSV for analysis
python scripts/benchmark_performance.py --export-csv results.csv
```

### Understanding the Output

The benchmark will produce output like this:

```
========================================
Performance Benchmark Results
========================================

Latency (uncached):
  Before: P50=15s, P95=28s, P99=45s
  After:  P50=4s, P95=8s, P99=12s
  Improvement: 73% faster

Latency (cached):
  L1 hit: <1ms
  L2 hit: 45ms
  L3 hit: 8ms
  L4 hit: 95ms

Cache Hit Rate:
  L1: 35%
  L2: 30%
  L3: 10%
  Total: 75%

Cost per 1K Requests:
  Before: $21.00
  After (uncached): $8.40
  After (with cache): $2.10
  Savings: 90%

First Token Latency:
  Streaming: <1s
  Non-streaming: N/A

DSPy vs Manual:
  Accuracy: +3.5% (DSPy)
  Tokens: -22% (DSPy)
  Cost: -20% (DSPy)
```

## What Gets Benchmarked

### 1. Latency Benchmark

**Tests:**
- **Before**: Synchronous agent without caching
- **After (Uncached)**: Async agent with parallel execution, no cache
- **After (Cached)**: Async agent with 4-tier caching

**Metrics:**
- P50, P95, P99 response times
- Min, max, mean, standard deviation
- Number of samples

**Test Queries:**
- Policy questions (return policy, shipping, etc.)
- Product inquiries (pricing, availability)
- Complaints (damaged orders, late delivery)
- Order placement requests
- General inquiries

### 2. Cache Efficiency Benchmark

**Tests:**
- L1 (Exact match) - Redis, ~1ms
- L2 (Semantic similarity) - ChromaDB, ~50ms
- L3 (Intent cache) - Redis, ~10ms
- L4 (RAG results) - Redis, ~100ms

**Simulates:**
- 40% exact repeats (L1 hits)
- 30% semantic variations (L2 hits)
- 30% new queries (cache misses)

**Metrics:**
- Hit rate per cache level
- Overall hit rate
- Cost savings from cache hits

### 3. Streaming Benchmark

**Tests:**
- Non-streaming: Wait for full response
- Streaming: Progressive token delivery

**Metrics:**
- First token latency (when user sees content)
- Total latency
- Perceived vs actual latency
- Improvement percentage

### 4. DSPy Comparison (Optional)

**Tests:**
- DSPy optimized prompts
- Manual prompts

**Metrics:**
- Accuracy comparison
- Token usage per request
- Cost per request
- Improvements in %

**Note:** Requires trained DSPy models. Run `scripts/optimize_dspy_example.py` first.

### 5. Cost Analysis

**Calculates:**
- Tokens per request (before/after)
- API costs using GPT-4 and GPT-3.5 pricing
- Impact of cache hit rate on costs
- Savings per 1K requests

**Pricing Used:**
- GPT-4: $0.03/1K input tokens, $0.06/1K output tokens
- GPT-3.5: $0.0015/1K input tokens, $0.002/1K output tokens

## Output Files

### JSON Output
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "latency_before_uncached": {
    "p50": 15234.5,
    "p95": 28456.2,
    "p99": 45678.9,
    "mean": 16234.7,
    "std_dev": 5234.1,
    "samples": 5
  },
  "latency_after_cached": {
    "p50": 234.5,
    "p95": 456.2,
    "p99": 678.9,
    "mean": 345.7,
    "std_dev": 123.4,
    "samples": 5
  },
  "cache_metrics": {
    "l1_hit_rate": 35.0,
    "l2_hit_rate": 30.0,
    "l3_hit_rate": 10.0,
    "l4_hit_rate": 5.0,
    "overall_hit_rate": 75.0,
    "cost_saved_usd": 25.50
  },
  "cost_analysis": {
    "before_cost_uncached": 21.00,
    "after_cost_cached": 2.10,
    "savings_pct": 90.0
  }
}
```

### CSV Output
```csv
Metric,Before,After (Uncached),After (Cached),Improvement %
Latency P50 (ms),15235,4123,235,98.5%
Latency P95 (ms),28456,8234,456,98.4%
Cost per 1K requests ($),21.00,8.40,2.10,90.0%

Cache Metrics,Hit Rate %
L1 (Exact),35.0%
L2 (Semantic),30.0%
L3 (Intent),10.0%
L4 (RAG),5.0%
Overall,75.0%
```

## Interpreting Results

### Latency

**Excellent:** P50 < 2s, P95 < 5s
**Good:** P50 < 5s, P95 < 10s
**Fair:** P50 < 10s, P95 < 20s
**Poor:** P50 > 10s, P95 > 20s

### Cache Hit Rate

**Excellent:** >70% overall hit rate
**Good:** 50-70% overall hit rate
**Fair:** 30-50% overall hit rate
**Poor:** <30% overall hit rate

### Cost Savings

**Excellent:** >80% cost reduction
**Good:** 50-80% cost reduction
**Fair:** 25-50% cost reduction
**Poor:** <25% cost reduction

## Troubleshooting

### "Redis connection failed"

Cache benchmarks (L1, L3, L4) will be disabled. The benchmark will still run but cache metrics will be limited.

**Solution:**
```bash
# Install Redis
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# macOS: brew install redis
# Linux: sudo apt-get install redis-server

# Start Redis
redis-server
```

### "ChromaDB not available"

L2 (semantic cache) benchmarks will be skipped.

**Solution:**
```bash
pip install chromadb sentence-transformers

# Initialize knowledge base
python scripts/build_knowledge_base.py
```

### "Skipping DSPy benchmark"

DSPy comparison requires trained models.

**Solution:**
```bash
# Train DSPy models first
python scripts/optimize_dspy_example.py --task intent
python scripts/optimize_dspy_example.py --task rag
```

### Slow Benchmarks

The complete benchmark suite can take 10-20 minutes depending on:
- Number of test queries
- API response times
- Cache initialization

**To speed up:**
- Use `--skip-dspy` flag (if implemented)
- Reduce test query count in code
- Run with cache already warmed up

## Advanced Usage

### Custom Test Queries

Edit the `test_queries` list in `PerformanceBenchmarkSuite.__init__()`:

```python
self.test_queries = [
    {
        "message": "Your custom query",
        "intent": "expected_intent",
        "complexity": "simple|medium|complex"
    },
    # Add more queries...
]
```

### Adjust Concurrency Levels

Modify the concurrent user levels in `run_all_benchmarks()`:

```python
concurrent_users=[10, 50, 100, 500]  # Test with more users
```

### Compare Multiple Runs

```bash
# Run 1: Before optimizations
python scripts/benchmark_performance.py --export-json run1.json

# Make changes...

# Run 2: After optimizations
python scripts/benchmark_performance.py --export-json run2.json

# Compare using external tools or custom script
```

## Related Scripts

- `scripts/performance_benchmark.py` - Original performance benchmark
- `scripts/test_cache_performance.py` - Cache-specific testing
- `scripts/test_quick_performance.py` - Quick single-request test
- `scripts/demo_multilevel_cache.py` - Cache demonstration
- `scripts/optimize_dspy_example.py` - DSPy optimization

## Technical Details

### Architecture

```
PerformanceBenchmarkSuite
├── Latency Benchmarks
│   ├── benchmark_latency_before() → Sync agent, no cache
│   ├── benchmark_latency_after_uncached() → Async agent, no cache
│   └── benchmark_latency_after_cached() → Async agent, 4-tier cache
├── Cache Benchmark
│   └── benchmark_cache_efficiency() → Test all 4 cache levels
├── Streaming Benchmark
│   └── benchmark_streaming() → Compare streaming vs non-streaming
├── DSPy Benchmark
│   └── benchmark_dspy_comparison() → Compare optimized vs manual
└── Cost Analysis
    └── analyze_costs() → Calculate cost savings
```

### Real Infrastructure

**NO MOCKING** - All benchmarks use:
- Real OpenAI API calls (GPT-4, GPT-3.5)
- Real Redis cache (if available)
- Real ChromaDB vector store (if available)
- Real RAG retrieval
- Real intent classification

### Performance Targets

Based on architectural improvements, we expect:

| Metric | Before | After (Target) |
|--------|--------|----------------|
| P50 Latency | 15s | <5s (70% faster) |
| Cache Hit Rate | 0% | >75% |
| Cost per 1K | $21 | <$5 (75% cheaper) |
| First Token | N/A | <1s |

## Contributing

To add new benchmarks:

1. Add method to `PerformanceBenchmarkSuite`
2. Define metrics dataclass
3. Update `run_all_benchmarks()` to call new method
4. Update `print_results()` to display new metrics
5. Document in this README

## License

Same as parent project (Tria AIBPO).
