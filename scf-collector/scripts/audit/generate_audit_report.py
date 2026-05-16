import asyncio
import aiomysql
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load env
current_dir = os.path.dirname(os.path.abspath(__file__))
scf_collector_dir = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(os.path.join(scf_collector_dir, '.env'))

def render_html(data):
    task_rows = ""
    for task in data['tasks']:
        task_rows += f"""
        <tr>
            <td>{task['id']}</td>
            <td>{task['task_type']}</td>
            <td><code>{task['ts_code']}</code></td>
            <td>{task['trade_date']}</td>
            <td><span class="error-tag">{task['error_type']}</span></td>
            <td><span class="status status-{task['status'].lower()}">{task['status']}</span></td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>数据对账审计报告 - E12-S1</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --danger-color: #dc2626;
            --success-color: #16a34a;
            --warning-color: #ca8a04;
            --bg-color: #f8fafc;
        }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg-color); color: #1e293b; line-height: 1.5; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
        h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin: 2rem 0; }}
        .card {{ padding: 1.5rem; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .card .label {{ font-size: 0.875rem; color: #64748b; font-weight: 500; }}
        .card .value {{ font-size: 1.875rem; font-weight: 700; margin-top: 0.5rem; }}
        .card.error {{ border-left: 4px solid var(--danger-color); }}
        .card.success {{ border-left: 4px solid var(--success-color); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 2rem; }}
        th {{ background: #f1f5f9; text-align: left; padding: 0.75rem; font-size: 0.875rem; color: #475569; }}
        td {{ padding: 0.75rem; border-bottom: 1px solid #f1f5f9; font-size: 0.875rem; }}
        .status {{ padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 600; font-size: 0.75rem; }}
        .status-pending {{ background: #fef9c3; color: #854d0e; }}
        .status-fixed {{ background: #dcfce7; color: #166534; }}
        .error-tag {{ color: var(--danger-color); font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 数据对账审计报告 (E12-S1)</h1>
        <p>生成时间: {data['now']}</p>
        
        <div class="summary-grid">
            <div class="card error">
                <div class="label">待修复异常 (K-line)</div>
                <div class="value">{data['kline_errors']}</div>
            </div>
            <div class="card warning">
                <div class="label">待修复异常 (Factor)</div>
                <div class="value">{data['factor_errors']}</div>
            </div>
            <div class="card success">
                <div class="label">当前巡检进度</div>
                <div class="value">{data['cursor']}</div>
            </div>
        </div>

        <h2>🚩 待处理任务清单 (Top 50)</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>类型</th>
                    <th>代码</th>
                    <th>日期</th>
                    <th>异常类型</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
                {task_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

async def generate():
    conn = await aiomysql.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT')),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        db=os.getenv('MYSQL_DB'),
        charset='utf8mb4'
    )
    
    async with conn.cursor(aiomysql.DictCursor) as cur:
        # Get statistics
        await cur.execute("SELECT COUNT(*) as cnt FROM meta_task_queue WHERE task_type = 'REPAIR_KLINE' AND status = 'PENDING'")
        kline_errors = (await cur.fetchone())['cnt']
        
        await cur.execute("SELECT COUNT(*) as cnt FROM meta_task_queue WHERE task_type = 'REPAIR_FACTOR' AND status = 'PENDING'")
        factor_errors = (await cur.fetchone())['cnt']
        
        await cur.execute("SELECT config_value FROM meta_config WHERE config_key = 'kline_audit_cursor'")
        cursor_row = await cur.fetchone()
        cursor = cursor_row['config_value'] if cursor_row else "N/A"
        
        # Get tasks
        await cur.execute("SELECT id, task_type, ts_code, trade_date, error_type, status FROM meta_task_queue ORDER BY id DESC LIMIT 50")
        tasks = await cur.fetchall()
        
    conn.close()
    
    data = {
        "now": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "kline_errors": kline_errors,
        "factor_errors": factor_errors,
        "cursor": cursor,
        "tasks": tasks
    }
    
    html_content = render_html(data)
    
    # Save to implementation_logs
    report_dir = os.path.join(scf_collector_dir, 'docs/features/kline_validation/implementation_logs/E12/S1')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'REPORT.html')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report generated at: {report_path}")

if __name__ == "__main__":
    asyncio.run(generate())
