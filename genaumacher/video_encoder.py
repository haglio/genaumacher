from __future__ import annotations

QP = 13
PRESET = "p7"


def encoder_arguments(*, qp: int = QP, preset: str = PRESET) -> list[str]:
    return ["-c:v", "h264_nvenc", "-preset", preset, "-tune", "hq",
            "-rc", "constqp", "-qp", str(qp)]
