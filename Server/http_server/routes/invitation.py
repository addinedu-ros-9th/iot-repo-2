import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.invitation_service as invitation_service
import json

bp = Blueprint('invitation', __name__, url_prefix='/connect')

@bp.route('/guardian-elderly', methods=['POST'])
def request_connection():
    data = request.get_json()
    result, status = invitation_service.request_connection(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/elderly-guardian', methods=['POST'])
def show_invitation_list():
    data = request.get_json()
    result, status = invitation_service.show_invitation_list(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/elderly-guardian/accept', methods=['POST'])
def get_accept():
    data = request.get_json()
    result, status = invitation_service.get_accept(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/elderly-guardian/decline', methods=['POST'])
def get_decline():
    data = request.get_json()
    result, status = invitation_service.get_decline(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status
