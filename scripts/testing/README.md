# 测试脚本

本目录包含用于验证和调试的临时测试脚本。

## 脚本说明

### test_akshare_direct.py
直接测试 AkShare Service 层的所有接口，绕过 HTTP 服务。

**用法**:
```bash
cd /home/ubuntu/microservice-stock
python3 scripts/testing/test_akshare_direct.py
```

### test_akshare_api.py
通过 HTTP 请求测试 AkShare API 的所有端点（需要服务运行）。

**用法**:
```bash
# 启动服务
cd akshare-api && uvicorn app.main:app --host 0.0.0.0 --port 8000

# 运行测试
python3 scripts/testing/test_akshare_api.py
```

### debug_akshare_finance.py
调试工具：查看 AkShare 财务数据接口的原始返回格式。

### list_metrics.py
列出 AkShare 财务摘要接口中所有可用的指标字段。

---

**注意**: 这些是临时验证脚本，正式的单元测试应放在各服务的 `tests/` 目录下。
