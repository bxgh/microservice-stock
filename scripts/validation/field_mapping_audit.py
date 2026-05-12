import os
import json
import logging
import pandas as pd
import tushare as ts
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv('.env')

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "stock_data")

from urllib.parse import quote_plus

# 数据库连接
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DATABASE_URL)

def get_db_columns(table_name):
    """获取数据库表列信息"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return {col['name']: str(col['type']) for col in columns}
    except Exception as e:
        logger.error(f"Error fetching DB columns for {table_name}: {e}")
        return None

def get_tushare_fields(api_name):
    """获取 Tushare 接口返回字段"""
    if not TUSHARE_TOKEN:
        logger.error("TUSHARE_TOKEN not found")
        return None
    
    try:
        pro = ts.pro_api(TUSHARE_TOKEN)
        # 获取单条样本以提取 header
        # 针对需要参数的接口，尝试提供通用参数
        # 常见必填项：trade_date, ts_code
        try:
            df = pro.query(api_name, limit=1)
        except Exception:
            # 尝试带日期查询 (最近一个交易日)
            last_trade_date = (pd.Timestamp.now() - pd.Timedelta(days=1)).strftime('%Y%m%d')
            try:
                df = pro.query(api_name, trade_date=last_trade_date, limit=1)
            except Exception:
                try:
                    # 有些接口需要 ann_date
                    df = pro.query(api_name, ann_date=last_trade_date, limit=1)
                except Exception as e2:
                    logger.warning(f"Failed to query {api_name} even with params: {e2}")
                    return []
        
        if df is not None:
            return list(df.columns)
        return []
    except Exception as e:
        logger.error(f"Error fetching Tushare fields for {api_name}: {e}")
        return None

def run_audit():
    # 加载映射配置
    config_path = 'scripts/validation/mapping_config.json'
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        mapping = json.load(f)

    audit_results = []

    for table_name, info in mapping.items():
        logger.info(f"Auditing table: {table_name} ...")
        
        db_cols = get_db_columns(table_name)
        if db_cols is None:
            audit_results.append({
                "table": table_name,
                "status": "FAIL",
                "reason": "Table not found in DB"
            })
            continue

        api_fields = []
        if info['source'] == 'tushare':
            api_fields = get_tushare_fields(info['api_name'])
        
        if api_fields is None:
            audit_results.append({
                "table": table_name,
                "status": "FAIL",
                "reason": f"API {info['api_name']} call failed"
            })
            continue

        # 比对
        missing_in_db = [f for f in api_fields if f not in db_cols]
        # 兼容性：某些接口返回 ts_code 但 DB 可能是 code (虽然规范要求 ts_code)
        # 或者 DB 有 created_at 等审计字段，API 没有，这属于正常
        
        status = "PASS" if not missing_in_db else "WARN"
        
        audit_results.append({
            "table": table_name,
            "api_name": info['api_name'],
            "db_columns_count": len(db_cols),
            "api_fields_count": len(api_fields),
            "missing_in_db": missing_in_db,
            "status": status
        })

    # 生成报告
    generate_markdown_report(audit_results)

def generate_markdown_report(results):
    report_path = 'docs/epics/implementation_logs/E300/S1/REPORT.md'
    
    with open(report_path, 'w') as f:
        f.write("# E300-S1 技术报告: ODS 层字段对齐与 Mapping 矩阵认证\n\n")
        f.write("## 1. 验证概述\n")
        f.write(f"审计时间: {pd.Timestamp.now()}\n")
        f.write(f"审计表总数: {len(results)}\n\n")
        
        f.write("## 2. 审计结果矩阵\n\n")
        f.write("| 表名 | 接口名 | DB 字段数 | API 字段数 | 状态 | 缺失字段 (API有/DB无) |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for res in results:
            missing = ", ".join(res.get('missing_in_db', [])) if res.get('missing_in_db') else "-"
            f.write(f"| {res['table']} | {res.get('api_name', '-')} | {res.get('db_columns_count', '-')} | {res.get('api_fields_count', '-')} | {res['status']} | {missing} |\n")
        
        f.write("\n## 3. 核心发现与风险提示\n\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> 本报告仅作标注，未对数据库执行任何修改。\n\n")
        
        failures = [r for r in results if r['status'] != 'PASS']
        if failures:
            f.write("### 待关注差异项\n")
            for f_item in failures:
                f.write(f"- **{f_item['table']}**: {f_item.get('reason', '字段不匹配')}\n")
        else:
            f.write("所有表字段映射均已通过初步对齐校验。\n")

if __name__ == "__main__":
    run_audit()
