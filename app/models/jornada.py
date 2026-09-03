from app.extensions import db


class Jornada(db.Model):
    __tablename__ = "jornada"

    id_jornada = db.Column(db.Integer, primary_key=True)
    direccion = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            "id_jornada": self.id_jornada,
            "direccion": self.direccion,
            "fecha_inicio": (
                self.fecha_inicio.isoformat()
                if self.fecha_inicio else None
            ),
            "fecha_fin": (
                self.fecha_fin.isoformat()
                if self.fecha_fin else None
            ),
            "nombre": self.nombre,
            "estado": self.estado
        }