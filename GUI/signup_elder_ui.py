from PyQt6.QtWidgets import QDialog, QMessageBox,QLineEdit
from PyQt6 import uic
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
import requests

class ElderSignupDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/signup_elder.ui", self)

        #  플레이스홀더 설정
        self.lineEdit_elderId.setPlaceholderText("아이디")
        self.lineEdit_elderpassword.setPlaceholderText("비밀번호")
        self.lineEdit_elderpassword_2.setPlaceholderText("비밀번호 확인")
        self.lineEdit_elderpassword.setEchoMode(QLineEdit.EchoMode.Password)
        self.lineEdit_elderpassword_2.setEchoMode(QLineEdit.EchoMode.Password)
        self.lineEdit_eldername.setPlaceholderText("이름")
        self.lineEdit_elderbirthday.setPlaceholderText("생년월일 (예: 19700101)")
        self.lineEdit_eldernumber.setPlaceholderText("전화번호 (예: 01012345678)")
        self.lineEdit_elderRFID.setPlaceholderText("RFID 코드")

        #  숫자 입력만 가능하도록 제한
        number_validator = QRegularExpressionValidator(QRegularExpression("[0-9]+"))
        self.lineEdit_elderbirthday.setValidator(number_validator)
        self.lineEdit_eldernumber.setValidator(number_validator)

        #  자동 포맷팅
        self.lineEdit_elderbirthday.textChanged.connect(self.format_birthday)
        self.lineEdit_eldernumber.textChanged.connect(self.format_phonenumber)

        #  비밀번호 일치 여부 확인
        self.lineEdit_elderpassword.textChanged.connect(self.check_password_match)
        self.lineEdit_elderpassword_2.textChanged.connect(self.check_password_match)

        #  아이디 중복 확인 버튼
        self.pushButton_checkelderId.clicked.connect(self.check_id_duplicate)

        #  가입 버튼
        self.pushButton_eldersignup.clicked.connect(self.register_elder)

    def check_password_match(self):
        pw1 = self.lineEdit_elderpassword.text()
        pw2 = self.lineEdit_elderpassword_2.text()

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
        user_id = self.lineEdit_elderId.text().strip()
        if not user_id:
            QMessageBox.warning(self, "입력 오류", "아이디를 입력해주세요.")
            return

        url = "http://34.64.53.123:9999/auth/check_id"
        data = {"user_id": user_id}
        print("[ID 중복확인 요청]:", data)

        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                result = response.json()
                is_available = result.get("available", False)
                if is_available:
                    QMessageBox.information(self, "확인", "사용 가능한 아이디입니다.")
                else:
                    QMessageBox.warning(self, "중복", "이미 사용 중인 아이디입니다.")
            else:
                QMessageBox.critical(self, "오류", "서버 오류가 발생했습니다.")
        except Exception as e:
            print("[ID 중복 예외]:", str(e))
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def register_elder(self):
        user_id = self.lineEdit_elderId.text().strip()
        password = self.lineEdit_elderpassword.text().strip()
        password2 = self.lineEdit_elderpassword_2.text().strip()
        name = self.lineEdit_eldername.text().strip()
        birth_date = self.lineEdit_elderbirthday.text().strip()
        phone_number = self.lineEdit_eldernumber.text().strip()
        rfid = self.lineEdit_elderRFID.text().strip()

        if not all([user_id, password, password2, name, birth_date, phone_number, rfid]):
            QMessageBox.warning(self, "입력 오류", "모든 항목을 입력해주세요.")
            return

        if password != password2:
            QMessageBox.warning(self, "비밀번호 오류", "비밀번호가 일치하지 않습니다.")
            return

        # 하이픈 붙이기
        if len(birth_date) == 8:
            birth_date = f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:]}"
        if len(phone_number) == 11:
            phone_number = f"{phone_number[:3]}-{phone_number[3:7]}-{phone_number[7:]}"

        url = "http://34.64.53.123:9999/auth/elderly"
        data = {
            "user_id": user_id,
            "password": password,
            "name": name,
            "birth_date": birth_date,
            "phone_number": phone_number,
            "rfid": rfid
        }

        print("[회원가입 전송]:", data)

        try:
            response = requests.post(url, json=data)
            status = response.status_code
            print("[응답 코드]:", status)
            response_data = response.json()

            if status == 201:  # 200 → 201로 수정
                QMessageBox.information(self, "가입 성공", "회원가입이 완료되었습니다.")
                self.clear_fields()
                self.close()
            else:
                error_msg = response_data.get("message", "서버 오류가 발생했습니다.")
                QMessageBox.critical(self, "가입 실패", error_msg)
                self.clear_fields()

        except Exception as e:
            print("[가입 예외]:", str(e))
            QMessageBox.critical(self, "네트워크 오류", str(e))
            self.clear_fields()

    def clear_fields(self):
        self.lineEdit_elderId.setText("")
        self.lineEdit_elderpassword.setText("")
        self.lineEdit_elderpassword_2.setText("")
        self.lineEdit_eldername.setText("")
        self.lineEdit_elderbirthday.setText("")
        self.lineEdit_eldernumber.setText("")
        self.lineEdit_elderRFID.setText("")
        self.label_passwordMatch.setText("")

    def format_birthday(self):
        text = self.lineEdit_elderbirthday.text().replace("-", "").strip()
        if len(text) >= 8:
            formatted = f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        elif len(text) >= 6:
            formatted = f"{text[:4]}-{text[4:6]}-{text[6:]}"
        elif len(text) >= 4:
            formatted = f"{text[:4]}-{text[4:]}"
        else:
            formatted = text
        self.lineEdit_elderbirthday.blockSignals(True)
        self.lineEdit_elderbirthday.setText(formatted)
        self.lineEdit_elderbirthday.blockSignals(False)

    def format_phonenumber(self):
        text = self.lineEdit_eldernumber.text().replace("-", "").strip()
        if text.startswith("02") and len(text) >= 9:
            formatted = f"{text[:2]}-{text[2:5]}-{text[5:9]}"
        elif len(text) >= 11:
            formatted = f"{text[:3]}-{text[3:7]}-{text[7:11]}"
        elif len(text) >= 10:
            formatted = f"{text[:3]}-{text[3:6]}-{text[6:]}"
        else:
            formatted = text
        self.lineEdit_eldernumber.blockSignals(True)
        self.lineEdit_eldernumber.setText(formatted)
        self.lineEdit_eldernumber.blockSignals(False)
