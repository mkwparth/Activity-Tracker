from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from extractor.basic_logger import ActivityObserver


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Activity tracker")
        self.setFixedSize(390, 780)

        self._observer = ActivityObserver()

        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignCenter)

        self._status_hint_label = QLabel()
        self._status_hint_label.setObjectName("statusHintLabel")
        self._status_hint_label.setAlignment(Qt.AlignCenter)
        self._status_hint_label.setWordWrap(True)

        title_label = QLabel("Activity tracker")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Monitor user activity with a single tap")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)

        self._start_btn = QPushButton("Start Tracking")
        self._start_btn.setObjectName("startButton")

        self._stop_btn = QPushButton("Stop Tracking")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setEnabled(False)

        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)

        card = QFrame()
        card.setObjectName("card")

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(22, 26, 22, 26)
        card_layout.setSpacing(16)
        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addSpacing(10)
        card_layout.addWidget(self._status_label)
        card_layout.addWidget(self._status_hint_label)
        card_layout.addSpacing(20)
        card_layout.addWidget(self._start_btn)
        card_layout.addWidget(self._stop_btn)
        card_layout.addStretch()
        card.setLayout(card_layout)

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.addWidget(card)
        root.setLayout(root_layout)

        self.setCentralWidget(root)
        self._apply_styles()
        self._set_status(is_running=False)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0D1B2A,
                    stop:0.55 #1B263B,
                    stop:1 #415A77
                );
            }
            #card {
                background-color: rgba(248, 250, 252, 0.95);
                border-radius: 28px;
            }
            #titleLabel {
                font-size: 30px;
                font-weight: 800;
                color: #0f172a;
                letter-spacing: 0.5px;
            }
            #subtitleLabel {
                font-size: 14px;
                color: #475569;
            }
            #statusLabel {
                background-color: #fee2e2;
                border: 2px solid #cbd5e1;
                border-radius: 14px;
                padding: 14px;
                font-size: 18px;
                font-weight: 700;
                color: #1e293b;
            }
            #statusHintLabel {
                font-size: 13px;
                color: #334155;
                padding: 2px 8px 0 8px;
            }
            QPushButton {
                border: none;
                border-radius: 14px;
                padding: 14px;
                font-size: 16px;
                font-weight: 700;
            }
            #startButton {
                background-color: #059669;
                color: #ffffff;
            }
            #startButton:hover {
                background-color: #047857;
            }
            #startButton:disabled {
                background-color: #9ca3af;
                color: #f3f4f6;
            }
            #stopButton {
                background-color: #ef4444;
                color: #ffffff;
            }
            #stopButton:hover {
                background-color: #dc2626;
            }
            #stopButton:disabled {
                background-color: #9ca3af;
                color: #f3f4f6;
            }
            """
        )

    def _set_status(self, is_running: bool) -> None:
        if is_running:
            self._status_label.setText("Now Running")
            self._status_label.setStyleSheet(
                "background-color: #dcfce7; border: 2px solid #86efac; color: #14532d;"
            )
            self._status_hint_label.setText("Activity capture is active. Tap Stop Tracking to finish.")
        else:
            self._status_label.setText("Currently Stopped")
            self._status_label.setStyleSheet(
                "background-color: #fee2e2; border: 2px solid #fca5a5; color: #7f1d1d;"
            )
            self._status_hint_label.setText("Tracking is paused. Tap Start Tracking when you're ready.")

    def _on_start_clicked(self) -> None:
        if self._observer.is_recording:
            return

        try:
            self._observer.start()
        except Exception as exc:
            QMessageBox.critical(self, "Start Failed", f"Failed to start observer:\n{exc}")
            return

        self._set_status(is_running=True)
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

        self._set_status(is_running=False)
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
