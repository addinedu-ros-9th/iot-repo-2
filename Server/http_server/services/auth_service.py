from server.db.mysql_connect import get_connection
from datetime import datetime
import re

def is_valid_phone(phone):
    return re.fullmatch(r'010-\d{4}-\d{4}', phone) is not None

def login_user(user_id, password):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT user_id FROM User WHERE user_id = %s AND password = %s", (user_id, password))
        user = cur.fetchone()
        if user:
            return {"message": "로그인 성공", "user": user}, 200
        else:
            return {"message": "아이디 또는 비밀번호가 잘못되었습니다."}, 401
    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()

def check_user_id(user_id):
    if not user_id:
        return {"message": "아이디를 입력해주세요."}, 400
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT user_id FROM User WHERE user_id = %s", (user_id,))
        exists = cur.fetchone()
        return {"available": not bool(exists)}, 200
    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()

def check_elderly_id(data):
    user_id = data.get("user_id")          # 보호자 본인
    elderly_id = data.get("elderly_id")    # 입력한 케어대상자 ID

    if not user_id or not elderly_id:
        return {"message": "보호자 ID와 케어대상자 ID를 모두 입력해주세요."}, 400

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # elderly_id가 실제 존재하는지 확인
        cur.execute("SELECT * FROM User WHERE user_id = %s", (elderly_id,))
        target_user = cur.fetchone()

        if not target_user:
            return {"message": "존재하지 않는 케어대상자 ID입니다."}, 404

        # elderly_id가 보호자인지 확인
        cur.execute("SELECT 1 FROM ElderlyGuardian WHERE guardian_id = %s", (elderly_id,))
        if cur.fetchone():
            return {"message": "해당 ID는 보호자 계정입니다. 케어대상자로 등록할 수 없습니다."}, 400

        # elderly_id가 케어대상자로 이미 등록되었는지 확인
        cur.execute("SELECT * FROM ElderlyGuardian WHERE elderly_id = %s AND guardian_id = %s", (elderly_id, user_id))
        relation = cur.fetchone()

        if relation:
            if relation["valid"] == 0:
                return {"message": "이미 신청한 케어대상자입니다. 수락 대기 중입니다."}, 409
            else:
                return {"message": "이미 등록된 케어대상자입니다."}, 409

        return {"message": "등록 가능한 케어대상자입니다.", "available": True}, 200

    except Exception as e:
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()

def signup_elderly_user(data):
    conn = None
    try:
        user_id = data.get('user_id')
        password = data.get('password')
        name = data.get('name')
        birth_date_str = data.get('birth_date')
        phone = data.get('phone_number')
        rfid = data.get('rfid')

        if not all([user_id, password, name, birth_date_str, phone, rfid]):
            return {"message": "모든 항목을 입력해주세요"}, 400

        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            return {"message": "생년월일 형식은 YYYY-MM-DD입니다."}, 400

        if not is_valid_phone(phone):
            return {"message": "전화번호는 010-XXXX-XXXX 형식으로 입력해주세요."}, 400

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT rfid FROM Rfid WHERE rfid = %s", (rfid,))
        if cur.fetchone():
            return {"message": "이미 등록된 기기 번호입니다"}, 400

        cur.execute(
            "INSERT INTO User (user_id, password, name, birth_date, phone_number) VALUES (%s, %s, %s, %s, %s)",
            (user_id, password, name, birth_date, phone)
        )
        cur.execute("INSERT INTO Rfid (rfid, user_id) VALUES (%s, %s)", (rfid, user_id))

        conn.commit()
        return {"message": "케어 대상자 가입 성공"}, 201

    except Exception as e:
        if conn:
            conn.rollback()
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()

def signup_guardian_user(data):
    conn = None
    try:
        user_id = data.get('user_id')
        password = data.get('password')
        name = data.get('name')
        birth_date_str = data.get('birth_date')
        phone = data.get('phone_number')
        elderly_id = data.get('elderly_id')

        if not all([user_id, password, name, birth_date_str, phone, elderly_id]):
            return {"message": "모든 항목을 입력해주세요"}, 400

        try:
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        except ValueError:
            return {"message": "생년월일 형식은 YYYY-MM-DD입니다."}, 400

        if not is_valid_phone(phone):
            return {"message": "전화번호는 010-XXXX-XXXX 형식으로 입력해주세요."}, 400

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT user_id FROM User WHERE user_id = %s", (elderly_id,))
        if not cur.fetchone():
            return {"message": "입력한 케어 대상자 아이디가 존재하지 않습니다."}, 400

        # cur.execute("SELECT * FROM ElderlyGuardian WHERE elderly_id = %s", (elderly_id,))
        # if cur.fetchone():
        #     return {"message": "해당 케어 대상자는 이미 보호자가 등록되어 있습니다."}, 400

        cur.execute(
            "INSERT INTO User (user_id, password, name, birth_date, phone_number) VALUES (%s, %s, %s, %s, %s)",
            (user_id, password, name, birth_date, phone)
        )

        cur.execute("INSERT INTO ElderlyGuardian (elderly_id, guardian_id) VALUES (%s, %s)", (elderly_id, user_id))

        conn.commit()
        return {"message": "보호자 가입 성공"}, 201

    except Exception as e:
        if conn:
            conn.rollback()
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()

