#!/usr/bin/env python3
"""project.json → 모션그래픽 mp4 (프레임 캡처 + 배경음악 합성 + ffmpeg 합치기)

  python build.py examples/demo/project.json            # out/<이름>.mp4
  python build.py my/project.json --preview             # 장면별 미리보기 PNG 만 빠르게 (영상 안 만듦)
  python build.py my/project.json --voice               # (선택) 장면별 narration 을 Gemini TTS 로 음성 추가
"""
import argparse, base64, glob, json, math, mimetypes, os, subprocess, sys, wave
import numpy as np
from bgm import synth, write_wav

HERE = os.path.dirname(os.path.abspath(__file__))
TYPES = {"intro", "outro", "statement", "flow", "stats", "showcase", "list", "image"}


def data_uri(path):
    mt = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mt};base64," + base64.b64encode(open(path, "rb").read()).decode()


def load_project(path, logo=None):
    base = os.path.dirname(os.path.abspath(path)); P = json.load(open(path, encoding="utf-8"))
    P.setdefault("brand", {}); P["brand"].setdefault("colors", {})
    if not P["brand"].get("name"): sys.exit("project.json: brand.name 이 필요합니다")
    if not P.get("scenes"): sys.exit("project.json: scenes 가 비어 있습니다")
    def img(p):
        full = p if os.path.isabs(p) else os.path.join(base, p)
        if not os.path.exists(full): sys.exit(f"이미지를 찾을 수 없습니다: {full}")
        return data_uri(full)
    if logo: P["brand"]["logo"] = logo if os.path.isabs(logo) else os.path.abspath(logo)
    if P["brand"].get("logo"): P["brand"]["logo"] = img(P["brand"]["logo"])
    for i, s in enumerate(P["scenes"]):
        if s.get("type") not in TYPES: sys.exit(f"scenes[{i}].type 은 {sorted(TYPES)} 중 하나여야 합니다 (현재: {s.get('type')})")
        if s["type"] == "image":
            if not s.get("image"): sys.exit(f"scenes[{i}] image 장면에는 image 경로가 필요합니다")
            s["image"] = img(s["image"])
        s.setdefault("duration", {"intro": 4, "outro": 3}.get(s["type"], 6))
    return P, base


def timeline(P, voice_durs=None):
    bpm = P.get("music", {}).get("bpm", 120); beat = 60 / bpm; t = 0.0
    for i, s in enumerate(P["scenes"]):
        d = max(s["duration"], (voice_durs or {}).get(i, 0) + 1.2)
        d = math.ceil(d / beat - 1e-9) * beat           # 장면 경계를 박자에 맞춤
        s["start"], s["dur"] = round(t, 4), round(d, 4); t += d
    P["total"] = round(t, 4)
    return P


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--preview", action="store_true", help="장면별 PNG 미리보기만 생성"); ap.add_argument("--voice", action="store_true"); ap.add_argument("--logo", help="브랜드 로고 이미지 경로 (project.json 의 brand.logo 대신 사용)")
    a = ap.parse_args()
    P, base = load_project(a.project, a.logo); voice_durs, voice_files = {}, {}
    if a.voice:
        from tts import synth_lines
        lines = [(f"s{i}", s["narration"]) for i, s in enumerate(P["scenes"]) if s.get("narration")]
        if not lines: sys.exit("--voice 를 쓰려면 장면에 narration 이 필요합니다")
        files = synth_lines(lines, P.get("voice", {}), os.path.join(HERE, "out", "voice"))
        for sid, p in files.items():
            with wave.open(p) as w: voice_durs[int(sid[1:])] = w.getnframes() / w.getframerate()
            voice_files[int(sid[1:])] = p
    timeline(P, voice_durs); fps = a.fps; name = P.get("output", "motion")
    out = a.out or os.path.join(HERE, "out", name + ".mp4"); os.makedirs(os.path.dirname(out), exist_ok=True)
    from playwright.sync_api import sync_playwright
    exe = next(iter(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")), None)
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": exe, "args": ["--no-sandbox"]} if exe else {}))
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.add_init_script("window.PROJECT=" + json.dumps(P, ensure_ascii=False))
        pg.goto("file://" + os.path.join(HERE, "engine.html")); pg.evaluate("document.fonts.ready")
        events = pg.evaluate("window.events")
        if a.preview:
            d = os.path.join(HERE, "out", "preview"); os.makedirs(d, exist_ok=True)
            for i, s in enumerate(P["scenes"]):
                pg.evaluate(f"render({s['start'] + s['dur'] - 0.5})"); pg.screenshot(path=f"{d}/{i + 1:02d}_{s['type']}.png")
            print(f"미리보기 {len(P['scenes'])}장 → {d}  (총 {P['total']}초)"); return
        fd = os.path.join(HERE, "out", "frames"); os.makedirs(fd, exist_ok=True)
        for f in glob.glob(fd + "/*.jpg"): os.remove(f)
        n = int(round(fps * P["total"]))
        for i in range(n):
            pg.evaluate(f"render({i / fps})"); pg.screenshot(path=f"{fd}/{i:05d}.jpg", type="jpeg", quality=92)
            if i % 150 == 0: print(f"  프레임 {i}/{n}", flush=True)
        b.close()
    voice = []
    for i, p in voice_files.items():
        with wave.open(p) as w: voice.append((P["scenes"][i]["start"] + .5, np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768))
    m = P.get("music", {}); wav = os.path.join(HERE, "out", name + ".wav")
    write_wav(wav, synth(P["total"], events, m.get("bpm", 120), m.get("mood", "bright"), voice or None))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{fd}/%05d.jpg", "-i", wav, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"완성: {out}  ({P['total']}초)")


if __name__ == "__main__":
    main()
