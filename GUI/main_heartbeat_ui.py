from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QMessageBox, QComboBox, QLabel, QHBoxLayout,QListWidgetItem,
    QDialog, QLineEdit, QPushButton, QListWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6 import uic
from PyQt6.QtCore import QDate
import pyqtgraph as pg
import requests
from PyQt6.QtGui import QGuiApplication


class MainHeartbeatWindow(QMainWindow):
    def __init__(self, user_id="", target_user_id=None):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/main_heartbeat.ui", self)
        self.user_id = user_id
        self.target_user_id = target_user_id or user_id
        self.user_role = ""
        self.center_window()

        print(f"[DEBUG] MainHeartbeatWindow 초기화 → 로그인 ID: {self.user_id}, 대상 ID: {self.target_user_id}")

        self.set_login_greeting()

        # 버튼 & 캘린더
        self.pushButton_main.clicked.connect(self.go_to_main_monitor)
        self.pushButton_logout.clicked.connect(self.go_to_login)
        self.action_medicine.triggered.connect(self.open_medicine_monitor)
        self.calendarWidget.selectionChanged.connect(self.update_heartbeat_graphs)
        self.action_temperature.triggered.connect(self.open_temperature_monitor)
        self.action_oxygen.triggered.connect(self.open_oxygen_monitor)
        self.pushButton_alertLog.clicked.connect(self.show_alert_log_dialog)

        # 보호자라면 콤보박스 표시 및 세팅
        if self.user_role == "guardian":
            self.setup_comboBox_user()
        else:
            self.comboBox_user.setVisible(False)

        # 메뉴 액션 설정
        if self.user_role == "guardian":
            self.action_requestElderLink.setVisible(True)
            self.action_requestElderLink.triggered.connect(self.show_elder_request_dialog)
            self.action_requestgaurdianLink.setVisible(False)
        elif self.user_role == "elderly":
            self.action_requestgaurdianLink.setVisible(True)
            self.action_requestgaurdianLink.triggered.connect(self.show_guardian_request_check_dialog)
            self.action_requestElderLink.setVisible(False)

        # 24시간 심박 플롯
        self.heartbeat_plot = pg.PlotWidget(title="24시간 심박수")
        self.heartbeat_plot.setBackground('w')
        self.heartbeat_plot.setYRange(40, 120)
        self.heartbeat_plot.showGrid(x=True, y=True)
        hb_layout = self.heartbeat_widget.layout() or QVBoxLayout(self.heartbeat_widget)
        hb_layout.addWidget(self.heartbeat_plot)

        # 평균 비교 막대그래프
        self.heartbeat_compare_plot = pg.PlotWidget(title="평균 심박수 비교")
        self.heartbeat_compare_plot.setBackground('w')
        self.heartbeat_compare_plot.setYRange(0, 200)
        self.heartbeat_compare_plot.showGrid(x=True, y=True)
        cmp_layout = self.daily_heartbeat_widget.layout() or QVBoxLayout(self.daily_heartbeat_widget)
        cmp_layout.addWidget(self.heartbeat_compare_plot)

        self.update_heartbeat_graphs()

    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def set_login_greeting(self):
        try:
            res = requests.post("http://34.64.53.123:9999/main/user-detail-info", json={"user_id": self.user_id})
            res.raise_for_status()
            info = res.json()
            self.user_role = info.get("role", "")
            name = info.get("name", "")
            greeting = f"{name} 보호자님, 안녕하세요!" if self.user_role == "guardian" else f"{name}님, 안녕하세요!"
            self.label_userGreeting.setText(greeting)
            print(f"[DEBUG] 로그인 인사말: {greeting}")
        except Exception as e:
            print(f"[ERROR] 사용자 정보 로드 실패: {e}")

    def setup_comboBox_user(self):
        self.comboBox_user.clear()
        self.comboBox_user.setVisible(True)
        self.comboBox_user.currentIndexChanged.connect(self.on_user_changed)
        try:
            res = requests.post("http://34.64.53.123:9999/main/elderly-list", json={"user_id": self.user_id})
            res.raise_for_status()
            for _, info in res.json().items():
                self.comboBox_user.addItem(info.get("name", ""), info.get("elderly_id", ""))
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def get_selected_elderly_id(self):
        if self.user_role == "guardian":
            index = self.comboBox_user.currentIndex()
            if index >= 0:
                return self.comboBox_user.itemData(index)
        return self.user_id

    def update_heartbeat_graphs(self):
        uid = self.get_selected_elderly_id()
        date_str = self.calendarWidget.selectedDate().toString("yyyy-MM-dd")
        payload = {"user_id": uid, "date": date_str}

        try:
            res = requests.post("http://34.64.53.123:9999/query/cal-heart", json=payload)
            res.raise_for_status()
            data = res.json()

            # 정렬된 시간-값 리스트 생성
            items = sorted(data.get("hourly", {}).items(), key=lambda x: int(x[0]))
            hours = [int(k) for k, _ in items if 0 <= int(k) <= 23]
            vals = [float(v.get("heart_rate", 0)) for k, v in items if 0 <= int(k) <= 23]

            # 실시간 심박수 그래프
            self.heartbeat_plot.clear()
            self.heartbeat_plot.setBackground('w')
            self.heartbeat_plot.setYRange(40, 120)
            self.heartbeat_plot.setXRange(0, 24)
            self.heartbeat_plot.showGrid(x=True, y=True)
            self.heartbeat_plot.setTitle("24시간 심박수")

            # x축 2시간 단위 눈금
            ticks = [(i, f"{i}시") for i in range(0, 25, 2)]
            self.heartbeat_plot.getPlotItem().getAxis('bottom').setTicks([ticks])
            self.heartbeat_plot.getPlotItem().getAxis('bottom').setHeight(30)

            self.heartbeat_plot.plot(
                hours, vals,
                pen=pg.mkPen(width=2, color='blue'),
                symbol='o',
                symbolSize=7,
                symbolBrush='navy'
            )

            # 평균 심박수 비교 그래프
            avg = float(data.get("average", 0))
            self.heartbeat_compare_plot.clear()
            self.heartbeat_compare_plot.setBackground('w')
            self.heartbeat_compare_plot.setYRange(0, 200)
            self.heartbeat_compare_plot.showGrid(x=True, y=True)
            self.heartbeat_compare_plot.setTitle(f"{date_str} 평균: {avg:.2f} BPM")

            self.heartbeat_compare_plot.addItem(pg.BarGraphItem(x=[0], height=[avg], width=0.5, brush='red'))
            self.heartbeat_compare_plot.addItem(pg.BarGraphItem(x=[1], height=[65], width=0.5, brush='green'))
            self.heartbeat_compare_plot.getPlotItem().getAxis('bottom').setTicks([[(0, "평균"), (1, "정상(65 BPM)")]])
            self.heartbeat_compare_plot.getPlotItem().getAxis('bottom').setHeight(30)

        except Exception as e:
            print("[ERROR] 심박수 데이터 오류:", e)

        self.update_today_summary()

    def update_today_summary(self):
        def sf(x): return float(x) if x else 0.0

        try:
            uid = self.get_selected_elderly_id()
            ay = requests.post("http://34.64.53.123:9999/main/avg-sensor-data", json={"user_id": uid}).json()
            at = requests.post("http://34.64.53.123:9999/main/sensor-data", json={"user_id": uid}).json()

            def update(label, icon, y, t, unit):
                d = round(t - y, 1)
                label.setText(f"{t}{unit} / {'+' if d >= 0 else ''}{d}{unit}")
                if d > 0:
                    icon.setPixmap(QPixmap("/home/kbj/dev_ws/project/image/up.png").scaled(16, 16))
                elif d < 0:
                    icon.setPixmap(QPixmap("/home/kbj/dev_ws/project/image/down.png").scaled(16, 16))
                else:
                    icon.clear()

            update(self.label_heartbeat, self.label_updown_heartbeat, sf(ay.get("heart_rate")), sf(at.get("heart_rate")), "회")
            update(self.label_temperature, self.label_updown_temperature, sf(ay.get("temperature")), sf(at.get("temperature")), "°C")
            update(self.label_oxygen, self.label_updown_oxygen, sf(ay.get("spo2")), sf(at.get("spo2")), "%")

        except Exception as e:
            print("요약 데이터 오류", e)

    def on_user_changed(self):
        self.target_user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 대상자 변경 → {self.target_user_id}")
        self.update_heartbeat_graphs()

    def go_to_main_monitor(self):
        from main_monitor_ui import MainMonitorWindow
        self.main_window = MainMonitorWindow(user_id=self.user_id)
        self.main_window.show()
        self.close()

    def go_to_login(self):
        if QMessageBox.question(self, "로그아웃", "로그아웃 하시겠습니까?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            from login_ui import LoginDialog
            self.login_window = LoginDialog()
            self.login_window.show()
            self.close()

    def show_elder_request_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("케어 대상자 연동 요청")
        dialog.resize(300, 120)
        layout = QVBoxLayout()
        label = QLabel("케어 대상자 아이디를 입력하세요:")
        line_edit = QLineEdit()
        request_btn = QPushButton("요청하기")
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(request_btn)
        dialog.setLayout(layout)

        def send():
            eid = line_edit.text().strip()
            if not eid:
                QMessageBox.warning(dialog, "입력 오류", "아이디를 입력해주세요.")
                return
            try:
                r = requests.post("http://34.64.53.123:9999/connect/guardian-elderly",
                                  json={"user_id": self.user_id, "elderly_id": eid})
                if r.status_code == 200:
                    QMessageBox.information(dialog, "성공", f"{eid}님에게 요청을 보냈습니다.")
                else:
                    QMessageBox.warning(dialog, "실패", "잘못된 아이디거나 서버 오류입니다.")
            except Exception as e:
                QMessageBox.critical(dialog, "네트워크 오류", str(e))
            dialog.accept()

        request_btn.clicked.connect(send)
        dialog.exec()

    def show_alert_log_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("알림 기록")
        dialog.resize(400, 500)

        layout = QVBoxLayout()
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        list_widget.setDragEnabled(True)
        list_widget.setFlow(QListWidget.Flow.TopToBottom)
        list_widget.setWrapping(False)
        list_widget.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        layout.addWidget(list_widget)

        # 케어대상자 ID 추출 (보호자일 경우 콤보에서 선택된 ID)
        target_user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 알림 요청용 user_id: {target_user_id}")

        url = "http://34.64.53.123:9999/main/alert"
        try:
            res = requests.post(url, json={"user_id": target_user_id})
            print(f"[DEBUG] 알림 기록 요청 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                logs = res.json()
                print(f"[DEBUG] logs keys: {list(logs.keys())}")

                if not logs:
                    list_widget.addItem("알림 기록이 없습니다.")
                else:
                    type_kor = {
                        "fall_detection": "낙상 감지",
                        "temperature": "체온 이상",
                        "heartbeat": "심박 이상"
                    }
                    for key in sorted(logs.keys(), key=int):
                        item = logs[key]
                        alert_type_eng = item.get("type", "알림종류없음")
                        alert_type = type_kor.get(alert_type_eng, alert_type_eng)
                        start = item.get("start_time", "시작시간없음")
                        end = item.get("end_time", "종료시간없음")
                        text = f"{start} ~ {end} : {alert_type}"
                        list_item = QListWidgetItem(text)
                        list_widget.addItem(list_item)
            else:
                QMessageBox.warning(self, "오류", "알림 기록을 불러오지 못했습니다.")
                return
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))
            return

        dialog.setLayout(layout)
        dialog.exec()

    def open_temperature_monitor(self):
        from main_temperature_ui import MainTemperatureWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_temperature_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.temperature_window = MainTemperatureWindow(user_id=self.user_id, target_user_id=target_id)
        self.temperature_window.show()
        self.close()

    def open_oxygen_monitor(self):
        from main_oxygen_ui import MainOxygenWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_heartbeat_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.oxygen_window = MainOxygenWindow(user_id=self.user_id, target_user_id=target_id)
        self.oxygen_window.show()
        self.close()

    def open_medicine_monitor(self):
        from medicine_monitor_ui import MedicineMonitorWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_medicine_monitor() → 로그인 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.medicine_window = MedicineMonitorWindow(user_id=self.user_id, target_user_id=target_id)
        self.medicine_window.show()
        self.close()

    def show_guardian_request_check_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("보호자 연동 요청 목록")
        dialog.resize(300, 200)
        layout = QVBoxLayout()
        guardian_list = QListWidget()
        layout.addWidget(guardian_list)

        try:
            res = requests.post("http://34.64.53.123:9999/connect/elderly-guardian", json={"user_id": self.user_id})
            if res.status_code == 200:
                for item in res.json():
                    gid = item.get("guardian_id")
                    if gid:
                        guardian_list.addItem(gid)
            else:
                QMessageBox.warning(dialog, "오류", "목록을 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(dialog, "네트워크 오류", str(e))

        btn_accept = QPushButton("수락")
        btn_reject = QPushButton("거절")

        def handle(action):
            selected = guardian_list.currentItem()
            if not selected:
                QMessageBox.warning(dialog, "선택 오류", "선택된 항목이 없습니다.")
                return
            gid = selected.text()
            url = f"http://34.64.53.123:9999/connect/elderly-guardian/{'accept' if action == 'accept' else 'decline'}"
            try:
                res = requests.post(url, json={"user_id": self.user_id, "guardian_id": gid})
                if res.status_code == 200:
                    QMessageBox.information(dialog, "완료", f"{gid}님 요청을 {'수락' if action == 'accept' else '거절'}했습니다.")
                else:
                    QMessageBox.warning(dialog, "실패", "처리 실패")
            except Exception as e:
                QMessageBox.critical(dialog, "네트워크 오류", str(e))
            dialog.close()

        layout.addWidget(btn_accept)
        layout.addWidget(btn_reject)
        btn_accept.clicked.connect(lambda: handle("accept"))
        btn_reject.clicked.connect(lambda: handle("reject"))
        dialog.setLayout(layout)
        dialog.exec()
