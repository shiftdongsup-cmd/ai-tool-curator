import os
import requests
import json
from datetime import datetime
from google import genai
from google.genai import types
from openai import OpenAI

# 1. 환경 변수 설정
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def get_today_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # AI가 딴소리 못하게 하는 강력한 프롬프트
    prompt = f"""
    당신은 실시간 인터넷 검색 권한이 있는 AI 비서입니다.
    반드시 'Google Search' 도구를 사용하여 오늘({today_str}) 발행된 최신 AI 뉴스 3개를 찾으세요.
    "검색할 수 없다"는 답변은 절대 하지 마십시오.
    
    [보고 양식]
    1. 툴/뉴스 이름 및 공식 URL
    2. 오늘 아침 발표된 핵심 기술 내용 요약
    3. 삼성중공업 자율운항 연구소 동료들을 위한 기술적 활용 포인트
    
    반드시 한국어로 작성하세요.
    """

    # --- Step 1: Gemini 실시간 검색 시도 ---
    try:
        print(f"🔍 [Gemini] {today_str} 실시간 검색 가동...")
        client = genai.Client(api_key=GEMINI_KEY)
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[search_tool], temperature=0.0)
        )
        
        # 검색 실패 멘트가 포함되어 있는지 체크
        if response.text and "검색할 수 없" not in response.text and "기능이 없" not in response.text:
            return f"[Gemini 리포트]\n{response.text}"
            
    except Exception as e:
        print(f"⚠️ Gemini 시스템 오류: {e}")

    # --- Step 2: Gemini 실패 시 ChatGPT(OpenAI) 백업 ---
    if OPENAI_KEY:
        try:
            print("🤖 [OpenAI] ChatGPT로 전환하여 리포트 생성 중...")
            client = OpenAI(api_key=OPENAI_KEY)
            res = client.chat.completions.create(
                model="gpt-4o", # 최신 데이터 반영이 뛰어난 모델
                messages=[{"role": "user", "content": prompt}]
            )
            return f"[ChatGPT 리포트]\n{res.choices[0].message.content}"
        except Exception as e:
            print(f"❌ OpenAI 오류: {e}")
            
    return None

def main():
    print("🚀 실시간 하이브리드 파이프라인(Gemini & GPT) 가동...")
    report = get_today_report()
    
    if report:
        requests.post(SLACK_URL, json={"text": report})
        print("📬 슬랙 리포트 전송 완료!")
    else:
        print("🚨 모든 엔진 호출 실패")

if __name__ == "__main__":
    main()
