import multiprocessing
import sys
import os
import asyncio
import warnings
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from rsi.gui.qfluentwidgets.common.style_sheet import setTheme, Theme
from rsi.gui.qfluentwidgets.components.dialog_box import MessageBox
from rsi.gui.views.fluentwindow import WindowBase
from rsi.appmanager.setting.config import cfg
from qasync import QEventLoop


class MainWindow(WindowBase):
    """Main application window for RSI Monitor"""
    
    def __init__(self):
        self.isMicaEnabled = False
        super().__init__()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event with confirmation dialog"""
        quit_msg = QCoreApplication.translate(
            "MainWindow", 
            "To close window click button OK", 
            None
        )
        msg_box = MessageBox("Quit Application?", quit_msg, self.window())
        response = msg_box.exec()
        
        if response:
            self.close_window()
            self.deleteLater()
            event.accept()
        else:
            event.ignore()


def setup_application_info():
    """Setup application information and metadata"""
    return {
        "version": "1.0.0",
        "name": "RSI Monitor"
    }


def configure_dpi_scaling():
    """Configure DPI scaling based on user settings"""
    dpi_scale = cfg.get(cfg.dpiScale)
    if dpi_scale != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(dpi_scale)


def create_application(app_info):
    """Create and configure Qt application"""
    app = QApplication(sys.argv + ['--no-sandbox'])
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    app.setStyle("Fusion")
    app.setApplicationVersion(app_info["version"])
    app.setApplicationName(app_info["name"])
    app.setApplicationDisplayName(f"{app_info['name']} (v{app_info['version']})")
    return app


def create_main_window(app_info):
    """Create and configure main window"""
    window = MainWindow()
    window.setWindowTitle(app_info["name"])
    return window


def setup_async_event_loop():
    """Setup async event loop based on platform"""
    platform = sys.platform
    
    if platform in ("darwin", "linux"):
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass
    else:
        # Windows specific setup
        try:
            import winloop
            winloop.install()
        except ImportError:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    """Main application entry point"""
    app_info = setup_application_info()
    configure_dpi_scaling()
    setTheme(Theme.DARK, True, True)
    app = create_application(app_info)
    window = create_main_window(app_info)
    window.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()


if __name__ == '__main__':
    # Suppress warnings
    warnings.simplefilter(action='ignore', category=FutureWarning)
    
    # Setup multiprocessing
    multiprocessing.freeze_support()
    
    # Setup async event loop
    #setup_async_event_loop()
    
    # Run main application
    main()
    
    