#!/usr/bin/env python3
import re
import sys
import argparse

# 强制 DDL 规范
MANDATORY_FIELDS = [
    ("is_deleted", r"is_deleted\s+TINYINT\(1\)"),
    ("created_at", r"created_at\s+TIMESTAMP"),
    ("updated_at", r"updated_at\s+TIMESTAMP.*ON\s+UPDATE"),
    ("idx_updated_at", r"KEY\s+idx_updated_at\s*\(updated_at\)")
]

MANDATORY_TRIO_SQL = """
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  KEY idx_updated_at (updated_at)
"""

DEFAULT_CHARSET = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC"

# 历史存量表白名单（豁免审计）
LEGACY_WHITELIST = {
    "stock_kline_daily",
    "trade_cal",
    "meta_trading_calendar",
    "ods_stock_daily", # 示例：部分上游同步表可能不带三件套
}

class SchemaEnforcer:
    def __init__(self, ddl_text):
        self.ddl_text = ddl_text
        self.violations = []
        self.table_name = self._extract_table_name()

    def _extract_table_name(self):
        match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[`"]?)([^\s\(`"]+)', self.ddl_text, re.IGNORECASE)
        return match.group(1) if match else "UNKNOWN"

    def audit(self):
        if "CREATE TABLE" not in self.ddl_text.upper():
            return []
        
        # 0. 白名单检查
        if self.table_name in LEGACY_WHITELIST:
            return []

        # 1. 检查三件套
        for field_name, pattern in MANDATORY_FIELDS:
            if not re.search(pattern, self.ddl_text, re.IGNORECASE):
                self.violations.append(f"缺失规范项: {field_name}")

        # 2. 检查字符集
        if "utf8mb4" not in self.ddl_text.lower():
            self.violations.append("字符集未显式声明为 utf8mb4 或配置错误")

        return self.violations

    def get_fix_suggestion(self):
        """生成自动补全建议"""
        if not self.violations:
            return None
        
        # 简单的补全逻辑：在最后一个字段定义后，右括号前，注入三件套
        # 寻找最后一个右括号前的内容
        fixed_ddl = self.ddl_text.strip()
        if fixed_ddl.endswith(';'):
            fixed_ddl = fixed_ddl[:-1].strip()
        
        # 移除原有的字符集尾缀进行重新拼接
        base_ddl = re.sub(r'\)\s*(?:ENGINE|DEFAULT|CHARSET|COLLATE).*$', '', fixed_ddl, flags=re.IGNORECASE | re.DOTALL)
        
        if base_ddl.endswith(')'):
            base_ddl = base_ddl[:-1].rstrip().rstrip(',')
        
        suggestion = f"{base_ddl},\n{MANDATORY_TRIO_SQL.strip()}\n) {DEFAULT_CHARSET};"
        return suggestion

def main():
    parser = argparse.ArgumentParser(description="Schema Enforcer (skill:schema-enforcer)")
    parser.add_argument("--file", help="SQL file to audit")
    parser.add_argument("--ddl", help="Direct DDL string to audit")
    
    args = parser.parse_args()
    
    ddl_content = ""
    if args.file:
        with open(args.file, 'r') as f:
            ddl_content = f.read()
    elif args.ddl:
        ddl_content = args.ddl
    else:
        print("Error: No input provided.")
        sys.exit(1)

    enforcer = SchemaEnforcer(ddl_content)
    violations = enforcer.audit()
    
    print(f"--- Schema Audit Report [Table: {enforcer.table_name}] ---")
    if not violations:
        print("✅ 审核通过：符合 MySQL 5.7 标准化规范。")
    else:
        print("❌ 发现规范违规：")
        for v in violations:
            print(f"  - {v}")
        
        print("\n[!] 修正建议 (Auto-Fix DDL):")
        print(enforcer.get_fix_suggestion())
        sys.exit(1)

if __name__ == "__main__":
    main()
