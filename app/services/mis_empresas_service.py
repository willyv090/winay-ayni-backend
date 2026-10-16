# Compatibilidad con importaciones anteriores. La lógica reside en EmpresaService.
from app.services.empresa_service import EmpresaService


class MisEmpresasService:
    autorizado = staticmethod(EmpresaService.emprendedor_autorizado)
    consulta = staticmethod(EmpresaService.consulta_propias)
    serializar = staticmethod(EmpresaService.serializar_propia)
    listar = staticmethod(EmpresaService.listar_mias)
    obtener = staticmethod(EmpresaService.obtener_mia)
