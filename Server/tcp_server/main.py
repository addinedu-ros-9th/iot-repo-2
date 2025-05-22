import socket
import threading
import datetime
import sys
import time
sys.path.append('/home/tunguser/iot_project')

from server.db.mysql_connect import get_connection

# TCP 서버 설정
HOST = '0.0.0.0'  # 모든 네트워크 인터페이스에서 연결을 수신합니다 (서버 실행 시)
# 참고: 34.64.53.123은 아두이노 코드에서 연결할 서버 주소입니다.
# 아두이노는 TCP_SERVER = "34.64.53.123"로 이 서버에 연결을 시도합니다.
PORT = 8888       # Arduino 코드와 일치하는 포트

# 현재 연결된 사용자 정보를 저장하는 딕셔너리
connected_users = {}  # {client_socket: user_id}
# 사용자 ID로 소켓을 찾기 위한 역방향 매핑
user_sockets = {}  # {user_id: client_socket}

# 마지막으로 약 알림을 보낸 시간을 저장하는 딕셔너리
last_medicine_check = {}  # {user_id: {med_name: datetime}}

# 명령어 처리 함수
def process_command(command, client_socket):
    """명령어 처리 함수"""
    try:
        # 앞 2바이트를 명령어로 사용
        cmd_type = command[:2]
        
        if cmd_type == "SU":  # Send Uid (IF-01)
            # {SU(2)}{TAG UID(32)}{\n(1)}
            uid = command[2:].strip()
            print(f"UID 수신: {uid}")
            
            # RFID로 사용자 확인
            conn = None
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                
                # RFID로 사용자 조회
                query = "SELECT u.user_id, u.name FROM Rfid r JOIN User u ON r.user_id = u.user_id WHERE r.rfid = %s"
                cur.execute(query, (uid,))
                user = cur.fetchone()
                
                if user:
                    # 사용자 찾음
                    user_id = user['user_id']
                    name = user['name']
                    
                    # 현재 소켓에 사용자 ID 연결
                    connected_users[client_socket] = user_id
                    user_sockets[user_id] = client_socket
                    
                    # 이름을 바이트로 변환하여 길이 확인 (한글은 UTF-8에서 3바이트)
                    id_bytes = user_id.encode('utf-8')
                    
                    # 이름이 9바이트를 초과하면 잘라냄
                    if len(id_bytes) > 12:
                        # 바이트 단위로 자르면 한글이 깨질 수 있으므로 글자 단위로 줄여가며 확인
                        while len(id_bytes) > 12:
                            user_id = user_id[:-1]
                            id_bytes = user_id.encode('utf-8')
                    # 이름이 9바이트 미만이면 공백으로 채움
                    elif len(id_bytes) < 12:
                        # 남은 바이트 수만큼 공백 추가
                        padding = 12 - len(id_bytes)
                        user_id = user_id + ' ' * padding
                    
                    # IF-02: {GN(2)}{Status(1)}{ID(12)}{\n(1)}
                    return f"GN1{user_id}\n"
                else:
                    # 사용자 없음
                    # IF-03: {GE(2)}{Status(1)}{ERROR(3)}{\n(1)}
                    return "GE1404\n"  # 404: 사용자 없음
            
            except Exception as e:
                print(f"데이터베이스 오류: {str(e)}")
                return "GE1500\n"  # 500: 서버 오류
            
            finally:
                if conn:
                    conn.close()
                
        elif cmd_type == "SD":  # Send sensorData (IF-04)
            # {SD(2)}{Heart_rate(3)}{Sp02(3)}{Temperature(3)}{\n(1)}
            # 예: SD102098241 -> 심박수=102, SpO2=098, 온도=24.1
            data = command[2:].strip()
            
            if len(data) >= 9:  # 최소 9자리 데이터(심박수 3자리 + SpO2 3자리 + 온도 3자리)
                try:
                    heart_rate = int(data[0:3])  # 처음 3자리는 심박수
                    spo2 = int(data[3:6])        # 다음 3자리는 SpO2
                    temp_int = int(data[6:8])    # 다음 2자리는 온도 정수 부분
                    temp_decimal = int(data[8:9])  # 마지막 1자리는 온도 소수 부분
                    temperature = temp_int + (temp_decimal / 10.0)
                    print(f"센서 데이터 수신: 심박수={heart_rate}, SpO2={spo2}, 체온={temperature}")
                    
                    # 현재 소켓에 연결된 사용자 ID 확인
                    user_id = connected_users.get(client_socket)
                    if user_id:
                        # DB에 센서 데이터 저장
                        conn = None
                        try:
                            conn = get_connection()
                            cur = conn.cursor(dictionary=True)
                            
                            # 센서 데이터 저장
                            query = "INSERT INTO SensorData (user_id, heart_rate, spo2, temperature) VALUES (%s, %s, %s, %s)"
                            cur.execute(query, (user_id, heart_rate, spo2, temperature))
                            conn.commit()
                            
                            return "OK\n"
                        
                        except Exception as e:
                            print(f"데이터베이스 오류: {str(e)}")
                            return "ER1DB\n"  # 데이터베이스 오류
                        
                        finally:
                            if conn:
                                conn.close()
                    else:
                        print("연결된 사용자 정보 없음")
                        return "ER1AU\n"  # 인증 필요 오류
                except ValueError:
                    return "ER1FT\n"  # 데이터 형식 오류
            else:
                return "ER1FT\n"  # 데이터 형식 오류   


        elif cmd_type == "SS":  # Send Alertlog Start (IF-05)
            # {SS(2)}{alert_type(1)}{\n(1)} - 1바이트 비트 플래그로 변경
            alert_data = command[2:]  # strip() 제거
            
            if len(alert_data) >= 1:
                # 1바이트 비트 플래그로 처리
                alert_byte = ord(alert_data[0])
                
                # 알림 유형 확인
                alert_types = []
                if alert_byte & 0x01:  # 비트 0: 낙상 감지
                    alert_types.append("낙상 감지")
                if alert_byte & 0x02:  # 비트 1: 고온
                    alert_types.append("고온")
                if alert_byte & 0x04:  # 비트 2: 저온
                    alert_types.append("저온")
                if alert_byte & 0x08:  # 비트 3: 빠른 심박수
                    alert_types.append("빠른 심박수")
                if alert_byte & 0x10:  # 비트 4: 느린 심박수
                    alert_types.append("느린 심박수")
                if alert_byte & 0x40:  # 비트 5: 낮은 산소포화도
                    alert_types.append("낮은 산소포화도")
                
                alert_message = ", ".join(alert_types)
                print(f"알림 시작: {alert_message} (비트 플래그: {alert_byte})")
                
                # 현재 소켓에 연결된 사용자 ID 확인
                user_id = connected_users.get(client_socket)
                if user_id and alert_types:
                    # DB에 알림 로그 저장
                    conn = None
                    try:
                        conn = get_connection()
                        cur = conn.cursor(dictionary=True)
                        
                        # 각 알림 유형별로 별도의 레코드 생성
                        for alert_type in alert_types:
                            query = "INSERT INTO AlertLog (user_id, alert_type) VALUES (%s, %s)"
                            cur.execute(query, (user_id, alert_type))
                        
                        conn.commit()
                        return "OK\n"
                    
                    except Exception as e:
                        print(f"데이터베이스 오류: {str(e)}")
                        return "ER1DB\n"  # 데이터베이스 오류
                    
                    finally:
                        if conn:
                            conn.close()
                else:
                    print("연결된 사용자 정보 없음 또는 알림 없음")
                    return "ER1AU\n"  # 인증 필요 오류
            else:
                return "ER1FT\n"  # 데이터 형식 오류
                
        elif cmd_type == "SE":  # Send Alertlog End (IF-06)
            # {SE(2)}{alert_type(1)}{\n(1)} - 1바이트 비트 플래그로 변경
            alert_data = command[2:]  # strip() 제거
            
            if len(alert_data) >= 1:
                # 1바이트 비트 플래그로 처리
                alert_byte = ord(alert_data[0])
                
                # 알림 유형 확인
                alert_types = []
                if alert_byte & 0x01:  # 비트 0: 낙상 감지
                    alert_types.append("낙상 감지")
                if alert_byte & 0x02:  # 비트 1: 고온
                    alert_types.append("고온")
                if alert_byte & 0x04:  # 비트 2: 저온
                    alert_types.append("저온")
                if alert_byte & 0x08:  # 비트 3: 빠른 심박수
                    alert_types.append("빠른 심박수")
                if alert_byte & 0x10:  # 비트 4: 느린 심박수
                    alert_types.append("느린 심박수")
                if alert_byte & 0x40:  # 비트 5: 낮은 산소포화도
                    alert_types.append("낮은 산소포화도")
                
                alert_message = ", ".join(alert_types)
                print(f"알림 종료: {alert_message} (비트 플래그: {alert_byte})")
                
                # 현재 소켓에 연결된 사용자 ID 확인
                user_id = connected_users.get(client_socket)
                if user_id and alert_types:
                    # DB에 알림 종료 시간 업데이트
                    conn = None
                    try:
                        conn = get_connection()
                        cur = conn.cursor(dictionary=True)
                        
                        # 각 알림 유형별로 가장 최근 로그 업데이트
                        for alert_type in alert_types:
                            query = """
                                UPDATE AlertLog 
                                SET end_time = CURRENT_TIMESTAMP 
                                WHERE user_id = %s AND alert_type = %s AND end_time IS NULL 
                                ORDER BY start_time DESC 
                                LIMIT 1
                            """
                            cur.execute(query, (user_id, alert_type))
                        
                        conn.commit()
                        return "OK\n"
                    
                    except Exception as e:
                        print(f"데이터베이스 오류: {str(e)}")
                        return "ER1DB\n"  # 데이터베이스 오류
                    
                    finally:
                        if conn:
                            conn.close()
                else:
                    print("연결된 사용자 정보 없음 또는 알림 없음")
                    return "ER1AU\n"  # 인증 필요 오류
            else:
                return "ER1FT\n"  # 데이터 형식 오류
                
        else:
            print(f"알 수 없는 명령어: {cmd_type}")
            return "ER1CM\n"  # 알 수 없는 명령어
            
    except Exception as e:
        print(f"명령어 처리 오류: {str(e)}")
        return "ER1SV\n"  # 서버 내부 오류

