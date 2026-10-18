import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from carconnect.ui.backend import Backend

QML_DIR = Path(__file__).parent / "qml"


def run() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("CarConnect")
    QQuickStyle.setStyle("Material")

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        return 1

    code = app.exec()
    backend.shutdown()
    return code
