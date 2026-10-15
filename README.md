# Patch Labeler

Десктопное приложение (PySide6 + OpenCV) для разметки медицинских/научных снимков
патчами 512×512 с перекрытием 64 пикселей. Работает в двух режимах:
**разметка** и **просмотр разметки**.

## Установка

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
PYTHONPATH=src python -m patch_labeler
```

## Структура

```
src/patch_labeler/
├── __main__.py          — точка входа (QApplication + MainWindow)
├── config.py            — PATCH_SIZE, OVERLAP, CLASSES, цвета состояний/классов/сетки
├── utils.py             — normalize_for_display (16→8 бит), numpy_to_qimage
├── image_processor.py   — загрузка изображений (PNG/PGM, 8/16 бит)
├── grid_generator.py    — генерация сетки патчей с overlap
├── data_manager.py      — DataManager (labels.json, вырезка патчей на диск) и ViewData (режим просмотра)
├── patch_manager.py     — состояния патчей: unlabeled → selected → labeled
└── ui/                  — main_window, mode_dialog, graphics_view, image_list_panel, right_panel, view_panel
```

## Горячие клавиши

### Режим разметки

| Клавиша | Действие |
|---|---|
| `S` | Сохранить разметку текущего снимка и перейти к следующему |
| `Ctrl+S` | Пропустить снимок (при наличии разметки — с подтверждением и удалением старых патчей) |
| `A` / `←` | Перейти к предыдущему снимку |
| `D` / `→` | Перейти к следующему снимку |
| `1–9` | Назначить класс выделенным патчам (классов столько, сколько задано в `CLASSES`, по умолчанию 4) |
| `E` | Снять выделение с патчей |
| `Shift+E` | Снять всю разметку со снимка |
| `H` | Показать/скрыть сетку |
| ЛКМ | Выделение патча / «кисть» |
| ПКМ | Панорамирование; колесо мыши — зум |

### Режим просмотра

| Клавиша | Действие |
|---|---|
| `A` / `←` | Предыдущий снимок |
| `D` / `→` | Следующий снимок |
| `H` | Показать/скрыть сетку |
| Колесо мыши | Зум; ПКМ — панорамирование |

## Выходные данные

- `output/<stem>/labels.json` — метки (`{row}_{col}` → класс)
- `output/<stem>/<class>/<row>_<col>.png` — вырезанные патчи
