# [Epic E8] 复权因子存储与计算方案重设计

## 背景

当前 `stock_adjust_factor` 存在两个问题：

1. **字段语义错误**：`fore_adjust_factor` 和 `back_adjust_factor` 被设计为独立字段，但前复权因子本质上是动态值（依赖当前最新因子），不能静态存储；SCF 仅填充 `adjust_factor` 导致 `fore_adjust_factor` 为 NULL，下游复权失效。
2. **存储冗余**：SCF 每日全量写入约 5000+ 条，而多数股票的复权因子并未发生变化，记录无意义。

本次重设计的核心判断：**累积后复权因子（Tushare `adj_factor`）是唯一适合持久化的基础量**，前复权价格应在查询时实时计算，不存储前复权因子。

## 目标

- `stock_adjust_factor` 仅存储"变动事件"，记录数从当前量级压缩 90%+ （待实测）
- 字段语义清晰，废弃 `fore_adjust_factor`，`back_adjust_factor` 与 `adjust_factor` 保持一致
- 下游可通过统一公式派生前复权、后复权、不复权三种价格，且结果与 Tushare 官方误差 < $10^{-3}$

## 范围

- `scf-collector`：`dao.py` 中 `save_adj_factor` 方法
- `stock_adjust_factor` 表结构（字段废弃标记）
- 历史数据一次性修复脚本
- 单元测试 & 审计脚本

## 非目标

- **不改动 `KlineService` 及任何下游服务**（本次方案聚焦存储侧正确性，下游读取逻辑作为独立 Story 后续处理）
- 不引入新的中间件或缓存层
- 不处理港股、美股复权逻辑

---

## 核心算法约定

Tushare `adj_factor` 接口返回的是**累积后复权因子** $F$，各复权价格的计算公式如下：

$$P_{\text{back}} = P_{\text{raw}} \times F_{\text{date}}$$

$$P_{\text{fore}} = P_{\text{raw}} \times \frac{F_{\text{date}}}{F_{\text{latest}}}$$

其中 $F_{\text{latest}}$ 为该股票**当前最新交易日**对应的因子值，需在查询时动态获取。

**推论**：

- `back_adjust_factor` = `adjust_factor` = Tushare 的 $F$，可静态存储，历史值不变
- `fore_adjust_factor` 无法静态存储——每次除权事件后，所有历史记录的前复权因子都会变，存储无意义

---

## 3. 用户故事 (User Stories)

采集侧从"每日全量写入"改为"仅写入变动事件"，字段统一为累积后复权因子。

### E8-S1 变动检测写入

**作为** `scf-collector`，**我希望** 在写入复权因子前先比对最新库存值，仅当因子发生变化时才执行 INSERT，**以便** 消除冗余记录，使表中每行都代表一个真实的除权除息事件。

#### 任务

- [x] **E8-S1-T1** 修改 `dao.py` `save_adj_factor`：写入前执行 `SELECT adjust_factor FROM stock_adjust_factor WHERE ts_code = %s ORDER BY adjust_date DESC LIMIT 1`，对比新旧值
- [x] **E8-S1-T2** 仅当 `new_factor != latest_factor`（或该股票无历史记录）时执行 INSERT
- [x] **E8-S1-T3** 浮点比对使用 `abs(new - old) > 1e-8` 判断，避免浮点精度误判

#### 核心代码示意

```python
def save_adj_factor(self, ts_code: str, adjust_date: str, adj_factor: float) -> bool:
    """
    仅在因子发生变化时写入，实现变动点存储。
    返回 True 表示实际写入，False 表示跳过（无变化）。
    """
    sql_latest = """
        SELECT adjust_factor FROM stock_adjust_factor
        WHERE ts_code = %s
        ORDER BY adjust_date DESC
        LIMIT 1
    """
    with self.conn.cursor() as cur:
        cur.execute(sql_latest, (ts_code,))
        row = cur.fetchone()
        if row and abs(row[0] - adj_factor) < 1e-8:
            return False  # 未变化，跳过

        sql_insert = """
            INSERT INTO stock_adjust_factor
                (ts_code, adjust_date, fore_adjust_factor, back_adjust_factor, adjust_factor)
            VALUES (%s, %s, NULL, %s, %s)
        """
        cur.execute(sql_insert, (ts_code, adjust_date, adj_factor, adj_factor))
        self.conn.commit()
        return True
```

> `fore_adjust_factor` 显式写入 `NULL`，标记为废弃字段。

#### 验收标准(AC)

##### AC 1: 幂等性——无除权变化时不产生新记录
- **Given** 数据库中 `600519.SH` 最新 `adjust_factor` = `1.234`
- **When** SCF 采集到今日 `adj_factor` = `1.234` 并调用 `save_adj_factor`
- **Then** `stock_adjust_factor` 中该股票记录数不增加，返回值为 `False`

