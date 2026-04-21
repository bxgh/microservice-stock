import httpx
import logging
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI(title="WXCH Gateway", description="API Gateway for Microservice Stock")

# VPS 内网 IP
VPS_IP = "10.0.12.7"

SERVICE_ROUTES = {
    "/baostock": f"http://{VPS_IP}:8001",
    "/wencai": f"http://{VPS_IP}:8002",
    "/akshare": f"http://{VPS_IP}:8003",
    "/manager": f"http://{VPS_IP}:8004",
    "/tushare": f"http://{VPS_IP}:8005",
    "/monitor": f"http://{VPS_IP}:8006",
}

# 显式禁用环境变量中的代理干扰
client = httpx.AsyncClient(trust_env=False, timeout=30.0)

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()

@app.get("/health")
async def health_check():
    return {"status": "gateway proxy healthy", "vps_ip": VPS_IP}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    target_url = None
    
    # 路径匹配逻辑
    for prefix, base_url in SERVICE_ROUTES.items():
        clean_prefix = prefix.strip('/')
        if path.startswith(clean_prefix):
            path_without_prefix = path[len(clean_prefix):]
            if not path_without_prefix.startswith('/') and path_without_prefix != "":
                continue # 防止前缀部分匹配，如 /baostocks 匹配到 /baostock
            target_url = f"{base_url}{path_without_prefix}"
            break
            
    if not target_url:
        # 默认转发到 manager 或者返回 404
        target_url = f"http://{VPS_IP}:8004/{path}"

    # 合并查询参数
    url_str = target_url
    if request.url.query:
        url_str = f"{target_url}?{request.url.query}"
    
    url = httpx.URL(url_str)
    
    # 转发 header
    headers = dict(request.headers.items())
    headers.pop("host", None)
    headers.pop("content-length", None) # httpx 会自动处理

    try:
        req = client.build_request(
            request.method,
            url,
            headers=headers,
            content=await request.body()
        )
        
        response = await client.send(req, stream=True)
        
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=dict(response.headers),
            background=response.aclose
        )
    except httpx.RequestError as exc:
        logger.error(f"Proxy error: {type(exc).__name__} -> {str(exc)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "PROXY_ERROR",
                    "message": f"Error proxying to {target_url}",
                    "exception": type(exc).__name__,
                    "detail": str(exc)
                }
            }
        )
    except Exception as e:
        logger.error(f"Internal gateway error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "GATEWAY_INTERNAL_ERROR", "message": str(e)}}
        )
