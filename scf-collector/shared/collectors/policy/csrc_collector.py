import logging
import hashlib
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from shared.db.connection import execute_query

logger = logging.getLogger(__name__)

class CsrcCollector:
    """
    中国证监会 (csrc.gov.cn) 政策采集器 - 动态 JSON API 版本
    """
    SOURCE_NAME = "CSRC"
    # 证监会公告栏目 JSON API 接口
    LIST_API_URL = "http://www.csrc.gov.cn/searchList/cd11df89f5894c1eac37ae37cc11e369?_isAgg=true&_isJson=true&_pageSize=15&page=1"

    @staticmethod
    def calculate_md5(text: str) -> str:
        """计算文本的 MD5 指纹"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def fetch_latest_list(self) -> List[Dict[str, str]]:
        """从证监会 JSON 接口抓取最新政策列表"""
        logger.info(f"Fetching CSRC policy list from API: {self.LIST_API_URL}")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = await client.get(self.LIST_API_URL, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch CSRC list API: {resp.status_code}")
                return []
            
            try:
                data = resp.json()
                results = data.get("data", {}).get("results", [])
                items = []
                for entry in results:
                    title = entry.get("title")
                    url = entry.get("url")
                    pub_time = entry.get("publishedTimeStr") or ""
                    
                    if title and url:
                        # 格式化 title，剔除可能存在的 HTML 标签
                        soup_title = BeautifulSoup(title, "html.parser")
                        clean_title = soup_title.get_text(strip=True)
                        
                        items.append({
                            "title": clean_title,
                            "url": url,
                            "date": pub_time
                        })
                
                logger.info(f"Successfully parsed {len(items)} items from CSRC searchList API")
                return items
            except Exception as e:
                logger.error(f"Failed to parse CSRC JSON response: {e}")
                return []

    async def fetch_detail(self, url: str) -> Optional[str]:
        """抓取证监会政策详情页正文"""
        # 补全 URL
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = "https://www.csrc.gov.cn" + url
            
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch CSRC detail {url}: {resp.status_code}")
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 证监会正文容器通常为 .content, 也有可能存在 .pages_content 或 .article-content
            content_div = soup.select_one(".content") or \
                          soup.select_one(".pages_content") or \
                          soup.select_one("#UCAP-CONTENT") or \
                          soup.select_one(".article-content")
            
            if content_div:
                # 移除脚本和样式
                for s in content_div(["script", "style"]):
                    s.decompose()
                return content_div.get_text(separator="\n", strip=True)
            
            # 兜底查找所有 p 标签
            ps = soup.find_all("p")
            if ps:
                return "\n".join([p.get_text(strip=True) for p in ps if p.get_text(strip=True)])
                
            return None

    async def run(self) -> int:
        """运行证监会采集流程"""
        items = await self.fetch_latest_list()
        new_count = 0
        for item in items:
            # 格式化 URL 为标准库存储 URL (如果是相对路径补齐 //)
            raw_url = item['url']
            if raw_url.startswith("//"):
                source_url = "https:" + raw_url
            elif raw_url.startswith("/"):
                source_url = "https://www.csrc.gov.cn" + raw_url
            else:
                source_url = raw_url

            # 检查 URL 是否已存在 (一级去重)
            exists = await execute_query(
                "SELECT id FROM ods_policy_info WHERE source_url = %s",
                (source_url,)
            )
            if exists:
                continue
            
            # 抓取详情
            content = await self.fetch_detail(raw_url)
            if not content:
                continue
            
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
                publish_date = item['date']
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
                self.SOURCE_NAME,
                item['title'],
                publish_date,
                source_url,
                content,
                content_md5
            ), is_select=False)
            
            new_count += 1
            logger.info(f"New CSRC policy saved: {item['title']}")
            
        return new_count

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv('scf-collector/.env')
    
    logging.basicConfig(level=logging.INFO)
    collector = CsrcCollector()
    asyncio.run(collector.run())
