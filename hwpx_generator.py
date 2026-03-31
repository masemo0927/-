#!/usr/bin/env python3
"""
HWPX Generator for 세종시설관리공단 Report Automation
hwpx = ZIP 컨테이너 기반 HWP XML 문서
"""

import zipfile
import io


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def xml_escape(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


# ─────────────────────────────────────────────
# 고정 XML 블록들
# ─────────────────────────────────────────────

CONTAINER_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<container>\n  <rootfiles>\n    <rootfile full-path="Contents/content.hpf" media-type="application/oebps-package+xml"/>\n  </rootfiles>\n</container>'

CONTENT_HPF = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<opf:package version="1.0" xmlns:opf="http://www.idpf.org/2007/opf">\n  <opf:metadata>\n    <opf:title>세종시설관리공단 보고서</opf:title>\n    <opf:creator>세종시설관리공단</opf:creator>\n  </opf:metadata>\n  <opf:manifest>\n    <opf:item id="header" href="header.xml" media-type="application/xml"/>\n    <opf:item id="section0" href="section0.xml" media-type="application/xml"/>\n  </opf:manifest>\n  <opf:spine>\n    <opf:itemref idref="section0"/>\n  </opf:spine>\n</opf:package>'


def create_header_xml():
    """header.xml: 폰트, charPr, paraPr, 스타일 정의"""

    # ── fontface 공통 패턴 (HANGUL/LATIN/HANJA 동일하게 7개 폰트 등록)
    def fontface_block(lang):
        return f"""      <hh:fontface lang="{lang}">
        <hh:font id="0" face="굴림" type="TTF" isEmbedded="0"/>
        <hh:font id="1" face="맑은 고딕" type="TTF" isEmbedded="0"/>
        <hh:font id="2" face="한컴바탕" type="TTF" isEmbedded="0"/>
        <hh:font id="3" face="함초롬돋움" type="TTF" isEmbedded="0"/>
        <hh:font id="4" face="함초롬바탕" type="TTF" isEmbedded="0"/>
        <hh:font id="5" face="휴먼명조" type="TTF" isEmbedded="0"/>
        <hh:font id="6" face="HY헤드라인M" type="TTF" isEmbedded="0"/>
      </hh:fontface>"""

    # ── charPr 생성 헬퍼
    # height: 1/100pt 단위  font_id: 폰트 인덱스
    def char_pr(cid, height, font_id):
        fi = font_id
        return f"""      <hh:charPr id="{cid}" height="{height}" textColor="#000000" shadeColor="#FFFFFF" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="0">
        <hh:font hangul="{fi}" latin="{fi}" hanja="{fi}" japanese="{fi}" other="{fi}" symbol="{fi}" user="{fi}"/>
        <hh:ratio stretch="100" xscale="100" yscale="100"/>
        <hh:spacing letterSpacing="0"/>
        <hh:relSz baseSize="100" basePosition="0"/>
        <hh:offset dx="0" dy="0"/>
        <hh:bold value="0"/>
        <hh:italic value="0"/>
        <hh:underLine type="NONE" shape="SOLID" color="#000000"/>
        <hh:strikeout type="NONE" shape="SOLID" color="#000000"/>
        <hh:outline type="NONE"/>
        <hh:shadow type="NONE" color="#000000" dx="0" dy="0"/>
      </hh:charPr>"""

    # ── paraPr 생성 헬퍼
    # align: JUSTIFY / CENTER / RIGHT
    # line_ratio: 160, 130, 120
    # left_indent: 1/100mm 단위 (0, 1000=10mm, 1500=15mm)
    def para_pr(pid, align, line_ratio, left_indent=0):
        return f"""      <hh:paraPr id="{pid}" tabStop="1000" condense="0" fontLineHeight="0" snapToGrid="1" suppressOverlap="0" checked="0">
        <hh:align horizontal="{align}" vertical="BASELINE"/>
        <hh:heading type="NONE" idRef="0" level="0"/>
        <hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="NORMAL" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" columnBreakBefore="0"/>
        <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
        <hh:lineSpacing type="RATIO" value="{line_ratio}"/>
        <hh:indent left="{left_indent}" right="0" indent="0" firstIndent="0" hangingIndent="0"/>
        <hh:border borderFillIDRef="0" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/>
        <hh:margins marginLeft="0" marginRight="0" marginTop="0" marginBottom="0"/>
        <hh:tabDef autoTabLeft="0" autoTabRight="0"/>
        <hh:numbering numerable="0"/>
        <hh:bullet bullable="0"/>
      </hh:paraPr>"""

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"
         xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hh:beginNum para="1" char="1"/>
  <hh:refList>
    <hh:fontfaces>
{fontface_block("HANGUL")}
{fontface_block("LATIN")}
{fontface_block("HANJA")}
      <hh:fontface lang="JAPANESE">
        <hh:font id="0" face="굴림" type="TTF" isEmbedded="0"/>
      </hh:fontface>
      <hh:fontface lang="OTHER">
        <hh:font id="0" face="굴림" type="TTF" isEmbedded="0"/>
      </hh:fontface>
      <hh:fontface lang="SYMBOL">
        <hh:font id="0" face="Symbol" type="TTF" isEmbedded="0"/>
      </hh:fontface>
      <hh:fontface lang="USER">
        <hh:font id="0" face="굴림" type="TTF" isEmbedded="0"/>
      </hh:fontface>
    </hh:fontfaces>
    <hh:borderFills>
      <hh:borderFill id="1" threeD="0" shadow="0" centerLine="0" breakCellSeparateLine="0">
        <hh:slash type="NONE"/>
        <hh:backSlash type="NONE"/>
        <hh:leftBorder type="SOLID" width="0.12mm" color="#000000"/>
        <hh:rightBorder type="SOLID" width="0.12mm" color="#000000"/>
        <hh:topBorder type="SOLID" width="0.12mm" color="#000000"/>
        <hh:bottomBorder type="SOLID" width="0.12mm" color="#000000"/>
        <hh:diagonal type="NONE" width="0.12mm" color="#000000"/>
        <hh:fillInfo><hh:noFill/></hh:fillInfo>
      </hh:borderFill>
    </hh:borderFills>
    <hh:charProperties>
{char_pr(0, 2200, 6)}
{char_pr(1, 1600, 6)}
{char_pr(2, 1500, 5)}
{char_pr(3, 1000, 3)}
{char_pr(4, 1200, 1)}
{char_pr(5, 1200, 1)}
{char_pr(6, 1500, 5)}
    </hh:charProperties>
    <hh:paraProperties>
{para_pr(0, "JUSTIFY", 160, 0)}
{para_pr(1, "JUSTIFY", 160, 1000)}
{para_pr(2, "JUSTIFY", 160, 1500)}
{para_pr(3, "CENTER",  160, 0)}
{para_pr(4, "RIGHT",   160, 0)}
{para_pr(5, "CENTER",  120, 0)}
{para_pr(6, "CENTER",  130, 0)}
    </hh:paraProperties>
    <hh:styles>
      <hh:style id="0" type="PARA" name="바탕글" engName="Normal"
                paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042"/>
    </hh:styles>
  </hh:refList>
</hh:head>"""


# ─────────────────────────────────────────────
# 단락 빌더
# ─────────────────────────────────────────────

# 페이지 설정 (A4, HMM = 1/100mm 단위)
# 좌우여백 56.7mm, 상하여백 42.5mm, 머리말 28.3mm
SEC_PR_XML = """      <hp:secPr memoAttrRef="0">
        <hp:startNum pageStartsOn="BOTH" pageNum="1"/>
        <hp:pagePr paperWidth="21000" paperHeight="29700"
                   leftMargin="5670" rightMargin="5670"
                   topMargin="4250" bottomMargin="4250"
                   headerLen="2830" footerLen="0"
                   bindingMargin="0" switchBind="0"
                   dispensingPaper="0" bookFold="0" bookFoldCount="0"/>
        <hp:pageBorderFill type="BOTH" borderFillIDRef="0"
                           textDist="0" headerDist="0"
                           fill="0" border="0" headerOffset="0"/>
        <hp:masterPage bodyTextFrame="0">
          <hp:masterPageRef type="EVEN" masterPageIDRef="0"/>
          <hp:masterPageRef type="ODD" masterPageIDRef="0"/>
          <hp:masterPageRef type="FIRST" masterPageIDRef="0"/>
        </hp:masterPage>
        <hp:footnote lineWidth="150" lineAlignment="LEFT" textDist="850" noteDist="567"/>
        <hp:endnote lineWidth="150" textDist="850"/>
        <hp:pageFillColors bodyFill="0" headerFill="0" footerFill="0"/>
        <hp:lineGrid type="NONE" lineStep="0" charStep="0"/>
        <hp:charGrid type="NONE" lineStep="0" charStep="0"/>
        <hp:tabStop repeatCount="40"/>
      </hp:secPr>"""


class ParagraphBuilder:
    def __init__(self):
        self.para_id = 1
        self.paragraphs = []

    def add(self, text, char_pr_id, para_pr_id, first=False):
        self.paragraphs.append({
            'id': self.para_id,
            'char_pr_id': char_pr_id,
            'para_pr_id': para_pr_id,
            'text': text,
            'first': first,
        })
        self.para_id += 1

    def empty(self):
        """빈 줄 추가"""
        self.add('', 2, 0)

    def title(self, text):
        """보고서 제목 (charPr=0, paraPr=3, 최초 단락에 secPr 포함)"""
        self.add(text, 0, 3, first=(self.para_id == 1))

    def date_line(self, text):
        """날짜/팀명/담당자 줄 (charPr=3, paraPr=4)"""
        self.add(text, 3, 4)

    def section(self, text):
        """□ 소제목 (charPr=1, paraPr=0)"""
        self.add(text, 1, 0)

    def item(self, text):
        """○ 항목 (charPr=2, paraPr=1)"""
        self.add(text, 2, 1)

    def sub_item(self, text):
        """  - 세부 항목 (charPr=2, paraPr=2)"""
        self.add(text, 2, 2)

    def attachment(self, text="붙임  관련자료 1부."):
        """붙임 (charPr=6, paraPr=0)"""
        self.add(text, 6, 0)

    def ending(self, text="세종시설관리공단  끝."):
        """끝. (charPr=6, paraPr=4)"""
        self.add(text, 6, 4)

    def to_xml(self):
        lines = []
        for p in self.paragraphs:
            cid = p['char_pr_id']
            ppid = p['para_pr_id']
            pid = p['id']
            text = xml_escape(p['text'])
            sec = SEC_PR_XML if p['first'] else ""
            if sec:
                ppr_inner = sec
            else:
                ppr_inner = ""
            lines.append(
                f'  <hp:p id="{pid}">\n'
                f'    <hp:pPr charPrIDRef="{cid}" paraPrIDRef="{ppid}">\n'
                f'{ppr_inner}'
                f'    </hp:pPr>\n'
                f'    <hp:run>\n'
                f'      <hp:charPrIDRef id="{cid}"/>\n'
                f'      <hp:t>{text}</hp:t>\n'
                f'    </hp:run>\n'
                f'  </hp:p>'
            )
        return '\n'.join(lines)


def create_section_xml(paragraphs_xml):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"
        pageCount="0" hideFirstHeader="0">
{paragraphs_xml}
</hs:sec>"""


# ─────────────────────────────────────────────
# 보고서 종류별 단락 구성
# ─────────────────────────────────────────────

def build_review_report(data):
    """검토 보고"""
    b = ParagraphBuilder()
    b.title(data.get('title', ''))
    b.date_line(f"{data.get('date', '')}  {data.get('team', '')} {data.get('person', '')} ☎ {data.get('phone', '')}")
    b.empty()

    if data.get('background'):
        b.section("□ 검토배경")
        for line in _split_lines(data['background']):
            b.item(f"○ {line}")
        b.empty()

    items = data.get('items', [])
    if items:
        b.section("□ 검토결과")
        for item in items:
            if item.get('title'):
                b.item(f"○ {item['title']}")
            for sub in _split_lines(item.get('content', '')):
                b.sub_item(f"- {sub}")
        b.empty()

    if data.get('conclusion'):
        b.section("□ 결론")
        for line in _split_lines(data['conclusion']):
            b.item(f"○ {line}")
        b.empty()

    b.attachment()
    b.ending()
    return b.to_xml()


def build_plan_report(data):
    """계획 보고"""
    b = ParagraphBuilder()
    b.title(data.get('title', ''))
    b.date_line(f"{data.get('date', '')}  {data.get('team', '')} {data.get('person', '')} ☎ {data.get('phone', '')}")
    b.empty()

    if data.get('background'):
        b.section("□ 추진배경")
        for line in _split_lines(data['background']):
            b.item(f"○ {line}")
        b.empty()

    if data.get('purpose'):
        b.section("□ 추진목적")
        for line in _split_lines(data['purpose']):
            b.item(f"○ {line}")
        b.empty()

    if data.get('current_status'):
        b.section("□ 현황")
        for line in _split_lines(data['current_status']):
            b.item(f"○ {line}")
        b.empty()

    b.section("□ 추진계획")
    if data.get('period'):
        b.item(f"○ 기간 : {data['period']}")
    if data.get('target'):
        b.item(f"○ 대상 : {data['target']}")
    if data.get('content'):
        b.item("○ 내용")
        for line in _split_lines(data['content']):
            b.sub_item(f"- {line}")
    if data.get('budget'):
        b.item(f"○ 예산 : {data['budget']}")
    b.empty()

    if data.get('effect'):
        b.section("□ 기대효과")
        for line in _split_lines(data['effect']):
            b.item(f"○ {line}")
        b.empty()

    if data.get('schedule'):
        b.section("□ 향후일정")
        for line in _split_lines(data['schedule']):
            b.item(f"○ {line}")
        b.empty()

    b.attachment()
    b.ending()
    return b.to_xml()


def build_inspection_report(data):
    """현장점검 보고"""
    b = ParagraphBuilder()
    b.title(data.get('title', ''))
    b.date_line(f"{data.get('date', '')}  {data.get('team', '')} {data.get('person', '')} ☎ {data.get('phone', '')}")
    b.empty()

    b.section("□ 점검 개요")
    if data.get('inspection_date'):
        b.item(f"○ 일 시 : {data['inspection_date']}")
    if data.get('location'):
        b.item(f"○ 장 소 : {data['location']}")
    b.empty()

    if data.get('results'):
        b.section("□ 점검결과")
        for line in _split_lines(data['results']):
            b.item(f"○ {line}")
        b.empty()

    if data.get('actions'):
        b.section("□ 조치사항")
        for line in _split_lines(data['actions']):
            b.item(f"○ {line}")
        b.empty()

    b.attachment()
    b.ending()
    return b.to_xml()


def build_seminar_report(data):
    """세미나/행사 개최 계획"""
    b = ParagraphBuilder()
    b.title(data.get('title', ''))
    b.date_line(f"{data.get('date', '')}  {data.get('team', '')} {data.get('person', '')} ☎ {data.get('phone', '')}")
    b.empty()

    b.section("□ 행사 개요")
    if data.get('event_name'):
        b.item(f"○ 행사명 : {data['event_name']}")
    if data.get('event_date'):
        b.item(f"○ 일   시 : {data['event_date']}")
    if data.get('venue'):
        b.item(f"○ 장   소 : {data['venue']}")
    b.empty()

    if data.get('main_content'):
        b.section("□ 주요내용")
        for line in _split_lines(data['main_content']):
            b.item(f"○ {line}")
        b.empty()

    if data.get('budget'):
        b.section("□ 예산")
        for line in _split_lines(data['budget']):
            b.item(f"○ {line}")
        b.empty()

    b.attachment()
    b.ending()
    return b.to_xml()


def _split_lines(text):
    """줄바꿈 기준으로 분리, 빈 줄 제거"""
    if not text:
        return []
    return [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]


# ─────────────────────────────────────────────
# HWPX 패키징
# ─────────────────────────────────────────────

REPORT_BUILDERS = {
    'review':     build_review_report,
    'plan':       build_plan_report,
    'inspection': build_inspection_report,
    'seminar':    build_seminar_report,
}

REPORT_NAMES = {
    'review':     '검토보고',
    'plan':       '계획보고',
    'inspection': '현장점검보고',
    'seminar':    '세미나행사개최계획',
}


def generate_hwpx(report_type, data):
    """
    hwpx 파일 바이트를 반환한다.
    ZIP 컨테이너 규격:
      - mimetype: ZIP_STORED, extra 없이, 가장 먼저
      - 나머지: ZIP_DEFLATED
    """
    builder = REPORT_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unknown report type: {report_type}")

    paras_xml = builder(data)
    section_xml = create_section_xml(paras_xml)
    header_xml = create_header_xml()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype: 압축 없이(ZIP_STORED), extra field 없이, 반드시 첫 번째
        mi = zipfile.ZipInfo('mimetype')
        mi.compress_type = zipfile.ZIP_STORED
        mi.extra = b''
        zf.writestr(mi, 'application/hwp+zip')

        zf.writestr('META-INF/container.xml', CONTAINER_XML.encode('utf-8'))
        zf.writestr('Contents/content.hpf',   CONTENT_HPF.encode('utf-8'))
        zf.writestr('Contents/header.xml',    header_xml.encode('utf-8'))
        zf.writestr('Contents/section0.xml',  section_xml.encode('utf-8'))

    return buf.getvalue()


def make_filename(report_type, data):
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    rname = REPORT_NAMES.get(report_type, report_type)
    title = data.get('title', '문서')
    # 파일명에 사용 불가한 문자 제거
    safe_title = ''.join(c for c in title if c not in r'\/:*?"<>|').strip()[:30]
    return f"{today}_{rname}_{safe_title}.hwpx"
