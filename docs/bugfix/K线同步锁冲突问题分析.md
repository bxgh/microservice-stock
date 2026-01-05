# K线同步锁冲突问题分析报告

**问题发现时间**: 2026-01-05 22:50  
**影响范围**: 每日K线增量同步任务  
**严重程度**: 🔴 高 (导致数据完整性问题)

---

## 📋 问题现象

2026-01-05 18:30:00 执行的每日综合同步任务中,K线数据仅同步了1只股票(sh.600000),其余5467只股票未同步,数据完整度仅为 **0.02%**。

### 日志证据

```log
2026-01-05 18:30:00,001 - app.scheduler.jobs - INFO - >>> 阶段 1/2: 正在执行逐日 K 线增量补齐...
2026-01-05 18:30:00,025 - baostock-api.service - INFO - 【增量同步】启动。目标日期: 2026-01-05
2026-01-05 18:30:00,104 - baostock-api.service - INFO - 同步完成: sh.600000, 数量=1, 耗时=78ms
2026-01-05 18:30:09,894 - baostock-api.service - INFO - 日期 2026-01-05 存在部分缺失 (1/5468)，触发补齐...
2026-01-05 18:30:09,894 - baostock-api.service - INFO - 触发 2026-01-05 全市场缺口补齐程序...
2026-01-05 18:30:09,895 - baostock-api.service - WARNING - 全市场同步任务已在运行中  ⚠️
2026-01-05 18:30:09,895 - app.scheduler.jobs - INFO - >>> 阶段 2/2: 正在执行最新复权因子计算与同步...
```

---

## 🔍 根本原因分析

### 问题1: 双重锁检查逻辑缺陷 ⚠️

**文件**: `baostock-api/app/services/baostock_service.py`

#### 代码位置1: `sync_daily_increment()` (第124-173行)

```python
async def sync_daily_increment(self, target_date: Optional[str] = None) -> Dict[str, Any]:
    """全市场每日增量同步 (符合收盘批处理原则)"""
    # 1. 确定目标日期并立即执行运行状态保护 (原子操作)
    async with self.lock:
        if self._sync_status["running"]:
            return {"success": False, "error": "任务已在运行"}
        self._sync_status["running"] = True  # ✅ 设置锁
        self._sync_status["start_time"] = time.time()
    
    try:
        # ... 抽样校验、统计检查 ...
        
        # 4. 执行定向增量同步
        logger.info(f"触发 {sync_date} 全市场缺口补齐程序...")
        await self.sync_all_stocks_kline(start_date=sync_date)  # ⚠️ 调用子方法
        
        return {"success": True, "message": "同步任务已启动", "target_date": sync_date}
    except Exception as e:
        logger.error(f"【增量同步】执行异常: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        async with self.lock:
            self._sync_status["running"] = False  # ✅ 释放锁
```

#### 代码位置2: `sync_all_stocks_kline()` (第492-671行)

```python
async def sync_all_stocks_kline(self, start_date: str = "1990-12-19") -> None:
    """同步全市场股票 K 线 (支持断点续传)"""
    if self._sync_status["running"]:  # ❌ 检查锁状态
        logger.warning("全市场同步任务已在运行中")
        return  # ❌ 直接返回,不执行任何操作!
    
    self._sync_status["running"] = True  # ⚠️ 再次设置锁
    logger.info("开始获取全市场股票列表...")
    
    # ... 后续同步逻辑 ...
```

### 🔴 问题本质

这是一个**经典的双重检查锁定(Double-Checked Locking)反模式**问题:

1. **父方法** `sync_daily_increment()` 在第130行设置 `self._sync_status["running"] = True`
2. **父方法** 在第165行调用 `await self.sync_all_stocks_kline(start_date=sync_date)`
3. **子方法** `sync_all_stocks_kline()` 在第494行检查到 `self._sync_status["running"]` 已经为 `True`
4. **子方法** 误判为"有其他任务在运行",直接返回,**不执行任何同步操作**
5. **父方法** 在第173行的 `finally` 块中释放锁

