import os
import requests
import json
from bs4 import BeautifulSoup
from google import genai

# 환경 변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def scrape_tools():
    # 1순위 타겟: There's An AI For That (TAAFT) - 구조가 비교적 안정적
    url = "https://theresanaiforthat.com/"
    # 봇 차단을 피하기 위한 실제 브라우저 위장 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        print("There's An AI For That 수집 시도 중...")
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        tools = []

        # TAAFT의 신규 도구 리스트 섹션 (2026 구조 반영)
        items = soup.find_all('div', class_=lambda x: x and 'tool_card' in x.lower())[:10]
        
        if not items:
            # Futurepedia 재시도 (더 넓은 범위의 클래스 탐색)
            print("TAAFT 수집 실패, Futurepedia로 전환...")
            url = "https://www.futurepedia.io/new"
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            # 'card'나 'item' 문구가 들어간 모든 div/a 태그 검색
            items = soup.find_all(['div', 'a'], class_=lambda x: x and ('card' in x.lower() or 'item' in x.lower()))[:12]

        for item in items:
            name = item.find(['h2', 'h3', 'div', 'span'], class_=lambda x: x and 'name' in x.lower())
            desc = item.find(['p', 'div', 'span'], class_=lambda x: x and ('desc' in x.lower() or 'text' in x.lower()))
            
            if name and desc:
                tools.append({"name": name.text.strip(), "description": desc.text.strip()})
        
        return tools
    except Exception as e:
        print(f"Scraping Error: {e}")
        return []

def filter_with_gemini(tool_list):
    client = genai.Client(api_key=GEMINI_API_KEY)
    # 페르소나 강화 프롬프트
    prompt = f"""
    너는 파이썬 개발자이자 마케팅 자동화 전문가인 '정수'님의 개인 비서야.
    아래 수집된 AI 툴 목록 중 업무 효율을 극대화할 툴 3개를 선정해줘.
    [데이터] {json.dumps(tool_list, ensure_ascii=False)}
    
    [보고 양식]
    1. 툴 이름 및 링크(유추 가능할 경우)
    2. 개발자/마케터 관점에서의 핵심 활용 포인트
    3. 기대 효과 (한 줄 요약)
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text

def main():
    print("🚀 파이프라인 가동...")
    raw_tools = scrape_tools()
    
    if not raw_tools:
        print("❌ 모든 사이트에서 데이터를 가져오지 못했습니다. 사이트의 보안 설정이 강화되었을 수 있습니다.")
        return

    print(f"✅ {len(raw_tools)}개의 후보 발견. AI 필터링 중...")
    summary = filter_with_gemini(raw_tools)
    
    requests.post(SLACK_WEBHOOK_URL, json={"text": summary})
    print("📬 슬랙 보고 완료!")

if __name__ == "__main__":
    main()
