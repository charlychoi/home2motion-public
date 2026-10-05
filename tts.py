"""(선택) 내레이션 음성 생성 — Google Gemini TTS (REST, 표준 라이브러리만 사용).
키 전달: 환경변수 GEMINI_API_KEY 가 있으면 헤더로 보내고, 없으면 환경(프록시)이 주입하는 자격 증명을 사용합니다.
키는 저장소에 절대 커밋하지 마세요.
project.json: "voice": {"model": "gemini-3.8-flash-lite-tts", "name": "Kore", "style": "차분하고 따뜻한 톤으로"}"""
import base64, json, os, urllib.request, wave

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def synth_one(text, model, voice, style=None, path="out.wav"):
    prompt = f"{style}: {text}" if style else text
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    h = {"Content-Type": "application/json"}
    if os.environ.get("GEMINI_API_KEY"): h["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]
    req = urllib.request.Request(URL.format(model=model), json.dumps(body).encode(), h)
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"TTS 호출 실패 {e.code}: {e.read().decode()[:300]}")
    pcm = None
    for p in r["candidates"][0]["content"]["parts"]:
        if "inlineData" in p: pcm = base64.b64decode(p["inlineData"]["data"])
    if pcm is None: raise SystemExit(f"오디오가 응답에 없습니다: {str(r)[:300]}")
    if pcm[:4] == b"RIFF": open(path, "wb").write(pcm)
    else:
        with wave.open(path, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    return path


def synth_lines(lines, voice_cfg, outdir):
    """lines: [(id, text)] → {id: wav경로 (24kHz 모노)}"""
    os.makedirs(outdir, exist_ok=True)
    out = {}
    for sid, t in lines:   # 같은 문장·음성이면 기존 wav 재사용(재렌더링 시 API 호출 절약)
        path = os.path.join(outdir, f"{sid}.wav"); tag = path + ".txt"
        sig = json.dumps([t, voice_cfg.get("model"), voice_cfg.get("name"), voice_cfg.get("style")], ensure_ascii=False)
        if not (os.path.exists(path) and os.path.exists(tag) and open(tag, encoding="utf-8").read() == sig):
            synth_one(t, voice_cfg.get("model", "gemini-3.8-flash-lite-tts"), voice_cfg.get("name", "Kore"), voice_cfg.get("style"), path)
            open(tag, "w", encoding="utf-8").write(sig)
        out[sid] = path
    return out


def _unused(lines, voice_cfg, outdir):
    return {sid: synth_one(t, voice_cfg.get("model", "gemini-3.8-flash-lite-tts"), voice_cfg.get("name", "Kore"),
                           voice_cfg.get("style"), os.path.join(outdir, f"{sid}.wav")) for sid, t in lines}
