FROM python:3.12-slim

WORKDIR /app

# 优化: 换源以加速构建
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources || \
    sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并使用国内镜像加速 pip
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制共享库并安装 (本地路径)
COPY libs/gsd-shared/ /app/libs/gsd-shared/
RUN pip install --no-cache-dir -e /app/libs/gsd-shared/

# 复制源代码
COPY src/ ./src/

# 创建日志目录
RUN mkdir -p /app/logs

# 设置 Python 路径
ENV PYTHONPATH=/app/src

# 健康检查 (使用 Python)
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口 (内部 8000)
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
