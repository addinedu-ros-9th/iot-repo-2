from server.db.mysql_connect import get_connection
from datetime import date, datetime, timedelta 

def convert_timedelta_to_str(td):
    if isinstance(td, timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return td

def convert_date_to_str(d):
    if isinstance(d, date):
        return d.strftime('%Y-%m-%d')
    return d

def show_med_list(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        today = datetime.today().date()

        delete_sql = "DELETE FROM Medicine WHERE user_id = %s AND end_date < %s"
        cursor.execute(delete_sql, (user_id, today))
        conn.commit()

        #print(user_id)

        query = """
        SELECT mr.med_name, mr.time, mr.day_of_week, m.end_date
        FROM MedicationReminder mr
        JOIN Medicine m ON mr.user_id = m.user_id AND mr.med_name = m.med_name
        WHERE mr.user_id = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchall()

        # day_of_week를 6자리 이진 문자열로 변환
        for row in result:
            # day_of_week 값이 0부터 6까지의 숫자로 저장되므로, 이를 이진 문자열로 변환
            day_of_week_bin = ['0'] * 7  # 7일에 해당하는 이진 문자열 리스트 초기화
            day_of_week_bin[row['day_of_week']] = '1'  # 해당 요일의 위치를 1로 변경
            row['day_of_week'] = ''.join(day_of_week_bin)  # 이진 문자열로 결합

            row['time'] = convert_timedelta_to_str(row['time'])
            row['end_date'] = convert_date_to_str(row['end_date'])

        #print(result)

        return result, 200

    except Exception as e:
        return {'error': str(e)}, 500

    finally:
        cursor.close()
        conn.close()


def add_med(user_id, med_name, end_date, day_of_week, time):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        insert_med_sql = """
        INSERT INTO Medicine (user_id, med_name, end_date)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE end_date = VALUES(end_date)
        """
        cursor.execute(insert_med_sql, (user_id, med_name, end_date))

         # day_of_week가 6자리 문자열일 경우 각 자리를 숫자로 변환하여 day_of_week 컬럼에 저장
        for i, val in enumerate(day_of_week):  # day_of_week는 6자리 문자열로 받음
            if val == '1':
                insert_reminder_sql = """
                INSERT INTO MedicationReminder (user_id, med_name, day_of_week, time)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE time = VALUES(time)
                """
                cursor.execute(insert_reminder_sql, (user_id, med_name, i, time))

        conn.commit()
        return {'message': '추가되었습니다'}, 200

    except Exception as e:
        return {'error': str(e)}, 500

    finally:
        cursor.close()
        conn.close()


def check_med_name(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT DISTINCT med_name FROM Medicine WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        names = cursor.fetchall()
        result = {str(i): {"med_name": name[0]} for i, name in enumerate(names)}
        return result, 200

    except Exception as e:
        return {'error': str(e)}, 500

    finally:
        cursor.close()
        conn.close()


def delete_med(user_id, med_name, end_date, day_of_week, time):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # day_of_week 이진 문자열을 받아서 각 요일(0~6)에 대해 처리
        for i, val in enumerate(day_of_week):
            if val == '1':  # 해당 요일에 알림이 설정되어 있으면
                # i는 0~6으로, 월요일부터 일요일까지의 값을 나타냄
                delete_reminder_sql = """
                DELETE FROM MedicationReminder
                WHERE user_id = %s AND med_name = %s AND day_of_week = %s AND time = %s
                """
                cursor.execute(delete_reminder_sql, (user_id, med_name, i, time))

        conn.commit()
        return {'message': '삭제되었습니다'}, 200

    except Exception as e:
        return {'error': str(e)}, 500

    finally:
        cursor.close()
        conn.close()



def delete_med_name(user_id, med_name):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM MedicationReminder WHERE user_id = %s AND med_name = %s", (user_id, med_name))
        cursor.execute("DELETE FROM Medicine WHERE user_id = %s AND med_name = %s", (user_id, med_name))

        conn.commit()
        return {'message': '삭제되었습니다'}, 200

    except Exception as e:
        return {'error': str(e)}, 500

    finally:
        cursor.close()
        conn.close()