from __future__ import annotations

import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://barunjoon.com"
BLOG_HOME = "https://blog.naver.com/barnjun"
BLOG_RSS = "https://rss.blog.naver.com/barnjun.xml"
NAVER_MAP = "https://naver.me/GeUXqdb0"
NAVER_PLACE = "https://map.naver.com/p/entry/place/36351446"
CLINIC_NAME = "바른준한의원"
DOCTOR = "조형준"
PHONE = "031-722-2161"
ADDRESS = "경기도 성남시 중원구 광명로 119, 금성빌딩 2층"
POSTAL_CODE = "13357"

BLOG_START = "<!-- NAVER_BLOG_SYNC_START -->"
BLOG_END = "<!-- NAVER_BLOG_SYNC_END -->"
BLOG_CSS_START = "/* NAVER_BLOG_SYNC_CSS_START */"
BLOG_CSS_END = "/* NAVER_BLOG_SYNC_CSS_END */"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def text_only(value: str, limit: int = 180) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value


def parse_date(value: str) -> tuple[str, str]:
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone()
        return local.date().isoformat(), local.strftime("%Y.%m.%d")
    except Exception:
        return "", ""


def fetch_blog_posts(limit: int = 20) -> list[dict]:
    req = urllib.request.Request(
        BLOG_RSS,
        headers={"User-Agent": "Mozilla/5.0 (compatible; BarunjoonWebsiteSync/1.0; +https://barunjoon.com/)"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = root.findall("./channel/item")
    posts: list[dict] = []
    for item in items[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or ""
        iso_date, display_date = parse_date(pub)
        if not title or not link:
            continue
        posts.append({
            "title": title,
            "url": link,
            "excerpt": text_only(desc, 190),
            "date": iso_date,
            "display_date": display_date,
        })
    return posts


def clinic_graph() -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": ["MedicalClinic", "LocalBusiness"],
                "@id": f"{BASE}/#clinic",
                "name": CLINIC_NAME,
                "alternateName": ["수진역 바른준한의원", "수진역 한의원 바른준한의원"],
                "url": f"{BASE}/",
                "telephone": PHONE,
                "logo": {"@type": "ImageObject", "url": f"{BASE}/favicon.png"},
                "image": [f"{BASE}/naver-thumb.png", f"{BASE}/01-main.jpg"],
                "description": "수진역 2번 출구 인근의 한의원으로 통증, 교통사고 후유증, 비염·후비루, 소화기, 소아, 여성건강, 보약·한약, 공진단, 약침 등을 상담합니다.",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "광명로 119, 금성빌딩 2층",
                    "addressLocality": "성남시 중원구",
                    "addressRegion": "경기도",
                    "postalCode": POSTAL_CODE,
                    "addressCountry": "KR",
                },
                "areaServed": [
                    {"@type": "City", "name": "성남시"},
                    {"@type": "AdministrativeArea", "name": "성남시 중원구"},
                ],
                "hasMap": NAVER_MAP,
                "sameAs": [BLOG_HOME, NAVER_PLACE],
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        "opens": "09:00",
                        "closes": "19:00",
                    },
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": "Saturday",
                        "opens": "09:00",
                        "closes": "14:00",
                    },
                ],
                "employee": {"@id": f"{BASE}/#doctor"},
            },
            {
                "@type": "Person",
                "@id": f"{BASE}/#doctor",
                "name": DOCTOR,
                "jobTitle": "대표원장 · 한의사",
                "worksFor": {"@id": f"{BASE}/#clinic"},
                "alumniOf": {"@type": "EducationalOrganization", "name": "부산대학교 한의학전문대학원"},
            },
            {
                "@type": "WebSite",
                "@id": f"{BASE}/#website",
                "url": f"{BASE}/",
                "name": "바른준한의원 공식 홈페이지",
                "publisher": {"@id": f"{BASE}/#clinic"},
                "inLanguage": "ko-KR",
            },
        ],
    }


def replace_first_jsonld(doc: str, data: dict) -> str:
    block = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"
    pattern = r'<script type="application/ld\+json">.*?</script>'
    if re.search(pattern, doc, flags=re.S):
        return re.sub(pattern, block, doc, count=1, flags=re.S)
    return doc.replace("</head>", block + "\n</head>", 1)


