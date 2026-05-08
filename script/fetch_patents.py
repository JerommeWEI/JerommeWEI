import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

PATENTS_URL = (
    "https://patents.google.com/"
    "?inventor=%E9%AD%8F%E5%A8%81"
    "&assignee=%E5%B9%BF%E4%B8%9C%E5%B7%A5%E4%B8%9A%E5%A4%A7%E5%AD%A6"
    "&assignee=%E6%B7%B1%E5%9C%B3%E5%B8%82%E9%80%9F%E8%85%BE%E8%81%9A%E5%88%9B%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
    "&assignee=%E6%B7%B1%E5%9C%B3%E5%B8%82%E7%82%B9%E6%99%B4%E5%88%9B%E8%A7%86%E6%8A%80%E6%9C%AF%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
    "&assignee=%E5%85%89%E4%B8%BA%E7%A7%91%E6%8A%80%28%E5%B9%BF%E5%B7%9E%29%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
    "&assignee=%E6%B8%85%E5%8D%8E%E7%8F%A0%E4%B8%89%E8%A7%92%E7%A0%94%E7%A9%B6%E9%99%A2"
    "&assignee=%E4%BC%98%E5%B0%BC%E7%A7%91%28%E9%9D%92%E5%B2%9B%29%E5%BE%AE%E7%94%B5%E5%AD%90%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8"
)

OUTPUT_FILE = Path(__file__).parent / "patents_data.json"


async def fetch_patents():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Fetching patents from Google Patents...")
        await page.goto(PATENTS_URL, wait_until="networkidle")
        
        await page.wait_for_selector("search-result-item, .patent-result, article", timeout=30000)
        
        patents = []
        page_num = 1
        
        while True:
            print(f"Processing page {page_num}...")
            await page.wait_for_timeout(2000)
            
            items = await page.query_selector_all("search-result-item, article.result, tr.patent-row")
            
            if not items:
                items = await page.query_selector_all("[data-result], .result-item, li[class*='result']")
            
            if not items:
                page_content = await page.content()
                if "result" in page_content.lower() or "patent" in page_content.lower():
                    items = await page.query_selector_all("a[href*='patent/']")
                    items = list(set([await item.evaluate_handle("el => el.closest('div, li, tr, article')") for item in items if item]))
                    items = [item for item in items if item]
            
            for item in items:
                try:
                    patent = await extract_patent_data(item, page)
                    if patent and patent.get("title"):
                        patents.append(patent)
                except Exception as e:
                    print(f"Error extracting patent: {e}")
                    continue
            
            next_button = await page.query_selector("button[aria-label*='Next'], a[aria-label*='Next'], .next-page, [data-page='next']")
            if not next_button:
                next_button = await page.query_selector("button:has-text('Next'), a:has-text('Next'), button:has-text('>'), a:has-text('>')")
            
            if next_button:
                is_disabled = await next_button.get_attribute("disabled")
                if is_disabled:
                    break
                await next_button.click()
                page_num += 1
                await page.wait_for_timeout(2000)
            else:
                break
            
            if page_num > 50:
                print("Reached maximum page limit (50)")
                break
        
        await browser.close()
        
        unique_patents = []
        seen_titles = set()
        for p in patents:
            title_key = p.get("title", "").lower().strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_patents.append(p)
        
        return unique_patents


async def extract_patent_data(item, page):
    patent = {
        "title": "",
        "title_en": "",
        "patent_id": "",
        "application_number": "",
        "publication_date": "",
        "filing_date": "",
        "assignee": "",
        "inventors": [],
        "ipc_codes": [],
        "cpc_codes": [],
        "abstract": "",
        "status": "",
        "url": ""
    }
    
    title_elem = await item.query_selector("h3, h4, .title, [class*='title'], a[href*='patent/']")
    if title_elem:
        patent["title"] = await title_elem.inner_text() or ""
        patent["title"] = patent["title"].strip()
        
        href = await title_elem.get_attribute("href")
        if href:
            if href.startswith("/"):
                patent["url"] = f"https://patents.google.com{href}"
            else:
                patent["url"] = href
    
    id_elem = await item.query_selector("[class*='patent-number'], [class*='id'], .patent-id")
    if id_elem:
        patent["patent_id"] = await id_elem.inner_text() or ""
        patent["patent_id"] = patent["patent_id"].strip()
    else:
        text = await item.inner_text()
        id_match = re.search(r'(CN|US|WO|EP|JP|KR)\s*\d+[A-Z]?\d*', text)
        if id_match:
            patent["patent_id"] = id_match.group(0)
    
    date_elem = await item.query_selector("[class*='date'], time")
    if date_elem:
        date_text = await date_elem.inner_text() or ""
        patent["publication_date"] = date_text.strip()
    else:
        text = await item.inner_text()
        date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)', text)
        if date_match:
            patent["publication_date"] = date_match.group(1)
    
    assignee_elem = await item.query_selector("[class*='assignee'], [class*='applicant']")
    if assignee_elem:
        patent["assignee"] = await assignee_elem.inner_text() or ""
        patent["assignee"] = patent["assignee"].strip()
    
    abstract_elem = await item.query_selector("[class*='abstract'], [class*='summary']")
    if abstract_elem:
        patent["abstract"] = await abstract_elem.inner_text() or ""
        patent["abstract"] = patent["abstract"].strip()[:500]
    
    return patent


async def main():
    patents = await fetch_patents()
    
    print(f"\nTotal patents found: {len(patents)}")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(patents, f, ensure_ascii=False, indent=2)
    
    print(f"Data saved to: {OUTPUT_FILE}")
    
    return patents


if __name__ == "__main__":
    asyncio.run(main())
