import sys
from PyQt6.QtWidgets import QApplication
from login_ui import LoginDialog

app = QApplication(sys.argv)
window = LoginDialog()
window.show()
sys.exit(app.exec())


