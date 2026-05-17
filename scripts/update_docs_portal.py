# -*- coding: utf-8 -*-

import os
import datetime
import json
import re
from pathlib import Path
from config.portal_template import (
    HTML_TEMPLATE, SECTION_TEMPLATE, GRID_TEMPLATE, 
    CARD_TEMPLATE, DOC_LIST_TEMPLATE, DOC_ITEM_TEMPLATE
)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
GLOBAL_INDEX = PROJECT_ROOT / "docs" / "index.html"
GLOBAL_AI_INDEX = PROJECT_ROOT / "docs" / "docs_portal_index.json"
IGNORE_DIRS = {".git", ".agent", ".agents", "scripts", "migrations", "scratch", "logs"}

# Domain Mapping
DOMAIN_MAP = {
    "scf-collector": "data_hub",
    "tushare-api": "data_hub",
    "baostock-api": "data_hub",
    "akshare-api": "data_hub",
    "stock-manager-api": "data_hub",
    "stock-compute": "quant_engine",
    "monitor-service": "infrastructure",
    "wxch-gateway": "infrastructure",
    "scripts": "infrastructure"
}

DOMAIN_TITLES = {
    "data_hub": "数据采集与存储中心",
    "quant_engine": "量化计算与算法引擎",
    "infrastructure": "基础设施与运维工具",
    "other": "其他业务模块"
}

