import sys
sys.path.append('/home/tunguser/iot_project')

from flask import Flask
from routes.auth import bp as auth_bp
from routes.dashboard_info import bp as dashboard_info_bp
from routes.dashboard_sensor_data import bp as dashboard_sensor_data_bp
from routes.invitation import bp as invitation_bp
from routes.calendar_query import bp as calendar_query_bp
from routes.medicine import bp as medicine_bp

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

# 블루프린트 등록
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_info_bp)
app.register_blueprint(dashboard_sensor_data_bp)
app.register_blueprint(invitation_bp)
app.register_blueprint(calendar_query_bp)
app.register_blueprint(medicine_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
