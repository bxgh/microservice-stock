# Mootdx API Deployment Plan (Tencent Cloud)

This document outlines the strategy for deploying the `mootdx-api` service to the Tencent Cloud environment.

## Overview
Port `mootdx-api` from the `microservice-stock-ck` repository, adapt it for cloud deployment by removing internal network proxies, and integrate it into the existing `docker-compose` orchestration.

## Implementation Plan
Detailed implementation steps are documented in the [implementation plan](file:///home/ubuntu/microservice-stock/docs/deployment/mootdx/implementation_logs/E101/S1/implementation_plan.md).

### Key Adaptation Steps:
1.  **Remove Proxy**: Remove hardcoded `http://192.168.151.18:3128` from `Dockerfile` and environment variables.
2.  **Shared Library**: Include `gsd-shared` library within the `mootdx-api` service structure.
3.  **Port Mapping**: Assign external port `8007` (internal `8000`) to avoid conflict with `akshare-api` (`8003`).
4.  **Redis Integration**: Add a Redis container to support the `RedisStreamWorker`.

## Next Steps
1.  [ ] User review and approval of the plan.
2.  [ ] Setup `mootdx-api/` directory structure.
3.  [ ] Port source code and libraries.
4.  [ ] Update `docker-compose.yml` and `.env`.
5.  [ ] Deploy and verify health status.
