FROM python:3.12-slim

# 使用阿里云镜像加速
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 使用清华镜像加速 pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 运行服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
