#!/usr/bin/env python3
"""
세종시설관리공단 보고서 자동화 웹 시스템
Flask 웹 서버: 브라우저 입력 → hwpx 파일 자동 생성 + 다운로드
"""

import subprocess
import sys

# Flask 자동 설치
try:
    import flask
except ImportError:
    print("Flask를 설치합니다...")
    # --ignore-installed: debian 기본 패키지 충돌 우회
    ret = subprocess.call([sys.executable, "-m", "pip", "install", "flask",
                           "--ignore-installed", "--break-system-packages", "-q"])
    if ret != 0:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "-q"])
    import flask

from flask import Flask, render_template, request, send_file, jsonify
import io
from hwpx_generator import generate_hwpx, make_filename

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate/<report_type>', methods=['POST'])
def generate(report_type):
    """hwpx 파일 생성 및 다운로드"""
    valid_types = ('review', 'plan', 'inspection', 'seminar')
    if report_type not in valid_types:
        return jsonify({'error': '잘못된 보고서 유형입니다.'}), 400

    # 동적 항목(검토 보고) 처리
    data = request.form.to_dict()

    if report_type == 'review':
        items = []
        idx = 0
        while True:
            key_title   = f'item_title_{idx}'
            key_content = f'item_content_{idx}'
            if key_title not in data and key_content not in data:
                break
            items.append({
                'title':   data.pop(key_title, ''),
                'content': data.pop(key_content, ''),
            })
            idx += 1
        data['items'] = items

    try:
        hwpx_bytes = generate_hwpx(report_type, data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    filename = make_filename(report_type, data)

    return send_file(
        io.BytesIO(hwpx_bytes),
        mimetype='application/hwp+zip',
        as_attachment=True,
        download_name=filename,
    )


if __name__ == '__main__':
    print("=" * 50)
    print("  세종시설관리공단 보고서 자동화 시스템")
    print("  http://localhost:5000  에서 실행 중입니다.")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
