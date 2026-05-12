import os
import base64
from dotenv import load_dotenv
from tencentcloud.common import credential
from tencentcloud.scf.v20180416 import scf_client, models

base_path = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_path, '.env'))

secret_id = os.environ.get('TENCENT_SECRET_ID')
secret_key = os.environ.get('TENCENT_SECRET_KEY')
region = os.environ.get('REGION', 'ap-shanghai')
func_name = 'stock-serverless-collector'
layer_name = 'stock-patch-layer'

def deploy_layer_and_bind():
    cred = credential.Credential(secret_id, secret_key)
    client = scf_client.ScfClient(cred, region)
    
    zip_file = os.path.join(base_path, 'layer_patch.zip')
    if not os.path.exists(zip_file):
        print(f"Error: {zip_file} not found. Please run build_patch_layer.py first.")
        return

    print(f"--- 1. Publishing Layer: {layer_name} ---")
    with open(zip_file, 'rb') as f:
        code_base64 = base64.b64encode(f.read()).decode('utf-8')
        
    pub_req = models.PublishLayerVersionRequest()
    pub_req.LayerName = layer_name
    pub_req.CompatibleRuntimes = ["Python3.10"]
    content = models.Code()
    content.ZipFile = code_base64
    pub_req.Content = content
    
    try:
        pub_resp = client.PublishLayerVersion(pub_req)
        new_version = pub_resp.LayerVersion
        print(f"[OK] Layer Published Successfully. Version: {new_version}")
    except Exception as e:
        print(f"[FAIL] Failed to publish layer: {e}")
        return

    print(f"--- 2. Binding Layer to Function: {func_name} ---")
    
    # 获取函数当前配置
    get_req = models.GetFunctionRequest()
    get_req.FunctionName = func_name
    
    try:
        get_resp = client.GetFunction(get_req)
        current_layers = get_resp.Layers or []
        
        # 过滤掉旧版本的同名 Layer，保留其他 Layer，并且只取必需字段
        new_layers = []
        for l in current_layers:
            if l.LayerName != layer_name:
                simple_layer = models.LayerVersionSimple()
                simple_layer.LayerName = l.LayerName
                simple_layer.LayerVersion = l.LayerVersion
                new_layers.append(simple_layer)
        
        # 加入新版本 Layer
        new_layer_req = models.LayerVersionSimple()
        new_layer_req.LayerName = layer_name
        new_layer_req.LayerVersion = new_version
        new_layers.append(new_layer_req)
        
        # 更新函数配置
        update_req = models.UpdateFunctionConfigurationRequest()
        update_req.FunctionName = func_name
        update_req.Layers = new_layers
        
        client.UpdateFunctionConfiguration(update_req)
        print(f"[OK] Function Configuration Updated. Bound to Layer {layer_name} v{new_version}")
        
    except Exception as e:
        print(f"[FAIL] Failed to bind layer to function: {e}")

if __name__ == "__main__":
    deploy_layer_and_bind()
