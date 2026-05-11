---
trigger: always_on
---

# Antigravity Rules: Microservice Stock Data System

You are an expert developer specializing in high-performance, asynchronous Python microservices. When working on this project, adhere to the following strict rules:

## 1. Core Principles
- **Async Only**: Use `async/await` for ALL I/O. Use `httpx`, `motor`, or `aioredis`. Never use `requests` or `time.sleep`.
- **Concurrency Control**: Use `asyncio.Lock()` when accessing shared state or limited resources.
- **Resource Discipline**: Default memory limit ≤128MB. Specific services: `akshare-api` (256MB), `pywencai-api` (512MB), `stock-manager` (192MB). Use generators or streaming for large data.

## 2. Technical Stack
- **Framework**: FastAPI + Pydantic v2.
- **Performance**: Use `python:3.12-slim` to balance build speed and image size.
- **Port Mapping**: Respect fixed ports: 8000 (Dict), 8001 (BaoStock), 8002 (PyWencai), 8003 (AkShare), 8005 (Tushare).
- **Configuration**: Use `.env` and `pydantic-settings`. NEVER hardcode credentials or URLs.
- **Localization**: Default timezone is `Asia/Shanghai`.

## 3. API & Implementation Standards
- **Routing**: Fixed prefix `/api/v1/`. Required `GET /health` endpoint.
- **Reliability**: 
  - Standard timeout: 30 seconds for all external calls.
  - Mandatory `try...finally` or `async with` for resource cleanup.
- **Error Format**: Must return `{"error": {"code": "...", "message": "...", "request_id": "..."}}`.
- **Logging**: JSON format only. Every log entry MUST include `request_id`.

## 4. Data Source Handling (CRITICAL)
- **Tushare**: 主力数据源 (P0)；负责历史 K 线、复权因子、指数及财务数据。需确保积分合规并处理流控。
- **BaoStock**: 次要数据源 (P1)；负责日线补偿及基础 K 线，需在服务层实现 Broken pipe 自动重连。
- **AkShare**: 补充数据源 (P2)；负责个股异动、实时快照及概念板块。
- **PyWencai**: 严格限流 (~10 requests/min)，默认实施 3 次指数退避重试。

## 5. Quality Assurance & QC Flow
- **Tests**: Every new feature requires `pytest` + `pytest-asyncio` coverage. Tests MUST be conducted within Docker containers.
- **Mandatory QC**: After any code change, you MUST:
  1. **Health Check**: Verify `GET /health` returns `200 OK`.
  2. **Regression**: Run relevant scripts in `scripts/testing/` to confirm functionality.
  3. **Linting**: Ensure code adheres to PEP8 and project standards.
- **Git**: Follow Conventional Commits. Summary must be in Chinese.
- **Language**: All documentation, code comments, and commit messages MUST be in Chinese.
- **Doc Sync**: Any architecture/API change must be reflected in `docs/` and `README.md` (in Chinese).
- **Orchestration**: New services MUST be integrated into `docker-compose.yml`.
## 6. Frontend Standards (Mobile/Web)
- **Tech Stack**:
  - **Framework**: Vite + React 18 + TypeScript.
  - **State Management**: React Query (Server State) + React Context (UI State).
  - **Styling**: Vanilla CSS + CSS Variables. No Tailwind/Sass unless approved.
  - **Charts**: Apache ECharts (Complex) or Lightweight Charts (Performance).
- **Architecture**:
  - **Component**: Functional Components + Hooks only.
  - **API**: Use centralized `api/` client with Axios interceptors for standard error handling.
  - **Performance**: Use `React.memo` and `useCallback` for high-frequency data components (e.g., Ticks/OrderBooks).
- **Routing**: Client-side routing via React Router v6.
## 7. 全程不准使用夸张的词汇。