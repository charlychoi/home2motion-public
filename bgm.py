"""배경 효과음악 합성 (외부 API·저작권 걱정 없음). numpy 만 사용.
engine.html 이 알려주는 이벤트(장면 전환 whoosh, 요소 등장 pop, 숫자 카운트 count, 선 연결 tick)를
영상 시점에 맞춰 얹고, 선택적으로 내레이션 wav 를 섞는다(음악은 말할 때 자동으로 낮아짐)."""
import wave
import numpy as np

SR = 44100
MOODS = {  # 코드 진행(MIDI 루트·3음·5음), 비트 세기
    "bright":    dict(chords=[(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)], drums=1.0, arp=1.0),
    "calm":      dict(chords=[(48, 52, 55), (55, 59, 62), (57, 60, 64), (53, 57, 60)], drums=0.0, arp=0.8),
    "dramatic":  dict(chords=[(57, 60, 64), (52, 55, 59), (53, 57, 60), (55, 59, 62)], drums=1.3, arp=1.1),
}


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def tone(f, d, atk=.01, dec=3.0, harm=(1, .4, .2)):
    t = np.arange(int(d * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * (k + 1) * t) for k, a in enumerate(harm)) * np.minimum(t / atk, 1) * np.exp(-dec * t)


def pad(f, d):
    t = np.arange(int(d * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-.004, 0, .004)) / 3
    return s * np.minimum(t / .5, 1) * np.minimum((d - t) / .6, 1)


def synth(total, events, bpm=120, mood="bright", voice=None, seed=7):
    """voice: [(시작초, 24kHz 모노 float 배열), ...] → (N,2) int16 스테레오"""
    rng = np.random.default_rng(seed)
    cfg = MOODS.get(mood, MOODS["bright"]); beat = 60.0 / bpm
    N = int(SR * total); L = np.zeros(N); R = np.zeros(N)

    def add(sig, t0, pan=0.0, gain=1.0):
        i = int(max(0, t0) * SR)
        if i >= N: return
        sig = sig[: N - i] * gain
        L[i:i + len(sig)] += sig * (1 - max(pan, 0)); R[i:i + len(sig)] += sig * (1 + min(pan, 0))

    ch, bar = cfg["chords"], 4 * beat
    first_full = events and min([e["t"] for e in events if e["kind"] == "whoosh"] + [total])
    for c in range(int(total / bar) + 1):
        t0 = c * bar; notes = ch[c % 4]
        for m in notes: add(pad(hz(m), bar + .3), t0, gain=.07)
        add(pad(hz(notes[0] - 12), bar + .3), t0, gain=.10)
        if t0 >= bar:
            for k in range(4):
                m = notes[[0, 1, 2, 1][k]] + 12
                add(tone(hz(m), 1.2, dec=4.5), t0 + k * beat, pan=(-.4 if k % 2 else .4), gain=.11 * cfg["arp"])
                if t0 >= first_full:
                    add(tone(hz(notes[[2, 1, 0, 1][k]] + 24), .9, dec=6), t0 + k * beat + beat / 2, pan=(.5 if k % 2 else -.5), gain=.07 * cfg["arp"])
    if cfg["drums"]:
        kt = np.arange(int(.35 * SR)) / SR
        kick = np.sin(2 * np.pi * (45 * kt + 90 * (1 - np.exp(-kt * 25)) / 25)) * np.exp(-9 * kt)
        ht = np.arange(int(.06 * SR)) / SR; hat = np.diff(rng.standard_normal(len(ht)), prepend=0) * np.exp(-60 * ht)
        end = total - 2.0
        for b in range(int(total / beat)):
            t0 = b * beat
            if bar <= t0 < end: add(kick, t0, gain=(.5 if t0 >= first_full else .3) * cfg["drums"])
            if first_full <= t0 < end: add(hat, t0 + beat / 2, gain=.08 * cfg["drums"], pan=.3)

    def whoosh(d=.9):
        t = np.arange(int(d * SR)) / SR; n = rng.standard_normal(len(t))
        return (np.convolve(n, np.ones(40) / 40, "same") * 4 + n * .15) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    pops = [e for e in events if e["kind"] == "pop"]
    for e in events:
        if e["kind"] == "whoosh": add(whoosh(), e["t"], gain=.22)
        elif e["kind"] == "tick": add(tone(hz(90), .05, atk=.001, dec=60, harm=(1,)), e["t"], gain=.05)
        elif e["kind"] == "count":
            for ts in np.arange(e["t"], e["t"] + e["dur"], .12): add(tone(hz(96), .05, atk=.001, dec=60, harm=(1,)), ts, gain=.04)
    for k, e in enumerate(pops):
        add(tone(hz([84, 88, 91][k % 3]), .35, atk=.003, dec=9, harm=(1, .3)), e["t"], gain=.10, pan=.2 if k % 2 else -.2)
    # 엔딩 화음
    add(tone(hz(ch[0][0] + 15), 2.5, atk=.02, dec=1.6, harm=(1, .5, .3, .15)), max(0, total - 2.6), gain=.16)

    for d, g in ((.28, .25), (.56, .14)):  # 간단한 잔향
        k = int(d * SR); L[k:] += R[:-k] * g; R[k:] += L[:-k] * g
    env = np.minimum(np.arange(N) / (SR * .8), 1) * np.minimum((N - np.arange(N)) / (SR * 1.5), 1)
    m = np.stack([L * env, R * env], 1); m = m / (np.abs(m).max() + 1e-9) * .8

    if voice:  # 내레이션: 24kHz → 44.1kHz, 말하는 동안 음악 -9dB
        duck = np.ones(N); vm = np.zeros(N)
        for t0, w in voice:
            w = np.interp(np.arange(int(len(w) * SR / 24000)) / SR * 24000, np.arange(len(w)), w)
            i = int(t0 * SR); seg = w[: max(0, N - i)]; vm[i:i + len(seg)] += seg
            a, b = max(0, i - int(.25 * SR)), min(N, i + len(seg) + int(.4 * SR)); duck[a:b] = .35
        duck = np.convolve(duck, np.ones(2205) / 2205, "same")
        m = m * duck[:, None] * .9 + vm[:, None] * .9
        m = m / max(1.0, np.abs(m).max()) * .95
    return (m * 32767).astype("<i2")


def write_wav(path, pcm):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
