from __future__ import annotations

from genaumacher.normalize_media import encode_command
from genaumacher.normalize_options import NormalizeOptions
from genaumacher.video_encoder import encoder_arguments


def _encoder(argv: list[str]) -> str:
    return argv[argv.index("-c:v") + 1]


def test_videos_are_encoded_on_the_graphics_card_since_an_lgpl_ffmpeg_has_no_x264():
    assert _encoder(encoder_arguments()) == "h264_nvenc"


def test_a_normalized_loop_is_encoded_at_the_quality_and_preset_it_was_asked_for():
    options = NormalizeOptions(input="loop in.mp4", output="loop out.mp4", qp=20, preset="p4")

    argv = encode_command(width=640, height=360, fps=30.0, options=options)

    assert _encoder(argv) == "h264_nvenc"
    assert argv[argv.index("-qp") + 1] == "20"
    assert argv[argv.index("-preset") + 1] == "p4"
    assert argv[-1] == "loop out.mp4"
