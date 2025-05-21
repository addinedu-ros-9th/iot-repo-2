from server.db.mysql_connect import get_connection
from datetime import datetime

def get_user_role(user_id, cursor):
    """
    사용자 역할 확인 함수
    보호자인 경우: 'guardian'
    케어대상자인 경우: 'elderly'
    """
    # 보호자 여부 확인
    cursor.execute("SELECT * FROM ElderlyGuardian WHERE guardian_id = %s", (user_id,))
    guardian_rows = cursor.fetchall()
    if guardian_rows:
        return "guardian", guardian_rows

    # 케어대상자 여부 확인 (elderly_id 기준으로 존재 유무만 체크)
    cursor.execute("SELECT * FROM ElderlyGuardian WHERE elderly_id = %s", (user_id,))
    elderly_rows = cursor.fetchall()
    if elderly_rows or True:  # ElderlyGuardian에 없어도 케어대상자는 맞음
        return "elderly", elderly_rows  # 존재하든 말든 케어대상자는 역할이 elderly

    return "unknown", None



def get_user_detail_info(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # 유저 정보 가져오기
        cur.execute("SELECT * FROM User WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"message": f"User with user_id {user_id} not found"}, 404

        birth_date_str = user["birth_date"].strftime("%Y-%m-%d") if user["birth_date"] else None

        # 역할 판단
        role, pending_flag = get_user_role(user_id, cur)

        # 역할 확인
        if role in ["elderly", "guardian"]:
            if role == "elderly":
                # 케어대상자는 연결이 없어도 로그인 가능
                return {
                    "name": user["name"],
                    "role": role,
                    "birth_date": birth_date_str,
                    "phone_number": user["phone_number"]
                }, 200
                
            # elderlyGuardian 테이블에서 해당 유저가 guardian_id로 존재하는지 확인
            cur.execute("""
                SELECT * FROM ElderlyGuardian
                WHERE guardian_id = %s
            """, (user_id,))
            all_requests = cur.fetchall()  # 보호자와 연결된 모든 케어대상자

            # 유효한 연결 (valid=1) 찾기
            valid_connection_found = False
            pending_request_found = False

            for request in all_requests:
                if request["valid"] == 1:
                    valid_connection_found = True
                elif request["valid"] == 0:
                    pending_request_found = True

           # 유효한 연결이 없고, 신청대기 중인 경우
            if pending_request_found and not valid_connection_found:
                return {"message": "신청대기 중입니다"}, 403  # 신청대기 상태인 경우

            # 유효한 연결이 있을 경우 정상적으로 로그인 처리
            if valid_connection_found:
                return {
                    "name": user["name"],
                    "role": role,
                    "birth_date": birth_date_str,
                    "phone_number": user["phone_number"]
                }, 200

            # valid=1인 연결이 없으면 (기타 상황) 처리
            return {"message": "유효한 케어대상자 연결이 없습니다."}, 400

        return {"message": "역할이 확인되지 않았습니다."}, 400

    except Exception as e:
        print("Error:", str(e))
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()


def get_elderly_list(user_id):
    conn = None
    try:
        conn = get_connection()

        cur = conn.cursor(dictionary=True)

        print("Received user_id:", repr(user_id))

        # 1차: 보호자 ID로 연결된 케어 대상자 ID만 가져오기
        cur.execute("""
            SELECT elderly_id
            FROM ElderlyGuardian
            WHERE guardian_id = %s AND valid = 1
        """, (user_id.strip(),))
        
        rows = cur.fetchall()
        print("Rows fetched:", rows)

        if not rows:
            return {"message": "연결된 케어 대상자가 없습니다."}, 204

        accepted_elderly_info = {}

        for idx, row in enumerate(rows, start=1):
            elderly_id = row["elderly_id"]

            # 2차: User 테이블에서 상세 정보 가져오기
            cur.execute("SELECT name, birth_date, phone_number FROM User WHERE user_id = %s", (elderly_id,))
            elderly_info = cur.fetchone()

            if elderly_info:  # 존재할 경우만 추가
                accepted_elderly_info[f"elderly{idx:02}"] = {
                    "elderly_id": elderly_id,
                    "name": elderly_info["name"],
                    "role": "elderly",
                    "birth_date": elderly_info["birth_date"].strftime("%Y-%m-%d") if elderly_info["birth_date"] else None,
                    "phone_number": elderly_info["phone_number"]
                }

        print("Accepted elderly info:", accepted_elderly_info)
        return accepted_elderly_info, 200

    except Exception as e:
        print("Error in get_elderly_list:", str(e))
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()
