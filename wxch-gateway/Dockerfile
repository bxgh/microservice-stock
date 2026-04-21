FROM python:3.12-slim

WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

# 暴露 FastAPI 端口 (微信云托管推荐 80)
EXPOSE 80

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
