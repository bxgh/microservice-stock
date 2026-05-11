# 腾讯云 SCF 采集系统部署指引

本指引旨在帮助您将 `scf-collector` 部署至腾讯云。

## 1. 准备工作
1. **安装 Serverless Framework**:
   ```bash
   npm install -g serverless
   ```
2. **准备环境变量**:
   - 将 `.env.example` 复制并重命名为 `.env`。
   - 填入您的数据库内网 IP、VPC ID、子网 ID、Tushare Token 以及 SMTP 配置。

## 2. 依赖打包 (Layer)
由于项目依赖包（Pandas 等）体积较大，建议使用 **SCF Layer** 部署：
1. **本地打包**:
   ```bash
   mkdir -p layers/python
   pip install -r requirements.txt -t layers/python/
   ```
2. **控制台操作**:
   - 在腾讯云 SCF 控制台 -> 层管理 -> 新建层。
   - 上传 `layers/` 目录的压缩包。
   - 在 `serverless.yml` 中引用该层的名称和版本。

## 3. 一键部署
在项目根目录下执行：
```bash
serverless deploy
```
部署完成后，您可以在腾讯云控制台看到名为 `stock-serverless-collector` 的云函数及关联的定时触发器。

## 4. 连通性测试
在腾讯云控制台点击「测试」，使用以下 JSON 事件触发：
```json
{
  "ts_code": "000001.SZ",
  "trade_date": "2024-05-10",
  "source": "akshare"
}
```
**成功标志**: 
- 控制台返回 `status: success`。
- 数据库 `stock_kline_daily` 产生了对应的记录。
- 您的邮箱收到了「SCF SUCCESS」通知邮件。
