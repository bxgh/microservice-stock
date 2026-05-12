import os
import sys
import zipfile
import base64
import json
from dotenv import load_dotenv

# 1. 加载配置
base_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(base_path))
load_dotenv(os.path.join(project_root, '.env'))

secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-guangzhou')

# 2. 目标函数名称
func_name = 'stock-scf-meta'

try:
    from tencentcloud.common import credential
    from tencentcloud.scf.v20180416 import scf_client, models
except ImportError:
    print("Error: Tencent Cloud SDK not installed. Run: pip install tencentcloud-sdk-python")
    exit(1)

def package_code():
    """
    打包当前函数的 index.py 和全局 shared/ 目录
    """
    print(f"[Package] Packaging code for {func_name}...")
    zip_path = os.path.join(project_root, '.output', 'meta_code.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 写入入口文件
        source_index = os.path.join(base_path, 'index.py')
        if not os.path.exists(source_index):
            print(f"Error: {source_index} not found!")
            sys.exit(1)
        zf.write(source_index, 'index.py')
        
        # 写入 .env 文件 (确保云端可以加载配置)
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
                rel_path = os.path.relpath(full_path, project_root)
                zf.write(full_path, rel_path)
    return zip_path

def deploy():
    # 1. 打包
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
        # 尝试更新代码
        client.UpdateFunctionCode(req)
        print(f"Success: {func_name} Code Updated Successfully!")
        
    except Exception as e:
        # 检查错误码，兼容不同版本的 SDK 错误表现
        is_not_found = False
        if hasattr(e, 'code') and e.code == 'ResourceNotFound.Function':
            is_not_found = True
        elif "ResourceNotFound" in str(e):
            is_not_found = True

        if is_not_found:
            print(f"Function {func_name} not found. Attempting to create it...")
            create_req = models.CreateFunctionRequest()
            create_req.FunctionName = func_name
            create_req.Runtime = "Python3.10"
            create_req.Handler = "index.main_handler"
            create_req.MemorySize = 256
            create_req.Timeout = 900
            
            # 使用 .env 中的 VPC 配置
            vpc_id = os.environ.get('VPC_ID')
            subnet_id = os.environ.get('SUBNET_ID')
            if vpc_id and subnet_id:
                create_req.VpcConfig = models.VpcConfig()
                create_req.VpcConfig.VpcId = vpc_id
                create_req.VpcConfig.SubnetId = subnet_id
            
            # 基础代码
            with open(zip_file, 'rb') as f:
                create_req.Code = models.Code()
                create_req.Code.ZipFile = base64.b64encode(f.read()).decode('utf-8')
            
            # 绑定 Layers (参考 stock-serverless-collector)
            l1 = models.LayerVersionSimple()
            l1.LayerName = "stock_collector_layer"
            l1.LayerVersion = 2
            l2 = models.LayerVersionSimple()
            l2.LayerName = "stock-patch-layer"
            l2.LayerVersion = 3
            create_req.Layers = [l1, l2]
            
            # 角色
            create_req.Role = "SCF_QcsRole"
            
            # 环境参数同步
            env_vars = [
                "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB",
                "TUSHARE_TOKEN", "VPC_ID", "SUBNET_ID"
            ]
            create_req.Environment = models.Environment()
            create_req.Environment.Variables = []
            for v in env_vars:
                val = os.environ.get(v)
                if val:
                    kv = models.Variable()
                    kv.Key = v
                    kv.Value = str(val)
                    create_req.Environment.Variables.append(kv)
            
            try:
                client.CreateFunction(create_req)
                print(f"Success: {func_name} Created and Deployed Successfully!")
            except Exception as ce:
                print(f"Error: Failed to create function: {ce}")
        else:
            print(f"Error: Deployment failed: {e}")

def sync_config():
    """同步环境变量到云端配置 (针对已有函数)"""
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
    
    # 关键修复：强制同步 VPC 和开启公网访问
    vpc_id = os.environ.get('VPC_ID')
    subnet_id = os.environ.get('SUBNET_ID')
    if vpc_id and subnet_id:
        req.VpcConfig = models.VpcConfig()
        req.VpcConfig.VpcId = vpc_id
        req.VpcConfig.SubnetId = subnet_id
    
    # 开启公网访问 (使用共享公网 IP)
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
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    triggers = [
        {
            "name": "DailyStockList",
            "cron": "0 0 6 * * * *",
            "payload": {"op": "sync_stock_list"}
        },
        {
            "name": "MonthlyCalendar",
            "cron": "0 30 6 1 * * *",
            "payload": {"op": "sync_calendar"}
        },
        {
            "name": "MonthlySWIndustry",
            "cron": "0 30 6 1 * * *",
            "payload": {"op": "sync_sw_industry_member"}
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
                # 如果已存在，尝试更新 (某些环境下需要先删再建，或调用更新接口)
                # 简单处理：提示已存在。如需强制覆盖可增加删除逻辑
                print(f"Info: Trigger {t['name']} already exists. Skipping creation.")
            else:
                print(f"Error: Failed to setup trigger {t['name']}: {e}")

if __name__ == "__main__":
    deploy()
    # 增加等待时间，确保函数状态从 Updating 回到 Active (10秒更稳健)
    import time
    print("Waiting for function to be active (10s)...")
    time.sleep(10)
    sync_config()
    setup_triggers()
