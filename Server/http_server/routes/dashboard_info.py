import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.dashboard_info_service as dashboard_info_service
import json

bp = Blueprint('dashboard_info', __name__, url_prefix='/main')

@bp.route('/user-detail-info', methods=['POST'])
def get_user_detail_info():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_info_service.get_user_detail_info(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status



@bp.route('/elderly-list', methods=['POST'])
def get_elderly_list():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = dashboard_info_service.get_elderly_list(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status
