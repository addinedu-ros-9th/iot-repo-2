from server.db.mysql_connect import get_connection
from datetime import datetime, timedelta 

def _get_cal_sensor_data(user_id, date, column):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 주어진 날짜에 해당하는 센서 데이터 조회
        query = f"""
            SELECT timestamp, {column}
            FROM SensorData
            WHERE user_id = %s AND DATE(timestamp) = %s
            ORDER BY timestamp
        """
        cursor.execute(query, (user_id, date))
        values = cursor.fetchall()

        if not values:
            return {"message": "No data found for the specified date."}, 404

        # 시간별 데이터 생성
        hourly_data = {}
        for i, row in enumerate(values):
            data = {
                "timestamp": row[0].strftime('%H:%M:%S'),
                column: str(row[1])
            }
            hourly_data[str(i)] = data

        # 평균 계산
        avg_value = sum(row[1] for row in values) / len(values)

        # 결과 반환
        result = {
            "average": round(avg_value, 2),
            "hourly": hourly_data
        }

        #print(result)

        return result, 200

    except Exception as e:
        return {"message": str(e)}, 500

    finally:
        if conn:
            cursor.close()
            conn.close()


def get_day_temp(user_id, date):
    return _get_cal_sensor_data(user_id, date, "temperature")

def get_day_heart(user_id, date):
    return _get_cal_sensor_data(user_id, date, "heart_rate")

def get_day_spo2(user_id, date):
    return _get_cal_sensor_data(user_id, date, "spo2")