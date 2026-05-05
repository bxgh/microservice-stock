import yaml
import os
import logging
from typing import List, Dict, Any, Callable
from pydantic import BaseModel

logger = logging.getLogger("stock-manager.rule_engine")


class RuleDef(BaseModel):
    id: str
    name: str
    severity: str
    handler: str
    description: str
    enabled: bool = True


class RuleEngine:
    """声明式校验规则引擎 (E8)"""

    def __init__(self, rules_path: str = None):
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(__file__), "rules", "rules.yaml")
        self.rules_path = rules_path
        self.rules: List[RuleDef] = []
        self._handlers: Dict[str, Callable] = {}
        self.load_rules()

    def load_rules(self):
        """从 YAML 加载规则定义"""
        try:
            if not os.path.exists(self.rules_path):
                logger.warning(f"规则文件不存在: {self.rules_path}")
                return

            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.rules = [RuleDef(**r) for r in data.get("rules", [])]
            logger.info(f"成功加载 {len(self.rules)} 条规则")
        except Exception as e:
            logger.error(f"加载规则失败: {e}")

    def register_handler(self, name: str, handler: Callable):
        """注册规则处理器"""
        self._handlers[name] = handler

    async def execute_all(self, context: Dict[str, Any]):
        """执行所有已启用的规则"""
        for rule in self.rules:
            if not rule.enabled:
                continue

            handler = self._handlers.get(rule.handler)
            if not handler:
                logger.warning(f"规则 {rule.id} 的处理器 {rule.handler} 未注册")
                continue

            try:
                logger.debug(f"正在执行规则: {rule.name} ({rule.id})")
                await handler(rule, context)
            except Exception as e:
                logger.error(f"规则 {rule.id} 执行异常: {e}")


rule_engine = RuleEngine()
