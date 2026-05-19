import os
import zipfile
import base64
from dotenv import load_dotenv

# 加载配置
import sys
base_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(base_path))
load_dotenv(os.path.join(project_root, '.env'))
secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-guangzhou')

# 根据命令行参数决定部署目标
func_name = 'stock-serverless-collector'
if '--test' in sys.argv:
    func_name = 'stock-collector-test'
    print(f"[Mode] Target function: {func_name} (Staging)")
else:
    print(f"[Mode] Target function: {func_name} (Production)")

try:
    from tencentcloud.common import credential
    from tencentcloud.scf.v20180416 import scf_client, models
except ImportError:
    print("Error: Tencent Cloud SDK not installed. Run: pip install tencentcloud-sdk-python")
    exit(1)

def package_code():
    """自动打包 index.py 和全局 shared/ 目录"""
    print("[Package] Packaging code...")
    zip_path = os.path.join(project_root, '.output', 'daily_quotes_code.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 写入入口文件
        index_file = os.path.join(base_path, 'index.py')
        zf.write(index_file, 'index.py')
        
        # 写入 .env 文件
        env_file = os.path.join(project_root, '.env')
        if os.path.exists(env_file):
            zf.write(env_file, '.env')
            
        # 递归写入 shared 目录
        shared_dir = os.path.join(project_root, 'shared')
        for root, _, files in os.walk(shared_dir):
            for f in files:
                if f.endswith('.pyc') or '__pycache__' in root:
                    continue
                full_path = os.path.join(root, f)
                # 计算在 zip 中的相对路径
                rel_path = os.path.relpath(full_path, project_root)
                zf.write(full_path, rel_path)
    return zip_path

def deploy():
    # 1. 自动打包
    zip_file = package_code()
    
    # 2. 初始化客户端
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    # 3. 读取代码并更新
    print(f"[Deploy] Updating code for {func_name} in {region}...")
    with open(zip_file, 'rb') as f:
        code_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    req = models.UpdateFunctionCodeRequest()
    req.FunctionName = func_name
    req.ZipFile = code_base64
    
    try:
        client.UpdateFunctionCode(req)
        print("Success: Code Updated Successfully!")
    except Exception as e:
        print(f"Error: Deployment failed: {e}")

def sync_config():
    """同步环境变量到云端配置"""
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    req = models.UpdateFunctionConfigurationRequest()
    req.FunctionName = func_name
    
    # 同步环境变量
    env_vars = [
        "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB",
        "TUSHARE_TOKEN", "VPC_ID", "SUBNET_ID"
    ]
    req.Environment = models.Environment()
    req.Environment.Variables = []
    for v in env_vars:
        val = os.environ.get(v)
        if val:
            kv = models.Variable()
            kv.Key = v
            kv.Value = str(val)
            req.Environment.Variables.append(kv)
            
    # 强制注入 TZ=Asia/Shanghai 时区环境变量，锁定东八区北京时间
    tz_var = models.Variable()
    tz_var.Key = "TZ"
    tz_var.Value = "Asia/Shanghai"
    req.Environment.Variables.append(tz_var)
    
    # 强制同步 VPC 和开启公网访问
    vpc_id = os.environ.get('VPC_ID')
    subnet_id = os.environ.get('SUBNET_ID')
    if vpc_id and subnet_id:
        req.VpcConfig = models.VpcConfig()
        req.VpcConfig.VpcId = vpc_id
        req.VpcConfig.SubnetId = subnet_id
    
    # 开启公网访问
    req.PublicNetConfig = models.PublicNetConfigIn()
    req.PublicNetConfig.PublicNetStatus = "ENABLE"
    req.PublicNetConfig.EipConfig = models.EipConfigIn()
    req.PublicNetConfig.EipConfig.EipStatus = "DISABLE"
            
    try:
        client.UpdateFunctionConfiguration(req)
        print(f"[Config] Environment variables synchronized for {func_name}")
    except Exception as e:
        print(f"[Config] Error syncing env vars: {e}")

def setup_triggers():
    """自动化配置定时触发器 (修复 UTC 时区差，并自动重建触发器更新配置)"""
    import json
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    # 腾讯云 SCF 定时触发器在中国大陆地域直接采用北京时间 (CST)
    triggers = [
        {
            "name": "DailyKline",
            "cron": "0 30 16 * * * *",  # 对应北京时间 16:30 CST
            "payload": {"op": "sync_kline_daily"}
        },
        {
            "name": "DailyAdjFactor",
            "cron": "0 25 9 * * * *",  # 对应北京时间 09:25 CST (标准盘前因子同步)
            "payload": {"op": "sync_adj_factor"}
        },
        {
            "name": "DailyIndex",
            "cron": "0 40 16 * * * *",  # 对应北京时间 16:40 CST
            "payload": {"op": "sync_index_daily"}
        },
        {
            "name": "IntegrityFailOver",
            "cron": "0 0 17 * * * *",   # 对应北京时间 17:00 CST
            "payload": {"op": "validate_and_failover"}
        },
        {
            "name": "DailyFinancialSheets",
            "cron": "0 0 18 * * * *",   # 对应北京时间 18:00 CST
            "payload": {"op": "sync_financial_sheets"}
        }
    ]
    
    print(f"[Trigger] Syncing triggers for {func_name}...")
    for t in triggers:
        # 1. 尝试删除已存在的触发器以允许更新 Cron 表达式
        try:
            del_req = models.DeleteTriggerRequest()
            del_req.FunctionName = func_name
            del_req.TriggerName = t["name"]
            del_req.Type = "timer"
            client.DeleteTrigger(del_req)
            print(f"[Trigger] Deleted existing trigger: {t['name']}")
        except Exception as de:
            # 忽略不存在触发器时的异常
            pass

        # 2. 创建新触发器
        req = models.CreateTriggerRequest()
        req.FunctionName = func_name
        req.TriggerName = t["name"]
        req.Type = "timer"
        req.TriggerDesc = t["cron"]
        req.CustomArgument = json.dumps(t["payload"])
        
        try:
            client.CreateTrigger(req)
            print(f"Success: Trigger {t['name']} created ({t['cron']})")
        except Exception as e:
            print(f"Error: Failed to setup trigger {t['name']}: {e}")

if __name__ == "__main__":
    deploy()
    import time
    print("Waiting for function to be active (10s)...")
    time.sleep(10)
    sync_config()
    setup_triggers()
