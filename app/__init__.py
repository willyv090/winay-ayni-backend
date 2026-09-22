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
    from app.routes.empresa_routes import empresa_bp
    from app.routes.producto_routes import producto_bp
    from app.routes.jornada_routes import jornada_bp
    from app.routes.jornada_cajero_routes import jornada_cajero_bp
    from app.routes.jornada_producto_routes import jornada_producto_bp
    from app.routes.metodo_pago_routes import metodo_pago_bp
    from app.routes.venta_routes import venta_bp
    from app.routes.detalle_venta_routes import detalle_venta_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(persona_bp)
    app.register_blueprint(rol_bp)
    app.register_blueprint(empresa_bp)
    app.register_blueprint(producto_bp)
    app.register_blueprint(jornada_bp)
    app.register_blueprint(jornada_cajero_bp)
    app.register_blueprint(jornada_producto_bp)
    app.register_blueprint(metodo_pago_bp)
    app.register_blueprint(venta_bp)
    app.register_blueprint(detalle_venta_bp)

    return app