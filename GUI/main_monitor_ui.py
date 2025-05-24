import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QMessageBox, QDialog, QLabel, QLineEdit, QPushButton,QListWidget,QListWidgetItem,QTextEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6 import uic
import random
import requests
import numpy as np
from PyQt6.QtGui import QGuiApplication

from medicine_monitor_ui import MedicineMonitorWindow
from main_temperature_ui import MainTemperatureWindow
from main_heartbeat_ui import MainHeartbeatWindow
from main_oxygen_ui import MainOxygenWindow

class MainMonitorWindow(QMainWindow):
    def __init__(self, user_id=""):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/main_monitor.ui", self)
        self.user_id = user_id
        self.user_role = ""
        self.center_window()
        self.load_user_info()

        self.pushButton_logout.clicked.connect(self.go_to_login)
        self.action_medicine.triggered.connect(self.open_medicine_monitor)
        self.action_temperature.triggered.connect(self.open_temperature_monitor)
        self.action_heartbeat.triggered.connect(self.open_heartbeat_monitor) 
        self.action_oxygen.triggered.connect(self.open_oxygen_monitor)
        self.pushButton_alertLog.clicked.connect(self.show_alert_log_dialog)

        self.setup_24hour_heart_graph() 
        self.setup_24hour_temp_graph()
        self.setup_24hour_oxygen_graph()

        self.setup_weekly_heart_graph()
        self.setup_weekly_temp_graph()
        self.setup_weekly_oxygen_graph()


        self.update_sensor_summary_from_server()

    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def load_user_info(self):
        url = "http://34.64.53.123:9999/main/user-detail-info"
        data = {"user_id": self.user_id}
        print(f"[DEBUG] self.user_id: '{self.user_id}'")

        try:
            response = requests.post(url, json=data)
            print(f"[DEBUG] user-detail-info 응답코드: {response.status_code}")
            print(f"[DEBUG] user-detail-info 응답내용: {response.text}")

            if response.status_code == 200:
                info = response.json()
                print("[DEBUG] 서버 응답 전체:", info)

                self.user_role = info.get("role", "")
                print(f"[DEBUG] 사용자 역할: {self.user_role}")

                name = info.get("name", "")
                birth = info.get("birth_date", "")
                phone = info.get("phone_number", "")
                greeting = f"{name} 보호자님, 안녕하세요!" if self.user_role == "guardian" else f"{name}님, 안녕하세요!"
                self.label_userGreeting.setText(greeting)
                print(f"[DEBUG] greeting 텍스트: {greeting}")
                print(f"[DEBUG] label_userGreeting 존재 여부: {hasattr(self, 'label_userGreeting')}")

                if self.user_role == "guardian":
                    self.action_requestElderLink.setVisible(True)
                    self.action_requestElderLink.triggered.connect(self.show_elder_request_dialog)
                    self.action_requestgaurdianLink.setVisible(False)

                    # 케어 대상자 리스트 요청
                    url_list = "http://34.64.53.123:9999/main/elderly-list"
                    print(f"[DEBUG] 케어대상자 요청 URL: {url_list}")
                    print(f"[DEBUG] 요청 데이터: {{'user_id': '{self.user_id}'}}")
                    
                    res = requests.post(url_list, json={"user_id": self.user_id})

                    print(f"[DEBUG] 응답 코드: {res.status_code}")
                    print(f"[DEBUG] 응답 본문: {res.text}")

                    if res.status_code == 200:
                        try:
                            self.elder_data = res.json()
                            print(f"[DEBUG] 파싱된 케어대상자 데이터: {self.elder_data}")
                        except Exception as e:
                            print(f"[ERROR] JSON 파싱 실패: {e}")
                            QMessageBox.critical(self, "오류", "서버 응답을 처리할 수 없습니다.")
                            return

                        self.comboBox_user.clear()
                        for _, info in self.elder_data.items():
                            name = info.get("name", "")
                            elderly_id = info.get("elderly_id", "")
                            print(f"[DEBUG] comboBox 추가: {name} ({elderly_id})")
                            self.comboBox_user.addItem(name, elderly_id)

                        self.comboBox_user.currentIndexChanged.connect(self.on_combo_user_changed)
                        self.on_combo_user_changed(self.comboBox_user.currentIndex())
                    else:
                        QMessageBox.warning(self, "오류", "케어 대상자 목록을 불러오지 못했습니다.")

                elif self.user_role == "elderly":
                    self.action_requestgaurdianLink.setVisible(True)
                    self.action_requestgaurdianLink.triggered.connect(self.show_guardian_request_check_dialog)
                    self.action_requestElderLink.setVisible(False)

                    self.label_userName.setText(name)
                    self.label_userbirthday.setText(birth)
                    self.label_usernumber.setText(phone)

            elif response.status_code == 403:
                result = response.json()
                message = result.get("message", "신청 대기 상태입니다.")
                QMessageBox.information(self, "신청 대기", message)
                self.go_to_login()

            else:
                QMessageBox.warning(self, "오류", "사용자 정보를 불러오지 못했습니다.")

        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def on_combo_user_changed(self, index):
        if not hasattr(self, "elder_data") or index < 0:
            return

        selected_elderly_id = self.comboBox_user.itemData(index)
        print(f"[DEBUG] comboBox에서 선택된 elderly_id: {selected_elderly_id}")

        for _, info in self.elder_data.items():
            if info.get("elderly_id") == selected_elderly_id:
                name = info.get("name", "")
                birth = info.get("birth_date", "")
                phone = info.get("phone_number", "")

                print(f"[DEBUG] setting label_userName: {name}")
                print(f"[DEBUG] setting label_userbirthday: {birth}")
                print(f"[DEBUG] setting label_usernumber: {phone}")

                self.label_userName.setText(name)
                self.label_userbirthday.setText(birth)
                self.label_usernumber.setText(phone)

                #  콤보박스 바뀔 때마다 심박 그래프도 갱신
                self.setup_24hour_heart_graph()
                self.setup_24hour_temp_graph()
                self.setup_24hour_oxygen_graph()

                self.setup_weekly_heart_graph()
                self.setup_weekly_temp_graph()
                self.setup_weekly_oxygen_graph()


                self.update_sensor_summary_from_server()

                break



    def load_elder_info(self):
        url = "http://34.64.53.123:9999/main/linked-elder-info"
        data = {"guardian_id": self.user_id}
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                elder = response.json()
                self.label_userName.setText(elder.get("name", ""))
                self.label_userbirthday.setText(elder.get("birth_date", ""))
                self.label_usernumber.setText(elder.get("phone_number", ""))
            else:
                QMessageBox.warning(self, "오류", "케어 대상자 정보를 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def show_guardian_request_check_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("보호자 연동 신청 확인")
        dialog.resize(300, 120)
        layout = QVBoxLayout()
        label = QLabel("보호자 연동 요청을 확인하는 기능입니다.")
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec()

    def setup_24hour_heart_graph(self):
        url = "http://34.64.53.123:9999/main/total-heart-data"
        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 24시간 심박 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                data = res.json()
                if not data:
                    self.clear_heartbeat_graph()  # 그래프 초기화
                    return

                # 기존 그래프 삭제
                layout = self.heartbeat_widget.layout()
                if layout is None:
                    layout = QVBoxLayout(self.heartbeat_widget)
                    self.heartbeat_widget.setLayout(layout)
                else:
                    while layout.count():
                        child = layout.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()

                # 정렬 및 데이터 준비
                sorted_items = sorted(data.items(), key=lambda x: int(x[0]))
                heart_rates = [float(v["value"]) for _, v in sorted_items]
                timestamps = [v["timestamp"][:-3] for _, v in sorted_items]  # HH:MM
                total_points = len(timestamps)

                # X축 tick 위치: 시작 ~ 끝 기준으로 총 12개 균등 인덱스
                tick_positions = np.linspace(0, total_points - 1, 12, dtype=int)
                tick_labels = [(i, timestamps[i]) for i in tick_positions]

                # 그래프 생성
                plot = pg.PlotWidget(title="24시간 심박수")
                plot.setBackground('w')
                plot.setYRange(50, 150)
                plot.showGrid(x=True, y=True)
                plot.plot(list(range(total_points)), heart_rates, pen='r')

                axis = plot.getPlotItem().getAxis('bottom')
                axis.setTicks([tick_labels])

                layout.addWidget(plot)

            else:
                QMessageBox.warning(self, "오류", "심박수 데이터를 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def setup_24hour_temp_graph(self):
        url = "http://34.64.53.123:9999/main/total-temp-data"
        user_id = self.get_selected_elderly_id()  # ✅ 여기 중요
        print(f"[DEBUG] 24시간 체온 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                data = res.json()
                if not data:
                    self.clear_temp_graph()
                    return

                # 정렬
                sorted_items = sorted(data.items(), key=lambda x: int(x[0]))
                temperatures = [float(v["value"]) for _, v in sorted_items]
                timestamps = [v["timestamp"][:5] for _, v in sorted_items]  # HH:MM

                # 그래프 준비
                plot = pg.PlotWidget(title="24시간 체온 변화")
                plot.setBackground('w')
                plot.setYRange(35, 39)
                plot.showGrid(x=True, y=True)
                plot.plot(list(range(len(temperatures))), temperatures, pen='orange')

                # x축 라벨 12개로 나누기
                tick_count = 12
                tick_interval = max(1, len(timestamps) // (tick_count - 1))
                tick_labels = [(i, timestamps[i]) for i in range(0, len(timestamps), tick_interval)]
                plot.getPlotItem().getAxis('bottom').setTicks([tick_labels])

                # 기존 레이아웃 초기화 후 추가
                layout = self.temperature_widget.layout()
                if layout is None:
                    layout = QVBoxLayout(self.temperature_widget)
                    self.temperature_widget.setLayout(layout)
                else:
                    while layout.count():
                        child = layout.takeAt(0)
                        if child.widget():
                            child.widget().deleteLater()

                layout.addWidget(plot)

            else:
                self.clear_temp_graph()
        except Exception as e:
            print(f"[ERROR] 네트워크 오류: {e}")
            self.clear_temp_graph()

    def setup_24hour_oxygen_graph(self):
        url = "http://34.64.53.123:9999//main/total-spo2-data"
        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 24시간 산소 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            # oxygen_widget 초기화
            self.clear_layout(self.oxygen_widget)

            if res.status_code == 200:
                data = res.json()
                if not data:
                    print("[DEBUG] 산소 데이터 없음")
                    return

                sorted_items = sorted(data.items(), key=lambda x: int(x[0]))
                values = [float(v["value"]) for _, v in sorted_items]
                times = [v["timestamp"][:5] for _, v in sorted_items]

                # 12개 x축 tick 생성
                num_ticks = 12
                tick_indices = [round(i * (len(times) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
                tick_labels = [(i, times[i]) for i in tick_indices]

                plot = pg.PlotWidget(title="24시간 산소포화도")
                plot.setBackground('w')
                plot.setYRange(85, 100)
                plot.showGrid(x=True, y=True)
                plot.plot(list(range(len(values))), values, pen='g')

                plot.getPlotItem().getAxis('bottom').setTicks([tick_labels])

                layout = self.oxygen_widget.layout() or QVBoxLayout(self.oxygen_widget)
                layout.addWidget(plot)
            else:
                print("[DEBUG] 산소 데이터 응답 실패")
        except Exception as e:
            print(f"[ERROR] 산소 네트워크 오류: {e}")

    def setup_weekly_heart_graph(self):
        url = "http://34.64.53.123:9999/main/avg7-heart-data"
        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 주간 심박 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                data = res.json()
                if not data:
                    self.clear_layout(self.heartbeat_weekly_widget)
                    return
                
                sorted_data = sorted(data.items(), key=lambda x: int(x[0]))
                weekdays = [v["weekday"] for _, v in sorted_data]
                values = [float(v["value"]) for _, v in sorted_data]

                bar_chart = pg.PlotWidget(title="주간 평균 심박수")
                bar_chart.setBackground('w')
                plot_item = bar_chart.getPlotItem()
                plot_item.setYRange(50, 150)
                plot_item.showGrid(x=True, y=True)
                plot_item.setLabel('left', 'BPM')
                plot_item.setLabel('bottom', '요일')

                x_values = list(range(len(weekdays)))
                plot_item.getAxis('bottom').setTicks([list(zip(x_values, weekdays))])

                bar_item = pg.BarGraphItem(x=x_values, height=values, width=0.6, brush='red')
                plot_item.addItem(bar_item)

                # 안전하게 기존 layout 사용
                layout = self.heartbeat_weekly_widget.layout()
                if layout is None:
                    layout = QVBoxLayout(self.heartbeat_weekly_widget)
                self.clear_layout(self.heartbeat_weekly_widget)
                layout.addWidget(bar_chart)

            else:
                QMessageBox.warning(self, "오류", "주간 심박 데이터를 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def setup_weekly_temp_graph(self):
        url = "http://34.64.53.123:9999/main/avg7-temp-data"
        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 주간 체온 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                data = res.json()
                if not data:
                    self.clear_layout(self.temperature_weekly_widget)
                    return

                sorted_data = sorted(data.items(), key=lambda x: int(x[0]))
                weekdays = [v["weekday"] for _, v in sorted_data]
                values = [float(v["value"]) for _, v in sorted_data]

                bar_chart = pg.PlotWidget(title="주간 평균 체온")
                bar_chart.setBackground('w')
                plot_item = bar_chart.getPlotItem()
                plot_item.setYRange(35, 38)
                plot_item.showGrid(x=True, y=True)
                plot_item.setLabel('left', '℃')
                plot_item.setLabel('bottom', '요일')

                x_values = list(range(len(weekdays)))
                plot_item.getAxis('bottom').setTicks([list(zip(x_values, weekdays))])

                bar_item = pg.BarGraphItem(x=x_values, height=values, width=0.6, brush='orange')
                plot_item.addItem(bar_item)

                layout = self.temperature_weekly_widget.layout()
                if layout is None:
                    layout = QVBoxLayout(self.temperature_weekly_widget)
                self.clear_layout(self.temperature_weekly_widget)
                layout.addWidget(bar_chart)

            else:
                QMessageBox.warning(self, "오류", "주간 체온 데이터를 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def setup_weekly_oxygen_graph(self):
        url = "http://34.64.53.123:9999/main/avg7-spo2-data"
        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 주간 산소포화도 요청 user_id: {user_id}")

        try:
            res = requests.post(url, json={"user_id": user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")

            if res.status_code == 200:
                data = res.json()
                if not data:
                    self.clear_layout(self.oxygen_weekly_widget)
                    return

                sorted_data = sorted(data.items(), key=lambda x: int(x[0]))
                weekdays = [v["weekday"] for _, v in sorted_data]
                values = [float(v["value"]) for _, v in sorted_data]

                bar_chart = pg.PlotWidget(title="주간 평균 산소포화도")
                bar_chart.setBackground('w')
                plot_item = bar_chart.getPlotItem()
                plot_item.setYRange(85, 100)
                plot_item.showGrid(x=True, y=True)
                plot_item.setLabel('left', '%')
                plot_item.setLabel('bottom', '요일')

                x_values = list(range(len(weekdays)))
                plot_item.getAxis('bottom').setTicks([list(zip(x_values, weekdays))])

                bar_item = pg.BarGraphItem(x=x_values, height=values, width=0.6, brush='green')
                plot_item.addItem(bar_item)

                layout = self.oxygen_weekly_widget.layout()
                if layout is None:
                    layout = QVBoxLayout(self.oxygen_weekly_widget)
                self.clear_layout(self.oxygen_weekly_widget)
                layout.addWidget(bar_chart)

            else:
                QMessageBox.warning(self, "오류", "주간 산소포화도 데이터를 불러오지 못했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def clear_heartbeat_graph(self):
        layout = self.heartbeat_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.heartbeat_widget)
            self.heartbeat_widget.setLayout(layout)
        else:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

    def clear_temp_graph(self):
        layout = self.temperature_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.temperature_widget)
            self.temperature_widget.setLayout(layout)
        else:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

    def clear_layout(self, widget):
        layout = widget.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget_to_remove = item.widget()
                if widget_to_remove is not None:
                    widget_to_remove.setParent(None)

    def update_sensor_summary_from_server(self):
        def safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        user_id = self.get_selected_elderly_id()
        print(f"[DEBUG] 센서 요약 요청 user_id: {user_id}")

        # 어제 평균 데이터 요청
        url_yesterday = "http://34.64.53.123:9999/main/avg-sensor-data"
        # 오늘 평균 데이터 요청
        url_today = "http://34.64.53.123:9999/main/sensor-data"

        try:
            res_y = requests.post(url_yesterday, json={"user_id": user_id})
            res_t = requests.post(url_today, json={"user_id": user_id})

            if res_y.status_code == 200 and res_t.status_code == 200:
                avg_yesterday = res_y.json()
                avg_today = res_t.json()

                print(f"[DEBUG] 어제 평균 데이터: {avg_yesterday}")
                print(f"[DEBUG] 오늘 평균 데이터: {avg_today}")

                # 각 센서별 float 변환 및 차이 계산
                y_heart = safe_float(avg_yesterday.get("heart_rate"))
                t_heart = safe_float(avg_today.get("heart_rate"))
                d_heart = round(t_heart - y_heart, 1)

                y_temp = safe_float(avg_yesterday.get("temperature"))
                t_temp = safe_float(avg_today.get("temperature"))
                d_temp = round(t_temp - y_temp, 1)

                y_oxy = safe_float(avg_yesterday.get("spo2"))
                t_oxy = safe_float(avg_today.get("spo2"))
                d_oxy = round(t_oxy - y_oxy, 1)

                print(f"[DEBUG] Heartbeat - 어제: {y_heart}, 오늘: {t_heart}, 차이: {d_heart}")
                print(f"[DEBUG] Temperature - 어제: {y_temp}, 오늘: {t_temp}, 차이: {d_temp}")
                print(f"[DEBUG] Oxygen - 어제: {y_oxy}, 오늘: {t_oxy}, 차이: {d_oxy}")

                # UI 갱신
                self.label_heartbeat.setText(f"{t_heart}회 / {'+' if d_heart >= 0 else ''}{d_heart}회")
                self.label_temperature.setText(f"{t_temp}도 / {'+' if d_temp >= 0 else ''}{d_temp}도")
                self.label_oxygen.setText(f"{t_oxy}% / {'+' if d_oxy >= 0 else ''}{d_oxy}%")

                # 아이콘 업데이트
                def update_icon(label, diff, unit):
                    if diff > 0:
                        path = "/home/kbj/dev_ws/project/image/up.png"
                    elif diff < 0:
                        path = "/home/kbj/dev_ws/project/image/down.png"
                    else:
                        label.clear()
                        return
                    label.setPixmap(QPixmap(path).scaled(20, 20))

                update_icon(self.label_updown_heartbeat, d_heart, "회")
                update_icon(self.label_updown_temperature, d_temp, "도")
                update_icon(self.label_updown_oxygen, d_oxy, "%")

            else:
                QMessageBox.warning(self, "오류", "센서 평균 데이터를 불러오지 못했습니다.")

        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))


    def go_to_login(self):
        reply = QMessageBox.question(self, "로그아웃 확인", "로그아웃 하시겠습니까?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from login_ui import LoginDialog
            self.login_window = LoginDialog()
            self.login_window.show()
            self.close()

    def open_medicine_monitor(self):
        from medicine_monitor_ui import MedicineMonitorWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_medicine_monitor() → 로그인 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.medicine_window = MedicineMonitorWindow(user_id=self.user_id, target_user_id=target_id)
        self.medicine_window.show()
        self.close()

    def open_temperature_monitor(self):
        from main_temperature_ui import MainTemperatureWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_temperature_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.temperature_window = MainTemperatureWindow(user_id=self.user_id, target_user_id=target_id)
        self.temperature_window.show()
        self.close()


    def open_heartbeat_monitor(self):
        from main_heartbeat_ui import MainHeartbeatWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_heartbeat_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.heartbeat_window = MainHeartbeatWindow(user_id=self.user_id, target_user_id=target_id)
        self.heartbeat_window.show()
        self.close()


    def open_oxygen_monitor(self):
        from main_oxygen_ui import MainOxygenWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_oxygen_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.oxygen_window = MainOxygenWindow(user_id=self.user_id, target_user_id=target_id)
        self.oxygen_window.show()
        self.close()

    
    def get_selected_elderly_id(self):
        if self.user_role == "guardian":
            index = self.comboBox_user.currentIndex()
            if index >= 0:
                return self.comboBox_user.itemData(index)
        return self.user_id



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




    def show_guardian_request_check_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("보호자 연동 요청 목록")
        dialog.resize(300, 200)

        layout = QVBoxLayout()
        guardian_list = QListWidget()
        selected_guardian_id = {"value": None}  # 선택된 ID 저장용

        url = "http://34.64.53.123:9999/connect/elderly-guardian"

        try:
            res = requests.post(url, json={"user_id": self.user_id})
            if res.status_code == 200:
                requests_data = res.json()

                if not requests_data:
                    QMessageBox.information(self, "알림", "보호자 요청이 없습니다.")
                    return

                for req in requests_data:
                    guardian_id = req.get("guardian_id")
                    if guardian_id:
                        guardian_list.addItem(guardian_id)
            else:
                QMessageBox.warning(self, "오류", "요청 목록을 불러오지 못했습니다.")
                return

        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))
            return

        # 리스트 항목 클릭 시 선택값 저장
        def on_item_selected():
            selected_item = guardian_list.currentItem()
            if selected_item:
                selected_guardian_id["value"] = selected_item.text()

        guardian_list.itemClicked.connect(on_item_selected)

        # 수락 버튼
        accept_btn = QPushButton("수락")
        accept_btn.clicked.connect(lambda: self.respond_guardian_request(selected_guardian_id["value"], "accept", dialog))

        # 거절 버튼
        reject_btn = QPushButton("거절")
        reject_btn.clicked.connect(lambda: self.respond_guardian_request(selected_guardian_id["value"], "reject", dialog))

        layout.addWidget(QLabel("보호자 요청 목록"))
        layout.addWidget(guardian_list)
        layout.addWidget(accept_btn)
        layout.addWidget(reject_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def respond_guardian_request(self, guardian_id, action, dialog):
        # 요청 URL 결정
        if action == "accept":
            url = "http://34.64.53.123:9999/connect/elderly-guardian/accept"
        elif action == "reject":
            url = "http://34.64.53.123:9999/connect/elderly-guardian/decline"
        else:
            QMessageBox.warning(self, "오류", "알 수 없는 작업입니다.")
            return

        # 요청 데이터
        data = {
            "user_id": self.user_id,
            "guardian_id": guardian_id
        }
        print(f"[DEBUG] 보호자 연동 처리 요청 전송 데이터: {data}")

        try:
            res = requests.post(url, json=data)
            if res.status_code == 200:
                QMessageBox.information(
                    self,
                    "처리 완료",
                    f"{guardian_id}님의 요청을 {'수락' if action == 'accept' else '거절'}했습니다."
                )
            else:
                QMessageBox.warning(self, "실패", "요청 처리에 실패했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

        dialog.close()

    def show_elder_request_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("케어 대상자 연동 요청")
        dialog.resize(300, 120)

        layout = QVBoxLayout()
        label = QLabel("케어 대상자 아이디를 입력하세요:")
        label.setWordWrap(True)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("예: elder123")
        request_btn = QPushButton("요청하기")

        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(request_btn)
        dialog.setLayout(layout)

        def send_request():
            elder_id = line_edit.text().strip()
            if not elder_id:
                QMessageBox.warning(dialog, "입력 오류", "아이디를 입력해주세요.")
                return

            url = "http://34.64.53.123:9999/connect/guardian-elderly"
            data = {
                "user_id": self.user_id,
                "elderly_id": elder_id
            }

            try:
                print(f"[DEBUG] 연동 요청 전송 데이터: {data}")
                response = requests.post(url, json=data)
                print(f"[DEBUG] 응답 코드: {response.status_code}")
                print(f"[DEBUG] 응답 내용: {response.text}")

                if response.status_code == 200:
                    QMessageBox.information(dialog, "요청 완료", f"{elder_id}님에게 연동 요청을 보냈습니다.")
                else:
                    QMessageBox.warning(dialog, "요청 실패", "서버 오류 또는 잘못된 아이디입니다.")
            except Exception as e:
                QMessageBox.critical(dialog, "네트워크 오류", str(e))

            dialog.accept()

        request_btn.clicked.connect(send_request)
        dialog.exec()
