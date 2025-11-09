"""
API Gateway Service Entry Point

Main Flask application that aggregates all API routes.
"""
import logging
from flask import Flask
from flask_cors import CORS

from shared.config.settings import get_settings
from shared.utils.logging_config import setup_logging
from shared.utils.health import health_bp

# Import all route blueprints
from api_gateway.auth_routes import auth_bp
from api_gateway.user_routes import user_bp
from api_gateway.broker_routes import broker_bp
from api_gateway.symbol_mapping_routes import symbol_mapping_bp
from api_gateway.risk_management_routes import risk_management_bp
from api_gateway.order_routes import order_bp
from api_gateway.position_routes import position_bp
from api_gateway.backtest_routes import backtest_bp
from api_gateway.analytics_routes import analytics_bp
from api_gateway.notification_routes import notification_bp
from api_gateway.admin_routes import admin_bp

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configure app
app.config['SECRET_KEY'] = settings.jwt_secret_key
app.config['JSON_SORT_KEYS'] = False

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(broker_bp)
app.register_blueprint(symbol_mapping_bp)
app.register_blueprint(risk_management_bp)
app.register_blueprint(order_bp)
app.register_blueprint(position_bp)
app.register_blueprint(backtest_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(admin_bp)

logger.info("API Gateway service initialized")

if __name__ == '__main__':
    port = int(settings.api_gateway_port) if hasattr(settings, 'api_gateway_port') else 8080
    app.run(host='0.0.0.0', port=port, debug=False)
