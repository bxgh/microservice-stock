import os

# API Endpoints
MOOTDX_TICK_ENDPOINT = "/api/v1/tick/{code}"

# Table Names
TABLE_INTRADAY_LOCAL = "tick_data_intraday_local"  # 本地当日表 (原 stock_tick_data_local)
TABLE_INTRADAY_DIST = "tick_data_intraday"         # 分布式当日表
TABLE_HISTORY_LOCAL = "tick_data_local"            # 本地历史表
TABLE_HISTORY_DIST = "tick_data"                   # 分布式历史表

# Default Configs
DEFAULT_CACHE_SIZE = int(os.getenv("TICK_CACHE_SIZE", "1500"))
DEFAULT_WRITER_BATCH_SIZE = int(os.getenv("TICK_WRITE_BATCH", "1000"))
