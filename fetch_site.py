#!/usr/bin/env python3
"""홈페이지 URL → project.json 초안 (표준 라이브러리만 사용).
  python fetch_site.py https://example.com projects/mysite
사이트의 제목·설명·제목 태그(h1~h3)·숫자 문구·대표 이미지를 모아 장면 초안을 만듭니다.
초안은 출발점일 뿐입니다 — 문구를 다듬고 사실관계를 확인한 뒤 build.py 로 영상을 만드세요."""
import json, os, re, sys, urllib.parse, urllib.request
from html.parser import HTMLParser


class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.meta, s.h, s.title, s._cur, s._buf, s.text, s.skip, s.imgs = {}, [], "", None, [], [], 0, []
    def handle_starttag(s, t, a):
        a = dict(a)
        if t in ("script", "style", "noscript"): s.skip += 1
        if t == "meta":
            k = a.get("property") or a.get("name")
            if k and a.get("content"): s.meta[k.lower()] = a["content"].strip()
        if t in ("h1", "h2", "h3", "title"): s._cur, s._buf = t, []
        if t == "img" and a.get("src"): s.imgs.append(a["src"])
    def handle_endtag(s, t):
        if t in ("script", "style", "noscript"): s.skip = max(0, s.skip - 1)
        if t == s._cur:
            x = re.sub(r"\s+", " ", "".join(s._buf)).strip()
            if t == "title": s.title = x
            elif x: s.h.append((t, x))
            s._cur = None
    def handle_data(s, d):
        if s.skip: return
        if s._cur: s._buf.append(d)
        d = d.strip()
        if d: s.text.append(d)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (home2motion)"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    for enc in ("utf-8", "euc-kr"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode("utf-8", "ignore")


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    url, outdir = sys.argv[1], sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    p = P(); p.feed(fetch(url))
    name = (p.meta.get("og:site_name") or re.split(r"[|\-–·:]", p.meta.get("og:title") or p.title or urllib.parse.urlparse(url).netloc)[0]).strip()
    desc = p.meta.get("og:description") or p.meta.get("description") or ""
    heads = [x for t, x in p.h if 3 <= len(x) <= 40]; seen = set(); heads = [h for h in heads if not (h in seen or seen.add(h))]
    nums = []                                   # "20만+ 교육", "500개" 같은 숫자 문구 후보
    for line in p.text:
        for m in re.finditer(r"(\d[\d,\.]*)\s*(만|천|억)?\s*(\+|%|명|개|건|곳|회|년|개사|시간)?", line):
            v, big, unit = m.groups()
            if not (big or unit) or len(line) > 40: continue
            label = re.sub(r"\s+", " ", line.replace(m.group(0), "")).strip(" ·:-") or line
            try: val = float(v.replace(",", ""))
            except ValueError: continue
            nums.append({"value": int(val) if val == int(val) else val, "suffix": (big or "") + (unit or ""), "label": label[:14]})
    nums = nums[:3]
    colors = {}
    if p.meta.get("theme-color", "").startswith("#"): colors["accent"] = p.meta["theme-color"]
    og = p.meta.get("og:image"); logo = None
    if og:
        try:
            full = urllib.parse.urljoin(url, og); ext = os.path.splitext(urllib.parse.urlparse(full).path)[1] or ".jpg"
            logo = "og_image" + ext; open(os.path.join(outdir, logo), "wb").write(urllib.request.urlopen(urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        except Exception as e: print("대표 이미지 저장 실패:", e); logo = None
    sc = [{"type": "intro", "duration": 4},
          {"type": "statement", "eyebrow": "ABOUT", "lines": [(heads[0] if heads else name)], "sub": desc[:60], "duration": 6}]
    if len(heads) >= 3: sc.append({"type": "flow", "eyebrow": "WHAT WE DO", "title": "핵심 *서비스*", "steps": [{"label": h[:10]} for h in heads[1:4]], "duration": 6.5})
    if len(nums) >= 2: sc.append({"type": "stats", "eyebrow": "IMPACT", "title": f"숫자로 보는 *{name[:8]}*", "items": nums, "duration": 6.5})
    if len(heads) >= 7: sc.append({"type": "showcase", "eyebrow": "MORE", "title": "이런 것도 *함께*", "chips": [h[:12] for h in heads[4:8]], "big": None, "duration": 4.5})
    sc.append({"type": "outro", "line": (desc[:24] or name), "duration": 3})
    for s in sc:
        if s.get("big") is None: s.pop("big", None)
    proj = {"output": re.sub(r"\W+", "_", name)[:30] or "motion", "brand": {"name": name, "tagline": desc[:40], "url": urllib.parse.urlparse(url).netloc, "colors": colors},
            "music": {"bpm": 120, "mood": "bright"}, "scenes": sc}
    path = os.path.join(outdir, "project.json"); json.dump(proj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"초안 저장: {path}\n제목 후보 {len(heads)}개, 숫자 후보 {len(nums)}개 — 문구를 다듬은 뒤 python build.py {path}")


if __name__ == "__main__":
    main()