##### AC 2: 变动点捕获——除权后正常入库
- **Given** 数据库中 `600519.SH` 最新 `adjust_factor` = `1.234`
- **When** SCF 采集到今日 `adj_factor` = `1.356`（发生分红）并调用 `save_adj_factor`
- **Then** 插入一条新记录，`back_adjust_factor` = `adjust_factor` = `1.356`，`fore_adjust_factor` = `NULL`，返回值为 `True`

---

### E8-S2 字段废弃标记

**作为** DB Auditor，**我希望** 在表结构上明确标记 `fore_adjust_factor` 为废弃字段，**以便** 防止后续新代码误读该列。

#### 任务

- [ ] **E8-S2-T1** 执行以下 DDL，为列添加注释

```sql
ALTER TABLE stock_adjust_factor
    MODIFY COLUMN fore_adjust_factor DECIMAL(20, 6) NULL
        COMMENT '已废弃。前复权因子不可静态存储，请用 adjust_factor / latest_adjust_factor 实时计算',
    MODIFY COLUMN back_adjust_factor DECIMAL(20, 6) NULL
        COMMENT '累积后复权因子，与 adjust_factor 同值，保留用于 legacy 兼容';
```

- [ ] **E8-S2-T2** 在 `TABLES_INDEX.md` 中更新字段说明，注明废弃原因和替代方案

#### 验收标准(AC)
##### AC 1: 数据库元数据审计
- **Given** 执行上述 DDL
- **When** `SHOW FULL COLUMNS FROM stock_adjust_factor`
- **Then** `fore_adjust_factor` 的 Comment 包含"已废弃"字样

---

## E8-Stage2: 历史数据修复

一次性脚本，修复存量数据的字段缺失和冗余记录。**按顺序执行，不可跳步。**

### E8-S3 字段回填

**作为** Data Quality Steward，**我希望** 将历史记录中 `fore_adjust_factor IS NULL` 的行的 `back_adjust_factor` 对齐为 `adjust_factor` 值，**以便** 消除字段空值对下游 legacy 查询的影响。

#### 任务

- [ ] **E8-S3-T1** 执行回填 SQL（可分批，每次 10000 行）

```sql
-- 回填 back_adjust_factor（fore 保持 NULL，不回填）
UPDATE stock_adjust_factor
SET back_adjust_factor = adjust_factor
WHERE back_adjust_factor IS NULL
  AND adjust_factor IS NOT NULL
LIMIT 10000;
-- 循环执行直到 affected rows = 0
```

- [ ] **E8-S3-T2** 验证回填结果

```sql
SELECT COUNT(*) AS remaining_nulls
FROM stock_adjust_factor
WHERE back_adjust_factor IS NULL AND adjust_factor IS NOT NULL;
-- 预期结果：0
```

#### 验收标准(AC)
##### AC 1: 存量数据空值审计
- **Given** 执行回填脚本完毕
- **When** 执行上述验证 SQL
- **Then** `remaining_nulls` = 0

---

### E8-S4 冗余记录压缩

**作为** Data Quality Steward，**我希望** 删除 `adjust_factor` 与前一条记录相同的冗余行，仅保留变动点，**以便** 使历史数据符合"变动事件"存储规范。

#### 任务

- [ ] **E8-S4-T1** **执行前备份**

```bash
# 在数据库服务器执行
mysqldump -u root -p your_db stock_adjust_factor \
  > /backup/stock_adjust_factor_$(date +%Y%m%d).sql
```

- [ ] **E8-S4-T2** 通过 Python 脚本逐股票处理（避免大事务锁表）

```python
import pymysql

def compress_adj_factors(conn, ts_code: str) -> int:
    """
    删除 ts_code 中与前一条记录 adjust_factor 相同的冗余行。
    返回删除的行数。
    """
    sql_select = """
        SELECT id, adjust_date, adjust_factor
        FROM stock_adjust_factor
        WHERE ts_code = %s
        ORDER BY adjust_date ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql_select, (ts_code,))
        rows = cur.fetchall()

    ids_to_delete = []
    prev_factor = None
    for row_id, adjust_date, factor in rows:
        if prev_factor is not None and abs(factor - prev_factor) < 1e-8:
            ids_to_delete.append(row_id)
        else:
            prev_factor = factor

    if ids_to_delete:
        sql_delete = "DELETE FROM stock_adjust_factor WHERE id IN ({})".format(
            ','.join(['%s'] * len(ids_to_delete))
        )
        with conn.cursor() as cur:
            cur.execute(sql_delete, ids_to_delete)
        conn.commit()

    return len(ids_to_delete)
```

