#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import datetime
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
    
    <!-- Local Offline Libraries -->
    <script src="{rel_marked_js}"></script>
    <link rel="stylesheet" href="{rel_github_css}">
    <script src="{rel_mermaid_js}"></script>
    
    <!-- Syntax Highlighting (Local) -->
    <link rel="stylesheet" href="{rel_highlight_css}">
    <script src="{rel_highlight_js}"></script>
    
    <style>
        :root {
            --bg: #0a0a0a;
            --surface: #121212;
            --surface-hover: #1a1a1a;
            --border: #222222;
            --accent: #eab308;
            --accent-glow: rgba(234, 179, 8, 0.1);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --font-sans: 'Outfit', 'Noto Sans SC', -apple-system, sans-serif;
            --font-serif: 'Noto Serif SC', serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.7;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }

        /* Subtle background glow */
        body::after {
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
        }

        .sidebar {
            width: 260px;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            border-right: 1px solid var(--border);
            background: var(--bg);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            overflow-y: auto;
            z-index: 100;
        }

        .nav-link {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: color 0.2s;
            padding: 0.5rem;
            border-radius: 6px;
        }
        .nav-link:hover { color: var(--accent); background: var(--surface); }

        .toc-title {
            font-family: var(--font-serif);
            font-size: 1rem;
            color: var(--text-primary);
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding-left: 0.5rem;
        }
        .toc-title::before {
            content: '';
            width: 3px;
            height: 1rem;
            background: var(--accent);
            border-radius: 2px;
        }

        .toc-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }
        .toc-item {
            font-size: 0.8rem;
            line-height: 1.3;
        }
        .toc-item a {
            color: var(--text-muted);
            text-decoration: none;
            transition: all 0.2s;
            display: block;
            padding: 0.4rem 0.5rem;
            border-radius: 4px;
        }
        .toc-item a:hover { color: var(--accent); background: var(--surface); }
        .toc-item.level-3 { margin-left: 0.8rem; border-left: 1px solid var(--border); }

        .container {
            max-width: 860px;
            margin: 0 auto 0 260px;
            padding: 3rem 4rem;
            animation: fadeIn 0.6s ease-out;
        }

        @media (max-width: 1024px) {
            .sidebar { width: 220px; padding: 1rem; }
            .container { margin-left: 220px; padding: 2rem; }
        }

        @media (max-width: 800px) {
            .sidebar { position: static; width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--border); }
            .container { margin-left: 0; padding: 1.5rem; }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        header {
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
        }

        .meta {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .meta::before {
            content: '';
            width: 20px;
            height: 1px;
            background-color: var(--accent);
        }

        h1 {
            font-family: var(--font-serif);
            font-size: 2.2rem;
            font-weight: 900;
            line-height: 1.2;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }

        .markdown-body {
            background: transparent !important;
            color: var(--text-primary) !important;
            font-family: var(--font-sans) !important;
            font-size: 0.95rem !important;
        }

        .markdown-body h2 {
            font-family: var(--font-serif);
            font-size: 1.5rem !important;
            color: var(--accent) !important;
            border-bottom: 1px solid var(--border) !important;
            padding-bottom: 0.5rem !important;
            margin-top: 2.5rem !important;
            scroll-margin-top: 1rem;
        }

        .markdown-body h3 {
            font-family: var(--font-serif);
            font-size: 1.25rem !important;
            color: var(--text-primary) !important;
            margin-top: 2rem !important;
            scroll-margin-top: 1rem;
        }

        .markdown-body p, .markdown-body li {
            font-size: 0.95rem !important;
            color: var(--text-primary) !important;
        }
        
        .markdown-body pre {
            background-color: #1a1b26 !important; /* Match Tokyo Night Dark */
            border: 1px solid var(--border);
            border-radius: 8px !important;
            padding: 0 !important; /* Code internal handles padding */
            margin: 1.2rem 0 !important;
            overflow: hidden;
        }

        .markdown-body pre code {
            background-color: transparent !important;
            padding: 1.2rem !important;
            display: block;
            font-family: var(--font-mono) !important;
            font-size: 0.85rem !important;
            line-height: 1.5;
        }

        .markdown-body blockquote {
            border-left: 3px solid var(--accent) !important;
            background: var(--surface);
            padding: 0.8rem 1.2rem;
            color: var(--text-secondary) !important;
            margin: 1.2rem 0 !important;
        }

        .markdown-body table {
            background: var(--surface);
            font-size: 0.85rem !important;
            margin: 1.2rem 0 !important;
        }

        footer {
            margin-top: 4rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.8rem;
            text-align: center;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

    </style>
</head>
<body>
    <aside class="sidebar">
        <a href="index.html" class="nav-link">
            <span>←</span> 返回目录门户
        </a>
        
        <div class="toc-container">
            <h3 class="toc-title">文档导航</h3>
            <ul class="toc-list" id="toc">
                <!-- TOC items will be injected here -->
            </ul>
        </div>
    </aside>

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

    <script id="markdown-raw" type="text/markdown">__MD_CONTENT__</script>

    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            const rawMd = document.getElementById('markdown-raw').textContent;
            const contentEl = document.getElementById('content');
            const tocEl = document.getElementById('toc');
            
            // Set options for marked
            marked.setOptions({
                gfm: true,
                breaks: true,
                headerIds: true,
                mangle: false,
                highlight: function(code, lang) {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                }
            });

            // Parse Markdown
            contentEl.innerHTML = marked.parse(rawMd);
            
            // Generate TOC
            const headings = contentEl.querySelectorAll('h2, h3');
            headings.forEach((h, index) => {
                if (!h.id) h.id = 'heading-' + index;
                
                const li = document.createElement('li');
                li.className = 'toc-item level-' + h.tagName.toLowerCase().charAt(1);
                
                const a = document.createElement('a');
                a.href = '#' + h.id;
                a.textContent = h.textContent;
                
                li.appendChild(a);
                tocEl.appendChild(li);
            });

            // Handle Mermaid
            if (window.mermaid) {
                mermaid.initialize({ startOnLoad: false, theme: 'dark', useWorker: false });
                document.querySelectorAll('pre code.language-mermaid').forEach(el => {
                    const pre = el.parentElement;
                    const div = document.createElement('div');
                    div.className = 'mermaid';
                    div.textContent = el.textContent;
                    pre.parentElement.replaceChild(div, pre);
                });
                mermaid.run();
            }
        });
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
        print(f"Error: File not found: {input_path}")
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
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Calculate relative paths to local assets
    project_root = Path(__file__).parent.parent.resolve()
    assets_js = project_root / "docs" / "assets" / "js"
    assets_css = project_root / "docs" / "assets" / "css"
    html_dir = output_path.parent.resolve()
    
    rel_marked_js = os.path.relpath(assets_js / "marked.min.js", html_dir).replace('\\', '/')
    rel_mermaid_js = os.path.relpath(assets_js / "mermaid.min.js", html_dir).replace('\\', '/')
    rel_highlight_js = os.path.relpath(assets_js / "highlight.min.js", html_dir).replace('\\', '/')
    
    rel_github_css = os.path.relpath(assets_css / "github-markdown-dark.css", html_dir).replace('\\', '/')
    rel_highlight_css = os.path.relpath(assets_css / "tokyo-night-dark.min.css", html_dir).replace('\\', '/')
    
    html_content = TEMPLATE.format(
        title=display_title,
        display_title=display_title,
        service=service_name,
        date=date_str,
        md_content=md_content,
        rel_marked_js=rel_marked_js,
        rel_mermaid_js=rel_mermaid_js,
        rel_highlight_js=rel_highlight_js,
        rel_github_css=rel_github_css,
        rel_highlight_css=rel_highlight_css
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Successfully converted {input_path.name} to {output_path.name}")
    print(f"Path: {output_path}")

if __name__ == "__main__":
    main()
