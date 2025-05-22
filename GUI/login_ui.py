from PyQt6.QtWidgets import QDialog, QMessageBox, QLineEdit
from PyQt6 import uic
import requests
from signup_ui import SignupDialog
from main_monitor_ui import MainMonitorWindow
from PyQt6.QtGui import QGuiApplication

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/login_1.ui", self)
        self.center_window()

        # ✅ 플레이스홀더 설정
        self.lineEdit_id.setPlaceholderText("아이디를 입력하세요")
        self.lineEdit_password.setPlaceholderText("비밀번호를 입력하세요")
        self.lineEdit_password.setEchoMode(QLineEdit.EchoMode.Password)

        # ✅ 오류 메시지 초기화
        self.label_error.setText("")

        # 회원가입
        self.pushButton_signup.clicked.connect(self.open_signup)

        # 로그인
        self.pushButton_login.clicked.connect(self.check_login)

    def open_signup(self):
        self.signup_window = SignupDialog()
        self.signup_window.show()

    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def check_login(self):
        user_id = self.lineEdit_id.text().strip()
        user_pw = self.lineEdit_password.text().strip()

        # 필수 입력 확인
        if not user_id or not user_pw:
            self.label_error.setText("아이디와 비밀번호를 모두 입력해주세요.")
            return

        # 서버 요청
        url = "http://34.64.53.123:9999/auth/login"
        data = {
            "user_id": user_id,
            "password": user_pw
        }

        print("[로그인 요청 URL]:", url)
        print("[전송 데이터]:", data)

        try:
            response = requests.post(url, json=data)
            print("[응답 코드]:", response.status_code)

            if response.status_code == 200:
                result = response.json()
                print("[응답 내용]:", result)

                user_info = result.get("user")
                if not user_info or "user_id" not in user_info:
                    QMessageBox.warning(self, "오류", "로그인 응답에 사용자 정보가 없습니다.")
                    return

                logged_in_user_id = user_info["user_id"]

                # 검색 성공했지만 없는 정보로 403이 나온 경우(복수)
                user_detail_url = "http://34.64.53.123:9999/main/user-detail-info"
                detail_response = requests.post(user_detail_url, json={"user_id": logged_in_user_id})
                print("[DEBUG] user-detail-info 응답코드:", detail_response.status_code)
                if detail_response.status_code == 403:
                    result = detail_response.json()
                    message = result.get("message", "신청 대기 상황입니다.")
                    QMessageBox.information(self, "신청 대기", message)
                    return

                self.label_error.setText("")
                QMessageBox.information(self, "로그인 성공", f"{logged_in_user_id}님 환영합니다!")

                self.main_window = MainMonitorWindow(user_id=logged_in_user_id)
                self.main_window.show()
                self.close()
            else:
                error_msg = response.json().get("message", "로그인 실패")
                self.label_error.setText(error_msg)

        except Exception as e:
            print("[네트워크 예제]:", str(e))
            QMessageBox.critical(self, "네트워크 오류", str(e))
