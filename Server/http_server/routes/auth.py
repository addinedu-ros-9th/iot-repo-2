import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Blueprint, request, Response
import services.auth_service as auth_service
import json

bp = Blueprint('auth', __name__, url_prefix='/auth')

# @bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     user_id = data.get('user_id')
#     password = data.get('password')

#     try:
#         result, status_code = auth_service.login_user(user_id, password)
#         return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status_code
#     except Exception:
#         return Response(json.dumps({"message": "서버 오류 발생"}, ensure_ascii=False), mimetype='application/json'), 500

import traceback

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')

    try:
        result, status_code = auth_service.login_user(user_id, password)
        return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status_code
    except Exception as e:
        print("로그인 중 예외 발생:", e)
        traceback.print_exc()  # ← 자세한 오류 트레이스백 출력
        return Response(json.dumps({"message": "서버 오류 발생"}, ensure_ascii=False), mimetype='application/json'), 500

@bp.route('/check_id', methods=['POST'])
def check_user_id():
    data = request.get_json()
    user_id = data.get('user_id')
    result, status = auth_service.check_user_id(user_id)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/elderly', methods=['POST'])
def signup_elderly():
    data = request.get_json()
    result, status = auth_service.signup_elderly_user(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/guardian', methods=['POST'])
def signup_guardian():
    data = request.get_json()
    result, status = auth_service.signup_guardian_user(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

@bp.route('/check-elderly-id', methods=['POST'])
def check_elderly_id():
    data = request.get_json()
    result, status = auth_service.check_elderly_id(data)
    return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json'), status

