import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.medicine_service as medicine_service
import json

bp = Blueprint('medicine', __name__, url_prefix='/med')

@bp.route('/list', methods=['POST'])
def show_med_list():
    data = request.get_json()
    user_id = data.get('user_id')

    result, status = medicine_service.show_med_list(user_id)

    response_data = {
    "user_id": user_id,
    "medicine_list": result
    }

    return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/add', methods=['POST'])
def add_med():
    data = request.get_json()
    user_id = data.get('user_id')
    end_date = data.get('end_date')
    day_of_week = data.get('day_of_week')
    time = data.get('time')
    med_name = data.get('med_name')

    result, status = medicine_service.add_med(user_id, med_name, end_date, day_of_week, time)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/check-med-name', methods=['POST'])
def check_med_name():
    data = request.get_json()
    user_id = data.get('user_id')

    result, status = medicine_service.check_med_name(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status


@bp.route('/delete', methods=['POST'])
def delete_med():
    data = request.get_json()
    user_id = data.get('user_id')
    end_date = data.get('end_date')
    day_of_week = data.get('day_of_week')
    time = data.get('time')
    med_name = data.get('med_name')

    result, status = medicine_service.delete_med(user_id, med_name, end_date, day_of_week, time)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/delete-med-name', methods=['POST'])
def delete_med_name():
    data = request.get_json()
    user_id = data.get('user_id')
    med_name = data.get('med_name')

    result, status = medicine_service.delete_med_name(user_id, med_name)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status
