from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from extractor.basic_logger import ActivityObserver


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Activity Logger")
        self.setMinimumSize(360, 200)

        self._observer = ActivityObserver()

        self._status_label = QLabel("Status: stopped")
        self._status_label.setAlignment(Qt.AlignCenter)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)

        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._start_btn)
        layout.addWidget(self._stop_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _on_start_clicked(self) -> None:
        if self._observer.is_recording:
            return

        try:
            self._observer.start()
        except Exception as exc:
            QMessageBox.critical(self, "Start Failed", f"Failed to start observer:\n{exc}")
            return

        self._status_label.setText("Status: running")
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

    def _on_stop_clicked(self) -> None:
        if not self._observer.is_recording:
            return

        try:
            self._observer.stop()
        except Exception as exc:
            QMessageBox.critical(self, "Stop Failed", f"Failed to stop observer:\n{exc}")
            return

        self._status_label.setText("Status: stopped")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._observer.is_recording:
            try:
                self._observer.stop()
            except Exception:
                pass
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
