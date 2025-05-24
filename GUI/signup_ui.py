# signup_ui.py

from PyQt6.QtWidgets import QDialog
from PyQt6 import uic
from signup_elder_ui import ElderSignupDialog
from signup_guardian_ui import GuardianSignupDialog  

class SignupDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/signup.ui", self)

        self.pushButton_elderSignup.clicked.connect(self.open_elder_signup)
        self.pushButton_guardianSignup.clicked.connect(self.open_guardian_signup)

    def open_elder_signup(self):
        self.elder_window = ElderSignupDialog()
        self.elder_window.show()

    def open_guardian_signup(self):
        self.guardian_window = GuardianSignupDialog()
        self.guardian_window.show()
