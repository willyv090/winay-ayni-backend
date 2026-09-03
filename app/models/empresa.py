from app.extensions import db


class Empresa(db.Model):
    __tablename__ = "empresa"

    id_empresa = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    direccion = db.Column(db.Text, nullable=True)
    telefono = db.Column(db.BigInteger, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            "id_empresa": self.id_empresa,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "telefono": self.telefono,
            "estado": self.estado
        }