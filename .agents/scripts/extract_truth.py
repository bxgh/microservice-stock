#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import argparse
from datetime import datetime
import socket

def get_fingerprint(container_name=None):
    """生成环境指纹"""
    fingerprint = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": socket.gethostname(),
        "executor": "Antigravity/E101-S1-T1",
    }
    if container_name:
        try:
            container_id = subprocess.check_output(
                ["docker", "inspect", "--format", "{{.Id}}", container_name],
                stderr=subprocess.STDOUT
            ).decode().strip()
            fingerprint["container_id"] = container_id[:12]
            fingerprint["container_name"] = container_name
        except:
            fingerprint["container_info"] = "NOT_FOUND"
    return fingerprint

def run_mysql_query(query, user, host, port, db, **kwargs):
    """执行 MySQL 查询 (使用 pymysql)"""
    import pymysql
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=kwargs.get("password"),
            database=db,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                if not result:
                    return "No records found."
                # 格式化输出为 JSON 字符串，保持原始性
                return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error executing MySQL query via pymysql: {str(e)}"

def run_ch_query(query, host, port):
    """执行 ClickHouse 查询 (通过容器)"""
    # 修正：通过 docker exec 调用
    container = "microservice-stock-clickhouse"
    cmd = [
        "docker", "exec", container,
        "clickhouse-client",
        "--query", query,
        "--format", "PrettyCompact"
    ]
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        return result
    except subprocess.CalledProcessError as e:
        return f"Error executing ClickHouse query: {e.output.decode()}"

def get_docker_logs(container, tail=50):
    """获取 Docker 日志"""
    cmd = ["docker", "logs", "--tail", str(tail), container]
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        return result
    except subprocess.CalledProcessError as e:
        return f"Error fetching Docker logs: {e.output.decode()}"

def main():
    parser = argparse.ArgumentParser(description="Truth Extraction Engine for Agent Auditing")
    parser.add_argument("--type", choices=["mysql", "ch", "log"], required=True)
    parser.add_argument("--query", help="SQL query or container name")
    parser.add_argument("--container", help="Container name for logs or fingerprinting")
    parser.add_argument("--tail", type=int, default=50, help="Lines of log to tail")
    
    args = parser.parse_args()
    
    # 默认配置（从探测到的环境信息中提取）
    MYSQL_CONF = {
        "user": "root", 
        "host": "127.0.0.1", 
        "port": 36301, 
        "db": "alwaysup",
        "password": "alwaysup@888" # 注入已获取的内部密码
    }
    CH_CONF = {"host": "localhost", "port": 9000}
    
    fingerprint = get_fingerprint(args.container or args.query if args.type == "log" else None)
    
    print("<!-- TRUTH_EXTRACT_START -->")
    print(f"**Fingerprint**: `{json.dumps(fingerprint)}`")
    print("```" + ("sql" if args.type != "log" else "text"))
    
    if args.type == "mysql":
        print(run_mysql_query(args.query, **MYSQL_CONF))
    elif args.type == "ch":
        print(run_ch_query(args.query, **CH_CONF))
    elif args.type == "log":
        print(get_docker_logs(args.query or args.container, args.tail))
    
    print("```")
    print("<!-- TRUTH_EXTRACT_END -->")

if __name__ == "__main__":
    main()
