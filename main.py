import os
import requests
import json
import xml.etree.ElementTree as ET # RSS(XML) 해석용
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def scrape_via_rss():
    # 2026년 기준, 가장 안정적인 AI 뉴스 공급원 (예: RSS 제공 사이트)
    # 직접 크롤링 대신 RSS 주소를 활용하면 차단되지 않습니다.
    rss_url = "https://www.futurepedia.io/rss.xml" # 혹은 안정적인 대안 RSS
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        print("RSS 피드 수신 중...")
        res = requests.get(rss_url, headers=headers, timeout=15)
        # RSS는 XML 형식이므로 파싱 방식이 다릅니다.
        root = ET.fromstring(res.content)
        
        tools = []
        # RSS의 각 아이템(신규 툴) 추출
        for item in root.findall('.//item')[:10]:
            name = item.find('title').text
            desc = item.find('description').text
            tools.append({"name": name, "description": desc})
        return tools
    except Exception as e:
        print(f"RSS 수집 실패 (사이트 구조 변경 혹은 RSS 주소 만료): {e}")
        # RSS 실패 시 최후의 수단: AI가 직접 학습한 최신 트렌드를 물어보게 구성
        return [{"name": "AI Trend Monitoring", "description": "Latest AI tool trends as of 2026"}]

def filter_with_gemini(tool_list):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    너는 파이썬 개발자이자 마케팅 자동화 전문가인 '정수'님의 개인 비서야.
    다음 리스트 중 업무 효율을 높일 최신 AI 툴 3개를 골라 한국어로 보고해줘: {json.dumps(tool_list)}
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text

def main():
    print("🚀 파이프라인 가동...")
    raw_tools = scrape_via_rss()
    
    if raw_tools:
        print(f"✅ {len(raw_tools)}개의 데이터 확보 성공. AI 필터링 시작...")
        summary = filter_with_gemini(raw_tools)
        requests.post(SLACK_WEBHOOK_URL, json={"text": summary})
        print("📬 슬랙 보고 완료!")

if __name__ == "__main__":
    main()
