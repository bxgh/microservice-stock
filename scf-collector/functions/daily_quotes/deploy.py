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
    """自动化配置定时触发器"""
    import json
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    triggers = [
        {
            "name": "DailyKline",
            "cron": "0 30 16 * * * *",
            "payload": {"op": "sync_kline_daily"}
        },
        {
            "name": "DailyAdjFactor",
            "cron": "0 35 16 * * * *",
            "payload": {"op": "sync_adj_factor"}
        },
        {
            "name": "DailyIndex",
            "cron": "0 40 16 * * * *",
            "payload": {"op": "sync_index_daily"}
        }
    ]
    
    print(f"[Trigger] Syncing triggers for {func_name}...")
    for t in triggers:
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
            if "ResourceInUse" in str(e) or "AlreadyExists" in str(e):
                print(f"Info: Trigger {t['name']} already exists. Skipping creation.")
            else:
                print(f"Error: Failed to setup trigger {t['name']}: {e}")

if __name__ == "__main__":
    deploy()
    import time
    print("Waiting for function to be active (10s)...")
    time.sleep(10)
    sync_config()
    setup_triggers()
