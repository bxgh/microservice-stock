import re
import os
import sys
import json
from datetime import datetime
import html

def format_content(text):
    if not text: return ""
    # 转义 HTML 基础字符防止注入，但要小心处理后续的标签
    # 这里简单处理：先转义，再把我们的特定模式换回来
    text = html.escape(text)
    
    # 处理代码块: ```lang\ncode\n```
    # 使用 <div> 包装以便于样式控制和添加语言标签
    def replace_code(m):
        lang = m.group(1).strip().lower() if m.group(1) else "txt"
        code = m.group(2).strip()
        if lang == "mermaid":
            return f'<div class="block-mermaid"><div class="mermaid">{code}</div></div>'
        return f'<div class="code-wrapper" data-lang="{lang}"><pre><code class="language-{lang}">{code}</code></pre><button class="copy-btn" onclick="copyCode(this)">Copy</button></div>'
    
    # 更加宽松的正则，不强制要求结尾有换行
    text = re.sub(r'```(\w+)?\s*\n(.*?)\s*```', replace_code, text, flags=re.S)
    
    # 处理行内代码 `code`
    text = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', text)
    
    # 处理加粗 **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    return text.strip()

def parse_ac_block(story, header, body):
    ac = {
        "id": "",
        "title": header,
        "given": "",
        "when": "",
        "then": ""
    }
    # 提取 ID (如 AC1 或 ##### AC 1)
    id_m = re.search(r'AC\s*(\d+)', header)
    if id_m: ac["id"] = f"AC{id_m.group(1)}"
    
    # 提取 GWT (Given-When-Then)
    # 匹配 - **Given** ... 或 - Given ...
    given_m = re.search(r'[-\*]\s*\*\*(?:Given|前提)\*\*\s*[:：]?\s*(.*)', body, re.I)
    when_m = re.search(r'[-\*]\s*\*\*(?:When|当)\*\*\s*[:：]?\s*(.*)', body, re.I)
    then_m = re.search(r'[-\*]\s*\*\*(?:Then|那么)\*\*\s*[:：]?\s*(.*)', body, re.I)
    
    # 兼容不带加粗的情况
    if not given_m: given_m = re.search(r'[-\*]\s*(?:Given|前提)\s*[:：]?\s*(.*)', body, re.I)
    if not when_m: when_m = re.search(r'[-\*]\s*(?:When|当)\s*[:：]?\s*(.*)', body, re.I)
    if not then_m: then_m = re.search(r'[-\*]\s*(?:Then|那么)\s*[:：]?\s*(.*)', body, re.I)

    if given_m: ac["given"] = format_content(given_m.group(1))
    if when_m: ac["when"] = format_content(when_m.group(1))
    if then_m: ac["then"] = format_content(then_m.group(1))
    
    story["acs"].append(ac)