- [ ] **E8-S4-T3** 获取全量 `ts_code` 列表，循环调用上述函数，记录日志

#### 验收标准(AC)
##### AC 1: 压缩后无相邻重复审计
- **Given** 冗余压缩脚本执行完毕
- **When** 对任意 `ts_code` 查询相邻两行 `adjust_factor` 相同的记录数
- **Then** 结果为 0

##### AC 2: 变动点完整性审计
- **Given** 压缩完成后
- **When** 查询 `600519.SH` 在已知除权日（如 `2023-07-03`）前后的记录
- **Then** 该除权日对应的记录存在，且因子值与 Tushare 原始数据一致

---

## E8-Stage3: 深度审计

### E8-S5 抽样对齐与前复权校验

**作为** Data Quality Steward，**我希望** 对修复后的数据库进行抽样对齐验证，**以便** 确认本地数据与 Tushare 权威数据的一致性。

#### 任务

- [ ] **E8-S5-T1** 随机抽取 100 只活跃股票（含 `600519.SH`、`000001.SZ` 等权重股），调用 Tushare `adj_factor` 接口拉取全量历史，与本地变动点逐行对比

- [ ] **E8-S5-T2** 对 500 个随机历史价格点执行前复权公式校验

```python
def validate_fore_adj(conn, tushare_api, sample_size: int = 500):
    """
    随机抽取样本点，校验前复权计算误差。
    """
    errors = []
    samples = fetch_random_samples(conn, sample_size)  # 随机取 (ts_code, trade_date, raw_close)

    for ts_code, trade_date, raw_close in samples:
        # 本地：取 trade_date 当日因子
        f_date = get_factor(conn, ts_code, trade_date)
        # 本地：取最新因子
        f_latest = get_latest_factor(conn, ts_code)
        local_adj = raw_close * (f_date / f_latest)

        # Tushare 官方前复权收盘价
        tushare_adj = tushare_api.get_adj_close(ts_code, trade_date)

        error = abs(local_adj - tushare_adj) / tushare_adj
        if error > 1e-3:
            errors.append({
                'ts_code': ts_code,
                'trade_date': trade_date,
                'local': local_adj,
                'tushare': tushare_adj,
                'error': error
            })

    return errors
```

- [ ] **E8-S5-T3** 输出审计报告（CSV），记录异常点供人工复核

#### 验收标准(AC)
##### AC 1: 算法实现一致性验证
- **Given** 500 个样本点校验完毕
- **When** 统计误差 > $10^{-3}$ 的样本数
- **Then** 异常率 < 0.2%（即 500 个样本中异常点 ≤ 1 个）

---

## 技术依赖

- Tushare Token 有效，`adj_factor` 接口可正常调用
- `stock_adjust_factor` 表存在 `id`（主键）、`ts_code`、`adjust_date`、`adjust_factor`、`fore_adjust_factor`、`back_adjust_factor` 字段
- MySQL 5.7+，支持窗口函数（`LAG`）

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 压缩脚本误删变动点 | 高 | 低 | E8-S4-T1 执行前强制备份；压缩前后对比变动点总数 |
| Tushare 接口限流导致审计超时 | 中 | 中 | 审计脚本加 sleep(0.5) 控制频率，分批执行 |
| 下游 legacy 代码仍读 `fore_adjust_factor` | 高 | 高 | 本 Epic 不改下游；字段 comment 标记废弃，待独立 Story 修复 |
| 浮点比对阈值 `1e-8` 误判 | 低 | 低 | 人工抽查几只高价股（茅台等）确认因子精度 |

## 里程碑

| 里程碑 | 计划日期 | 交付物 |
|---|---|---|
| M1 | TBD | E8-S1 完成：SCF 变动检测上线 |
| M2 | TBD | E8-S3/S4 完成：历史数据修复 & 压缩 |
| M3 | TBD | E8-S5 完成：审计报告输出，异常率达标 |

## 度量指标

- `stock_adjust_factor` 表总行数（预期压缩后下降 ≥ 90%）
- 每日新增记录数（预期 ≤ 当日实际发生除权股票数，正常市场约 0~50 只）
- 前复权校验异常率 < 0.2%

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-13 | v0.1 | 初稿，基于累积后复权因子重设计方案 | — |

---

## 待确认事项

- [ ] **TBD-1**：`stock_adjust_factor` 是否有 `id` 主键字段（E8-S4 删除逻辑依赖主键）；若无则改用 `(ts_code, adjust_date)` 联合删除
- [ ] **TBD-2**：备份存储路径和保留时长与 DBA 确认
- [ ] **TBD-3**：M1~M3 实际上线时间窗口