def blog_cards(posts: list[dict], count: int = 4) -> str:
    if not posts:
        return (
            '<a class="blog-sync-card" href="https://blog.naver.com/barnjun" target="_blank" rel="noopener">'
            '<span class="blog-sync-kicker">공식 네이버 블로그</span><h3>바른준한의원 네이버 블로그</h3>'
            '<p>한의원 소식과 건강정보를 네이버 블로그에서도 확인하실 수 있습니다.</p><span class="blog-sync-more">블로그 바로가기 →</span></a>'
        )
    out = []
    for p in posts[:count]:
        date = f'<time datetime="{esc(p["date"])}">{esc(p["display_date"])}</time>' if p.get("date") else ""
        excerpt = f'<p>{esc(p["excerpt"])}</p>' if p.get("excerpt") else ""
        out.append(
            f'<a class="blog-sync-card" href="{esc(p["url"])}" target="_blank" rel="noopener">'
            f'<span class="blog-sync-kicker">NAVER BLOG {date}</span>'
            f'<h3>{esc(p["title"])}</h3>{excerpt}<span class="blog-sync-more">네이버 블로그에서 읽기 →</span></a>'
        )
    return "".join(out)


def homepage_blog_section(posts: list[dict]) -> str:
    return f'''{BLOG_START}
<section class="section" id="naver-blog">
  <div class="container">
    <div class="section-label">OFFICIAL NAVER BLOG</div>
    <h2 class="section-title">바른준한의원 네이버 블로그 최신 글</h2>
    <p class="section-desc">기존 네이버 블로그의 건강정보와 한의원 소식을 공식 홈페이지에서도 찾기 쉽게 연결했습니다.</p>
    <div class="blog-sync-grid">{blog_cards(posts, 4)}</div>
    <div class="blog-sync-actions"><a class="btn primary" href="naver-blog.html">블로그 글 모아보기 →</a><a class="btn" href="{BLOG_HOME}" target="_blank" rel="noopener">네이버 블로그 바로가기 →</a></div>
  </div>
</section>
{BLOG_END}'''


def ensure_homepage(posts: list[dict]) -> None:
    path = ROOT / "index.html"
    doc = path.read_text(encoding="utf-8")
    if BLOG_RSS not in doc:
        doc = doc.replace(
            '<link rel="canonical" href="https://barunjoon.com/">',
            '<link rel="canonical" href="https://barunjoon.com/">\n<link rel="alternate" type="application/rss+xml" title="바른준한의원 네이버 블로그 RSS" href="https://rss.blog.naver.com/barnjun.xml">',
            1,
        )
    doc = replace_first_jsonld(doc, clinic_graph())
    if 'href="naver-blog.html"' not in doc:
        needle = '      <a href="index.html#location">오시는 길</a>\n    </nav>'
        repl = '      <a href="index.html#location">오시는 길</a>\n      <a href="naver-blog.html">네이버 블로그</a>\n    </nav>'
        if needle in doc:
            doc = doc.replace(needle, repl, 1)
    css = f'''{BLOG_CSS_START}
.blog-sync-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:26px}}
.blog-sync-card{{padding:22px;border:1px solid #e1e9e3;border-radius:16px;background:#fff;transition:.18s ease}}
.blog-sync-card:hover{{transform:translateY(-2px);box-shadow:0 10px 26px rgba(39,93,61,.07)}}
.blog-sync-kicker{{display:block;color:#2b8552;font-size:10px;font-weight:900;letter-spacing:.8px}}
.blog-sync-kicker time{{margin-left:6px;color:#89958e;font-weight:700;letter-spacing:0}}
.blog-sync-card h3{{margin:8px 0 8px;font-size:17px;line-height:1.45;color:#34443b}}
.blog-sync-card p{{margin:0;color:#6d7b73;font-size:12px;line-height:1.7}}
.blog-sync-more{{display:inline-block;margin-top:13px;color:#267a4a;font-size:11px;font-weight:900}}
.blog-sync-actions{{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}}
@media(max-width:780px){{.blog-sync-grid{{grid-template-columns:1fr}}}}
{BLOG_CSS_END}
'''
    if BLOG_CSS_START in doc and BLOG_CSS_END in doc:
        doc = re.sub(re.escape(BLOG_CSS_START) + r".*?" + re.escape(BLOG_CSS_END), css.strip(), doc, count=1, flags=re.S)
    else:
        doc = doc.replace("footer{", css + "\nfooter{", 1)
    section = homepage_blog_section(posts)
    if BLOG_START in doc and BLOG_END in doc:
        doc = re.sub(re.escape(BLOG_START) + r".*?" + re.escape(BLOG_END), section, doc, count=1, flags=re.S)
    else:
        doc = doc.replace("</main>", section + "\n</main>", 1)
    if '공식 네이버 블로그' not in doc.split("<footer>", 1)[-1]:
        doc = doc.replace(
            '      평일 09:00~19:00 · 토요일 09:00~14:00 · 점심시간 13:00~14:00 · 일요일·공휴일 휴진<br><br>',
            '      평일 09:00~19:00 · 토요일 09:00~14:00 · 점심시간 13:00~14:00 · 일요일·공휴일 휴진<br>\n      <a href="https://blog.naver.com/barnjun" target="_blank" rel="noopener">공식 네이버 블로그</a> · <a href="naver-blog.html">블로그 글 모아보기</a><br><br>',
            1,
        )
    path.write_text(doc, encoding="utf-8")


