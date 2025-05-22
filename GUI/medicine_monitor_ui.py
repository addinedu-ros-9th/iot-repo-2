from PyQt6.QtWidgets import (
    QMainWindow, QTableWidgetItem, QMessageBox, QAbstractItemView, QApplication,QDialog, QVBoxLayout, QListWidget, QListWidgetItem,QLineEdit, QPushButton,QLabel
)
from PyQt6.QtCore import Qt, QDate
from PyQt6 import uic
from PyQt6.QtGui import QPixmap, QGuiApplication
import requests
from datetime import datetime

class MedicineMonitorWindow(QMainWindow):
    def __init__(self, user_id="", target_user_id=None):
        super().__init__()
        uic.loadUi("/home/kbj/dev_ws/project/medicine_monitor.ui", self)
        self.user_id = user_id
        self.target_user_id = target_user_id or user_id 
        self.user_role = ""
        self.center_window()

        print(f"[DEBUG] MainHeartbeatWindow 초기화 → 로그인 ID: {self.user_id}, 대상 ID: {self.target_user_id}")

        self.calendar_selected = False
        self.timeEdit_medicinetime.setDisplayFormat("HH:mm")

        self.pushButton_main.clicked.connect(self.go_to_main_monitor)
        self.action_temperature.triggered.connect(self.open_temperature_monitor)
        self.action_heartbeat.triggered.connect(self.open_heartbeat_monitor) 
        self.action_oxygen.triggered.connect(self.open_oxygen_monitor)
        self.pushButton_save.clicked.connect(self.save_alarm)
        self.pushButton_delete.clicked.connect(self.delete_alarm)
        self.pushButton_logout.clicked.connect(self.logout)
        self.calendarWidget_medicine.selectionChanged.connect(self.on_calendar_selected)
        self.comboBox_medicine.currentTextChanged.connect(self.filter_medicine_list)
        self.pushButton_alertLog.clicked.connect(self.show_alert_log_dialog)

        self.set_login_greeting()
        

        if self.user_role == "guardian":
            self.action_requestElderLink.setVisible(True)
            self.action_requestElderLink.triggered.connect(self.show_elder_request_dialog)
            self.action_requestgaurdianLink.setVisible(False)
        elif self.user_role == "elderly":
            self.action_requestgaurdianLink.setVisible(True)
            self.action_requestgaurdianLink.triggered.connect(self.show_guardian_request_check_dialog)
            self.action_requestElderLink.setVisible(False)


        self.tableWidget_medicine.setColumnCount(5)
        self.tableWidget_medicine.setHorizontalHeaderLabels([
                "요일", "시간", "약 이름", "복용 종료일", "총 일수"
            ])

        self.tableWidget_medicine.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_medicine.setStyleSheet("""
            QTableWidget::item {
                padding-right: 0px;
            }
        """)

        self.load_user_info()
        if self.user_role == "guardian":
            self.setup_comboBox_user()  # 보호자일 경우 콤보박스 세팅
        else:
            self.comboBox_user.setVisible(False)

        self.load_medicine_list()
        self.update_today_summary()

    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def load_user_info(self):
        try:
            res = requests.post("http://34.64.53.123:9999/main/user-detail-info", json={"user_id": self.target_user_id})
            res.raise_for_status()
            info = res.json()
            name = info.get("name", "")
            birth = info.get("birth_date", "")
            phone = info.get("phone_number", "")

            self.label_userName.setText(name)
            self.label_userbirthday.setText(birth)
            self.label_usernumber.setText(phone)
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

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
            print(f"[DEBUG] user_id: {self.user_id}, target_user_id: {self.target_user_id}, role: {self.user_role}")

        except Exception as e:
            print(f"[ERROR] 로그인 인사말 로드 실패: {e}")

    def update_today_summary(self):
        def sf(x): return float(x) if x else 0.0

        try:
            uid = self.target_user_id
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
            print("[ERROR] 센서 요약 정보 로드 실패:", e)

    def get_selected_elderly_id(self):
        if self.user_role == "guardian" and hasattr(self, "comboBox_user"):
            index = self.comboBox_user.currentIndex()
            if index >= 0:
                return self.comboBox_user.itemData(index)
        return self.target_user_id

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

    def load_medicine_list(self):
        print(f"[DEBUG] 약 리스트 요청 user_id: {self.user_id}")
        try:
            res = requests.post("http://34.64.53.123:9999/med/list", json={"user_id": self.target_user_id})
            print(f"[DEBUG] 응답 코드: {res.status_code}")
            print(f"[DEBUG] 응답 내용: {res.text}")
            res.raise_for_status()
            data = res.json()
            medicine_list = data.get("medicine_list", [])
            print(f"[DEBUG] medicine_list 길이: {len(medicine_list)}")
            if medicine_list:
                print(f"[DEBUG] 첫 항목: {medicine_list[0]}")
            else:
                print("[DEBUG] 첫 항목: 비어있음")

            self.medicine_dicts = []
            self.tableWidget_medicine.setRowCount(0)

            for item in medicine_list:
                time_full = item.get("time", "-")
                time_str = time_full[:5] if time_full and ":" in time_full else "-"
                med_name = item.get("med_name", "-")

                days = item.get("day_of_week", "0000000").zfill(7)
                day_labels = ["월", "화", "수", "목", "금", "토", "일"]
                days_text = ", ".join([day_labels[i] for i, d in enumerate(days) if d == "1"]) or "-"

                end_date = item.get("end_date", "-")
                duration_text = "계산불가"

                try:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    today = datetime.today()
                    duration_days = (end_date_obj - today).days
                    duration_text = f"{duration_days}일" if duration_days >= 0 else "-"
                except:
                    pass

                med_dict = {
                    "time": time_str,
                    "med_name": med_name,
                    "days_text": days_text,
                    "end_date": end_date,
                    "duration_text": duration_text
                }
                self.medicine_dicts.append(med_dict)

                row = self.tableWidget_medicine.rowCount()
                self.tableWidget_medicine.insertRow(row)
                self.tableWidget_medicine.setItem(row, 0, QTableWidgetItem(med_dict["days_text"]))
                self.tableWidget_medicine.setItem(row, 1, QTableWidgetItem(med_dict["time"]))
                self.tableWidget_medicine.setItem(row, 2, QTableWidgetItem(med_dict["med_name"]))
                self.tableWidget_medicine.setItem(row, 3, QTableWidgetItem(med_dict["end_date"]))
                self.tableWidget_medicine.setItem(row, 4, QTableWidgetItem(med_dict["duration_text"]))

                print(f"[DEBUG] Row {row} 시간 셀 내용: {self.tableWidget_medicine.item(row, 0).text() if self.tableWidget_medicine.item(row, 0) else 'None'}")

                QApplication.processEvents()
            

        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

        self.comboBox_medicine.blockSignals(True) 
        self.comboBox_medicine.clear()
        self.comboBox_medicine.addItem("전체 보기")
        unique_meds = sorted(set(item.get("med_name", "-") for item in medicine_list))
        self.comboBox_medicine.addItems(unique_meds)
        self.comboBox_medicine.blockSignals(False)
        print(f"[DEBUG] medicine_list 약 이름들: {[item['med_name'] for item in medicine_list]}")

    def setup_comboBox_user(self):
        self.comboBox_user.clear()
        self.comboBox_user.setVisible(True)
        self.comboBox_user.currentIndexChanged.connect(self.on_user_changed)

        try:
            res = requests.post("http://34.64.53.123:9999/main/elderly-list", json={"user_id": self.user_id})
            res.raise_for_status()
            data = res.json()
            for i, (_, info) in enumerate(data.items()):
                name = info.get("name", "이름없음")
                eid = info.get("elderly_id", "")
                self.comboBox_user.addItem(name, eid)
                if i == 0:
                    self.target_user_id = eid
                    self.load_user_info()
                    self.load_medicine_list()
            if self.comboBox_user.count() > 0:
                self.comboBox_user.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def show_elder_request_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("케어 대상자 연동 요청")
        dialog.resize(300, 120)
        layout = QVBoxLayout(dialog)

        label = QLabel("케어 대상자 아이디를 입력하세요:")
        line_edit = QLineEdit()
        request_btn = QPushButton("요청하기")

        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(request_btn)

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
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "실패", "잘못된 아이디거나 서버 오류입니다.")
            except Exception as e:
                QMessageBox.critical(dialog, "네트워크 오류", str(e))

        request_btn.clicked.connect(send)
        dialog.exec()

    def show_guardian_request_check_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("보호자 연동 요청 목록")
        dialog.resize(300, 200)
        layout = QVBoxLayout(dialog)

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
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "실패", "처리 실패")
            except Exception as e:
                QMessageBox.critical(dialog, "네트워크 오류", str(e))

        layout.addWidget(btn_accept)
        layout.addWidget(btn_reject)
        btn_accept.clicked.connect(lambda: handle("accept"))
        btn_reject.clicked.connect(lambda: handle("reject"))
        dialog.setLayout(layout)
        dialog.exec()




    def on_calendar_selected(self):
        self.calendar_selected = True
    
    def on_user_changed(self, index):
        if index < 0:
            return
        self.target_user_id = self.comboBox_user.itemData(index)
        print(f"[DEBUG] 선택된 케어 대상자 ID: {self.target_user_id}")
        self.load_user_info()  # 인사말, 전화번호 등 라벨 갱신
        self.load_medicine_list()  # 약 목록 갱신

    def go_to_main_monitor(self):
        from main_monitor_ui import MainMonitorWindow
        self.main_window = MainMonitorWindow(user_id=self.user_id)
        self.main_window.show()
        self.close()

    def logout(self):
        from login_ui import LoginDialog
        self.login_window = LoginDialog()
        self.login_window.show()
        self.close()

    def save_alarm(self):
        time = self.timeEdit_medicinetime.time().toString("HH:mm")
        medicine_name = self.lineEdit_medicine.text().strip()

        if not medicine_name:
            QMessageBox.warning(self, "입력 오류", "약 이름을 입력해주세요.")
            return

        week_days = [
            self.checkBox_mon, self.checkBox_tue, self.checkBox_wed,
            self.checkBox_thu, self.checkBox_fri, self.checkBox_sat, self.checkBox_sun
        ]
        selected_days = [i for i, cb in enumerate(week_days) if cb.isChecked()]
        if not selected_days:
            QMessageBox.warning(self, "입력 오류", "요일을 선택해주세요.")
            return

        start_date_qdate = QDate.currentDate()
        start_date = start_date_qdate.toString("yyyy-MM-dd")

        if self.calendar_selected:
            end_date_qdate = self.calendarWidget_medicine.selectedDate()
            end_date = end_date_qdate.toString("yyyy-MM-dd")
            duration_days = start_date_qdate.daysTo(end_date_qdate)
            duration_text = f"{duration_days}일"
        else:
            end_date = start_date
            duration_text = "매일"

        day_labels = ["월", "화", "수", "목", "금", "토", "일"]

        # 중복 검사
        for idx in selected_days:
            current_day = day_labels[idx]
            for row in range(self.tableWidget_medicine.rowCount()):
                existing_day = self.tableWidget_medicine.item(row, 0).text()
                existing_time = self.tableWidget_medicine.item(row, 1).text()
                existing_name = self.tableWidget_medicine.item(row, 2).text()
                existing_end_date = self.tableWidget_medicine.item(row, 3).text()

                if (
                    existing_day == current_day and
                    existing_time == time and
                    existing_name == medicine_name and
                    existing_end_date == end_date
                ):
                    QMessageBox.warning(self, "중복 알림", f"{current_day}요일의 동일한 알림이 이미 존재합니다.")
                    return

        # 중복 없으면 실제 저장 및 테이블 반영
        for idx in selected_days:
            week_str = ['0'] * 7
            week_str[idx] = '1'
            week_str = ''.join(week_str)

            payload = {
                "user_id": self.target_user_id,
                "end_date": end_date,
                "day_of_week": week_str,
                "time": time,
                "med_name": medicine_name
            }

            try:
                res = requests.post("http://34.64.53.123:9999/med/add", json=payload)
                if res.status_code != 200:
                    QMessageBox.warning(self, "서버 오류", f"{day_labels[idx]}요일 알림 추가 실패")
                else:
                    # 테이블에 직접 추가
                    row = self.tableWidget_medicine.rowCount()
                    self.tableWidget_medicine.insertRow(row)
                    self.tableWidget_medicine.setItem(row, 0, QTableWidgetItem(day_labels[idx]))  # 요일
                    self.tableWidget_medicine.setItem(row, 1, QTableWidgetItem(time))
                    self.tableWidget_medicine.setItem(row, 2, QTableWidgetItem(medicine_name))
                    self.tableWidget_medicine.setItem(row, 3, QTableWidgetItem(end_date))
                    self.tableWidget_medicine.setItem(row, 4, QTableWidgetItem(duration_text))
            except Exception as e:
                QMessageBox.critical(self, "네트워크 오류", str(e))

        self.lineEdit_medicine.clear()
        self.reset_checkboxes()
        self.calendar_selected = False


        self.load_medicine_list()


    def delete_medicine_by_name(self):
        selected_med_name = self.comboBox_medicine.currentText().strip()
        if not selected_med_name:
            QMessageBox.warning(self, "선택 오류", "삭제할 약 이름을 선택해주세요.")
            return

        # 삭제 전 사용자 확인
        confirm = QMessageBox.question(
            self,
            "확인",
            f"'{selected_med_name}' 약과 관련된 모든 알림을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        payload = {
            "user_id": self.target_user_id,
            "med_name": selected_med_name
        }

        try:
            res = requests.post("http://34.64.53.123:9999/med/delete-med-name", json=payload)
            if res.status_code == 200:
                QMessageBox.information(self, "완료", f"'{selected_med_name}' 관련 알림이 모두 삭제되었습니다.")
                self.load_medicine_list()
            else:
                QMessageBox.warning(self, "서버 오류", "삭제 요청이 실패했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))

    def filter_medicine_list(self, selected_med_name):
        selected_med_name = selected_med_name.strip()

        # 전체 약 보기 옵션이 있다면 처리할 수 있음
        if selected_med_name == "전체 보기":
            self.load_medicine_list()
            return

        # 전체 약 리스트 다시 요청 (서버에서 가져와도 되고, 이미 캐시된 self.medicine_dicts 사용 가능)
        try:
            res = requests.post("http://34.64.53.123:9999/med/list", json={"user_id": self.target_user_id})
            res.raise_for_status()
            medicine_list = res.json().get("medicine_list", [])
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))
            return

        self.tableWidget_medicine.setRowCount(0)

        for item in medicine_list:
            med_name = item.get("med_name", "-")
            if med_name != selected_med_name:
                continue  # 선택한 약과 다른 것은 표시하지 않음

            time_full = item.get("time", "-")
            time_str = time_full[:5] if time_full and ":" in time_full else "-"

            days = item.get("day_of_week", "0000000").zfill(7)
            day_labels = ["월", "화", "수", "목", "금", "토", "일"]
            days_text = ", ".join([day_labels[i] for i, d in enumerate(days) if d == "1"]) or "-"

            end_date = item.get("end_date", "-")
            duration_text = "계산불가"
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                today = datetime.today()
                duration_days = (end_date_obj - today).days
                duration_text = f"{duration_days}일" if duration_days >= 0 else "-"
            except:
                pass

            row = self.tableWidget_medicine.rowCount()
            self.tableWidget_medicine.insertRow(row)
            self.tableWidget_medicine.setItem(row, 0, QTableWidgetItem(days_text))
            self.tableWidget_medicine.setItem(row, 1, QTableWidgetItem(time_str))
            self.tableWidget_medicine.setItem(row, 2, QTableWidgetItem(med_name))
            self.tableWidget_medicine.setItem(row, 3, QTableWidgetItem(end_date))
            self.tableWidget_medicine.setItem(row, 4, QTableWidgetItem(duration_text))

    def open_heartbeat_monitor(self):
        from main_heartbeat_ui import MainHeartbeatWindow
        target_id = self.get_selected_elderly_id()
        print(f"[DEBUG] open_heartbeat_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.heartbeat_window = MainHeartbeatWindow(user_id=self.user_id, target_user_id=target_id)
        self.heartbeat_window.show()
        self.close()

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
        print(f"[DEBUG] open_oxygen_monitor() → 보호자 ID: {self.user_id}, 케어 대상자 ID: {target_id}")
        self.oxygen_window = MainOxygenWindow(user_id=self.user_id, target_user_id=target_id)
        self.oxygen_window.show()
        self.close()

    def reset_checkboxes(self):
        self.checkBox_mon.setChecked(False)
        self.checkBox_tue.setChecked(False)
        self.checkBox_wed.setChecked(False)
        self.checkBox_thu.setChecked(False)
        self.checkBox_fri.setChecked(False)
        self.checkBox_sat.setChecked(False)
        self.checkBox_sun.setChecked(False)

    def delete_alarm(self):
        selected = self.tableWidget_medicine.currentRow()
        selected_combo_med = self.comboBox_medicine.currentText().strip()

        # 콤보박스만 선택된 경우 → 약 전체 삭제
        if selected < 0 and selected_combo_med:
            payload = {
                "user_id": self.target_user_id,
                "med_name": selected_combo_med
            }

            try:
                res = requests.post("http://34.64.53.123:9999/med/delete-med-name", json=payload)
                if res.status_code == 200:
                    QMessageBox.information(self, "완료", f"'{selected_combo_med}' 약의 모든 알림이 삭제되었습니다.")
                    self.load_medicine_list()
                else:
                    QMessageBox.warning(self, "서버 오류", "약 이름으로 삭제 요청이 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "네트워크 오류", str(e))
            return  # 콤보박스 삭제 후 종료

        # 테이블에서 행이 선택된 경우 → 단일 알림 삭제
        if selected < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 항목을 선택해주세요.")
            return

        time_item = self.tableWidget_medicine.item(selected, 1)  # 시간 (열 순서 주의)
        med_name_item = self.tableWidget_medicine.item(selected, 2)  # 약 이름
        days_text_item = self.tableWidget_medicine.item(selected, 0)  # 요일
        end_date_item = self.tableWidget_medicine.item(selected, 3)  # 종료일

        if not all([time_item, med_name_item, days_text_item, end_date_item]):
            QMessageBox.warning(self, "데이터 오류", "삭제할 데이터를 읽을 수 없습니다.")
            return

        time = time_item.text()
        med_name = med_name_item.text()
        end_date = end_date_item.text()
        day_label = days_text_item.text().strip()

        if "," in day_label or day_label == "-":
            QMessageBox.warning(self, "삭제 오류", "하나의 요일만 선택된 알림만 삭제할 수 있습니다.")
            return

        week_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
        day_of_week = ["0"] * 7
        if day_label in week_map:
            day_of_week[week_map[day_label]] = "1"
        else:
            QMessageBox.warning(self, "요일 오류", "알 수 없는 요일 형식입니다.")
            return

        payload = {
            "user_id": self.user_id,
            "end_date": end_date,
            "day_of_week": ''.join(day_of_week),
            "time": time,
            "med_name": med_name
        }

        try:
            res = requests.post("http://34.64.53.123:9999/med/delete", json=payload)
            if res.status_code == 200:
                self.tableWidget_medicine.removeRow(selected)
                QMessageBox.information(self, "완료", "알림이 삭제되었습니다.")
            else:
                QMessageBox.warning(self, "서버 오류", "삭제 요청이 실패했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "네트워크 오류", str(e))
