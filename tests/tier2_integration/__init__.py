"""
Tier 2 Integration Tests
=========================

Integration tests with REAL infrastructure (NO MOCKING).
- Speed: < 5 seconds per test
- Infrastructure: Real Docker services
- NO MOCKING: Use real services only
- Focus: Component interactions

REQUIRED SETUP:
Before running these tests, start the test infrastructure:
```bash
# Navigate to test utilities
cd tests/utils

# Start all test services
./test-env up

# Verify services are ready
./test-env status
```
"""
