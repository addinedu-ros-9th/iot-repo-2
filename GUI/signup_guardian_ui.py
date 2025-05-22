from PyQt6.QtWidgets import QDialog, QMessageBox,QLineEdit
from PyQt6 import uic
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
import requests

class GuardianSignupDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/signup_guardian.ui", self)

        # 플레이스홀더
        self.lineEdit_guardianId.setPlaceholderText("아이디")
        self.lineEdit_guardian_elderId.setPlaceholderText("케어 대상자 아이디")
        self.lineEdit_guardianpassword.setPlaceholderText("비밀번호")
        self.lineEdit_guardianpassword_2.setPlaceholderText("비밀번호 확인")
        self.lineEdit_guardianpassword.setEchoMode(QLineEdit.EchoMode.Password)
        self.lineEdit_guardianpassword_2.setEchoMode(QLineEdit.EchoMode.Password)
        self.lineEdit_guardianname.setPlaceholderText("이름")
        self.lineEdit_guardianbirthday.setPlaceholderText("생년월일 (예: 19700101)")
        self.lineEdit_guardiannumber.setPlaceholderText("전화번호 (예: 01012345678)")

        # 숫자 입력만 가능
        validator = QRegularExpressionValidator(QRegularExpression("[0-9]+"))
        self.lineEdit_guardianbirthday.setValidator(validator)
        self.lineEdit_guardiannumber.setValidator(validator)

        # 하이픈 포맷
        self.lineEdit_guardianbirthday.textChanged.connect(self.format_birthday)
        self.lineEdit_guardiannumber.textChanged.connect(self.format_phonenumber)

        # 비밀번호 일치 확인
        self.lineEdit_guardianpassword.textChanged.connect(self.check_password_match)
        self.lineEdit_guardianpassword_2.textChanged.connect(self.check_password_match)

        # 중복 확인
        self.pushButton_checkguardianId.clicked.connect(self.check_id_duplicate)
        

        # 가입
        self.pushButton_guardiansignup.clicked.connect(self.register_guardian)

        # 케어 대상자 아이디 존재 및 요청
        self.pushButton_checkelderId.clicked.connect(self.send_elder_link_request)

    def check_password_match(self):
        pw1 = self.lineEdit_guardianpassword.text()
        pw2 = self.lineEdit_guardianpassword_2.text()
        if pw1 and pw2:
            if pw1 == pw2:
                self.label_passwordMatch.setText("✅ 비밀번호가 일치합니다.")
                self.label_passwordMatch.setStyleSheet("color: green;")
            else:
                self.label_passwordMatch.setText("❌ 비밀번호가 일치하지 않습니다.")
                self.label_passwordMatch.setStyleSheet("color: red;")
        else:
            self.label_passwordMatch.setText("")

    def check_id_duplicate(self):
        user_id = self.lineEdit_guardianId.text().strip()
        if not user_id:
            QMessageBox.warning(self, "입력 오류", "아이디를 입력해주세요.")
            return

        url = "http://34.64.53.123:9999/auth/check_id"
        try:
            response = requests.post(url, json={"user_id": user_id})
            if response.status_code == 200:
                result = response.json()
                if result.get("available"):
                    QMessageBox.information(self, "확인", "사용 가능한 아이디입니다.")
                else:
                    QMessageBox.warning(self, "중복", "이미 사용 중인 아이디입니다.")
            else:
                QMessageBox.critical(self, "오류", "서버 오류가 발생했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def send_elder_link_request(self):
        user_id = self.lineEdit_guardianId.text().strip()
        elderly_id = self.lineEdit_guardian_elderId.text().strip()

        if not user_id or not elderly_id:
            QMessageBox.warning(self, "입력 오류", "아이디와 케어 대상자 아이디를 모두 입력해주세요.")
            return

        url = "http://34.64.53.123:9999/auth/check-elderly-id"
        data = {
            "user_id": user_id,
            "elderly_id": elderly_id
        }

        print("[보호자 연동 요청 전송]:", data)

        try:
            response = requests.post(url, json=data)
            result = response.json()

            if response.status_code == 200:
                QMessageBox.information(self, "요청 성공", result.get("message", "요청이 완료되었습니다."))
            else:
                QMessageBox.warning(self, "요청 실패", result.get("message", "요청을 처리하지 못했습니다."))
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))


    def register_guardian(self):
        user_id = self.lineEdit_guardianId.text().strip()
        password = self.lineEdit_guardianpassword.text().strip()
        password2 = self.lineEdit_guardianpassword_2.text().strip()
        name = self.lineEdit_guardianname.text().strip()
        birth_date = self.lineEdit_guardianbirthday.text().strip()
        phone = self.lineEdit_guardiannumber.text().strip()
        elderly_id = self.lineEdit_guardian_elderId.text().strip()

        if not all([user_id, password, password2, name, birth_date, phone, elderly_id]):
            QMessageBox.warning(self, "입력 오류", "모든 항목을 입력해주세요.")
            return
        if password != password2:
            QMessageBox.warning(self, "비밀번호 오류", "비밀번호가 일치하지 않습니다.")
            return

        if len(birth_date) == 8:
            birth_date = f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:]}"
        if len(phone) == 11:
            phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"

        url = "http://34.64.53.123:9999/auth/guardian"
        data = {
            "user_id": user_id,
            "password": password,
            "name": name,
            "birth_date": birth_date,
            "phone_number": phone,
            "elderly_id": elderly_id
        }

        print("[보호자 가입 전송]:", data)

        try:
            response = requests.post(url, json=data)
            result = response.json()
            if response.status_code == 200 or response.status_code == 201:
                QMessageBox.information(self, "가입 성공", result.get("message", "가입 완료"))
                self.close()
            else:
                QMessageBox.critical(self, "가입 실패", result.get("message", "서버 오류 발생"))
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def format_birthday(self):
        text = self.lineEdit_guardianbirthday.text().replace("-", "").strip()
        if len(text) >= 8:
            formatted = f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        elif len(text) >= 6:
            formatted = f"{text[:4]}-{text[4:6]}-{text[6:]}"
        elif len(text) >= 4:
            formatted = f"{text[:4]}-{text[4:]}"
        else:
            formatted = text
        self.lineEdit_guardianbirthday.blockSignals(True)
        self.lineEdit_guardianbirthday.setText(formatted)
        self.lineEdit_guardianbirthday.blockSignals(False)

    def format_phonenumber(self):
        text = self.lineEdit_guardiannumber.text().replace("-", "").strip()
        if text.startswith("02") and len(text) >= 9:
            formatted = f"{text[:2]}-{text[2:5]}-{text[5:9]}"
        elif len(text) >= 11:
            formatted = f"{text[:3]}-{text[3:7]}-{text[7:11]}"
        elif len(text) >= 10:
            formatted = f"{text[:3]}-{text[3:6]}-{text[6:]}"
        else:
            formatted = text
        self.lineEdit_guardiannumber.blockSignals(True)
        self.lineEdit_guardiannumber.setText(formatted)
        self.lineEdit_guardiannumber.blockSignals(False)
