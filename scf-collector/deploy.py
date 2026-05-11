import os
import zipfile
import base64
from dotenv import load_dotenv

# 加载配置
load_dotenv('.env')
secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-guangzhou')
func_name = 'stock-serverless-collector'

try:
    from tencentcloud.common import credential
    from tencentcloud.scf.v20180416 import scf_client, models
except ImportError:
    print("Error: Tencent Cloud SDK not installed. Run: pip install tencentcloud-sdk-python")
    exit(1)

def package_code():
    """自动打包 index.py 和 shared/ 目录"""
    print("[Package] Packaging code...")
    zip_path = 'code.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 写入入口文件
        zf.write('index.py', 'index.py')
        # 递归写入 shared 目录
        for root, _, files in os.walk('shared'):
            for f in files:
                if f.endswith('.pyc') or '__pycache__' in root:
                    continue
                path = os.path.join(root, f)
                zf.write(path, path)
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

if __name__ == "__main__":
    deploy()
