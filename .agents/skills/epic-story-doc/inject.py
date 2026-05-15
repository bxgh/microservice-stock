#!/usr/bin/env python3
"""
inject.py — Epic-Story 评审台注入脚本
用法: python inject.py <draft.json> [template.html] [output_dir]

说明:
  将 draft.json 的数据注入评审台 HTML 模板，生成自包含的 review_{id}.html。
  默认模板路径: epic-story-reviewer.html（与 inject.py 同目录）
  默认输出目录: 与 draft.json 同目录
"""

import json, sys, os, re
from datetime import datetime

def inject(json_path: str, template_path: str = None, output_dir: str = None):
    # ---- 读取 JSON ----
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[错误] JSON 解析失败: {e}")
            sys.exit(1)

    # ---- 读取模板 ----
    if not template_path:
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'epic-story-reviewer.html')
    if not os.path.exists(template_path):
        print(f"[错误] 模板文件不存在: {template_path}")
        print("请确保 epic-story-reviewer.html 与 inject.py 在同一目录。")
        sys.exit(1)
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # ---- 生成输出路径 ----
    if not output_dir:
        output_dir = os.path.dirname(os.path.abspath(json_path))
    os.makedirs(output_dir, exist_ok=True)

    # 提取文档 ID 用于文件名（优先提取 E{N} 模式，否则取前 15 个字符）
    title = data.get('title', 'review')
    epic_id_match = re.search(r'E\d+', title)
    if epic_id_match:
        safe_title = epic_id_match.group(0)
    else:
        safe_title = re.sub(r'[\s\[\]《》【】/\\:*?"<>|]', '_', title)[:15]
    
    date_str = datetime.now().strftime('%Y%m%d')
    output_path = os.path.join(output_dir, f'review_{safe_title}_{date_str}.html')

    # ---- 注入数据 ----
    # 在 </script> 闭合前插入自动加载逻辑
    data_json = json.dumps(data, ensure_ascii=False)
    inject_script = f"""
// === AUTO-INJECTED BY inject.py ===
(function(){{
  try {{
    const injectedData = {data_json};
    if(document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', ()=>loadDoc(injectedData));
    }} else {{
      loadDoc(injectedData);
    }}
  }} catch(e) {{
    console.error('[inject.py] 数据注入失败:', e);
  }}
}})();
// === END AUTO-INJECTED ===
"""
    # Insert before last </script>
    last_script_close = template.rfind('</script>')
    if last_script_close == -1:
        print("[错误] 模板中未找到 </script> 标签")
        sys.exit(1)
    output_html = template[:last_script_close] + inject_script + template[last_script_close:]

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_html)

    print(f"[完成] 已生成: {output_path}")
    print(f"  文档: {title}")
    print(f"  大小: {os.path.getsize(output_path):,} bytes")
    print(f"  用法: 双击 {os.path.basename(output_path)} 用浏览器打开即可评审")
    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    json_path = sys.argv[1]
    template_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    inject(json_path, template_path, output_dir)
