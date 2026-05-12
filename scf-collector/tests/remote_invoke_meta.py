import os
import json
import uuid
from dotenv import load_dotenv

# 加载配置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-shanghai')

try:
    from tencentcloud.common import credential
    from tencentcloud.scf.v20180416 import scf_client, models
except ImportError:
    print("Error: Tencent Cloud SDK not installed.")
    exit(1)

def invoke_test(op='sync_calendar'):
    """
    远程调用云端 SCF 进行验证
    """
    print(f"[Remote] Invoking stock-scf-meta with op={op}...")
    
    print(f"[Debug] Region: {region}")
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    # Debug: Check if GetFunction works
    try:
        get_req = models.GetFunctionRequest()
        get_req.FunctionName = 'stock-scf-meta'
        get_req.Namespace = 'default'
        client.GetFunction(get_req)
        print("[Debug] GetFunction: Success")
    except Exception as ge:
        print(f"[Debug] GetFunction: Failed - {ge}")
    
    req = models.InvokeRequest()
    req.FunctionName = 'stock-scf-meta'
    req.Namespace = 'default'
    # 模拟 event
    event = {
        "op": op,
        "biz_date": "2026-05-12"
    }
    req.ClientContext = json.dumps(event)
    req.LogType = "Tail" # 获取日志
    
    try:
        resp = client.Invoke(req)
        
        # 优化：将结果保存到 .output 目录
        output_dir = os.path.join(project_root, '.output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        result_path = os.path.join(output_dir, 'invoke_result.json')
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(resp.to_json_string())
            
        print(f"Success: Response saved to {os.path.relpath(result_path, project_root)}")
        print("--- Result Message ---")
        print(resp.Result.RetMsg)
    except Exception as e:
        print(f"Error: Remote invoke failed: {e}")

if __name__ == "__main__":
    import sys
    operation = sys.argv[1] if len(sys.argv) > 1 else 'sync_calendar'
    invoke_test(operation)
