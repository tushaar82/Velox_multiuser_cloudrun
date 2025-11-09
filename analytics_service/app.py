"""
Analytics Service Entry Point

Flask application for analytics and reporting endpoints.
"""
import logging
from flask import Flask
from flask_cors import CORS

from shared.config.settings import get_settings
from shared.utils.logging_config import setup_logging
from shared.utils.health import health_bp
from api_gateway.analytics_routes import analytics_bp

# Setup logging
setup_logging('analytics_service')
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
app.register_blueprint(analytics_bp)

logger.info("Analytics service initialized")

if __name__ == '__main__':
    port = int(settings.analytics_port) if hasattr(settings, 'analytics_port') else 8082
    app.run(host='0.0.0.0', port=port, debug=False)