def ensure_columns() -> None:
    path = ROOT / "columns.html"
    if not path.exists():
        return
    doc = path.read_text(encoding="utf-8")
    if 'name="robots"' not in doc:
        doc = doc.replace(
            '<meta name="description" content="통증, 교통사고 후유증, 비염, 소화기, 소아, 여성건강, 공진단, 약침, 보약에 관한 바른준한의원 건강칼럼입니다.">',
            '<meta name="description" content="통증, 교통사고 후유증, 비염, 소화기, 소아, 여성건강, 공진단, 약침, 보약에 관한 바른준한의원 건강칼럼입니다.">\n<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">\n<link rel="icon" type="image/png" href="https://barunjoon.com/favicon.png">',
            1,
        )
    if 'property="og:title"' not in doc:
        og = '\n<meta property="og:type" content="website"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="바른준한의원"><meta property="og:title" content="건강칼럼 | 성남 수진역 바른준한의원"><meta property="og:description" content="바른준한의원이 진료실에서 자주 받는 건강 질문을 알기 쉽게 정리한 공식 건강정보 페이지입니다."><meta property="og:url" content="https://barunjoon.com/columns.html"><meta property="og:image" content="https://barunjoon.com/naver-thumb.png">'
        doc = doc.replace('<link rel="canonical" href="https://barunjoon.com/columns.html">', '<link rel="canonical" href="https://barunjoon.com/columns.html">' + og, 1)
    if 'href="naver-blog.html"' not in doc:
        doc = doc.replace('<a href="columns.html">건강칼럼</a>', '<a href="columns.html">건강칼럼</a><a href="naver-blog.html">네이버 블로그</a>', 1)
    if 'OFFICIAL NAVER BLOG' not in doc:
        callout = f'''<section class="cta"><div class="wrap"><div class="cta-box"><div class="label">OFFICIAL NAVER BLOG</div><h2>기존 네이버 블로그 글도 함께 보세요</h2><p>바른준한의원 공식 네이버 블로그의 최신 글을 홈페이지에서 한 번에 확인할 수 있도록 연결했습니다.</p><div class="buttons"><a class="btn primary" href="naver-blog.html">최신 블로그 글 보기 →</a><a class="btn" href="{BLOG_HOME}" target="_blank" rel="noopener">네이버 블로그 바로가기 →</a></div></div></div></section>'''
        doc = doc.replace("<footer>", callout + "\n<footer>", 1)
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "바른준한의원 건강칼럼",
        "url": f"{BASE}/columns.html",
        "inLanguage": "ko-KR",
        "publisher": {"@id": f"{BASE}/#clinic"},
        "isPartOf": {"@id": f"{BASE}/#website"},
    }
    if 'application/ld+json' not in doc:
        doc = doc.replace("</head>", '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + "</script>\n</head>", 1)
    path.write_text(doc, encoding="utf-8")


def page_meta(path: Path) -> tuple[str, str]:
    doc = path.read_text(encoding="utf-8")
    t = re.search(r"<title>(.*?)</title>", doc, flags=re.S | re.I)
    d = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', doc, flags=re.I)
    title = text_only(t.group(1), 140) if t else path.stem
    desc = html.unescape(d.group(1)).strip() if d else ""
    return title, desc


def ensure_article_schema() -> None:
    for path in sorted(ROOT.glob("column-*.html")):
        doc = path.read_text(encoding="utf-8")
        if '"@type":"Article"' in doc or '"@type": "Article"' in doc:
            continue
        title, desc = page_meta(path)
        data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title.split(" | ")[0],
            "description": desc,
            "mainEntityOfPage": f"{BASE}/{path.name}",
            "url": f"{BASE}/{path.name}",
            "inLanguage": "ko-KR",
            "author": {"@type": "Organization", "name": CLINIC_NAME, "url": f"{BASE}/"},
            "publisher": {"@id": f"{BASE}/#clinic"},
            "image": f"{BASE}/naver-thumb.png",
        }
        block = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"
        doc = doc.replace("</head>", block + "</head>", 1)
        path.write_text(doc, encoding="utf-8")