def check_medicine_for_user(user_id, client_socket):
    """특정 사용자의 현재 복용해야 할 약을 확인하고 알림을 보내는 함수"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        
        current_time = datetime.datetime.now().time()
        current_day = datetime.datetime.now().weekday() + 1  # 1(월요일)~7(일요일)
        
        # 현재 시간에 복용해야 할 약 조회
        query = """
            SELECT m.med_name 
            FROM MedicationReminder mr 
            JOIN Medicine m ON mr.med_name = m.med_name AND mr.user_id = m.user_id 
            WHERE mr.user_id = %s 
            AND TIME(mr.time) <= TIME(%s) 
            AND TIME(mr.time) >= TIME(DATE_SUB(%s, INTERVAL 5 MINUTE))
            AND (mr.day_of_week & %s > 0 OR mr.day_of_week IS NULL)
            AND (m.end_date IS NULL OR m.end_date >= CURRENT_DATE)
        """
        cur.execute(query, (user_id, current_time, current_time, 1 << (current_day - 1)))
        medicine = cur.fetchone()
        
        if medicine:
            med_name = medicine['med_name']
            # 이미 알림을 보낸 약인지 확인
            if user_id in last_medicine_check and med_name in last_medicine_check[user_id]:
                last_check = last_medicine_check[user_id][med_name]
                # 마지막 알림 이후 10분이 지나지 않았으면 알림을 보내지 않음
                if (datetime.datetime.now() - last_check).total_seconds() < 600:  # 10분 = 600초
                    return False
            
            # 약 이름을 바이트로 변환
            med_name_bytes = med_name.encode('utf-8')
            
            # 20바이트로 정확히 맞추기
            if len(med_name_bytes) > 20:
                # 바이트 단위로 자르면 한글이 깨질 수 있으므로 글자 단위로 줄여가며 확인
                while len(med_name_bytes) > 20:
                    med_name = med_name[:-1]
                    med_name_bytes = med_name.encode('utf-8')
            
            # 정확히 20바이트 배열 생성
            result_bytes = bytearray(20)
            # 약 이름 바이트 복사
            for i in range(len(med_name_bytes)):
                if i < 20:  # 20바이트 넘지 않도록 보호
                    result_bytes[i] = med_name_bytes[i]
            
            # 알림 시간 업데이트
            if user_id not in last_medicine_check:
                last_medicine_check[user_id] = {}
            last_medicine_check[user_id][medicine['med_name']] = datetime.datetime.now()
            
            # GM 명령어(2바이트) + 약 이름(20바이트) + 개행(1바이트)
            message = bytearray(b'GM') + result_bytes + bytearray(b'\n')
            
            # 바이트 데이터를 직접 소켓으로 전송
            try:
                client_socket.send(message)
                print(f"[{datetime.datetime.now()}] 약 복용 알림 전송: {user_id} → GM + {med_name}")
                return True
            except Exception as e:
                print(f"[{datetime.datetime.now()}] 약 복용 알림 전송 실패: {str(e)}")
                return False
        
        return False
    
    except Exception as e:
        print(f"약 정보 조회 오류: {str(e)}")
        return False
    
    finally:
        if conn:
            conn.close()

def medicine_reminder_scheduler():
    """약 복용 시간을 체크하고 알림을 보내는 스케줄러 함수"""
    while True:
        try:
            # 연결된 모든 사용자에 대해 약 복용 시간 체크
            for user_id, client_socket in list(user_sockets.items()):
                try:
                    # 소켓이 유효한지 확인
                    if client_socket not in connected_users:
                        del user_sockets[user_id]
                        continue
                    
                    # 현재 복용해야 할 약 정보 조회 및 알림 전송
                    check_medicine_for_user(user_id, client_socket)
                
                except Exception as e:
                    print(f"사용자 {user_id}에 대한 약 알림 처리 오류: {str(e)}")
                    # 오류 발생 시 연결 정보 정리
                    if user_id in user_sockets:
                        del user_sockets[user_id]
                    if client_socket in connected_users:
                        del connected_users[client_socket]
            
            # 1분마다 체크
            time.sleep(60)
        
        except Exception as e:
            print(f"약 알림 스케줄러 오류: {str(e)}")
            time.sleep(60)  # 오류 발생 시에도 계속 실행

def handle_client(client_socket, addr):
    """클라이언트 연결 처리 함수"""
    print(f"[{datetime.datetime.now()}] 연결됨: {addr[0]}:{addr[1]}")
    
    try:
        while True:
            # 데이터 수신
            data = client_socket.recv(1024)
            if not data:
                break
                
            # 수신 데이터 출력
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                decoded_data = data.decode('utf-8').strip()
                print(f"[{timestamp}] {addr[0]}:{addr[1]} → {decoded_data}")
                
                # 명령어 처리 및 응답
                response = process_command(decoded_data, client_socket)
                client_socket.send(response.encode('utf-8'))
                print(f"[{timestamp}] 응답 전송: {response}")
            except UnicodeDecodeError:
                # UTF-8로 디코딩할 수 없는 경우 바이트 값 출력
                print(f"[{timestamp}] 디코딩 오류. 바이트 데이터: {[b for b in data]}")
                client_socket.send("ER1DE\n".encode('utf-8'))  # 디코딩 오류
            except Exception as e:
                print(f"[{timestamp}] 데이터 처리 오류: {str(e)}")
                client_socket.send("ER1SV\n".encode('utf-8'))  # 서버 내부 오류
            
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 연결 오류: {e}")
    finally:
        # 연결 종료 시 사용자 정보 삭제
        user_id = connected_users.get(client_socket)
        if user_id and user_id in user_sockets:
            del user_sockets[user_id]
        if client_socket in connected_users:
            del connected_users[client_socket]
        client_socket.close()
        print(f"[{datetime.datetime.now()}] 연결 종료: {addr[0]}:{addr[1]}")

def start_server():
    """TCP 서버 시작 함수"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # DB 연결 테스트
        try:
            conn = get_connection()
            print("[INFO] 데이터베이스 연결 성공")
            conn.close()
        except Exception as e:
            print(f"[ERROR] 데이터베이스 연결 실패: {str(e)}")
            print("[ERROR] 데이터베이스 설정을 확인하세요.")
            return
        
        # 약 복용 알림 스케줄러 시작
        scheduler_thread = threading.Thread(target=medicine_reminder_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("[INFO] 약 복용 알림 스케줄러 시작")
        
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[{datetime.datetime.now()}] TCP 서버 시작: {HOST}:{PORT}")
        print("[INFO] 다음 명령어를 처리합니다:")
        print("  - SU: Send Uid (RFID TAG UID 값 수신)")
        print("  - SD: Send sensorData (센서 데이터 수신)")
        print("  - SS: Send Alertlog Start (위험 시작 알림 수신)")
        print("  - SE: Send Alertlog End (위험 종료 알림 수신)")
        print("  - GM: Get MedicineRemider (약 복용 알림 제공)")
        print("응답:")
        print("  - GN: Get NAME (사용자 이름 제공)")
        print("  - GE: Get Error (사용자를 찾을 수 없을 때 에러 반환)")
        print("  - ER: 에러 코드 (ER1XX 형식, XX는 에러 유형)")
        print("    - ER1DB: 데이터베이스 오류")
        print("    - ER1AU: 인증 필요 오류")
        print("    - ER1FT: 데이터 형식 오류")
        print("    - ER1CM: 알 수 없는 명령어")
        print("    - ER1SV: 서버 내부 오류")
        print("    - ER1DE: 디코딩 오류")
        
        while True:
            client_socket, addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n[!] 서버 종료 중...")
    except Exception as e:
        print(f"[!] 서버 오류: {e}")
    finally:
        server.close()
        print("[!] 서버가 종료되었습니다.")

if __name__ == "__main__":
    start_server() 
