from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AnomalyDerivedMetrics(BaseModel):
    trade_date: date
    ts_code: str
    volume_ratio_5d: Optional[float] = None
    volume_ratio_20d: Optional[float] = None
    vol_5d_to_60d: Optional[float] = None
    vol_consistency_days: Optional[int] = None
    cumulative_5d_pct: Optional[float] = None
    cumulative_20d_pct: Optional[float] = None
    cumulative_60d_pct: Optional[float] = None
    amplitude_today: Optional[float] = None
    amplitude_10d: Optional[float] = None
    industry_rank_pct_today: Optional[float] = None
    industry_rank_pct_avg_5d: Optional[float] = None
    capital_rank_today: Optional[int] = None
    capital_rank_avg_5d: Optional[float] = None
    dist_to_ma5: Optional[float] = None
    dist_to_ma10: Optional[float] = None
    dist_to_ma20: Optional[float] = None
    dist_to_ma60: Optional[float] = None
    dist_to_ma250: Optional[float] = None
    ma_convergence: Optional[float] = None
    box_test_count_60d: Optional[int] = None
    box_resistance_level: Optional[float] = None
    is_first_recovery_ma250: Optional[bool] = None
    extra_metrics: Optional[Dict[str, Any]] = None
    schema_version: str = "v1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnomalySignal(BaseModel):
    id: Optional[int] = None
    user_id: int = 1
    trade_date: date
    ts_code: str
    name: str
    industry_sw1: Optional[str] = None
    industry_sw3: Optional[str] = None
    pool_type: str
    signal_type: str
    signal_subtype: Optional[str] = None
    pct_chg: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume_ratio_5d: Optional[float] = None
    amount: Optional[float] = None
    main_net_inflow: Optional[float] = None
    signal_features: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    resonance_level: Optional[int] = None
    resonance_dimensions: Optional[Dict[str, Any]] = None
    resonance_score: Optional[float] = None
    counter_signals: Optional[Dict[str, Any]] = None
    counter_signal_score: Optional[float] = None
    temporal_resonance: Optional[Dict[str, Any]] = None
    raw_score: Optional[float] = None
    score_l3_capital: Optional[float] = None
    score_l4_emotion: Optional[float] = None
    score_user_pref: Optional[float] = None
    score_dedup_pen: Optional[float] = None
    composite_score: Optional[float] = None
    excluded_reasons: Optional[Dict[str, Any]] = None
    default_visible: bool = True
    explanation_zh: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    schema_version: str = "v1.0"
    created_at: Optional[datetime] = None
    is_deleted: bool = False


class AnomalyTop10(BaseModel):
    id: Optional[int] = None
    user_id: int = 1
    trade_date: date
    rank_no: int
    signal_id: int
    ts_code: str
    name: str
    industry_sw1: Optional[str] = None
    pool_type: str
    signal_type: str
    signal_subtype: Optional[str] = None
    composite_score: float
    resonance_level: Optional[int] = None
    quota_slot: str
    profile_code: Optional[str] = None
    headline: Optional[str] = None
    key_features: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    is_deleted: bool = False


class TagDictionary(BaseModel):
    tag_code: str
    tag_name_cn: str
    tag_category: str
    tag_subcategory: Optional[str] = None
    tag_description: Optional[str] = None
    display_order: int = 100
    is_active: bool = True
    tag_meta: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class FilterProfile(BaseModel):
    profile_code: str
    profile_name: str
    description: Optional[str] = None
    rules_json: Dict[str, Any]
    is_system: bool = True
    display_order: int = 100
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MarketState(BaseModel):
    trade_date: date
    is_normal: bool = True
    csi300_pct_chg: Optional[float] = None
    abnormal_reasons: Optional[Dict[str, Any]] = None
    signal_reliability: float = 1.0
    manual_override: bool = False
    note: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    is_deleted: bool = False


class AnomalyScoreWeight(BaseModel):
    version: str
    weight_key: str
    weight_value: float
    weight_desc: Optional[str] = None
    is_active: bool = False
    effective_from: Optional[date] = None
    created_at: Optional[datetime] = None


class UserSectorPref(BaseModel):
    id: Optional[int] = None
    user_id: int = 1
    sector_type: str
    sector_code: str
    sector_name: str
    weight: float = 1.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
