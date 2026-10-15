# image_processor.py

import cv2
import numpy as np


class ImageProcessor:
    """Загрузка изображений с диска."""
    
    @staticmethod
    def load_image(image_path):
        """
        Загружает изображение (PNG, PGM) в формате numpy-массива.
        Сохраняет оригинальную битность (8 или 16 бит).
        Если изображение цветное (RGB), конвертирует в grayscale.
        
        Args:
            image_path: Путь к файлу изображения.
        
        Returns:
            numpy-массив (grayscale, uint8 или uint16).
        
        Raises:
            ValueError: Если изображение не удалось загрузить.
        """
        # Загружаем изображение с сохранением битности
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        
        # Если изображение цветное (RGB), конвертируем в grayscale
        if img.ndim == 3:
            # img.shape = (height, width, channels)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # img.ndim == 2 (grayscale)
        return img