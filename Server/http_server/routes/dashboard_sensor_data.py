import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.dashboard_sensor_data_service as dashboard_sensor_data_service
import json

bp = Blueprint('dashboard_sensor_data', __name__, url_prefix='/main')

@bp.route('/avg-sensor-data', methods=['POST'])
def get_avg_sensor_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_avg_sensor_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/sensor-data', methods=['POST'])
def get_sensor_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_sensor_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/total-heart-data', methods=['POST'])
def get_total_heart_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_total_heart_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/total-temp-data', methods=['POST'])
def get_total_temp_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_total_temp_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/total-spo2-data', methods=['POST'])
def get_total_spo2_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_total_spo2_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/avg7-heart-data', methods=['POST'])
def get_avg7days_heart_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_avg7days_heart_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/avg7-temp-data', methods=['POST'])
def get_avg7days_temp_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_avg7days_temp_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/avg7-spo2-data', methods=['POST'])
def get_avg7days_spo2_data():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_avg7days_spo2_data(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/alert', methods=['POST'])
def get_alert():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_sensor_data_service.get_alert(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status