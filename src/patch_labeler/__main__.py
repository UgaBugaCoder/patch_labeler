import sys

from PySide6.QtWidgets import QApplication

from patch_labeler.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    if not window.ready:
        # Пользователь отменил выбор режима/путей или ошибка чтения JSON
        sys.exit(0)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()