def generate_naver_blog_page(posts: list[dict]) -> None:
    items = []
    for i, p in enumerate(posts, 1):
        li = {"@type": "ListItem", "position": i, "url": p["url"], "name": p["title"]}
        if p.get("date"):
            li["datePublished"] = p["date"]
        items.append(li)
    graph = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "바른준한의원 공식 네이버 블로그 최신 글",
        "url": f"{BASE}/naver-blog.html",
        "inLanguage": "ko-KR",
        "about": {"@id": f"{BASE}/#clinic"},
        "mainEntity": {"@type": "ItemList", "itemListElement": items},
    }
    cards = blog_cards(posts, 20)
    if not posts:
        cards += '<a class="card" href="https://blog.naver.com/barnjun/223282749562" target="_blank" rel="noopener"><span class="kicker">FEATURED</span><h2>조형준 원장 이야기</h2><p>바른준한의원 원장 소개 글입니다.</p><span class="more">네이버 블로그에서 읽기 →</span></a>'
    page = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>네이버 블로그 최신 글 | 성남 수진역 바른준한의원</title>
<meta name="description" content="바른준한의원 공식 네이버 블로그의 건강정보와 한의원 소식을 홈페이지에서 한 번에 확인하세요.">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{BASE}/naver-blog.html"><link rel="icon" type="image/png" href="{BASE}/favicon.png"><link rel="alternate" type="application/rss+xml" title="바른준한의원 네이버 블로그 RSS" href="{BLOG_RSS}">
<meta property="og:type" content="website"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="바른준한의원"><meta property="og:title" content="바른준한의원 공식 네이버 블로그 최신 글"><meta property="og:description" content="건강정보와 한의원 소식을 공식 홈페이지에서 모아봅니다."><meta property="og:url" content="{BASE}/naver-blog.html"><meta property="og:image" content="{BASE}/naver-thumb.png">
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False, separators=(",", ":"))}</script>
<style>
:root{{--green:#267a4a;--dark:#2d3d34;--muted:#68776f;--line:#e1e9e3;--mint:#eef8f2}}*{{box-sizing:border-box}}body{{margin:0;font-family:"Pretendard","Noto Sans KR",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--dark);line-height:1.7;word-break:keep-all}}a{{color:inherit;text-decoration:none}}.wrap{{width:min(980px,90%);margin:0 auto}}header{{border-bottom:1px solid #eef2ef}}.head{{min-height:76px;display:flex;align-items:center;justify-content:space-between;gap:20px}}.brand{{font-size:19px;font-weight:900;color:var(--green)}}nav{{display:flex;gap:18px;font-size:12px;font-weight:800;color:#53665b}}.hero{{padding:58px 0 48px;background:var(--mint)}}.label,.kicker{{color:var(--green);font-size:10px;font-weight:900;letter-spacing:1px}}h1{{font-size:42px;line-height:1.2;letter-spacing:-1.8px;margin:10px 0 16px}}.lead{{max-width:780px;margin:0;color:#5f7067;font-size:15px}}.actions{{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}}.btn{{display:inline-flex;padding:10px 16px;border:1px solid #dfe7e1;border-radius:999px;background:#fff;font-size:12px;font-weight:900}}.btn.primary{{background:var(--green);border-color:var(--green);color:#fff}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;padding:44px 0 64px}}.card,.blog-sync-card{{display:block;padding:24px;border:1px solid var(--line);border-radius:16px;background:#fff}}.card h2,.blog-sync-card h3{{font-size:19px;line-height:1.45;margin:8px 0 10px}}.card p,.blog-sync-card p{{font-size:12px;color:var(--muted);margin:0}}.more,.blog-sync-more{{display:inline-block;margin-top:13px;color:var(--green);font-size:11px;font-weight:900}}.blog-sync-kicker{{display:block;color:var(--green);font-size:10px;font-weight:900;letter-spacing:.8px}}.blog-sync-kicker time{{margin-left:6px;color:#89958e;letter-spacing:0}}footer{{padding:42px 0 55px;background:#edf5f0;color:#64736b;font-size:11px;line-height:1.9}}@media(max-width:720px){{.head{{padding:17px 0;display:block}}nav{{margin-top:10px;overflow-x:auto;white-space:nowrap}}h1{{font-size:34px}}.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class="wrap head"><a class="brand" href="index.html">바른준한의원</a><nav><a href="index.html#clinic">진료분야</a><a href="columns.html">건강칼럼</a><a href="naver-blog.html">네이버 블로그</a><a href="index.html#location">오시는 길</a></nav></div></header>
<section class="hero"><div class="wrap"><div class="label">OFFICIAL NAVER BLOG</div><h1>바른준한의원 네이버 블로그 최신 글</h1><p class="lead">기존 네이버 블로그의 글 제목과 요약을 공식 홈페이지에 연결해 검색엔진과 AI가 바른준한의원의 공개 콘텐츠 관계를 더 쉽게 이해하도록 구성했습니다. 전체 글은 네이버 블로그 원문에서 확인할 수 있습니다.</p><div class="actions"><a class="btn primary" href="{BLOG_HOME}" target="_blank" rel="noopener">네이버 블로그 바로가기 →</a><a class="btn" href="columns.html">홈페이지 건강칼럼 보기 →</a></div></div></section>
<main class="wrap"><div class="grid">{cards}</div></main>
<footer><div class="wrap"><strong>바른준한의원</strong><br>{ADDRESS} · 수진역 2번 출구 인근<br>대표전화 {PHONE}<br>공식 네이버 블로그: {BLOG_HOME}<br><br>※ 이 페이지는 공식 네이버 블로그의 공개 글 목록을 연결하며, 원문은 네이버 블로그에 있습니다.</div></footer>
</body></html>'''
    (ROOT / "naver-blog.html").write_text(page, encoding="utf-8")


def generate_robots() -> None:
    text = f'''User-agent: *
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

Sitemap: {BASE}/sitemap.xml
'''
    (ROOT / "robots.txt").write_text(text, encoding="utf-8")


def generate_llms(posts: list[dict]) -> None:
    latest = "\n".join(f'- [{p["title"]}]({p["url"]})' for p in posts[:8])
    if not latest:
        latest = f"- [공식 네이버 블로그]({BLOG_HOME})"
    text = f'''# 바른준한의원

> 경기도 성남시 중원구 수진역 2번 출구 인근의 한의원. 대표원장 조형준.

## 공식 정보
- 공식 홈페이지: {BASE}/
- 공식 네이버 블로그: {BLOG_HOME}
- 네이버 지도/길찾기: {NAVER_MAP}
- 주소: {ADDRESS}
- 전화: {PHONE}
- 평일 진료: 09:00-19:00 (점심 13:00-14:00)
- 토요일 진료: 09:00-14:00
- 일요일·공휴일: 휴진

## 대표원장
- 이름: {DOCTOR}
- 직함: 대표원장, 한의사
- 학력: 부산대학교 한의학전문대학원 졸업, 한의학 석사
- 석사논문: 요추 추간판탈출증(디스크)의 한의학적 치료 고찰

## 주요 진료 정보 페이지
- [통증 클리닉]({BASE}/pain.html)
- [자동차사고 후유증]({BASE}/traffic.html)
- [심신 클리닉]({BASE}/mind.html)
- [소화기 클리닉]({BASE}/digestive.html)
- [알레르기 클리닉]({BASE}/allergy.html)
- [체질 클리닉]({BASE}/constitution.html)
- [소아 클리닉]({BASE}/children.html)
- [여성 클리닉]({BASE}/women.html)
- [보약 클리닉]({BASE}/tonic.html)
- [공진단 클리닉]({BASE}/gongjindan.html)
- [약침 클리닉]({BASE}/pharmacopuncture.html)
- [건강칼럼]({BASE}/columns.html)
- [네이버 블로그 최신 글 모음]({BASE}/naver-blog.html)

## 공식 네이버 블로그 최근 글
{latest}

## 사용 시 주의
이 사이트의 건강정보는 일반적인 정보 제공을 위한 것이며 개인의 진단이나 치료를 대신하지 않습니다. 의료적 판단이 필요한 경우 실제 진료와 적절한 검사를 우선합니다.
'''
    (ROOT / "llms.txt").write_text(text, encoding="utf-8")


def generate_sitemap() -> None:
    html_files = sorted(ROOT.glob("*.html"), key=lambda p: (p.name != "index.html", p.name))
    urls = []
    for p in html_files:
        loc = f"{BASE}/" if p.name == "index.html" else f"{BASE}/{p.name}"
        urls.append(f"  <url><loc>{html.escape(loc)}</loc></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def main() -> None:
    try:
        posts = fetch_blog_posts(20)
        print(f"Fetched {len(posts)} Naver blog posts")
    except Exception as exc:
        print(f"Naver RSS fetch failed: {exc}")
        posts = []
    ensure_homepage(posts)
    ensure_columns()
    ensure_article_schema()
    generate_naver_blog_page(posts)
    generate_robots()
    generate_llms(posts)
    generate_sitemap()
    print("SEO/AI discovery assets updated")


if __name__ == "__main__":
    main()
