# grid_generator.py


class GridGenerator:
    """Генерация сетки патчей с учетом overlap."""

    @staticmethod
    def generate_grid(image_height, image_width, patch_size, overlap):
        """
        Генерирует список патчей, покрывающих всё изображение.

        Args:
            image_height: Высота изображения в пикселях.
            image_width: Ширина изображения в пикселях.
            patch_size: Кортеж (height, width) размера патча.
            overlap: Перекрытие между соседними патчами (одинаковое по X и Y).

        Returns:
            list of dict: Каждый патч — {"index": (row, col), "coords": (x, y, w, h)}.

        Raises:
            ValueError: При некорректных patch_size или overlap.
        """
        patch_h, patch_w = patch_size

        # Валидация
        if patch_h <= 0 or patch_w <= 0:
            raise ValueError(f"Некорректный размер патча: {patch_size}")
        if overlap < 0 or overlap >= min(patch_h, patch_w):
            raise ValueError(
                f"Overlap ({overlap}) должен быть >= 0 и < min(patch_size) "
                f"({min(patch_h, patch_w)})"
            )

        # Позиции по каждой оси независимо
        y_positions = GridGenerator._get_positions(image_height, patch_h, overlap)
        x_positions = GridGenerator._get_positions(image_width, patch_w, overlap)

        patches = []
        for row, y in enumerate(y_positions):
            for col, x in enumerate(x_positions):
                patches.append({
                    "index": (row, col),
                    "coords": (x, y, patch_w, patch_h)
                })

        return patches

    @staticmethod
    def _get_positions(dim, patch_size, overlap):
        """
        Рассчитывает стартовые позиции патчей вдоль одной оси.

        Логика:
        1. Идем от 0 с шагом (patch_size - overlap), пока патч целиком
           помещается в изображение.
        2. Если последний патч не достает до края — добавляем финальный
           патч, выровненный по краю (overlap с предыдущим станет больше).
        3. Если изображение меньше патча — одна позиция [0].

        Args:
            dim: Размер изображения по оси.
            patch_size: Размер патча по этой оси.
            overlap: Перекрытие.

        Returns:
            list of int: Список стартовых координат.
        """
        # Изображение меньше или равно патчу — один патч с начала
        if dim <= patch_size:
            return [0]

        step = patch_size - overlap
        positions = []
        pos = 0

        # Основная нарезка: пока патч целиком влезает
        while pos + patch_size <= dim:
            positions.append(pos)
            pos += step

        # Если последний патч не достал до края — добавляем выровненный по краю
        if positions[-1] + patch_size < dim:
            positions.append(dim - patch_size)

        return positions