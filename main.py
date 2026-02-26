import os
import requests
import json
from bs4 import BeautifulSoup
from google import genai

# 환경 변수 가져오기
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def scrape_futurepedia():
    # Futurepedia 대신 더 크롤링이 안정적인 'There's An AI For That'을 대안으로 사용하거나
    # Futurepedia의 변경된 구조(카드 클래스)를 타겟팅합니다.
    url = "https://www.futurepedia.io/new"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        tools = []

        # Futurepedia의 최신 HTML 구조를 반영한 여러 후보군 탐색
        items = soup.find_all(['div', 'a'], class_=lambda x: x and ('card' in x.lower() or 'item' in x.lower()))[:15]
        
        for item in items:
            # 이름과 설명을 찾기 위한 유연한 탐색
            name_tag = item.find(['h2', 'h3', 'div'], class_=lambda x: x and 'name' in x.lower())
            desc_tag = item.find(['p', 'div'], class_=lambda x: x and 'desc' in x.lower())
            
            if name_tag and desc_tag:
                tools.append({
                    "name": name_tag.text.strip(),
                    "description": desc_tag.text.strip()
                })
        
        # 만약 Futurepedia가 실패하면 대안 사이트(TAAFT)를 시도하는 로직 추가 가능
        if not tools:
            print("Futurepedia 구조 분석 실패, 대안 사이트 시도 중...")
            # 여기에 다른 사이트 크롤링 로직을 넣을 수 있습니다.

        return tools
    except Exception as e:
        print(f"Scraping Error: {e}")
        return []

def filter_with_gemini(tool_list):
    # 최신 SDK 방식 (google-genai)
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    너는 파이썬 개발자이자 마케팅 자동화 전문가를 위한 비서야. 
    다음 AI 툴 중 가장 혁신적인 3개를 골라 한국어로 요약해줘: {json.dumps(tool_list)}
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text

def main():
    print("프로세스 시작...")
    raw_tools = scrape_futurepedia()
    
    if not raw_tools:
        print("수집된 데이터가 없습니다. 사이트 구조를 확인해 보세요.")
        return

    print(f"{len(raw_tools)}개의 툴 수집 완료. 필터링 시작...")
    summary = filter_with_gemini(raw_tools)
    
    # 슬랙 전송 및 결과 출력
    res = requests.post(SLACK_WEBHOOK_URL, json={"text": summary})
    print(f"Slack 전송 결과: {res.status_code}")

if __name__ == "__main__":
    main()
