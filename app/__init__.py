from flask import Flask
from config import Config
from app.extensions import db, jwt


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.persona_routes import persona_bp
    from app.routes.rol_routes import rol_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(persona_bp)
    app.register_blueprint(rol_bp)

    return app