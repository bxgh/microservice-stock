import os
import sys
import zipfile
import base64
import json
from dotenv import load_dotenv

# 1. 加载全局配置
base_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(base_path))
load_dotenv(os.path.join(project_root, '.env'))

secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-shanghai')

# 2. 目标函数名称
func_name = 'stock-policy-collector'

try:
    from tencentcloud.common import credential
    from tencentcloud.scf.v20180416 import scf_client, models
except ImportError:
    print("Error: Tencent Cloud SDK not installed. Run: pip install tencentcloud-sdk-python")
    exit(1)

def package_code():
    """打包入口 index.py、全局 shared/ 目录和 .env 配置文件"""
    print(f"[Package] Packaging code for {func_name}...")
    zip_dir = os.path.join(project_root, '.output')
    if not os.path.exists(zip_dir):
        os.makedirs(zip_dir)
        
    zip_path = os.path.join(zip_dir, 'policy_collector_code.zip')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 写入入口文件
        source_index = os.path.join(base_path, 'index.py')
        if not os.path.exists(source_index):
            print(f"Error: {source_index} not found!")
            sys.exit(1)
        zf.write(source_index, 'index.py')
        
        # 写入 .env 配置文件
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
    
    # 3. 检测函数是否存在及其当前状态
    exists = False
    print(f"[Deploy] Checking if function {func_name} exists...")
    try:
        get_req = models.GetFunctionRequest()
        get_req.FunctionName = func_name
        get_resp = client.GetFunction(get_req)
        exists = True
        status = get_resp.Status
        print(f"Function {func_name} exists. Current status: {status}")
    except Exception as e:
        is_not_found = False
        if hasattr(e, 'code') and e.code == 'ResourceNotFound.Function':
            is_not_found = True
        elif "ResourceNotFound" in str(e):
            is_not_found = True
            
        if not is_not_found:
            print(f"Error checking function existence: {e}")
            sys.exit(1)
            
    # 4. 如果存在但正处于 Creating/Updating 状态，轮询直至 Active
    if exists:
        import time
        while True:
            try:
                get_req = models.GetFunctionRequest()
                get_req.FunctionName = func_name
                get_resp = client.GetFunction(get_req)
                status = get_resp.Status
                print(f"[Deploy] Checking status: {status}")
                if status == "Active":
                    break
                elif status in ["Failed", "CreateFailed"]:
                    print(f"Error: Function is in failed state: {status}")
                    sys.exit(1)
            except Exception as ge:
                print(f"Error checking status during deploy: {ge}")
            time.sleep(5)
            
        # 进入 Active，开始更新代码
        print(f"[Deploy] Updating code for {func_name}...")
        with open(zip_file, 'rb') as f:
            code_base64 = base64.b64encode(f.read()).decode('utf-8')
        req = models.UpdateFunctionCodeRequest()
        req.FunctionName = func_name
        req.ZipFile = code_base64
        try:
            client.UpdateFunctionCode(req)
            print(f"Success: {func_name} Code Updated Successfully!")
        except Exception as ue:
            print(f"Error updating code: {ue}")
            sys.exit(1)
            
    else:
        # 不存在，创建函数
        print(f"Function {func_name} not found. Creating function...")
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
        
        # 绑定核心依赖 Layer
        l1 = models.LayerVersionSimple()
        l1.LayerName = "stock_collector_layer"
        l1.LayerVersion = 2
        l2 = models.LayerVersionSimple()
        l2.LayerName = "stock-patch-layer"
        l2.LayerVersion = 13
        create_req.Layers = [l1, l2]
        
        # 基础角色
        create_req.Role = "SCF_QcsRole"
        
        # 注入环境变量
        env_vars = [
            "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB",
            "TUSHARE_TOKEN", "VPC_ID", "SUBNET_ID",
            "SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_RECEIVER",
            "SCT_KEY", "DEEPSEEK_API_KEY", "LLM_BASE_URL", "LLM_DAILY_COST_LIMIT_CNY"
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
            sys.exit(1)

def sync_config():
    """同步环境变量、VPC 与公网出口"""
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    req = models.UpdateFunctionConfigurationRequest()
    req.FunctionName = func_name
    
    env_vars = [
        "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB",
        "TUSHARE_TOKEN", "VPC_ID", "SUBNET_ID",
        "SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_RECEIVER",
        "SCT_KEY", "DEEPSEEK_API_KEY", "LLM_BASE_URL", "LLM_DAILY_COST_LIMIT_CNY"
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
    
    vpc_id = os.environ.get('VPC_ID')
    subnet_id = os.environ.get('SUBNET_ID')
    if vpc_id and subnet_id:
        req.VpcConfig = models.VpcConfig()
        req.VpcConfig.VpcId = vpc_id
        req.VpcConfig.SubnetId = subnet_id
    
    # 强制开启公网访问 (保证 VPC 环境下仍可调用 Tushare 与 DeepSeek API)
    req.PublicNetConfig = models.PublicNetConfigIn()
    req.PublicNetConfig.PublicNetStatus = "ENABLE"
    req.PublicNetConfig.EipConfig = models.EipConfigIn()
    req.PublicNetConfig.EipConfig.EipStatus = "DISABLE"
    
    # 强制同步最新 Layers 绑定，让 openai 和 aiosmtplib 在存量函数中立即生效
    l1 = models.LayerVersionSimple()
    l1.LayerName = "stock_collector_layer"
    l1.LayerVersion = 2
    l2 = models.LayerVersionSimple()
    l2.LayerName = "stock-patch-layer"
    l2.LayerVersion = 13
    req.Layers = [l1, l2]
            
    try:
        client.UpdateFunctionConfiguration(req)
        print(f"[Config] Environment variables and network synchronized for {func_name}")
    except Exception as e:
        print(f"[Config] Error syncing config: {e}")

def setup_triggers():
    """配置每 30 分钟触发一次的高频政策采集 Timer 触发器"""
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    t = {
        "name": "PolicyCollector30MinTimer",
        "cron": "0 */30 * * * * *",
        "payload": {"op": "collect_policies"}
    }
    
    print(f"[Trigger] Syncing triggers for {func_name}...")
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
    
    # 再次进行配置阶段的安全检测
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    print(f"Waiting for function {func_name} to become Active...")
    import time
    while True:
        try:
            get_req = models.GetFunctionRequest()
            get_req.FunctionName = func_name
            get_resp = client.GetFunction(get_req)
            status = get_resp.Status
            print(f"Current function status: {status}")
            if status == "Active":
                print("Function is now Active!")
                break
            elif status in ["Failed", "CreateFailed"]:
                print(f"Error: Function creation failed with status: {status}")
                sys.exit(1)
        except Exception as ge:
            print(f"Error checking function status: {ge}")
        time.sleep(5)
        
    sync_config()
    setup_triggers()
