#!/usr/bin/env python3
import os
import re
import sys
import argparse

# 核心禁令配置 (来自 AGENTS.md Section 3.2)
FORBIDDEN_TERMS = {
    "stock_code": "应使用 ts_code (VARCHAR(20))",
    "dt": "应使用 trade_date (DATE)",
    "t_date": "应使用 trade_date (DATE)",
    "pct": "应使用 pct_chg (DECIMAL(10,6))",
    "change_pct": "应使用 pct_chg",
    "vol": "成交额应使用 amount (DECIMAL(20,2)), 成交量应使用 volume (BIGINT)",
    "volume_hand": "成交量必须使用股为单位 (BIGINT)",
    "ctime": "应使用 created_at",
    "mtime": "应使用 updated_at",
    "create_time": "应使用 created_at",
    "is_del": "应使用 is_deleted",
    "deleted": "应使用 is_deleted",
}

MANDATORY_FILTERS = ["is_deleted"]

class SQLValidator:
    def __init__(self, file_path):
        self.file_path = file_path
        self.violations = []

    def check_line(self, line_no, content):
        # 移除行内注释以防止干扰检查 (支持 -- 和 #)
        clean_content = re.sub(r'(--|#).*$', '', content)
        
        # 识别 SQL 模式 (识别 SELECT/UPDATE/DELETE)
        sql_match = re.search(r'(SELECT|UPDATE|DELETE)\s+.*', clean_content, re.IGNORECASE)
        
        if sql_match:
            operation = sql_match.group(1).upper()
            sql_text = clean_content.lower()
            
            # 1. 检查软删除过滤
            if not any(f in sql_text for f in MANDATORY_FILTERS):
                # 排除 information_schema 和 TRUNCATE 逻辑(如果以字符串形式出现)
                if "information_schema" not in sql_text and "truncate" not in sql_text:
                    self.violations.append({
                        "line": line_no,
                        "type": "MISSING_SOFT_DELETE",
                        "detail": f"{operation} 语句中缺失 is_deleted = 0 过滤",
                        "snippet": content.strip()
                    })

            # 2. 检查命名规范
            for term, suggestion in FORBIDDEN_TERMS.items():
                if term in sql_text:
                    if f" {term} " in f" {sql_text} " or f".{term}" in sql_text:
                        self.violations.append({
                            "line": line_no,
                            "type": "FORBIDDEN_NAMING",
                            "detail": f"使用了禁用字段 '{term}', {suggestion}",
                            "snippet": content.strip()
                        })

    def check_units(self, line_no, content):
        """检查单位陷阱 (量纲审计)"""
        # 1. 针对 amount 的审计 (必须是元)
        if "amount" in content.lower():
            if re.search(r'amount\s*[/]\s*(1000|1e3|10000|1e4)', content):
                self.violations.append({
                    "line": line_no,
                    "type": "UNIT_TRAP_RISK",
                    "detail": "检测到对 amount 进行千元/万元缩放，amount 必须统一为'元'",
                    "snippet": content.strip()
                })
        
        # 2. 针对 pct_chg 的审计 (必须是小数)
        if "pct_chg" in content.lower():
            if re.search(r'pct_chg\s*[*]\s*100', content):
                self.violations.append({
                    "line": line_no,
                    "type": "UNIT_TRAP_RISK",
                    "detail": "检测到对 pct_chg 进行百分比化处理，pct_chg 必须统一为'小数'",
                    "snippet": content.strip()
                })

        # 3. 针对 ETF 净申购金额的审计 (必须乘 1e8)
        if "share_chg" in content.lower() or "nav" in content.lower():
            if "1e8" not in content and "100000000" not in content:
                self.violations.append({
                    "line": line_no,
                    "type": "UNIT_TRAP_RISK",
                    "detail": "检测到 ETF 净申购计算，缺失 1e8 缩放因子 (单位应为元)",
                    "snippet": content.strip()
                })

    def validate(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_no, line in enumerate(f, 1):
                    self.check_line(line_no, line)
                    self.check_units(line_no, line)
        except Exception as e:
            print(f"Error reading {self.file_path}: {e}")
        
        return self.violations

def main():
    parser = argparse.ArgumentParser(description="Static Data Auditor (skill:data-validator)")
    parser.add_argument("target", help="File or directory to scan")
    args = parser.parse_args()

    targets = []
    if os.path.isfile(args.target):
        targets = [args.target]
    else:
        for root, _, files in os.walk(args.target):
            for f in files:
                if f.endswith(".py") or f.endswith(".sql"):
                    targets.append(os.path.join(root, f))

    print(f"--- Data Validator Report ---")
    print(f"Target: {args.target}")
    
    total_found = 0
    for target in targets:
        validator = SQLValidator(target)
        violations = validator.validate()
        if violations:
            total_found += len(violations)
            print(f"\n[!] File: {target}")
            for v in violations:
                print(f"    L{v['line']}: [{v['type']}] {v['detail']}")
                print(f"       Code: {v['snippet']}")

    print(f"\nSummary: Found {total_found} violations.")
    if total_found > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
