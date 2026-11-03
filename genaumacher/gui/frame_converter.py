from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap


def bgr_to_qimage(frame: np.ndarray) -> QImage:
    h, w, ch = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    bytes_per_line = ch * w
    return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()


def scale_to_fit(image: QImage, max_w: int, max_h: int) -> QImage:
    if image.width() <= max_w and image.height() <= max_h:
        return image
    pixmap = QPixmap.fromImage(image)
    scaled = pixmap.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return scaled.toImage()
