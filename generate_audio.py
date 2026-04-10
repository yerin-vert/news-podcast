"""
TTS 오디오 생성 모듈
스크립트의 HOST/GUEST 턴별로 다른 목소리로 합성하고, 하나의 mp3 파일로 합친다.
Edge TTS (Microsoft Edge의 무료 TTS) 사용.

ffmpeg 없이 동작: mp3 파일들을 바이트 레벨에서 직접 이어붙인다.
(mp3는 스트리밍 포맷이라 이 방식으로 재생이 정상적으로 됨)
"""
from __future__ import annotations

import asyncio
import os
import shutil

import edge_tts


# ============================================================
# 음성 설정 (쉽게 수정 가능하도록 별도 변수로 분리)
# ============================================================

# HOST 수진 — 여성, 차분하고 지적인 톤
HOST_VOICE = "ko-KR-SunHiNeural"

# GUEST 민준 — 남성, 캐주얼한 톤
GUEST_VOICE = "ko-KR-HyunsuNeural"

# 말하기 속도 조절 ("+0%" = 기본, "+10%" = 빠름, "-10%" = 느림)
# 너무 빠르면 기계같이 들리므로 약간 느리게.
HOST_RATE = "-5%"
GUEST_RATE = "+0%"

# 피치(음높이) 조절 — 살짝 낮추면 덜 긴장한 느낌이 됨
HOST_PITCH = "-2Hz"
GUEST_PITCH = "-3Hz"

# 참고: ffmpeg 없이 바이트 이어붙이기 방식을 쓰기 때문에
# 턴 사이 무음(pause) 추가는 생략. 대신 Edge TTS가 자연스러운
# 문장 끝 여운을 포함해 주므로 대화 흐름이 끊기지 않는다.

# ============================================================
# 참고: 사용 가능한 한국어 음성
# ── Multilingual (최신, 가장 자연스러움) ──
#   ko-KR-HyunsuMultilingualNeural  (남성, 젊고 자연스러움) ← GUEST 추천
#   ko-KR-YuJinMultilingualNeural   (여성, 밝고 자연스러움) ← HOST 추천 후보
# ── 여성 (기존) ──
#   ko-KR-SunHiNeural     (차분, 뉴스앵커 스타일)
#   ko-KR-JiMinNeural     (밝고 친근함)
#   ko-KR-SeoHyeonNeural  (부드러움)
#   ko-KR-SoonBokNeural   (중년 여성)
#   ko-KR-YuJinNeural     (젊고 활기참)
# ── 남성 (기존) ──
#   ko-KR-InJoonNeural    (캐주얼, 젊은 남성)
#   ko-KR-BongJinNeural   (중년 남성)
#   ko-KR-GookMinNeural   (무게감 있는 남성)
#   ko-KR-HyunsuNeural    (젊은 남성)
# ============================================================


async def _synthesize_one(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: str,
) -> None:
    """한 개의 대사를 음성 파일로 변환"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


async def _generate_all_segments(
    turns: list[dict],
    temp_dir: str,
) -> list[str]:
    """모든 턴을 개별 mp3 파일로 생성"""
    segment_paths = []

    for i, turn in enumerate(turns):
        speaker = turn["speaker"]
        text = turn["text"]

        if not text.strip():
            continue

        if speaker == "HOST":
            voice = HOST_VOICE
            rate = HOST_RATE
            pitch = HOST_PITCH
        else:  # GUEST
            voice = GUEST_VOICE
            rate = GUEST_RATE
            pitch = GUEST_PITCH

        segment_path = os.path.join(temp_dir, f"turn_{i:03d}.mp3")
        preview = text[:30] + ("..." if len(text) > 30 else "")
        print(f"  🎙️  [{i + 1:2d}/{len(turns)}] {speaker}: {preview}")

        await _synthesize_one(text, voice, rate, pitch, segment_path)
        segment_paths.append(segment_path)

    return segment_paths


def _merge_audio_segments(segment_paths: list[str], output_path: str) -> None:
    """
    여러 mp3 파일을 하나로 합친다.
    mp3는 스트리밍 포맷이라 바이트를 그대로 이어붙여도 재생이 정상적으로 된다.
    (ffmpeg/pydub 없이 동작)
    """
    with open(output_path, "wb") as outfile:
        for segment_path in segment_paths:
            with open(segment_path, "rb") as infile:
                outfile.write(infile.read())


def generate_podcast_audio(
    turns: list[dict],
    output_path: str,
    temp_dir: str = "temp_audio",
) -> str:
    """
    스크립트 턴 리스트를 받아 팟캐스트 오디오 파일을 생성한다.

    Args:
        turns: [{"speaker": "HOST"|"GUEST", "text": "..."}, ...]
        output_path: 최종 mp3 파일 저장 경로
        temp_dir: 임시 오디오 파일을 저장할 디렉토리

    Returns:
        생성된 파일 경로
    """
    if not turns:
        raise ValueError("턴 리스트가 비어있습니다.")

    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: 턴별 음성 생성
        print(f"\n🎧 {len(turns)}개 대사를 음성으로 변환 중...")
        segment_paths = asyncio.run(_generate_all_segments(turns, temp_dir))

        # Step 2: 합치기
        print(f"\n🔗 {len(segment_paths)}개 오디오를 하나로 합치는 중...")
        _merge_audio_segments(segment_paths, output_path)

        # Step 3: 파일 크기 확인
        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        print(f"\n✅ 오디오 생성 완료!")
        print(f"   📁 파일: {output_path}")
        print(f"   📊 크기: {size_mb:.1f} MB")

    finally:
        # 임시 파일 정리
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    return output_path


# ── 단독 실행 테스트 ──
if __name__ == "__main__":
    sample_turns = [
        {"speaker": "HOST", "text": "안녕하세요, 수진입니다. 오늘은 흥미로운 뉴스 하나를 가져왔어요."},
        {"speaker": "GUEST", "text": "네, 저 민준이에요. 오늘 어떤 얘기인가요?"},
        {"speaker": "HOST", "text": "중동 정세 때문에 금값이 움직이고 있다는 소식인데요. 꽤 재밌어요."},
        {"speaker": "GUEST", "text": "아, 그 얘기 저도 관심 있었어요. 같이 풀어볼까요?"},
    ]

    output = "test_podcast.mp3"
    generate_podcast_audio(sample_turns, output)