def parse_epic(md_path, template_path=None):
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found")
        return

    # 默认模板路径处理
    if not template_path:
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.html')
    
    if not os.path.exists(template_path):
        print(f"Error: Template {template_path} not found")
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 重要：统一换行符，解决 Windows 兼容性
    content = content.replace('\r\n', '\n')

    data = {
        "epic_id": "E0",
        "title": "Epic Review",
        "sections": [],
        "tbds": []
    }

    # 1. 提取 Epic ID (支持 # [Epic E8], # E8_, # E8 )
    id_patterns = [
        r'#\s*\[Epic\s+([A-Z0-9]+)\]',
        r'#\s*([A-Z0-9]+)_',
        r'#\s*([A-Z0-9]+)\s+'
    ]
    for p in id_patterns:
        m = re.search(p, content)
        if m:
            data["epic_id"] = m.group(1)
            break
    
    # 提取标题
    title_match = re.search(r'#\s+(.*)', content)
    if title_match:
        data["title"] = title_match.group(1).strip()

    # 2. 分割出各个 H2 区域
    # 使用 \n\s*##\s+ 提高容错
    h2_sections = re.split(r'\n\s*##\s+', '\n' + content)[1:]
    for h2_sec in h2_sections:
        lines = h2_sec.split('\n')
        h2_title = lines[0].strip()
        h2_body = '\n'.join(lines[1:])
        
        section = {"title": h2_title, "content": "", "stories": []}
        
        # 提取 H2 内容直到第一个 H3
        h2_main_match = re.match(r'(.*?)(?=\n\s*###\s+|$)', h2_body, re.S)
        if h2_main_match:
            section["content"] = format_content(h2_main_match.group(1))

        # 3. 解析 H3 Stories
        h3_blocks = re.split(r'\n\s*###\s+', '\n' + h2_body)[1:]
        for h3_block in h3_blocks:
            h3_lines = h3_block.split('\n')
            h3_header = h3_lines[0].strip()
            h3_content = '\n'.join(h3_lines[1:])
            
            # 匹配 "E8-S1"
            id_match = re.match(r'([A-Z0-9]+-S\d+)', h3_header)
            if not id_match: continue
            
            story = {
                "id": id_match.group(1),
                "title": h3_header.replace(id_match.group(0), '').strip(),
                "desc": "",
                "tasks": [],
                "acs": []
            }
            
            # 提取描述 (作为...以便...)
            desc_m = re.search(r'(\*\*作为\*\*.*?\*\*以便\*\*.*?)(\n|$)', h3_content, re.S)
            if desc_m: story["desc"] = desc_m.group(1).strip()

            # 提取所有 H4 区域并根据标题分类
            h4_blocks = re.split(r'\n\s*####\s+', '\n' + h3_content)[1:]
            for h4_block in h4_blocks:
                h4_lines = h4_block.split('\n')
                h4_header = h4_lines[0].strip()
                h4_body = '\n'.join(h4_lines[1:]).strip()
                
                if '任务' in h4_header:
                    task_items = re.split(r'\n\s*[-\*]\s*\[[x\s]\]\s*', '\n' + h4_body)[1:]
                    for t in task_items:
                        t = t.strip()
                        if not t: continue
                        id_m = re.search(r'([A-Z0-9-]*T\d+)', t)
                        tid = id_m.group(1) if id_m else f"{story['id']}-T{len(story['tasks'])+1}"
                        story["tasks"].append({"id": tid, "text": format_content(t)})
                elif '验收标准' in h4_header:
                    if '##### ' in h4_body:
                        ac_sub = re.split(r'\n\s*#####\s+', '\n' + h4_body)[1:]
                        for ac_b in ac_sub:
                            alines = ac_b.strip().split('\n')
                            parse_ac_block(story, alines[0].strip(), '\n'.join(alines[1:]))
                else:
                    # 其他 H4 章节（如 核心代码示意）拼接到描述中
                    extra_desc = f"\n<div class='extra-section'><strong>{h4_header}</strong>\n{format_content(h4_body)}</div>"
                    story["desc"] += extra_desc
            
            section["stories"].append(story)
        
        if section["stories"] or section["content"]:
            data["sections"].append(section)

    # 4. 待确认事项
    tbd_m = re.search(r'##\s*待确认事项\n(.*?)(?=\n\s*##|$)', content, re.S)
    if tbd_m:
        for line in tbd_m.group(1).strip().split('\n'):
            m = re.search(r'TBD-(\d+)', line)
            if m: data["tbds"].append({"id": f"TBD-{m.group(1)}", "text": line.strip()})

    # 生成 HTML
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 使用 lambda 避免 re.sub 自动解析 JSON 字符串中的反斜杠（如 \n 变为换行）
    html = re.sub(r'{{\s*EPIC_DATA\s*}}', lambda m: json.dumps(data, ensure_ascii=False), template)
    
    output_dir = os.path.join(os.path.dirname(md_path), f"implementation_logs/{data['epic_id']}")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"review_{data['epic_id']}.html")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"[{data['epic_id']}] Successfully parsed {len(data['sections'])} sections and {sum(len(s['stories']) for s in data['sections'])} stories.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_epic.py <md_path> [template_path]")
    else:
        arg_template = sys.argv[2] if len(sys.argv) > 2 else None
        parse_epic(sys.argv[1], arg_template)
