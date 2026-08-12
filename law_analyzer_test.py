"""
법제처 API 연결 테스트 (로컬 PC에서 실행)
$ python3 law_analyzer_test.py
"""
import sys
sys.path.insert(0, '.')

from law_analyzer import _get_api_key, _fetch, _build_url

def test_connection():
    api_key = _get_api_key()
    print(f"API 키: {api_key}")

    url = _build_url('lawSearch.do', {
        'OC': api_key, 'type': 'XML',
        'target': 'law', 'query': '정보공개', 'display': '2'
    })
    print(f"요청 URL: {url[:80]}...")

    result = _fetch(url)
    if '<error>' in result:
        print(f"\n❌ 연결 실패:\n{result}")
        print("\n→ 로컬 PC에서 실행하면 정상 작동합니다.")
    else:
        print(f"\n✅ 연결 성공!")
        print(f"응답 길이: {len(result)} bytes")
        import re
        laws = re.findall(r'<법령명한글>(.*?)</법령명한글>', result)
        print(f"검색 결과: {laws}")

if __name__ == '__main__':
    test_connection()
