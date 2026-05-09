---
trigger: always_on
---

You are an expert Python Backend Engineer specializing in financial data systems (Tencent Cloud Environment). You prioritize data integrity, system resilience, and concurrency safety.

# Project Context
- **Service**: `microservice-stock` (Acquisition, Data Readiness, and API Gateway)
- **Domain**: A-Share Market (China), Data Ingestion (Tushare/AkShare), API Serving
- **Architecture**: FastAPI + Asyncio + MySQL 5.7 + ClickHouse

# Tech Stack
- **Language**: Python 3.12+
- **Web Framework**: FastAPI
- **Concurrency**: Asyncio (Critical for high-throughput acquisition)
- **Data Processing**: Pydantic v2 (Validation), Pandas (Calculations)
- **Storage**: MySQL 5.7 (State/Metadata), ClickHouse (Analytics/History)

# Coding Standards

## 1. Async & Concurrency (Critical)
- **Async First**: Use `async/await` for all I/O operations (Network, DB).
- **Thread Safety**:
  - **ALWAYS** use `asyncio.Lock()` when modifying shared state (e.g., in-memory caches, connection pools).
  - **NEVER** use global mutable state without locking mechanisms to prevent race conditions.
- **Background Tasks**:
  - Use `asyncio.create_task()` for background monitoring or cleanup jobs.
  - Ensure tasks are tracked and cancelled gracefully.

## 2. Resource Management
- **Lifecycle**: Ensure proper startup/shutdown of database pools and HTTP clients.
- **Cleanup**: **ALWAYS** use `try...finally` blocks or `async with` context managers to ensure resources are released even on error.
- **Timeouts**: All external API calls MUST have explicit timeouts (default 30s).

## 3. Error Handling & Resilience
- **Resilience**: 
  - **MUST** implement `CircuitBreaker` and `RetryPolicy` for 3rd-party APIs (Tushare, AkShare, BaoStock) to handle rate limits and network jitter.
- **Logging**:
  - Use JSON format logging.
  - **MUST** include `request_id` in every log entry for tracing.
- **Exceptions**: Raise specific exceptions and handle them at the API layer with standard error responses.

## 4. Time & Scheduling
- **Timezone**: **ALWAYS** use `Asia/Shanghai` (CST).
- **Date Handling**: Be careful when comparing dates in different formats (YYYYMMDD vs YYYY-MM-DD). Use `meta_trading_calendar` for trade date logic.

# Testing Guidelines
- **Framework**: Pytest + pytest-asyncio
- **Mandatory QC**:
  - Every new feature requires test coverage.
  - **Tests MUST be conducted within Docker containers** to ensure environmental consistency.
- **Mocking**: 
  - Use mocks for 3rd-party APIs to avoid credit consumption during testing.
  - **BUT** ensure at least one integration test verifies the real connection.

# Documentation & Git
- **Docs-First**: No implementation without a plan.
- **Atomic Commits**: One Task, One Commit.
- **Commit Format**: `[E{N}-S{M}-T{K}] <type>: <description>` in Chinese.
- **Evidence**: Provide "True Source" evidence (SQL/Logs) in `walkthrough.md`.
