import os
import subprocess
import zipfile
import shutil
import sys

def build_scf_layer(requirements_file, output_zip, target_dir='python', python_version='3.10'):
    """
    SCF 强约束打包工具：
    1. 强制跨平台下载 Linux Binary (manylinux)
    2. 自动读取 requirements.txt
    3. [强约束] 审计发现 .pyd 文件立即报错
    """
    base_dir = os.getcwd()
    build_root = os.path.join(base_dir, 'temp_build')
    lib_dir = os.path.join(build_root, target_dir)
    
    print(f"--- [SCF Build Tool] Starting Build for {requirements_file} ---")

    # 1. 环境清理
    if os.path.exists(build_root):
        shutil.rmtree(build_root)
    os.makedirs(lib_dir)

    # 2. 强制跨平台安装
    print(f"[Step 1] Installing dependencies for Linux (Platform: manylinux2014_x86_64)...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '-r', requirements_file,
            '-t', lib_dir,
            '--platform', 'manylinux2014_x86_64',
            '--only-binary=:all:',
            '--implementation', 'cp',
            '--python-version', python_version,
            '--no-cache-dir'
        ])
    except subprocess.CalledProcessError as e:
        print(f"\n[CRITICAL ERROR] Pip installation failed. Possible cause: Some packages do not have Linux Wheels on PyPI.")
        sys.exit(1)

    # 3. [核心强约束] 二进制审计
    print(f"[Step 2] Auditing for Windows binaries (.pyd)...")
    pyd_files = []
    for root, _, files in os.walk(lib_dir):
        for f in files:
            if f.lower().endswith('.pyd'):
                pyd_files.append(os.path.join(root, f))
    
    if pyd_files:
        print("\n" + "!"*60)
        print("[AUDIT FAILED] Found Windows binary files in Linux package!")
        for pf in pyd_files:
            print(f"  - {os.path.relpath(pf, lib_dir)}")
        print("!"*60)
        print("\n[ACTION REQUIRED] Please check why these packages are not being downloaded as Linux .so files.")
        print("Build Aborted.")
        sys.exit(1)
    else:
        print("[OK] No Windows binaries found. Audit passed.")

    # 4. 清理无用文件 (dist-info, __pycache__)
    print(f"[Step 3] Cleaning up metadata...")
    for root, dirs, files in os.walk(lib_dir):
        for d in list(dirs):
            if d.endswith('.dist-info') or d == '__pycache__':
                shutil.rmtree(os.path.join(root, d))

    # 5. 打包 ZIP
    print(f"[Step 4] Creating ZIP: {output_zip}...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(build_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, build_root)
                zf.write(full_path, rel_path)

    # 6. 最终清理
    shutil.rmtree(build_root)
    print(f"\n[SUCCESS] SCF Layer built successfully: {output_zip}")

if __name__ == "__main__":
    # 默认路径配置
    req = 'scf-collector/requirements.txt'
    out = 'scf-collector/layer_patch.zip'
    
    if not os.path.exists(req):
        print(f"Error: {req} not found. Run from project root.")
        sys.exit(1)
        
    build_scf_layer(req, out)
