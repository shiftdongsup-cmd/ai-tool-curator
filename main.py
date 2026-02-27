import os
import requests
import json
from google import genai
from openai import OpenAI

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 2. 공통 프롬프트 설정 (정수님 맞춤형 및 URL 포함 지시)
REPORT_PROMPT = """
너는 파이썬 개발자이자 마케팅 자동화 전문가인 '정수'님의 전용 AI 비서야.
오늘의 최신 AI 툴 중 업무 효율을 높일 혁신적인 툴 3개를 선정해줘.

[보고 형식]
1. 툴 이름 및 공식 웹사이트 URL (반드시 포함)
2. 주요 기능 및 개발자/마케터 관점의 활용 포인트
3. 기대 효과 (한 줄 요약)

반드시 한국어로 친절하고 전문적이게 보고해줘.
"""

def get_report_from_gemini():
    """메인 엔진: Gemini 2.0 Flash 사용"""
    try:
        print("💡 [Step 1] Gemini 호출 시도 중...")
        # 2026 최신 SDK: Client 객체 생성
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=REPORT_PROMPT
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini 오류 발생: {e}")
        return None

def get_report_from_openai():
    """예비 엔진: ChatGPT (OpenAI) 사용"""
    if not OPENAI_API_KEY:
        print("⏭️ OpenAI 키가 설정되지 않아 건너뜁니다.")
        return None
        
    try:
        print("🤖 [Step 2] ChatGPT로 자동 전환 중 (Fallback)...")
        client = OpenAI(api_key=OPENAI_API_KEY)
        # 2026 최신 SDK: chat.completions 사용
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": REPORT_PROMPT}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI 호출 실패: {e}")
        return None

def send_to_slack(message):
    """최종 요약본 슬랙 전송"""
    try:
        payload = {"text": message}
        response = requests.post(
            SLACK_WEBHOOK_URL, 
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            print("📬 슬랙 리포트 전송 성공!")
        else:
            print(f"❌ 슬랙 전송 실패 (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ 슬랙 연결 오류: {e}")

def main():
    print("🚀 AI 툴 큐레이션 파이프라인 가동...")
    
    # 먼저 Gemini에게 물어봄
    final_report = get_report_from_gemini()
    
    # Gemini 실패 시에만 OpenAI에게 물어봄 (이중화)
    if not final_report:
        final_report = get_report_from_openai()
    
    # 결과가 있으면 슬랙 전송
    if
