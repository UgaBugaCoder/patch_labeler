# utils.py

import cv2
import numpy as np
from PySide6.QtGui import QImage


def normalize_for_display(img_array):
    """
    Нормализует изображение в 8-битное для отображения.
    Поддерживает 8-битные и 16-битные изображения.
    Использует простую min-max нормализацию.
    
    Args:
        img_array: numpy-массив (8-битный или 16-битный, grayscale или RGB).
    
    Returns:
        numpy-массив (8-битный, тот же формат: grayscale или RGB).
    """
    # Определяем битность
    if img_array.dtype == np.uint16:
        # 16-битное → нормализуем в 8-битное
        img_8bit = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return img_8bit
    elif img_array.dtype == np.uint8:
        # Уже 8-битное → возвращаем как есть
        return img_array.copy()
    else:
        # Неизвестный тип → пытаемся нормализовать
        img_8bit = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return img_8bit


def numpy_to_qimage(img_array):
    """
    Конвертирует numpy-массив в QImage.
    Поддерживает grayscale (1 канал) и RGB (3 канала).
    
    Args:
        img_array: numpy-массив (8-битный, grayscale или RGB).
    
    Returns:
        QImage.
    """
    if img_array.ndim == 2:
        # Grayscale
        height, width = img_array.shape
        bytes_per_line = width
        return QImage(img_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    elif img_array.ndim == 3 and img_array.shape[2] == 3:
        # RGB
        height, width, channels = img_array.shape
        bytes_per_line = channels * width
        # Qt ожидает формат RGB, а OpenCV использует BGR, поэтому конвертируем
        img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        return QImage(img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
    else:
        raise ValueError(f"Unsupported array shape: {img_array.shape}")