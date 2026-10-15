import json
import shutil
from pathlib import Path

import cv2


class DataManager:
    """Чтение/запись labels.json и сохранение патчей. Режим разметки."""

    def __init__(self, labels_file, output_dir):
        self.labels_file = Path(labels_file)
        self.output_dir = Path(output_dir)
        self.data = self._load_labels()

    def _load_labels(self):
        if self.labels_file.exists():
            with open(self.labels_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"current_image": None, "images": {}}

    def save_labels(self):
        self.labels_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.labels_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_image_status(self, image_name):
        if image_name in self.data["images"]:
            return self.data["images"][image_name].get("status", "none")
        return "none"

    def set_image_status(self, image_name, status):
        if image_name not in self.data["images"]:
            self.data["images"][image_name] = {"status": status}
        else:
            self.data["images"][image_name]["status"] = status

    def get_image_patches(self, image_name):
        if image_name in self.data["images"]:
            return self.data["images"][image_name].get("patches", {})
        return {}

    def set_image_patches(self, image_name, patches):
        if image_name not in self.data["images"]:
            self.data["images"][image_name] = {"status": "none", "patches": patches}
        else:
            self.data["images"][image_name]["patches"] = patches

    def set_current_image(self, image_name):
        self.data["current_image"] = image_name

    def get_current_image(self):
        return self.data.get("current_image")

    def save_patches(self, image_name, image_16bit, labeled_patches):
        """
        Структура: output_dir/<stem>/ <class>/<row>_<col>.png
        Сначала удаляет всю старую папку снимка.
        """
        self.delete_old_patches(image_name)
        base_name = Path(image_name).stem

        for patch in labeled_patches:
            class_name = patch["class"]
            if class_name is None:
                continue

            row, col = patch["index"]
            x, y, w, h = patch["coords"]
            patch_img = image_16bit[y:y + h, x:x + w]

            class_dir = self.output_dir / base_name / str(class_name)
            class_dir.mkdir(parents=True, exist_ok=True)

            patch_path = class_dir / f"{row}_{col}.png"
            cv2.imwrite(str(patch_path), patch_img)

    def delete_old_patches(self, image_name):
        base_name = Path(image_name).stem
        image_dir = self.output_dir / base_name
        if image_dir.exists() and image_dir.is_dir():
            shutil.rmtree(image_dir)


class ViewData:
    """
    Read-only источник разметки для режима просмотра.

    Интерфейс совместим с PatchManager:
        get_image_patches(image_name) -> {"row_col": class_name или None}

    Поддерживает:
      1. labels.json от DataManager (многоснимковый)
      2. JSON предсказаний одного снимка:  {"image_name": ..., "patches": {...}}
      3. JSON предсказаний многих снимков: {"images": {name: {"patches": {...}}}}

    Значение патча может быть:
      - строкой ("1")            — ручная разметка
      - dict с ключом "class"    — предсказание нейросети
      - null                     — патч без класса
    """

    def __init__(self, json_path):
        self.json_path = Path(json_path)
        self._patches = {}
        self._load()

    def _load(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"Файл разметки не найден: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("JSON должен содержать объект верхнего уровня.")

        if isinstance(data.get("images"), dict):
            # Многоснимковый формат (labels.json или predictions)
            for name, entry in data["images"].items():
                if not isinstance(entry, dict):
                    continue
                raw = entry.get("patches", {})
                self._patches[Path(str(name)).name] = self._normalize(raw)

        elif isinstance(data.get("patches"), dict):
            # Один снимок
            name = data.get("image_name")
            if not name:
                path = data.get("image_path")
                if path:
                    name = Path(str(path)).name
            if not name:
                raise ValueError(
                    "В JSON одного снимка не найдено поле image_name или image_path."
                )
            self._patches[Path(str(name)).name] = self._normalize(data["patches"])

        else:
            raise ValueError(
                "Неизвестный формат JSON. Ожидаются ключи 'images' или 'patches'."
            )

    @staticmethod
    def _normalize(raw):
        """Приводит любое поддерживаемое представление патча к class_name | None."""
        result = {}
        if not isinstance(raw, dict):
            return result

        for key, value in raw.items():
            if isinstance(value, dict):
                class_name = value.get("class")
            elif isinstance(value, str):
                class_name = value
            else:
                class_name = None

            if class_name is not None:
                class_name = str(class_name)

            result[str(key)] = class_name

        return result

    def get_image_patches(self, image_name):
        """Для PatchManager. Возвращает {} если снимка нет в разметке."""
        return self._patches.get(image_name, {})

    def has_markup(self, image_name):
        """Есть ли хотя бы один патч с классом у этого снимка."""
        patches = self._patches.get(image_name, {})
        return any(value is not None for value in patches.values())