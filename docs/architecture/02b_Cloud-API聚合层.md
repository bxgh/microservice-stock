# 02b. Cloud-API 聚合层 (BFF Spec)

> **部署位置**: 腾讯云轻量服务器 (Docker 容器)
> **职责**: 身份鉴权、请求聚合、任务分发、Redis 交互

## 1. 服务定位

`Cloud-API` 是系统的 **BFF (Backend for Frontend)** 层，不直接采集数据，而是：
1.  **统一入口**: 前端只需对接一个服务，屏蔽后端复杂性。
2.  **鉴权中心**: 所有 API 请求必须经过 JWT 校验。
3.  **任务调度器**: 接收用户回测请求，写入 Redis 队列供内网消费。
4.  **数据聚合**: 按需调用 AkShare/BaoStock 微服务，组合返回。

---

## 2. 鉴权体系 (Authentication)

### 2.1 JWT 规范
*   **算法**: RS256 (非对称，私钥签名，公钥验证)
*   **有效期**: Access Token 2小时，Refresh Token 7天
*   **Payload 结构**:
    ```json
    {
      "sub": "user_12345",
      "exp": 1704067200,
      "iat": 1704060000,
      "scopes": ["read:data", "write:strategy", "run:backtest"]
    }
    ```

### 2.2 中间件实现
```python
from fastapi import Request, HTTPException
from jose import jwt, JWTError

async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/public"):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        request.state.user_id = payload["sub"]
        request.state.scopes = payload.get("scopes", [])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return await call_next(request)
```

---

## 3. 任务分发系统 (Task Dispatcher)

### 3.1 回测任务提交流程
```mermaid
sequenceDiagram
    participant User
    participant CloudAPI
    participant MySQL
    participant Redis
    participant HomeWorker

    User->>CloudAPI: POST /api/backtest/run
    CloudAPI->>CloudAPI: 校验 JWT
    CloudAPI->>MySQL: INSERT task (status=pending)
    CloudAPI->>Redis: LPUSH queue:backtest
    CloudAPI-->>User: 202 Accepted {task_id}
    
    HomeWorker->>Redis: BRPOP queue:backtest
    HomeWorker->>HomeWorker: Execute backtest
    HomeWorker->>MySQL: UPDATE task (status=done)
```

### 3.2 API 实现
```python
@router.post("/backtest/run", status_code=202)
async def submit_backtest(
    params: BacktestParams,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    user_id = request.state.user_id
    task_id = str(uuid.uuid4())
    
    # 1. 持久化任务元数据
    task = Task(
        id=task_id,
        user_id=user_id,
        strategy_code=params.strategy,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(task)
    await db.commit()
    
    # 2. 推送到 Redis 队列
    payload = {
        "task_id": task_id,
        "strategy": params.strategy,
        "codes": params.codes,
        "start_date": params.start_date.isoformat(),
        "end_date": params.end_date.isoformat()
    }
    await redis.lpush("queue:backtest", json.dumps(payload))
    
    return {"task_id": task_id, "status": "submitted"}
```

---

## 4. Redis 交互规范

### 4.1 Key 命名约定
| Key Pattern | 类型 | TTL | 用途 |
|:---|:---|:---|:---|
| `queue:backtest` | List | - | 回测任务队列 (FIFO) |
| `cache:quote:{code}` | String | 5s | 实时行情缓存 |
| `cache:wencai:{hash}` | String | 1h | PyWencai 查询结果缓存 |
| `session:{user_id}` | Hash | 7d | 用户会话信息 |

### 4.2 连接池配置
```python
import aioredis

redis_pool = aioredis.from_url(
    "redis://redis:6379",
    password=os.getenv("REDIS_PASSWORD"),
    encoding="utf-8",
    decode_responses=True,
    max_connections=20
)
```

---

## 5. 数据库连接池 (Critical)

云端内存仅 4G，连接池必须严格控制：

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # 基础连接数
    max_overflow=10,     # 允许临时超出
    pool_recycle=3600,   # 每小时回收，防止 MySQL 主动断开
    pool_pre_ping=True   # 每次使用前检测连接有效性
)
```

---

## 6. API 端点速查

| Method | Path | Description | Auth |
|:---|:---|:---|:---|
| POST | `/api/auth/login` | 用户登录获取 Token | ❌ |
| POST | `/api/auth/refresh` | 刷新 Token | ✅ |
| GET | `/api/quote/{code}` | 获取实时行情 | ✅ |
| GET | `/api/kline/{code}` | 获取 K 线数据 | ✅ |
| POST | `/api/backtest/run` | 提交回测任务 | ✅ |
| GET | `/api/backtest/{task_id}` | 查询任务状态 | ✅ |
| POST | `/api/wencai/query` | 问财选股 | ✅ |

---

## 7. Docker 部署

```yaml
services:
  cloud-api:
    build: ./cloud-api
    environment:
      - DATABASE_URL=mysql+aiomysql://user:pass@mysql:3306/stock
      - REDIS_URL=redis://:password@redis:6379/0
      - JWT_PUBLIC_KEY_PATH=/app/keys/public.pem
    deploy:
      resources:
        limits:
          memory: 800M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```
