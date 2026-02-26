import os
import requests
import json
from bs4 import BeautifulSoup
from google import genai

# 환경 변수 가져오기
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def scrape_futurepedia():
    url = "https://www.futurepedia.io/new"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        tools = []
        # 사이트 구조 변화에 대비해 핵심 카드 정보 수집
        items = soup.select('.tool-card-container')[:10]
        for item in items:
            name = item.select_one('.tool-card-name').text.strip()
            desc = item.select_one('.tool-card-description').text.strip()
            tools.append({"name": name, "description": desc})
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