**结果**: 整个全市场补齐程序被跳过,只有抽样股票(sh.600000)被同步!

---

## 🎯 影响范围

### 受影响的调用链

```
daily_comprehensive_sync_job()
  └─ sync_daily_increment()  [设置 running=True]
       └─ sync_all_stocks_kline()  [检测到 running=True, 直接返回 ❌]
```

### 数据完整性影响

| 日期 | 预期同步数 | 实际同步数 | 完整度 | 状态 |
|------|----------|----------|--------|------|
| 2026-01-05 | 5,468 | 1 | 0.02% | ❌ 严重不完整 |

---

## 🛠️ 修复方案

### 方案A: 移除子方法的重复锁检查 (推荐) ⭐

**原理**: 由于 `sync_all_stocks_kline()` 只会被 `sync_daily_increment()` 调用,不需要重复检查锁。

```python
async def sync_all_stocks_kline(self, start_date: str = "1990-12-19") -> None:
    """同步全市场股票 K 线 (支持断点续传)"""
    # ❌ 删除这段重复的锁检查
    # if self._sync_status["running"]:
    #     logger.warning("全市场同步任务已在运行中")
    #     return
    
    # ❌ 删除这行重复的锁设置
    # self._sync_status["running"] = True
    
    logger.info("开始获取全市场股票列表...")
    
    # 1. 获取全市场列表
    stocks = await self.get_all_a_shares()
    if not stocks:
        logger.error("未能获取股票列表，同步终止")
        return
    
    # ... 后续同步逻辑保持不变 ...
    
    try:
        # ... 同步逻辑 ...
        logger.info(f"全市场同步任务圆满完成! 处理了 {len(stocks_to_sync)} 只股票的新数据")
    except Exception as e:
        logger.error(f"全市场同步任务中途崩溃: {e}", exc_info=True)
    finally:
        # ❌ 删除这行,由父方法统一管理锁
        # self._sync_status["running"] = False
        self._sync_status["last_synced"] = time.strftime("%Y-%m-%d %H:%M:%S")
```

**优点**:
- ✅ 简单直接,符合单一职责原则
- ✅ 避免了锁的重复管理
- ✅ 由父方法统一控制锁的生命周期

**缺点**:
- ⚠️ 如果未来有其他地方直接调用 `sync_all_stocks_kline()`,需要额外注意

---

### 方案B: 引入调用上下文标识

**原理**: 通过参数区分是否为内部调用。

```python
async def sync_daily_increment(self, target_date: Optional[str] = None) -> Dict[str, Any]:
    # ... 前置逻辑 ...
    
    # 4. 执行定向增量同步,传递内部调用标识
    await self.sync_all_stocks_kline(start_date=sync_date, _internal_call=True)
    
    return {"success": True, "message": "同步任务已启动", "target_date": sync_date}

async def sync_all_stocks_kline(self, start_date: str = "1990-12-19", _internal_call: bool = False) -> None:
    """同步全市场股票 K 线 (支持断点续传)"""
    if not _internal_call:  # 仅对外部调用进行锁检查
        if self._sync_status["running"]:
            logger.warning("全市场同步任务已在运行中")
            return
        self._sync_status["running"] = True
    
    # ... 后续逻辑 ...
    
    finally:
        if not _internal_call:  # 仅对外部调用释放锁
            self._sync_status["running"] = False
        self._sync_status["last_synced"] = time.strftime("%Y-%m-%d %H:%M:%S")
```

**优点**:
- ✅ 保持了对外部调用的保护
- ✅ 明确区分内部/外部调用场景

**缺点**:
- ⚠️ 增加了代码复杂度
- ⚠️ 需要维护额外的参数

---

### 方案C: 使用可重入锁 (不推荐)

