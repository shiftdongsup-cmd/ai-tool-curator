import os
import requests
import json
from datetime import datetime  # 날짜 계산용 라이브러리 추가
from google import genai
from google.genai import types
from openai import OpenAI

# 1. 환경 변수 설정
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def get_report():
    # 2. 오늘 날짜를 "YYYY년 MM월 DD일" 형식으로 가져오기
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 3. 동적 프롬프트 생성 (날짜가 매일 바뀝니다)
    prompt = f"""
    너의 'Google Search' 도구를 사용하여 오늘({today_str}) 발행된 최신 AI 뉴스 3개를 검색해라.
    너는 실시간 웹 검색 권한이 있으므로 반드시 최신 정보를 찾아야 한다.

    [보고 양식]
    1. 뉴스 제목 및 원문 링크(URL)
    2. 오늘 아침 발표된 핵심 기술 내용
    3. 삼성중공업 자율운항 연구소 업무에 적용 가능한 포인트

    반드시 한국어로 작성하고, 오늘 날짜의 검색 결과를 바탕으로 보고해라.
    """
    
    # --- Gemini 시도 ---
    try:
        print(f"🔍 [Step 1] Gemini 실시간 검색 가동 ({today_str})...")
        client = genai.Client(api_key=GEMINI_KEY)
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[search_tool], temperature=0.1)
        )
        if response.text and "검색이 불가능" not in response.text:
            return response.text
    except Exception as e:
        print(f"⚠️ Gemini 오류: {e}")

    # --- OpenAI 시도 (Fallback) ---
    if OPENAI_KEY:
        try:
            print("🤖 [Step 2] ChatGPT 백업 가동 중...")
            client = OpenAI(api_key=OPENAI_KEY)
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content
        except Exception as e:
            print(f"❌ OpenAI 오류: {e}")
            
    return None

def main():
    print("🚀 실시간 하이브리드 파이프라인 가동 (날짜 자동화)...")
    report = get_report()
    
    if report:
        requests.post(SLACK_URL, json={"text": report})
        print("📬 리포트 전송 성공!")
    else:
        print("🚨 모든 API 호출 실패")

if __name__ == "__main__":
    main()