class PortalManager:
    def __init__(self):
        self.services = []
        self.all_docs = []
        self.kb_docs = [] # To hold *.kb.html, *.pitfall.html, *.summary.html

    def _extract_title_from_html(self, file_path):
        """Extract title from HTML title tag or h1 tag."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Try finding h1 content
                h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
                if h1_match:
                    title = h1_match.group(1).strip()
                    # Clean up emoji and tags
                    title = re.sub(r"<[^>]+>", "", title)
                    return title
                # Try title tag
                title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE)
                if title_match:
                    return title_match.group(1).strip()
        except Exception:
            pass
        return file_path.name

    def _check_deprecation(self, file_path):
        """Check if document has been deprecated/warnings in its markdown counterpart or html."""
        try:
            # Check Markdown first if it exists
            md_path = file_path.with_suffix(".md")
            if md_path.exists():
                with open(md_path, "r", encoding="utf-8") as f:
                    # Only check the first 800 characters for deprecation alerts
                    header = f.read(800)
                    if "[!WARNING]" in header and ("已废弃" in header or "被重构" in header or "已废弃" in header or "已过期" in header or "本方案已在" in header):
                        return True
            
            # Check HTML
            with open(file_path, "r", encoding="utf-8") as f:
                header = f.read(1500)
                # Check for explicit warning text about deprecation
                if "WARNING" in header and ("已废弃" in header or "被重构" in header or "已过期" in header or "本方案已在" in header):
                    return True
        except Exception:
            pass
        return False

    def _scan_html_in_dir(self, directory, tag):
        """Helper to scan HTML files in a directory."""
        docs = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".html") and file != "index.html":
                    full_path = Path(root) / file
                    mtime = datetime.datetime.fromtimestamp(full_path.stat().st_mtime)
                    
                    # 标签自动探测: 优先从 features/ 或 domains/ 路径中提取
                    current_tag = tag
                    parts = full_path.parts
                    if "features" in parts:
                        idx = parts.index("features")
                        if len(parts) > idx + 1:
                            current_tag = parts[idx + 1].upper()
                    elif "domains" in parts:
                        idx = parts.index("domains")
                        if len(parts) > idx + 2:
                            current_tag = parts[idx + 2].upper()
                        elif len(parts) > idx + 1:
                            current_tag = parts[idx + 1].upper()

                    # Check KB / Pitfall / Summary suffix
                    is_kb = False
                    kb_type = None
                    if file.endswith(".kb.html"):
                        is_kb = True
                        kb_type = "kb"
                    elif file.endswith(".pitfall.html"):
                        is_kb = True
                        kb_type = "pitfall"
                    elif file.endswith(".summary.html"):
                        is_kb = True
                        kb_type = "summary"

                    title = self._extract_title_from_html(full_path)
                    deprecated = self._check_deprecation(full_path)

                    doc_entry = {
                        "title": title,
                        "filename": file,
                        "path": full_path,
                        "service": current_tag,
                        "date": mtime.strftime("%Y-%m-%d %H:%M"),
                        "is_kb": is_kb,
                        "kb_type": kb_type,
                        "deprecated": deprecated
                    }
                    
                    if is_kb:
                        self.kb_docs.append(doc_entry)
                    else:
                        docs.append(doc_entry)
                        self.all_docs.append(doc_entry)
        return docs

    def scan(self):
        """Scan for microservices and their documents."""
        # 1. Scan Global Docs folder
        global_docs_dir = PROJECT_ROOT / "docs"
        if global_docs_dir.exists():
            self._scan_html_in_dir(global_docs_dir, "GLOBAL")

        # 2. Scan Microservices
        for item in PROJECT_ROOT.iterdir():
            if item.is_dir() and item.name not in IGNORE_DIRS and item.name != "docs":
                docs_dir = item / "docs"
                logs_dir = item / "implementation_logs"
                
                if docs_dir.exists() or logs_dir.exists():
                    service_info = {
                        "name": item.name,
                        "domain": DOMAIN_MAP.get(item.name, "other"),
                        "path": item,
                        "docs": []
                    }
                    service_info["docs"] = self._scan_html_in_dir(item, item.name)
                    
                    # Sort docs by date descending
                    service_info["docs"].sort(key=lambda x: x["date"], reverse=True)
                    self.services.append(service_info)
        
        # Sort docs
        self.all_docs.sort(key=lambda x: x["date"], reverse=True)
        self.kb_docs.sort(key=lambda x: x["date"], reverse=True)

    def generate_ai_index(self):
        """Generate high-density machine-friendly docs_portal_index.json."""
        index_data = []
        for doc in self.kb_docs + self.all_docs:
            rel_path = os.path.relpath(doc["path"], PROJECT_ROOT).replace("\\", "/")
            index_data.append({
                "title": doc["title"],
                "path": rel_path,
                "type": doc["kb_type"] if doc["is_kb"] else "standard",
                "service": doc["service"],
                "last_modified": doc["date"],
                "deprecated": doc["deprecated"]
            })
        
        with open(GLOBAL_AI_INDEX, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        print(f"Generated AI-Native Index: {GLOBAL_AI_INDEX}")

    def render_global(self):
        """Render the main docs/index.html with Domain grouping and KB library."""
        domain_groups = {}
        for svc in self.services:
            domain = svc["domain"]
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(svc)

        content_html = ""
        
        # Render KB/Pitfall/Summary Section
        if self.kb_docs:
            kb_items_html = ""
            for doc in self.kb_docs:
                # Filter out deprecated in human view if requested, or show warning
                status_suffix = " ⚠️ [已废弃/过期]" if doc["deprecated"] else ""
                rel_url = os.path.relpath(doc["path"], GLOBAL_INDEX.parent)
                
                type_badges = {
                    "kb": "最佳实践",
                    "pitfall": "排障避坑",
                    "summary": "阶段总结"
                }
                badge = type_badges.get(doc["kb_type"], "技术知识")
                
                kb_items_html += DOC_ITEM_TEMPLATE.format(
                    url=rel_url.replace("\\", "/"),
                    date=doc["date"],
                    tag=f"{doc['service']} · {badge}{status_suffix}",
                    title=doc["title"]
                )
            
            kb_list_html = DOC_LIST_TEMPLATE.format(items=kb_items_html)
            content_html += SECTION_TEMPLATE.format(
                title="📚 知识与避坑技术库 (Knowledge Base)",
                body=kb_list_html
            )

        # Render Domains
        icons = ["☁️", "📊", "🛡️", "🔗", "🤖", "📈", "⚙️"]
        icon_idx = 0
        for domain_id in ["data_hub", "quant_engine", "infrastructure", "other"]:
            if domain_id not in domain_groups: continue
            
            svcs = domain_groups[domain_id]
            cards_html = ""
            for svc in svcs:
                rel_url = os.path.relpath(svc["path"] / "docs" / "index.html", GLOBAL_INDEX.parent)
                # Count both standard docs and KB docs
                total_docs = len(svc["docs"]) + sum(1 for d in self.kb_docs if d["service"] == svc["name"].upper())
                cards_html += CARD_TEMPLATE.format(
                    url=rel_url.replace("\\", "/"),
                    icon=icons[icon_idx % len(icons)],
                    title=svc['name'].upper(),
                    desc=f"包含 {total_docs} 份设计文档、最佳实践与实施日志"
                )
                icon_idx += 1
            
            grid_html = GRID_TEMPLATE.format(cards=cards_html)
            content_html += SECTION_TEMPLATE.format(
                title=DOMAIN_TITLES.get(domain_id, "其他模块"),
                body=grid_html
            )

        # Render Recent Docs
        doc_items_html = ""
        for doc in self.all_docs[:15]:
            rel_url = os.path.relpath(doc["path"], GLOBAL_INDEX.parent)
            doc_items_html += DOC_ITEM_TEMPLATE.format(
                url=rel_url.replace("\\", "/"),
                date=doc["date"],
                tag=doc["service"].upper(),
                title=doc["title"]
            )
        
        recent_list_html = DOC_LIST_TEMPLATE.format(items=doc_items_html)
        content_html += SECTION_TEMPLATE.format(
            title="项目全局最新标准文档",
            body=recent_list_html
        )

        full_html = HTML_TEMPLATE.format(
            brand="Project Documentation Portal",
            subtitle="Centralized repository for domains, designs, and implementation logs",
            title="Docs Portal",
            breadcrumb="",
            content=content_html,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        
        with open(GLOBAL_INDEX, "w", encoding="utf-8") as f:
            f.write(full_html)

    def render_local(self):
        """Render local index.html for each microservice."""
        for svc in self.services:
            local_index = svc["path"] / "docs" / "index.html"
            local_index.parent.mkdir(parents=True, exist_ok=True)
            
            # Combine svc standard docs with relevant KB docs
            svc_kb = [d for d in self.kb_docs if d["service"] == svc["name"].upper()]
            combined_docs = svc_kb + svc["docs"]
            combined_docs.sort(key=lambda x: x["date"], reverse=True)

            doc_items_html = ""
            for doc in combined_docs:
                rel_path = os.path.relpath(doc["path"], svc["path"] / "docs")
                status_suffix = " ⚠️ [已废弃/过期]" if doc["deprecated"] else ""
                
                tag = doc["service"].upper()
                if doc["is_kb"]:
                    type_badges = {"kb": "最佳实践", "pitfall": "排障避坑", "summary": "阶段总结"}
                    tag += f" · {type_badges.get(doc['kb_type'], 'KB')}"
                
                doc_items_html += DOC_ITEM_TEMPLATE.format(
                    url=rel_path.replace("\\", "/"),
                    date=doc["date"],
                    tag=tag + status_suffix,
                    title=doc["title"]
                )
            
            list_html = DOC_LIST_TEMPLATE.format(items=doc_items_html)
            content_html = SECTION_TEMPLATE.format(
                title=f"{svc['name'].upper()} 模块文档与技术资产归档",
                body=list_html
            )
            
            # Use relative path back to global index
            rel_to_hub = os.path.relpath(GLOBAL_INDEX, svc["path"] / "docs")
            breadcrumb = '<div class="breadcrumb"><a href="{hub}">Project Hub</a> / {name}</div>'.format(
                hub=rel_to_hub.replace("\\", "/"), 
                name=svc['name'].upper()
            )
            
            full_html = HTML_TEMPLATE.format(
                brand=svc['name'].upper() + " Portal",
                subtitle="Local documentation index & Knowledge assets",
                title=f"{svc['name']} Docs Portal",
                breadcrumb=breadcrumb,
                content=content_html,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            with open(local_index, "w", encoding="utf-8") as f:
                f.write(full_html)

    def run(self):
        self.scan()
        self.generate_ai_index()
        self.render_global()
        self.render_local()
        print(f"Generated global portal: {GLOBAL_INDEX}")

if __name__ == "__main__":
    PortalManager().run()
