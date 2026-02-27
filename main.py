import os
import requests
import json
from google import genai
from openai import OpenAI

# 환경 변수 로드
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def get_report_from_gemini(prompt):
    try:
        print("💡 Gemini 호출 시도 중...")
        client = genai.Client(api_key=GEMINI_KEY)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini 실패: {e}")
        return None

def get_report_from_openai(prompt):
    try:
        print("🤖 ChatGPT(OpenAI)로 자동 전환 중...")
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI 실패: {e}")
        return None

def main():
    prompt = """
    너는 파이썬 개발자이자 마케팅 자동화 전문가인 '정수'님의 비서야.
    오늘의 최신 AI 툴 3개를 선정해 한국어로 요약 보고해줘.
    """
    
    # 1단계: Gemini 시도
    report = get_report_from_gemini(prompt)
    
    # 2단계: Gemini 실패 시 OpenAI 시도
    if not report and OPENAI_KEY:
        report = get_report_from_openai(prompt)
    
    # 3단계: 최종 결과 전송
    if report:
        requests.post(SLACK_URL, json={"text": report})
        print("📬 리포트 전송 완료!")
    else:
        print("❌ 모든 API 호출에 실패했습니다.")

if __name__ == "__main__":
    main()
