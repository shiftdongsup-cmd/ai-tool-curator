import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os

# 환경 변수에서 키를 가져옵니다 (GitHub Secrets 설정 필요)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

genai.configure(api_key=GEMINI_API_KEY)

def scrape_futurepedia():
    url = "https://www.futurepedia.io/new"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    tools = []
    # 최신 툴 카드 추출 (사이트 구조에 따라 변경될 수 있음)
    items = soup.select('.tool-card-container')[:10]
    for item in items:
        name = item.select_one('.tool-card-name').text.strip()
        desc = item.select_one('.tool-card-description').text.strip()
        tools.append({"name": name, "description": desc})
    return tools

def filter_tools(tool_list):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"너는 파이썬 개발자/마케팅 자동화 전문가를 위한 큐레이터야. 다음 리스트 중 가장 유용한 툴 3개를 골라 한국어로 요약해줘: {json.dumps(tool_list)}"
    response = model.generate_content(prompt)
    return response.text

# 기존 코드
# requests.post(SLACK_WEBHOOK_URL, json={"text": summary})

# 권장 코드 (전송 성공 여부를 출력하게 하여 에러 확인)
def main():
    raw_tools = scrape_futurepedia()
    if raw_tools:
        summary = filter_tools(raw_tools)
        # 응답값을 확인하기 위해 변수에 저장
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": summary})
        print(f"Slack response: {response.status_code}, {response.text}")
    else:
        print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()