**原理**: 使用 `asyncio.Lock` 的可重入版本。

**问题**: Python 的 `asyncio.Lock` 不支持可重入,需要自行实现,增加复杂度。

---

## 📝 推荐修复步骤

### Step 1: 修改代码

采用**方案A**,修改 `baostock_service.py`:

```python
# 第492-671行: sync_all_stocks_kline() 方法
async def sync_all_stocks_kline(self, start_date: str = "1990-12-19") -> None:
    """同步全市场股票 K 线 (支持断点续传)
    
    注意: 此方法由 sync_daily_increment() 调用,锁由父方法管理
    """
    logger.info("开始获取全市场股票列表...")
    
    # 1. 获取全市场列表
    stocks = await self.get_all_a_shares()
    if not stocks:
        logger.error("未能获取股票列表，同步终止")
        return
    
    # ... 保持原有逻辑 ...
    
    try:
        # ... 同步逻辑 ...
        logger.info(f"全市场同步任务圆满完成! 处理了 {len(stocks_to_sync)} 只股票的新数据")
    except Exception as e:
        logger.error(f"全市场同步任务中途崩溃: {e}", exc_info=True)
    finally:
        # 仅更新最后同步时间,不修改 running 状态
        self._sync_status["last_synced"] = time.strftime("%Y-%m-%d %H:%M:%S")
```

### Step 2: 检查其他调用点

确认 `sync_all_stocks_kline()` 是否有其他直接调用:

```bash
grep -rn "sync_all_stocks_kline" baostock-api/app/
```

如果有其他调用点,需要确保它们也通过 `sync_daily_increment()` 或类似的锁管理方法调用。

### Step 3: 补齐今日数据

修复代码后,立即补齐2026-01-05的缺失数据:

```bash
curl -X POST "http://localhost:8001/api/v1/sync/remediate?date=2026-01-05&dataType=kline&scope=incremental"
```

### Step 4: 验证修复

1. 重启服务
2. 检查明日(2026-01-06)的自动同步任务
3. 验证数据完整度达到 >99%

---

## 🔬 相关代码审查发现

### 问题2: 复权因子同步存在类似风险

**文件**: `baostock_service.py` 第175-196行

```python
async def sync_daily_adjust_increment(self, target_date: Optional[str] = None) -> Dict[str, Any]:
    """全市场每日复权因子增量同步"""
    if self._adjust_sync_status["running"]:  # ⚠️ 简单检查,未加锁
         return {"success": False, "error": "任务已在运行"}
    
    # ... 逻辑 ...
    
    await self.sync_all_stocks_adjust_factor(start_date=sync_date)  # ⚠️ 可能存在类似问题
```

**建议**: 同步修复,使用与K线同步一致的锁管理策略。

---

## 📊 测试建议

### 单元测试

```python
import pytest
from app.services.baostock_service import BaoStockService

@pytest.mark.asyncio
async def test_sync_daily_increment_no_lock_conflict():
    """测试增量同步不会因为锁冲突而跳过全市场同步"""
    service = BaoStockService()
    
    # 模拟调用
    result = await service.sync_daily_increment(target_date="2026-01-05")
    
    # 验证
    assert result["success"] == True
    assert "同步任务已启动" in result["message"]
    
    # 验证实际同步了数据
    # (需要mock数据库查询)
```

### 集成测试

1. 在测试环境执行完整的 `daily_comprehensive_sync_job()`
2. 验证K线数据完整度 >99%
3. 验证复权因子数据完整度 >99%

---

## 📚 相关文档

- [调度任务架构文档](../architecture/调度任务.md)
- [BaoStock服务规范](../architecture/02_云端服务与API.md)
- [QC流程规范](../../.agent/workflows/coding-standards.md)

---

**报告生成时间**: 2026-01-05 23:00  
**分析人员**: Antigravity AI  
**优先级**: P0 (影响数据完整性)
