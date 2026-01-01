from fastapi import APIRouter
from app.utils.http_client import http_client

router = APIRouter()

@router.get("/health")
async def health_check():
    """系统健康检查 (聚合所有容器)"""
    services = {}
    containers = [
        ("baostock", "baostock"),
        ("akshare", "akshare"),
        ("pywencai", "pywencai")
    ]
    
    for name, container in containers:
        try:
            await http_client.get(container, "/health")
            services[f"{name}_api"] = "healthy"
        except:
            services[f"{name}_api"] = "unhealthy"
    
    # 检查数据库连接
    from app.utils.database import db
    try:
        await db.execute("SELECT 1")
        services["mysql"] = "healthy"
    except:
        services["mysql"] = "unhealthy"
    
    overall_status = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    
    return {
        "status": overall_status,
        "services": services
    }
