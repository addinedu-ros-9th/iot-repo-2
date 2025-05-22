import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.calendar_query_service as calendar_query_service
import json

bp = Blueprint('calendar_query', __name__, url_prefix='/query')

@bp.route('/cal-temp', methods=['POST'])
def get_day_temp():
    data = request.get_json()
    user_id = data.get('user_id')
    date = data.get("date")  
    result, status = calendar_query_service.get_day_temp(user_id, date)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/cal-heart', methods=['POST'])
def get_day_heart():
    data = request.get_json()
    user_id = data.get('user_id')
    date = data.get("date")
    result, status = calendar_query_service.get_day_heart(user_id, date)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/cal-spo2', methods=['POST'])
def get_day_spo2():
    data = request.get_json()
    user_id = data.get('user_id')
    date = data.get('date')
    result, status = calendar_query_service.get_day_spo2(user_id, date)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status
