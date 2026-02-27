import os
import requests
import json
from google import genai
from google.genai import types
from openai import OpenAI

# 환경 변수 로드
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 공통 프롬프트 (실시간성 강조)
PROMPT = """
오늘 아침을 기준으로 가장 최신 AI 뉴스 및 신규 출시된 AI 툴 3개를 선정해줘.
반드시 실시간 검색 결과를 바탕으로 공식 웹사이트 URL을 포함하고, 
삼성중공업 자율운항연구 동료들에게 도움될 기술적 포인트를 한국어로 요약해줘.
"""

def get_report_from_gemini():
    """메인 엔진: Gemini 2.0 + Google Search (실시간 검색)"""
    try:
        if not GEMINI_KEY: return None
        print("🔍 [Step 1] Gemini 실시간 검색 시도 중...")
        client = genai.Client(api_key=GEMINI_KEY)
        
        # 구글 검색 도구 활성화
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=PROMPT,
            config=types.GenerateContentConfig(tools=[search_tool])
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini 실패 (할당량 초과 등): {e}")
        return None

def get_report_from_openai():
    """예비 엔진: ChatGPT (OpenAI)"""
    if not OPENAI_KEY: return None
    try:
        print("🤖 [Step 2] ChatGPT로 자동 전환 중...")
        client = OpenAI(api_key=OPENAI_KEY)
        # GPT-4o 모델은 학습 데이터 기반이지만 최신 트렌드 반영을 요청
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": PROMPT + "\n(인터넷 검색이 가능하다면 최신 정보를 참고해줘)"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI 실패: {e}")
        return None

def main():
    print("🚀 실시간 하이브리드 파이프라인 가동...")
    
    # 1순위 Gemini 시도
    report = get_report_from_gemini()
    
    # 2순위 실패 시 OpenAI 시도
    if not report:
        report = get_report_from_openai()
    
    # 결과 전송
    if report:
        requests.post(SLACK_URL, json={"text": report})
        print("📬 리포트 전송 성공!")
    else:
        print("🚨 모든 API 호출 실패")

if __name__ == "__main__":
    main()
