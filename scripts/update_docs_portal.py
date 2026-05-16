# -*- coding: utf-8 -*-

import os
import datetime
from pathlib import Path
from config.portal_template import (
    HTML_TEMPLATE, SECTION_TEMPLATE, GRID_TEMPLATE, 
    CARD_TEMPLATE, DOC_LIST_TEMPLATE, DOC_ITEM_TEMPLATE
)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
GLOBAL_INDEX = PROJECT_ROOT / "docs" / "index.html"
IGNORE_DIRS = {".git", ".agent", ".agents", "scripts", "migrations", "scratch", "logs", "投资指南html"}

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
                        # domains 下通常是 domain/feature_name，提取 feature_name
                        if len(parts) > idx + 2:
                            current_tag = parts[idx + 2].upper()
                        elif len(parts) > idx + 1:
                            current_tag = parts[idx + 1].upper()

                    doc_entry = {
                        "title": file,
                        "path": full_path,
                        "service": current_tag,
                        "date": mtime.strftime("%Y-%m-%d %H:%M")
                    }
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
        
        # Sort global docs by date descending
        self.all_docs.sort(key=lambda x: x["date"], reverse=True)

    def render_global(self):
        """Render the main docs/index.html with Domain grouping."""
        # Group services by domain
        domain_groups = {}
        for svc in self.services:
            domain = svc["domain"]
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(svc)

        content_html = ""
        
        # Render Domains
        icons = ["☁️", "📊", "🛡️", "🔗", "🤖", "📈", "⚙️"]
        icon_idx = 0
        for domain_id in ["data_hub", "quant_engine", "infrastructure", "other"]:
            if domain_id not in domain_groups: continue
            
            svcs = domain_groups[domain_id]
            cards_html = ""
            for svc in svcs:
                rel_url = os.path.relpath(svc["path"] / "index.html", GLOBAL_INDEX.parent)
                cards_html += CARD_TEMPLATE.format(
                    url=rel_url.replace("\\", "/"),
                    icon=icons[icon_idx % len(icons)],
                    title=svc['name'].upper(),
                    desc=f"包含 {len(svc['docs'])} 份文档与实施日志"
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
            title="项目全局最新文档",
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
            local_index = svc["path"] / "index.html"
            
            doc_items_html = ""
            for doc in svc["docs"]:
                rel_path = os.path.relpath(doc["path"], svc["path"])
                doc_items_html += DOC_ITEM_TEMPLATE.format(
                    url=rel_path.replace("\\", "/"),
                    date=doc["date"],
                    tag=doc["service"].upper(),
                    title=doc["title"]
                )
            
            list_html = DOC_LIST_TEMPLATE.format(items=doc_items_html)
            content_html = SECTION_TEMPLATE.format(
                title=f"{svc['name'].upper()} 模块文档归档",
                body=list_html
            )
            
            # Use relative path back to global index
            rel_to_hub = os.path.relpath(GLOBAL_INDEX, svc["path"])
            breadcrumb = '<div class="breadcrumb"><a href="{hub}">Project Hub</a> / {name}</div>'.format(
                hub=rel_to_hub.replace("\\", "/"), 
                name=svc['name'].upper()
            )
            
            full_html = HTML_TEMPLATE.format(
                brand=svc['name'].upper() + " Portal",
                subtitle="Local documentation index",
                title=f"{svc['name']} Docs",
                breadcrumb=breadcrumb,
                content=content_html,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            
            with open(local_index, "w", encoding="utf-8") as f:
                f.write(full_html)

    def run(self):
        self.scan()
        self.render_global()
        self.render_local()
        print(f"Generated global portal: {GLOBAL_INDEX}")

if __name__ == "__main__":
    PortalManager().run()
