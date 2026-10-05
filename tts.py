"""(선택) 내레이션 음성 생성 — Google Gemini TTS. 키는 환경변수 GEMINI_API_KEY 로만 읽습니다(저장소에 넣지 마세요).
project.json 의 각 장면에 "narration": "읽을 문장" 을 넣고 `python build.py ... --voice` 로 사용합니다.
※ 모델명·음성명은 계정/시점에 따라 달라질 수 있어 project.json 의 "voice": {"model","name"} 로 바꿀 수 있습니다."""
import base64, os, wave


def _find(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "data" and isinstance(v, str) and len(v) > 1000: return v
            r = _find(v)
            if r: return r
    if isinstance(o, list):
        for v in o:
            r = _find(v)
            if r: return r


def synth_lines(lines, voice_cfg, outdir):
    """lines: [(id, text)] → {id: wav경로 (24kHz 모노)}"""
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key: raise SystemExit("GEMINI_API_KEY 환경변수가 필요합니다 (https://aistudio.google.com/apikey)")
    c = genai.Client(api_key=key); os.makedirs(outdir, exist_ok=True); out = {}
    model = voice_cfg.get("model", "gemini-2.5-flash-preview-tts"); name = voice_cfg.get("name", "Kore")
    for sid, text in lines:
        it = c.interactions.create(model=model, input=[{"type": "user_input", "content": [{"type": "text", "text": text}]}],
                                   response_format={"type": "audio"}, generation_config={"speech_config": [{"voice": name}]})
        raw = base64.b64decode(_find(it.model_dump())); p = os.path.join(outdir, f"{sid}.wav")
        if raw[:4] == b"RIFF": open(p, "wb").write(raw)
        else:
            with wave.open(p, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
        out[sid] = p
    return out
