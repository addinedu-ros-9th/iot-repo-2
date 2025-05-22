from server.db.mysql_connect import get_connection
from datetime import datetime, timedelta 
import pytz

def get_avg_sensor_data(user_id):
    """IF-05: 전날 평균 센서 데이터"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        yesterday = (datetime.now() - timedelta(days=1)).date()
        query = """
            SELECT 
                ROUND(AVG(heart_rate), 1) AS heart_rate,
                ROUND(AVG(temperature), 1) AS temperature,
                ROUND(AVG(spo2), 1) AS spo2
            FROM SensorData
            WHERE user_id = %s AND DATE(timestamp) = %s
        """
        cur.execute(query, (user_id, yesterday))
        row = cur.fetchone()

        return row, 200

    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()


def get_sensor_data(user_id):
    """IF-06: 오늘 0시부터 현재까지 평균 센서 데이터"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = """
            SELECT 
                ROUND(AVG(heart_rate), 1) AS heart_rate,
                ROUND(AVG(temperature), 1) AS temperature,
                ROUND(AVG(spo2), 1) AS spo2
            FROM SensorData
            WHERE user_id = %s AND timestamp >= %s
        """
        cur.execute(query, (user_id, today))
        row = cur.fetchone()

        return row, 200

    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()


def _get_24hr_metric(user_id, column):
    """IF-07, 08, 09: 24시간 센서 데이터 (288개)"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        now = datetime.now()
        start_time = datetime(now.year, now.month, now.day)  # 오늘 0시
        #print("start time:", start_time)

        query = f"""
            SELECT timestamp, {column}
            FROM SensorData
            WHERE user_id = %s AND timestamp >= %s
            ORDER BY timestamp ASC
            LIMIT 288
        """

        #print(query)

        cur.execute(query, (user_id, start_time))
        values = cur.fetchall()

        # 결과를 시간만 포함한 포맷으로 변환
        result = {str(i): {"timestamp": row[0].strftime('%H:%M:%S'), "value": str(row[1])} for i, row in enumerate(values)}

        #print(result)
        return result, 200

    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()

def get_total_heart_data(user_id):
    return _get_24hr_metric(user_id, "heart_rate")

def get_total_temp_data(user_id):
    return _get_24hr_metric(user_id, "temperature")

def get_total_spo2_data(user_id):
    return _get_24hr_metric(user_id, "spo2")


def _get_7days_avg_metric(user_id, column):
    """7일 평균 센서 데이터 (오늘 기준으로 7일)"""
    conn = None
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    try:
        conn = get_connection()
        cur = conn.cursor()

        
        # 미리 7일치 날짜 만들기
        start_date = (datetime.now() - timedelta(days=6)).date()
        all_dates = [start_date + timedelta(days=i) for i in range(7)]

        # 7일의 데이터를 요일별로 평균을 계산한 쿼리
        query = f"""
            SELECT DATE(timestamp), ROUND(AVG({column}), 1)
            FROM SensorData
            WHERE user_id = %s AND DATE(timestamp) >= %s
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) ASC
            LIMIT 7
        """
        cur.execute(query, (user_id, start_date))
        values = cur.fetchall()

        # DB 결과를 dict로 변환
        fetched_data = {row[0]: row[1] for row in values}

        # 결과를 요일 순서로 변환
        result = {}
        for i, d in enumerate(all_dates):
            weekday_idx = d.weekday()
            avg_value = fetched_data.get(d, 0.0)  # 없으면 0.0으로 표시
            result[str(i)] = {"weekday": weekdays[weekday_idx], "value": str(round(avg_value, 1))}
            
        print(result)
        return result, 200

    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()

def get_avg7days_heart_data(user_id):
    return _get_7days_avg_metric(user_id, "heart_rate")

def get_avg7days_temp_data(user_id):
    return _get_7days_avg_metric(user_id, "temperature")

def get_avg7days_spo2_data(user_id):
    return _get_7days_avg_metric(user_id, "spo2")



def get_alert(user_id):
    """IF-13: 위험 알림 리스트 (예: 낙상감지 등 이벤트 기반)"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # 이벤트 로그 테이블이 따로 존재하는 경우
        query = """
            SELECT *
            FROM AlertLog
            WHERE user_id = %s
            ORDER BY start_time DESC
            LIMIT 30
        """
        cur.execute(query, (user_id, ))
        rows = cur.fetchall()
        # print(query)

        result = {str(i): {
            "type": row["alert_type"],
            "start_time": row["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": row["end_time"].strftime("%Y-%m-%d %H:%M:%S") if row["end_time"] else None
        } for i, row in enumerate(rows)}


        #print(result)

        return result, 200
        
    except Exception as e:
        return {"message": str(e)}, 500
    finally:
        if conn:
            cur.close()
            conn.close()
