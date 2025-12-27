#!/bin/bash
# 补录缺失历史数据的22只老股票

echo "开始补录缺失历史数据的老股票..."

# 这些是IPO在1990s但数据从2024年才开始的股票
stocks=(
    "sh.600867"
    "sh.600868"
    "sh.600869"
    "sh.600871"
    "sh.600872"
    "sh.600873"
    "sh.600874"
    "sh.600875"
    "sh.600876"
    "sh.600877"
    "sh.600879"
    "sh.600880"
    "sh.600881"
    "sh.600882"
    "sh.600883"
    "sh.600884"
    "sh.600885"
    "sh.600886"
    "sh.600887"
    "sh.600888"
    "sh.600889"
    "sh.600892"
)

total=${#stocks[@]}
count=0

for code in "${stocks[@]}"; do
    count=$((count + 1))
    echo "[$count/$total] 补录 $code ..."
    curl -s -X POST "http://localhost:8001/api/v1/sync/kline/${code}?start_date=1990-12-19" | jq -c '.'
    sleep 1  # 避免请求过快
done

echo ""
echo "补录任务已全部提交！请稍后检查同步状态。"
