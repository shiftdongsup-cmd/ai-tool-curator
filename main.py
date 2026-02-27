import os
import requests
import json
from google import genai
from openai import OpenAI

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 2. 동료들과 공유하기 좋은 세련된 프롬프트
REPORT_PROMPT = """
너는 삼성중공업 자율운항 연구소의 'AI 큐레이션 비서'야. 
연구소 동료분들에게 도움이 될만한 최신 AI 기술 3개를 선정해줘.

[보고 형식]
1. 🛠️ 툴 이름 및 공식 링크: (클릭 가능한 URL 포함)
2. 💡 핵심 기능: (연구소 업무나 개발/마케팅 자동화 관점)
3. 🚀 기대 효과: (우리 업무에 어떻게 적용할지 한 줄 요약)

동료분들에게 신뢰를 줄 수 있도록 전문적이고 친절한 한국어로 작성해줘.
"""

def get_report_from_gemini():
    """메인 엔진: Gemini 2.0 Flash 시도"""
    try:
        if not GEMINI_API_KEY:
            return None
        print("💡 [Step 1] Gemini 호출 시도 중...")
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
    """예비 엔진: ChatGPT (OpenAI) 시도"""
    if not OPENAI_API_KEY:
        print("⏭️ OpenAI 키가 없어 건너뜁니다.")
        return None
    try:
        print("🤖 [Step 2] ChatGPT로 전환 중...")
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": REPORT_PROMPT}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ OpenAI 호출 실패: {e}")
        return None

def send_to_slack(message):
    """최종 리포트를 슬랙으로 전송"""
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
            print(f"❌ 전송 실패 (상태 코드: {response.status_code})")
    except Exception as e:
        print(f"❌ 슬랙 연결 오류: {e}")

def main():
    print("🚀 AI 툴 큐레이션 파이프라인 가동...")
    
    # 1. Gemini 시도
    report = get_report_from_gemini()
    
    # 2. Gemini 실패 시 OpenAI 시도
    if not report:
        report = get_report_from_openai()
    
    # 3. 결과가 있으면 전송
    if report:
        send_to_slack(report)
    else:
        print("🚨 모든 AI 엔진 호출 실패")

if __name__ == "__main__":
    main()
