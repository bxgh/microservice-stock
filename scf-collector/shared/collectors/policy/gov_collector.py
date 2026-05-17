import logging
import hashlib
import httpx
import json
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from shared.db.connection import execute_query

logger = logging.getLogger(__name__)

class GovCollector:
    """
    中国政府网 (gov.cn) 政策采集器 - 动态 JSON 版本
    """
    SOURCE_NAME = "GOV_CN"
    # 动态数据接口
    LIST_API_URL = "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json"
    REFERER_URL = "https://www.gov.cn/zhengce/zuixin/"

    @staticmethod
    def calculate_md5(text: str) -> str:
        """计算文本的 MD5 指纹"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def fetch_latest_list(self) -> List[Dict[str, str]]:
        """从 JSON 接口抓取最新政策列表"""
        logger.info(f"Fetching policy list from API: {self.LIST_API_URL}")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": self.REFERER_URL
            }
            resp = await client.get(self.LIST_API_URL, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch {self.LIST_API_URL}: {resp.status_code}")
                return []
            
            try:
                # 尝试用 utf-8-sig 解密（以防存在 BOM 头）
                clean_text = resp.content.decode("utf-8-sig")
                data = json.loads(clean_text)
                items = []
                for entry in data:
                    items.append({
                        "title": entry.get("TITLE") or entry.get("title"),
                        "url": entry.get("URL") or entry.get("url"),
                        "date": entry.get("DOCRELPUBTIME") or entry.get("pubDate") or ""
                    })
                
                logger.info(f"Successfully parsed {len(items)} items from ZUIXINZHENGCE.json")
                return items
            except Exception as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return []

    async def fetch_detail(self, url: str) -> Optional[tuple[str, str]]:
        """抓取政策详情正文与发布机构"""
        # 补全 URL
        if not url.startswith("http"):
            url = "https://www.gov.cn" + url
            
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch detail {url}: {resp.status_code}")
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 解析发文机关并动态映射分类
            ts_code = self.SOURCE_NAME  # 默认 "GOV_CN"
            cells = soup.find_all(["td", "th"])
            for idx, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                if "发文机关" in text:
                    if idx + 1 < len(cells):
                        val = cells[idx + 1].get_text(strip=True)
                        if "人民银行" in val:
                            ts_code = "PBC"
                        elif "证监会" in val or "证券监督" in val:
                            ts_code = "CSRC"
                        break

            
            # 常见正文容器：.pages_content, #UCAP-CONTENT, .article-content
            content_div = soup.select_one(".pages_content") or \
                          soup.select_one("#UCAP-CONTENT") or \
                          soup.select_one(".article-content")
            
            if content_div:
                # 移除脚本和样式
                for s in content_div(["script", "style"]):
                    s.decompose()
                return content_div.get_text(separator="\n", strip=True), ts_code
            
            return None

    async def run(self):
        """运行采集流程"""
        items = await self.fetch_latest_list()
        new_count = 0
        for item in items:
            if not item.get('url') or not item.get('title'):
                continue
                
            # 检查 URL 是否已存在 (一级去重)
            exists = await execute_query(
                "SELECT id FROM ods_policy_info WHERE source_url = %s",
                (item['url'],)
            )
            if exists:
                continue
            
            # 抓取详情
            detail_res = await self.fetch_detail(item['url'])
            if not detail_res:
                continue
            
            content, ts_code = detail_res
            
            # 内容级去重 (二级去重)
            content_md5 = self.calculate_md5(content)
            md5_exists = await execute_query(
                "SELECT id FROM ods_policy_info WHERE content_md5 = %s",
                (content_md5,)
            )
            if md5_exists:
                logger.info(f"Skip duplicate content MD5: {item['title']}")
                continue
            
            # 处理日期
            try:
                publish_date = item['date'].replace(".", "-")
                if len(publish_date) > 10:
                    publish_date = publish_date[:10]
            except:
                publish_date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")

            # 入库
            sql = """
            INSERT INTO ods_policy_info (ts_code, title, publish_date, source_url, content_text, content_md5)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            await execute_query(sql, (
                ts_code,
                item['title'],
                publish_date,
                item['url'],
                content,
                content_md5
            ), is_select=False)
            
            new_count += 1
            logger.info(f"New policy saved under [{ts_code}]: {item['title']}")
            
        return new_count


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv('scf-collector/.env')
    
    logging.basicConfig(level=logging.INFO)
    collector = GovCollector()
    asyncio.run(collector.run())
