#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from pathlib import Path

# Premium HTML Template with Modern Aesthetics
TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;700;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Libraries -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css/github-markdown-dark.css">
    <script src="https://cdn.jsdelivr.net/npm/shiki"></script>
    
    <style>
        :root {{
            --bg: #0a0a0a;
            --surface: #121212;
            --surface-hover: #1a1a1a;
            --border: #222222;
            --accent: #eab308;
            --accent-glow: rgba(234, 179, 8, 0.2);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --font-sans: 'Outfit', 'Inter', -apple-system, sans-serif;
            --font-serif: 'Noto Serif SC', serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }}

        /* Subtle background glow */
        body::after {{
            content: '';
            position: fixed;
            top: 0;
            right: 0;
            width: 40vw;
            height: 40vh;
            background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
            z-index: -1;
            filter: blur(100px);
            pointer-events: none;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 4rem 2rem;
            animation: fadeIn 0.8s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        header {{
            margin-bottom: 4rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 2rem;
        }}

        .meta {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .meta::before {{
            content: '';
            width: 24px;
            height: 1px;
            background-color: var(--accent);
        }}

        h1 {{
            font-family: var(--font-serif);
            font-size: 3rem;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            background: linear-gradient(135deg, #fff 0%, #a5a5a5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .markdown-body {{
            background: transparent !important;
            color: var(--text-primary) !important;
            font-family: var(--font-sans) !important;
            font-size: 1.1rem !important;
        }}

        .markdown-body h2, .markdown-body h3, .markdown-body h4 {{
            font-family: var(--font-serif);
            border-bottom: none !important;
            color: var(--text-primary);
            margin-top: 2.5rem !important;
        }}

        .markdown-body h2 {{ font-size: 2rem; color: var(--accent); }}
        
        .markdown-body pre {{
            background-color: var(--surface) !important;
            border: 1px solid var(--border);
            border-radius: 12px !important;
            padding: 1.5rem !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}

        .markdown-body code {{
            background-color: var(--surface-hover) !important;
            color: var(--accent) !important;
            font-family: var(--font-mono) !important;
            border-radius: 4px;
            padding: 0.2rem 0.4rem;
        }}

        .markdown-body pre code {{
            background-color: transparent !important;
            padding: 0 !important;
        }}

        .markdown-body blockquote {{
            border-left: 4px solid var(--accent) !important;
            background: var(--surface);
            padding: 1rem 1.5rem;
            border-radius: 0 8px 8px 0;
            color: var(--text-secondary);
        }}

        .markdown-body table {{
            background: var(--surface);
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            width: 100%;
        }}

        .markdown-body table th, .markdown-body table td {{
            border: 1px solid var(--border) !important;
            padding: 1rem !important;
        }}

        .markdown-body table tr {{
            background: transparent !important;
        }}

        .markdown-body table tr:nth-child(2n) {{
            background: rgba(255,255,255,0.02) !important;
        }}

        footer {{
            margin-top: 6rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.9rem;
            text-align: center;
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: var(--bg); }}
        ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}

        /* TOC - Floating on larger screens */
        @media (min-width: 1400px) {{
            .toc {{
                position: fixed;
                left: 2rem;
                top: 10rem;
                width: 200px;
                font-size: 0.8rem;
                color: var(--text-muted);
            }}
            .toc ul {{ list-style: none; }}
            .toc li {{ margin-bottom: 0.5rem; }}
            .toc a {{ color: inherit; text-decoration: none; transition: color 0.2s; }}
            .toc a:hover {{ color: var(--accent); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="meta">{service} | {date}</div>
            <h1>{display_title}</h1>
        </header>

        <article id="content" class="markdown-body">
            <!-- Loading indicator -->
            <p style="color: var(--text-muted)">正在解析文档内容...</p>
        </article>

        <footer>
            &copy; 2026 MicroStock Project Docs | Generated by Antigravity
        </footer>
    </div>

    <script id="markdown-raw" type="text/markdown">{md_content}</script>

    <script>
        document.addEventListener('DOMContentLoaded', async () => {{
            const rawMd = document.getElementById('markdown-raw').textContent;
            const contentEl = document.getElementById('content');
            
            // Set options for marked
            marked.setOptions({{
                gfm: true,
                breaks: true,
                headerIds: true,
                mangle: false
            }});

            // Parse Markdown
            contentEl.innerHTML = marked.parse(rawMd);
            
            // Re-render math if needed (not implemented here)
            
            // Optional: Highlight code blocks with Shiki
            // Since Shiki is async and requires WASM, we'll keep it simple for now
            // or just use marked's default highlighting
        }});
    </script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description='Convert Markdown to Premium HTML')
    parser.add_argument('input', help='Input Markdown file path')
    parser.add_argument('-o', '--output', help='Output HTML file path')
    
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: File not found: {{input_path}}")
        sys.exit(1)
        
    output_path = Path(args.output) if args.output else input_path.with_suffix('.html')
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    # Extract Title (first # or filename)
    display_title = input_path.stem
    for line in md_content.splitlines():
        if line.startswith('# '):
            display_title = line[2:].strip()
            break
            
    # Extract Service Name (from path)
    service_name = "GLOBAL"
    parts = input_path.parts
    if 'scf-collector' in parts: service_name = "SCF-COLLECTOR"
    elif 'tushare-api' in parts: service_name = "TUSHARE-API"
    # ... add more as needed
    
    date_str = os.popen('date "+%Y-%m-%d %H:%M"').read().strip()
    
    # Escape some chars for JS
    # md_content_escaped = md_content.replace('`', '\\`').replace('$', '\\$')
    # Actually putting it in <script type="text/markdown"> is safer
    
    html_content = TEMPLATE.format(
        title=display_title,
        display_title=display_title,
        service=service_name,
        date=date_str,
        md_content=md_content
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Successfully converted {{input_path.name}} to {{output_path.name}}")
    print(f"Path: {{output_path}}")

if __name__ == "__main__":
    main()
