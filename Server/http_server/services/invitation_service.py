from server.db.mysql_connect import get_connection

def request_connection(data):
    user_id = data.get("user_id", "").strip()
    elderly_id = data.get("elderly_id", "").strip()

    if not user_id or not elderly_id:
        return {"message": "보호자 ID와 케어대상자 ID를 모두 입력해주세요."}, 400

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        print(f"elderly_id 받은 값: '{elderly_id}'")

        # 1. 케어대상자 존재 여부 확인
        cur.execute("SELECT * FROM User WHERE user_id = %s", (elderly_id,))
        elderly_user = cur.fetchone()

        if not elderly_user:
            return {"message": "등록되지 않은 케어대상자입니다."}, 404

        # 2. 이미 관계가 존재하는 경우 (중복 요청 방지)
        cur.execute("""
            SELECT * FROM ElderlyGuardian
            WHERE elderly_id = %s AND guardian_id = %s
        """, (elderly_id, user_id))
        existing = cur.fetchone()

        if not existing:
            # 3. 존재하지 않으면 요청 삽입 (valid = 0)
            cur.execute("""
                INSERT INTO ElderlyGuardian (elderly_id, guardian_id, valid)
                VALUES (%s, %s, 0)
            """, (elderly_id, user_id))
            conn.commit()

        return {"message": "요청을 보냈습니다."}, 200

    except Exception as e:
        print("Error in request_connection:", str(e))
        return {"message": str(e)}, 500

    finally:
        if conn:
            cur.close()
            conn.close()


def show_invitation_list(data):
    user_id = data.get("user_id")
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT 
                eg.guardian_id, 
                u.name AS guardian_name 
            FROM ElderlyGuardian eg
            JOIN User u ON eg.guardian_id = u.user_id
            WHERE eg.elderly_id = %s AND eg.valid = 0
        """, (user_id,))

        result = cur.fetchall()

        return result, 200

    except Exception as e:
        print("Error:", e)
        return {"message": "서버 오류 발생"}, 500

    finally:
        cur.close()
        conn.close()


def get_accept(data):
    elderly_id = data.get("user_id")
    guardian_id = data.get("guardian_id")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # valid = 1로 업데이트
        cur.execute("""
            UPDATE ElderlyGuardian
            SET valid = 1
            WHERE elderly_id = %s AND guardian_id = %s
        """, (elderly_id, guardian_id))

        conn.commit()
        return {"message": "연동 수락 완료"}, 200

    except Exception as e:
        print("Error:", e)
        return {"message": "서버 오류 발생"}, 500

    finally:
        cur.close()
        conn.close()


def get_decline(data):
    elderly_id = data.get("user_id")
    guardian_id = data.get("guardian_id")
    print(elderly_id, guardian_id)

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        print("0")

        # guardian_id가 다른 사람과 연결되어 있는지 확인
        cur.execute("""
            SELECT COUNT(*) as cnt FROM ElderlyGuardian
            WHERE guardian_id = %s AND valid = 1
        """, (guardian_id,))
        row = cur.fetchone()
        count = row["cnt"] if row else 0

        if count == 0:
            print("1")
            cur.execute("""
                DELETE FROM User WHERE user_id = %s
            """, (guardian_id,))
        else:
            print("2")
            cur.execute("""
            DELETE FROM ElderlyGuardian
            WHERE elderly_id = %s AND guardian_id = %s 
            AND valid = 0
        """, (elderly_id, guardian_id))

        conn.commit()
        print("3")
        return {"message": "연동 거절 처리 완료"}, 200

    except Exception as e:
        print("Error:", e)
        return {"message": "서버 오류 발생: " + str(e)}, 500

    finally:
        cur.close()
        conn.close()

