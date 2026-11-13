import unittest
from datetime import date
from decimal import Decimal
from config import Config

# Nunca usar la base configurada para desarrollo.
Config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
Config.JWT_SECRET_KEY = "test-only-key-at-least-thirty-two-characters"

from app import create_app
from app.extensions import db
from app.models import (Persona, Rol, RolPersona, Empresa, PersonaEmpresa,
    Producto, Jornada, JornadaCajero, JornadaProducto, MetodoPago, Venta, DetalleVenta)
from flask_jwt_extended import create_access_token


class BaseApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.users = [Persona(nombre=f"Persona {i}", usuario=f"u{i}", contrasenia="unused", estado=True) for i in range(4)]
        self.roles = [Rol(nombre=n, descripcion="test", estado=True) for n in ("ADMINISTRADOR", "EMPRENDEDOR", "CAJERO")]
        self.empresas = [Empresa(nombre=f"Empresa {i}", telefono=123, estado=True) for i in range(3)]
        self.jornada = Jornada(nombre="Feria", direccion="Centro", estado=True, fecha_inicio=date.today(), fecha_fin=date.today())
        self.pago = MetodoPago(nombre="Efectivo", descripcion="test", estado=True)
        db.session.add_all(self.users+self.roles+self.empresas+[self.jornada,self.pago])
        db.session.flush()
        # 0 multirol; 1 emprendedor ajeno; 2 cajero; 3 sin roles.
        for u,r in ((0,0),(0,1),(0,2),(1,1),(2,2)):
            db.session.add(RolPersona(persona_id_per=self.users[u].id_per, rol_id_rol=self.roles[r].id_rol, estado=True))
        self.vinculos = []
        for u,e in ((0,0),(0,2),(1,1)):
            link=PersonaEmpresa(persona_id_per=self.users[u].id_per, empresa_id_empresa=self.empresas[e].id_empresa, estado=True)
            db.session.add(link)
            self.vinculos.append(link)
        self.productos = [Producto(nombre=f"Producto {i}", cantidad=10, precio_u=Decimal("20"),
            rebaja=Decimal("2"), fecha_ingreso=date.today(), estado=True, empresa_id_empresa=e.id_empresa)
            for i,e in enumerate(self.empresas)]
        self.jc=JornadaCajero(fecha=date.today(),estado=True,jornada_id_jornada=self.jornada.id_jornada,persona_id_per=self.users[2].id_per)
        db.session.add_all(self.productos+[self.jc])
        db.session.flush()
        self.jp=[JornadaProducto(fecha=date.today(),estado=True,jornada_id_jornada=self.jornada.id_jornada,producto_id_prod=p.id_prod) for p in self.productos]
        db.session.add_all(self.jp)
        db.session.commit()
        self.headers=[{"Authorization":"Bearer "+create_access_token(identity=str(u.id_per))} for u in self.users]
        self.client=self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()


class VentasTest(BaseApiTest):
    def req(self, method, path="", body=None, user=0):
        return getattr(self.client,method)("/api/ventas"+path, json=body, headers=self.headers[user])

    def independiente(self, detalles=None):
        return self.req("post",body={"tipo":"INDEPENDIENTE","id_metodo_pago":self.pago.id_metodos,
            "fecha":"2026-10-14T16:30:00",
            "detalles":detalles if detalles is not None else [{"id_producto":self.productos[0].id_prod,"cantidad":2}]})

    def grupal(self):
        return self.req("post",body={"id_jornada_cajero":self.jc.id_jor_caj,"id_metodo_pago":self.pago.id_metodos,
            "detalles":[{"id_jornada_producto":jp.id_jor_prod,"cantidad":1} for jp in self.jp[:2]]},user=2)

    def test_independiente_stock_fechas_y_modificaciones(self):
        response=self.independiente()
        self.assertEqual(response.status_code,201,response.json)
        vid=response.json["venta"]["id"]
        self.assertIsNone(response.json["venta"]["jornada"])
        self.assertIsNotNone(response.json["venta"]["fecha_registro"])
        self.assertEqual(response.json["venta"]["fecha"],"2026-10-14T16:30:00")
        self.assertEqual(response.json["venta"]["total"],36)
        d=self.req("get",f"/{vid}/detalles?rol=EMPRENDEDOR").json["detalles"][0]
        self.assertIsNone(d["jornada_producto"])
        self.assertEqual(db.session.get(Producto,self.productos[0].id_prod).cantidad,8)
        # Cambiar el precio de catálogo no altera el precio histórico.
        self.productos[0].precio_u=50
        db.session.commit()
        edit=self.req("put",f"/{vid}/detalles/{d['id']}",{"cantidad":3})
        self.assertEqual(edit.status_code,200,edit.json)
        self.assertEqual(edit.json["total_venta"],54)
        self.assertEqual(self.productos[0].cantidad,7)
        self.assertEqual(self.req("delete",f"/{vid}/detalles/{d['id']}").status_code,200)
        self.assertEqual(self.productos[0].cantidad,10)
        self.assertEqual(db.session.get(Venta,vid).total,0)

    def test_rollback_de_venta_completa(self):
        for details in (
            [{"id_producto":self.productos[0].id_prod,"cantidad":2},{"id_producto":self.productos[1].id_prod,"cantidad":1}],
            [{"id_producto":self.productos[0].id_prod,"cantidad":2},{"id_producto":self.productos[2].id_prod,"cantidad":1}],
            [{"id_producto":self.productos[0].id_prod,"cantidad":11}],
            [{"id_producto":self.productos[0].id_prod,"cantidad":1.5}],
            [{"id_producto":self.productos[0].id_prod,"cantidad":True}],
            [{"id_producto":self.productos[0].id_prod,"cantidad":1}]*2,
        ):
            result=self.independiente(details)
            self.assertIn(result.status_code,(400,403),result.json)
            self.assertEqual(Venta.query.count(),0)
            self.assertEqual(DetalleVenta.query.count(),0)
            self.assertEqual(db.session.get(Producto,self.productos[0].id_prod).cantidad,10)

    def test_grupal_filtra_empresa_y_cajero(self):
        result=self.grupal()
        self.assertEqual(result.status_code,201,result.json)
        vid=result.json["venta"]["id"]
        self.assertEqual(result.json["venta"]["total"],36)
        mine=self.req("get",f"/{vid}/detalles?rol=EMPRENDEDOR").json
        self.assertEqual(len(mine["detalles"]),1)
        self.assertEqual(mine["venta"]["total"],18)
        other=self.req("get",f"/{vid}/detalles",user=1).json
        self.assertEqual(len(other["detalles"]),1)
        self.assertEqual(other["venta"]["total"],18)
        self.assertEqual(self.req("get",f"/{vid}?rol=CAJERO").status_code,404)
        self.assertEqual(self.req("get",f"/{vid}?rol=ADMINISTRADOR",user=1).status_code,403)
        self.assertEqual(self.req("get",f"?id_empresa={self.empresas[0].id_empresa}&rol=EMPRENDEDOR").json["ventas"][0]["total"],18)

    def test_consulta_incluye_ambos_tipos(self):
        self.independiente()
        self.grupal()
        self.assertEqual(len(self.req("get").json["ventas"]),2)
        self.assertEqual(len(self.req("get","?tipo=INDEPENDIENTE").json["ventas"]),1)
        self.assertEqual(len(self.req("get",f"?id_jornada={self.jornada.id_jornada}").json["ventas"]),1)
        self.assertEqual(self.req("get","?id_jornada=abc").status_code,400)
        self.assertEqual(self.req("get","?tipo=INVALIDO").status_code,400)

    def test_autenticacion_pertenencia_y_revocacion(self):
        self.assertEqual(self.client.get("/api/ventas").status_code,401)
        self.assertEqual(self.req("post",body=[]).status_code,400)
        self.assertEqual(self.req("get",user=3).status_code,403)
        result=self.independiente()
        vid=result.json["venta"]["id"]
        self.assertEqual(self.req("get",f"/{vid}",user=1).status_code,404)
        self.assertEqual(self.req("post",f"/{vid}/detalles",{"detalles":[{"id_producto":self.productos[1].id_prod,"cantidad":1}]},user=1).status_code,403)
        self.vinculos[0].estado=False
        db.session.commit()
        self.assertEqual(self.req("get",f"/{vid}?rol=EMPRENDEDOR").status_code,404)
        self.assertEqual(self.req("post",f"/{vid}/detalles",{"detalles":[{"id_producto":self.productos[0].id_prod,"cantidad":1}]}).status_code,403)

    def test_flujo_grupal_en_dos_pasos_y_jornada_cerrada(self):
        response=self.req("post",body={"id_jornada_cajero":self.jc.id_jor_caj,"id_metodo_pago":self.pago.id_metodos},user=2)
        self.assertEqual(response.status_code,201,response.json)
        vid=response.json["venta"]["id"]
        payload={"detalles":[{"id_jornada_producto":self.jp[0].id_jor_prod,"cantidad":2}]}
        added=self.req("post",f"/{vid}/detalles",payload,user=2)
        self.assertEqual(added.status_code,201,added.json)
        did=added.json["detalles"][0]["id"]
        self.assertEqual(self.req("post",f"/{vid}/detalles",payload,user=2).status_code,409)
        self.jp[0].estado=False
        db.session.commit()
        self.assertEqual(self.req("put",f"/{vid}/detalles/{did}",{"cantidad":3},user=2).status_code,400)
        self.jornada.estado=False
        db.session.commit()
        self.assertEqual(self.req("delete",f"/{vid}/detalles/{did}",user=2).status_code,400)
        self.assertEqual(self.req("get",f"/{vid}",user=2).status_code,200)

    def test_asignacion_ajena_y_datos_incompatibles(self):
        payload={"id_jornada_cajero":self.jc.id_jor_caj,"id_metodo_pago":self.pago.id_metodos}
        self.assertEqual(self.req("post",body=payload).status_code,403)
        payload["detalles"]=[{"id_jornada_producto":self.jp[0].id_jor_prod,"id_producto":self.productos[1].id_prod,"cantidad":1}]
        self.assertEqual(self.req("post",body=payload,user=2).status_code,400)
        self.assertEqual(Venta.query.count(),0)
        self.assertEqual(self.independiente([]).status_code,400)

    def test_producto_vendido_no_cambia_empresa(self):
        self.independiente()
        p=self.productos[0]
        result=self.client.put(f"/api/productos/{p.id_prod}",headers=self.headers[0],json={
            "nombre":p.nombre,"precio_u":20,"rebaja":2,"fecha_ingreso":date.today().isoformat(),
            "id_empresa":self.empresas[2].id_empresa})
        self.assertEqual(result.status_code,400,result.json)
        self.assertEqual(db.session.get(Producto,p.id_prod).empresa_id_empresa,self.empresas[0].id_empresa)

    def test_fallo_al_agregar_o_editar_no_altera_stock_total(self):
        result=self.independiente()
        vid=result.json["venta"]["id"]
        did=DetalleVenta.query.filter_by(venta_id_venta=vid).first().id_detalle
        edit=self.req("put",f"/{vid}/detalles/{did}",{"cantidad":99})
        self.assertEqual(edit.status_code,400)
        self.assertEqual(db.session.get(Producto,self.productos[0].id_prod).cantidad,8)
        self.assertEqual(db.session.get(Venta,vid).total,36)
        # Agrega primero un producto válido y luego uno de otra empresa:
        # incluso después de hacer flush debe revertir todo el lote.
        nuevo=Producto(nombre="Segundo",cantidad=10,precio_u=20,rebaja=0,
            fecha_ingreso=date.today(),estado=True,empresa_id_empresa=self.empresas[0].id_empresa)
        db.session.add(nuevo)
        db.session.commit()
        result=self.req("post",f"/{vid}/detalles",{"detalles":[
            {"id_producto":nuevo.id_prod,"cantidad":2},
            {"id_producto":99999,"cantidad":1}]})
        self.assertEqual(result.status_code,404,result.json)
        self.assertEqual(db.session.get(Producto,nuevo.id_prod).cantidad,10)
        self.assertEqual(DetalleVenta.query.filter_by(venta_id_venta=vid).count(),1)
        self.assertEqual(db.session.get(Venta,vid).total,36)

    def test_inactivos_y_asignacion_revocada(self):
        self.productos[0].estado=False
        db.session.commit()
        self.assertEqual(self.independiente().status_code,400)
        self.productos[0].estado=True
        self.pago.estado=False
        db.session.commit()
        self.assertEqual(self.independiente().status_code,404)
        self.pago.estado=True
        db.session.commit()
        venta=self.grupal().json["venta"]
        detalle=DetalleVenta.query.filter_by(venta_id_venta=venta["id"]).first()
        self.jc.estado=False
        db.session.commit()
        self.assertEqual(self.req("delete",f"/{venta['id']}/detalles/{detalle.id_detalle}",user=2).status_code,403)
        self.assertEqual(self.req("get",f"/{venta['id']}",user=2).status_code,200)

    def test_metricas_independientes_totales_ranking_y_fechas(self):
        self.independiente()
        extra=Producto(nombre="Otro",cantidad=10,precio_u=10,rebaja=0,
            fecha_ingreso=date.today(),estado=True,empresa_id_empresa=self.empresas[0].id_empresa)
        db.session.add(extra)
        db.session.commit()
        respuesta=self.req("post",body={"tipo":"INDEPENDIENTE","id_metodo_pago":self.pago.id_metodos,
            "fecha":"2026-10-15T23:59:59","detalles":[
                {"id_producto":self.productos[0].id_prod,"cantidad":1},
                {"id_producto":extra.id_prod,"cantidad":3}]})
        self.assertEqual(respuesta.status_code,201,respuesta.json)
        # Una venta de feria no se suma a las independientes.
        self.grupal()
        self.productos[0].estado=False
        self.productos[0].precio_u=99
        db.session.commit()
        url=f"/metricas/independientes?id_empresa={self.empresas[0].id_empresa}"
        response=self.req("get",url)
        self.assertEqual(response.status_code,200,response.json)
        data=response.json
        self.assertEqual(data["resumen"],{"ventas":2,"unidades_vendidas":6,
            "total_vendido":84,"productos_vendidos":2,"promedio_por_venta":42})
        self.assertEqual(data["ranking"][0]["producto"]["id"],self.productos[0].id_prod)
        self.assertEqual(data["ranking"][0]["unidades_vendidas"],3)
        self.assertEqual(data["ranking"][0]["total_vendido"],54)
        self.assertFalse(data["ranking"][0]["producto"]["estado"])
        daily=self.req("get",url+"&desde=2026-10-15&hasta=2026-10-15").json
        self.assertEqual(daily["resumen"]["ventas"],1)
        self.assertEqual(daily["resumen"]["total_vendido"],48)
        self.assertEqual(self.req("get",url+"&hasta=2026-10-14").json["resumen"]["total_vendido"],36)
        empty=self.req("get",url+"&desde=2026-10-16").json
        self.assertEqual(empty["resumen"]["total_vendido"],0)
        self.assertEqual(empty["ranking"],[])
        self.empresas[0].estado=False
        db.session.commit()
        self.assertEqual(self.req("get",url).json["resumen"]["total_vendido"],84)

    def test_metricas_acceso_y_validaciones(self):
        url=f"/metricas/independientes?id_empresa={self.empresas[0].id_empresa}"
        self.assertEqual(self.client.get("/api/ventas"+url).status_code,401)
        self.assertEqual(self.req("get",url,user=1).status_code,404)
        self.assertEqual(self.req("get",url,user=2).status_code,403)
        self.assertEqual(self.req("get","/metricas/independientes").status_code,400)
        for filtro in ("&desde=mal","&hasta=2026-02-30","&desde=2026-10-16&hasta=2026-10-15"):
            self.assertEqual(self.req("get",url+filtro).status_code,400)
        self.assertEqual(self.req("get",url).json["resumen"]["ventas"],0)
        # Un multirol administrador tampoco consulta empresas ajenas en este endpoint.
        self.assertEqual(self.req("get",f"/metricas/independientes?id_empresa={self.empresas[1].id_empresa}").status_code,404)
        self.vinculos[0].estado=False
        db.session.commit()
        self.assertEqual(self.req("get",url).status_code,404)

    def test_ranking_limite_y_orden_por_cantidad(self):
        nuevos=[Producto(nombre=f"Ranking {i}",cantidad=30,precio_u=10,rebaja=0,
            fecha_ingreso=date.today(),estado=True,empresa_id_empresa=self.empresas[0].id_empresa) for i in range(11)]
        db.session.add_all(nuevos)
        db.session.commit()
        response=self.independiente([{"id_producto":p.id_prod,"cantidad":i+1} for i,p in enumerate(nuevos)])
        self.assertEqual(response.status_code,201,response.json)
        result=self.req("get",f"/metricas/independientes?id_empresa={self.empresas[0].id_empresa}").json
        self.assertEqual(len(result["ranking"]),10)
        self.assertEqual(result["resumen"]["productos_vendidos"],11)
        self.assertEqual(result["resumen"]["ventas"],1)
        self.assertEqual([r["unidades_vendidas"] for r in result["ranking"]],list(range(11,1,-1)))


    def test_metricas_ferias_separadas_y_empresa(self):
        self.independiente()
        self.grupal()
        url=f"/metricas/ferias?id_empresa={self.empresas[0].id_empresa}"
        result=self.req("get",url)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(result.json["tipo"],"JORNADA")
        self.assertEqual(result.json["resumen"]["total_vendido"],18)
        self.assertEqual(result.json["resumen"]["ventas"],1)
        self.assertEqual(result.json["ranking"][0]["unidades_vendidas"],1)
        self.assertEqual(self.req("get",url+"&hasta=2000-01-01").json["ranking"],[])
        self.assertEqual(self.req("get",url+"&desde=mal").status_code,400)
        self.assertEqual(self.req("get",url,user=1).status_code,404)
        self.assertEqual(self.req("get",url,user=2).status_code,403)
        self.jornada.estado=False
        self.productos[0].estado=False
        self.productos[0].precio_u=99
        db.session.commit()
        self.assertEqual(self.req("get",url).json["resumen"]["total_vendido"],18)

    def test_detalle_filtrado_entre_dos_empresas_propias(self):
        result=self.req("post",body={"id_jornada_cajero":self.jc.id_jor_caj,
            "id_metodo_pago":self.pago.id_metodos,
            "detalles":[{"id_jornada_producto":jp.id_jor_prod,"cantidad":1} for jp in self.jp]},user=2)
        self.assertEqual(result.status_code,201,result.json)
        vid=result.json["venta"]["id"]
        for idx in (0,2):
            eid=self.empresas[idx].id_empresa
            detalle=self.req("get",f"/{vid}/detalles?rol=EMPRENDEDOR&id_empresa={eid}")
            self.assertEqual(detalle.status_code,200,detalle.json)
            self.assertEqual(detalle.json["venta"]["total"],18)
            self.assertEqual(detalle.json["venta"]["alcance_total"],"EMPRESA")
            self.assertEqual(len(detalle.json["detalles"]),1)
            self.assertEqual(detalle.json["detalles"][0]["producto"]["empresa_id"],eid)
        self.assertEqual(self.req("get",f"/{vid}/detalles?rol=EMPRENDEDOR&id_empresa={self.empresas[1].id_empresa}").status_code,404)
        self.assertEqual(self.req("get",f"/{vid}/detalles?rol=EMPRENDEDOR&id_empresa=mal").status_code,400)
        independiente=self.independiente().json["venta"]["id"]
        self.assertEqual(self.req("get",f"/{independiente}/detalles?rol=EMPRENDEDOR&id_empresa={self.empresas[2].id_empresa}").status_code,404)

    def test_ajuste_stock_validaciones_y_permisos(self):
        p=self.productos[0]
        path=f"/api/productos/{p.id_prod}/stock"
        def ajustar(n,user=0):
            return self.client.put(path,headers=self.headers[user],json={"ajuste":n})
        self.assertEqual(ajustar(5).status_code,200)
        self.assertEqual(ajustar(-3).json["inventario"]["stock_actual"],12)
        for n in (0,1.5,True,-13,"abc",9007199254740992):
            r=ajustar(n)
            self.assertEqual(r.status_code,400,r.json)
            self.assertEqual(db.session.get(Producto,p.id_prod).cantidad,12)
        self.assertIn(ajustar(1,user=1).status_code,(403,404))
        self.assertEqual(self.client.put(path,json={"ajuste":1}).status_code,401)
        self.empresas[0].estado=False
        db.session.commit()
        self.assertIn(ajustar(1).status_code,(400,403))
        self.empresas[0].estado=True
        self.productos[0].estado=False
        db.session.commit()
        self.assertEqual(ajustar(1).status_code,400)



    def test_caja_jornadas_y_catalogo_segun_asignacion(self):
        url="/api/jornadas/cajero/mias"
        self.assertEqual(self.client.get(url).status_code,401)
        self.assertEqual(self.client.get(url,headers=self.headers[1]).status_code,403)
        self.assertEqual(self.client.get(url,headers=self.headers[0]).json["jornadas"],[])
        response=self.client.get(url,headers=self.headers[2])
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json["jornadas"][0]["id_jornada_cajero"],self.jc.id_jor_caj)
        catalogo=f"/api/jornadas/{self.jornada.id_jornada}/productos/caja"
        self.assertEqual(self.client.get(catalogo,headers=self.headers[0]).status_code,403)
        datos=self.client.get(catalogo,headers=self.headers[2])
        self.assertEqual(datos.status_code,200,datos.json)
        self.assertEqual(len(datos.json["productos"]),3)
        self.assertEqual(len({p["empresa"]["id"] for p in datos.json["productos"]}),3)
        self.assertEqual(datos.json["productos"][0]["id_jornada_producto"],self.jp[0].id_jor_prod)
        self.jp[0].estado=False
        self.empresas[1].estado=False
        db.session.commit()
        self.assertEqual(len(self.client.get(catalogo,headers=self.headers[2]).json["productos"]),1)
        self.jc.estado=False
        db.session.commit()
        self.assertEqual(self.client.get(catalogo,headers=self.headers[2]).status_code,403)
        self.assertEqual(self.client.get(url,headers=self.headers[2]).json["jornadas"],[])

    def test_caja_jornada_finalizada_y_producto_archivado(self):
        self.productos[0].estado=False
        db.session.commit()
        catalogo=f"/api/jornadas/{self.jornada.id_jornada}/productos/caja"
        self.assertEqual(len(self.client.get(catalogo,headers=self.headers[2]).json["productos"]),2)
        self.assertEqual(self.grupal().status_code,400)
        self.assertEqual(Venta.query.count(),0)
        self.jornada.estado=False
        db.session.commit()
        self.assertEqual(self.client.get(catalogo,headers=self.headers[2]).status_code,403)
        self.assertEqual(self.client.get("/api/jornadas/cajero/mias",headers=self.headers[2]).json["jornadas"],[])

    def test_caja_precio_cambiado_revierte_toda_la_venta(self):
        payload={"tipo":"JORNADA","id_jornada_cajero":self.jc.id_jor_caj,
            "id_metodo_pago":self.pago.id_metodos,"total_esperado":35,
            "detalles":[{"id_jornada_producto":jp.id_jor_prod,"cantidad":1} for jp in self.jp[:2]]}
        response=self.req("post",body=payload,user=2)
        self.assertEqual(response.status_code,409,response.json)
        self.assertEqual(Venta.query.count(),0)
        self.assertEqual(DetalleVenta.query.count(),0)
        for p in self.productos:
            self.assertEqual(db.session.get(Producto,p.id_prod).cantidad,10)
        payload["total_esperado"]=36
        result=self.req("post",body=payload,user=2)
        self.assertEqual(result.status_code,201,result.json)
        vid=result.json["venta"]["id"]
        self.assertEqual(result.json["venta"]["total"],36)
        historial=self.req("get","?rol=CAJERO",user=2)
        self.assertEqual(len(historial.json["ventas"]),1)
        detalles=self.req("get",f"/{vid}/detalles?rol=CAJERO",user=2)
        self.assertEqual(len(detalles.json["detalles"]),2)
        self.assertEqual(self.req("get",f"/{vid}/detalles?rol=CAJERO",user=0).status_code,404)
        self.assertEqual(self.req("get","?rol=CAJERO",user=0).json["ventas"],[])



    def test_metricas_admin_totales_historicos_y_filtros(self):
        self.independiente()
        result=self.grupal()
        self.assertEqual(result.status_code,201)
        url="/metricas/admin"
        r=self.req("get",url)
        self.assertEqual(r.status_code,200,r.json)
        self.assertEqual(r.json["resumen"],{"ventas":1,"unidades":2,"total":36.0})
        self.assertEqual(len(r.json["empresas"]),2)
        self.assertEqual(len(r.json["productos"]),2)
        self.assertEqual(r.json["dias"][0]["ventas"],1)
        self.assertEqual(r.json["dias"][0]["total"],36)
        self.assertEqual(r.json["ferias"][0]["total"],36)
        otra=Jornada(nombre="Sin ventas",direccion="Otro",estado=True,
            fecha_inicio=date.today(),fecha_fin=date.today())
        db.session.add(otra)
        self.productos[0].precio_u=100
        self.productos[0].estado=False
        self.jornada.estado=False
        db.session.commit()
        r=self.req("get",url+f"?id_jornada={self.jornada.id_jornada}")
        self.assertEqual(r.json["resumen"]["total"],36)
        self.assertEqual(len(r.json["ferias"]),2)
        empty=self.req("get",url+f"?id_jornada={otra.id_jornada}").json
        self.assertEqual(empty["resumen"]["ventas"],0)
        self.assertEqual(empty["productos"],[])
        self.assertEqual(empty["dias"],[])
        self.assertEqual(self.req("get",url+"?hasta=2000-01-01").json["resumen"]["total"],0)
        hoy=date.today().isoformat()
        self.assertEqual(self.req("get",url+f"?desde={hoy}&hasta={hoy}").json["resumen"]["total"],36)

    def test_metricas_admin_autorizacion_y_validacion(self):
        url="/metricas/admin"
        self.assertEqual(self.client.get("/api/ventas"+url).status_code,401)
        for user in (1,2,3):
            self.assertEqual(self.req("get",url,user=user).status_code,403)
        for filtro in ("?id_jornada=abc","?desde=mal","?hasta=2026-02-30",
                       "?desde=2026-10-17&hasta=2026-10-16"):
            self.assertEqual(self.req("get",url+filtro).status_code,400)
        self.assertEqual(self.req("get",url+"?id_jornada=99999").status_code,404)
        r=self.req("get",url).json
        self.assertEqual(r["resumen"],{"ventas":0,"unidades":0,"total":0.0})
        self.assertEqual(r["empresas"],[])
        self.assertEqual(r["ferias"][0]["ventas"],0)



    def test_descuento_elegido_y_precio_historico(self):
        p=self.productos[0]
        normal=self.independiente([{"id_producto":p.id_prod,"cantidad":1,"aplicar_descuento":False}])
        self.assertEqual(normal.status_code,201,normal.json)
        self.assertEqual(normal.json["venta"]["total"],20)
        rebajada=self.independiente([{"id_producto":p.id_prod,"cantidad":1,"aplicar_descuento":True}])
        self.assertEqual(rebajada.json["venta"]["total"],18)
        did=DetalleVenta.query.filter_by(venta_id_venta=normal.json["venta"]["id"]).first().id_detalle
        p.precio_u=50
        p.rebaja=10
        db.session.commit()
        result=self.req("put",f"/{normal.json['venta']['id']}/detalles/{did}",{"cantidad":2})
        self.assertEqual(result.json["total_venta"],40)
        bad=self.independiente([{"id_producto":p.id_prod,"cantidad":1,"aplicar_descuento":"false"}])
        self.assertEqual(bad.status_code,400)
        self.assertEqual(Venta.query.count(),2)

    def test_reporte_completo_cierre_y_reapertura(self):
        self.grupal()
        url=f"/api/jornadas/{self.jornada.id_jornada}"
        r=self.client.get(url+"/reporte",headers=self.headers[0])
        self.assertEqual(r.status_code,200,r.json)
        self.assertTrue(r.json["cuadra"])
        self.assertEqual(r.json["total"],36)
        self.assertEqual(r.json["total_empresas"],36)
        self.assertEqual(len(r.json["empresas"]),3)
        cero=next(e for e in r.json["empresas"] if e["id"]==self.empresas[2].id_empresa)
        self.assertEqual(cero["total"],0)
        self.assertEqual(cero["ventas"],0)
        self.assertEqual(r.json["metodos_pago"][0]["total"],36)
        self.assertEqual(len(r.json["productos"]),3)
        close=self.client.put(url+"/cerrar",headers=self.headers[0])
        self.assertEqual(close.status_code,200,close.json)
        self.assertFalse(db.session.get(Jornada,self.jornada.id_jornada).estado)
        self.assertEqual(self.grupal().status_code,400)
        self.assertEqual(self.client.get(url+"/reporte",headers=self.headers[0]).json["total"],36)
        self.assertEqual(self.client.put(url+"/reactivar",headers=self.headers[0]).status_code,200)
        self.assertTrue(self.jornada.estado)

    def test_cierre_rechaza_inconsistencia_y_venta_sin_detalles(self):
        self.grupal()
        v=Venta.query.first()
        v.total=37
        db.session.commit()
        url=f"/api/jornadas/{self.jornada.id_jornada}"
        self.assertEqual(self.client.put(url+"/cerrar",headers=self.headers[0]).status_code,409)
        self.assertTrue(self.jornada.estado)
        # El DELETE existente tampoco debe permitir saltarse el cuadre.
        self.assertEqual(self.client.delete(url,headers=self.headers[0]).status_code,409)
        v.total=36
        db.session.commit()
        vacia=self.req("post",body={"id_jornada_cajero":self.jc.id_jor_caj,"id_metodo_pago":self.pago.id_metodos},user=2)
        self.assertEqual(vacia.status_code,201)
        r=self.client.get(url+"/reporte",headers=self.headers[0])
        self.assertFalse(r.json["cuadra"])
        self.assertEqual(self.client.put(url+"/cerrar",headers=self.headers[0]).status_code,409)

    def test_reporte_y_cierre_solo_administrador(self):
        url=f"/api/jornadas/{self.jornada.id_jornada}"
        self.assertEqual(self.client.get(url+"/reporte").status_code,401)
        self.assertEqual(self.client.put(url+"/cerrar").status_code,401)
        for user in (1,2,3):
            self.assertEqual(self.client.get(url+"/reporte",headers=self.headers[user]).status_code,403)
            self.assertEqual(self.client.put(url+"/cerrar",headers=self.headers[user]).status_code,403)
            self.assertEqual(self.client.put(url+"/reactivar",headers=self.headers[user]).status_code,403)
        self.assertEqual(self.client.put(url+"/cerrar",headers=self.headers[0]).status_code,200)



    def consulta(self, datos, user=0):
        return self.client.post("/api/productos/consulta", json=datos, headers=self.headers[user])

    def test_asistente_roles_y_catalogo_autorizado(self):
        from unittest.mock import patch
        import httpx
        self.app.config.update(CLOUDFLARE_WORKER_URL="https://test.workers.dev", WINAY_API_KEY="test-secret")
        respuesta = httpx.Response(200, json={"respuesta": "Datos de prueba"}, request=httpx.Request("POST", "https://test.workers.dev"))
        with patch("httpx.post", return_value=respuesta) as llamada:
            r = self.consulta({"rol": "EMPRENDEDOR", "pregunta": "¿Qué hay?", "productos": [{"nombre": "Inyectado"}]})
            self.assertEqual(r.status_code, 200, r.json)
            self.assertTrue(r.json["generada"])
            nombres = {p["nombre"] for p in llamada.call_args.kwargs["json"]["productos"]}
            self.assertEqual(nombres, {"Producto 0", "Producto 2"})
            self.assertNotIn("test-secret", r.get_data(as_text=True))
            r = self.consulta({"rol": "ADMINISTRADOR", "pregunta": "¿Qué hay?"}, user=1)
            self.assertEqual(r.status_code, 403)
            r = self.consulta({"rol": "EMPRENDEDOR", "pregunta": "¿Qué hay?", "id_empresa": self.empresas[1].id_empresa})
            self.assertEqual(r.status_code, 403)
            self.assertEqual(llamada.call_count, 1)

    def test_asistente_descripcion_desde_notas(self):
        from unittest.mock import patch
        import httpx
        self.productos[0].notas = "Perfume floral de 50 ml."
        self.productos[2].notas = " "
        db.session.commit()
        self.app.config.update(CLOUDFLARE_WORKER_URL="https://test.workers.dev", WINAY_API_KEY="test-secret")
        with patch("httpx.post", side_effect=httpx.ConnectError("offline")) as llamada:
            r = self.consulta({"rol": "EMPRENDEDOR", "pregunta": "x" * 700})
            self.assertEqual(r.status_code, 200, r.json)
            productos = {p["nombre"]: p for p in r.json["productos"]}
            self.assertEqual(productos["Producto 0"]["notas"], "Perfume floral de 50 ml.")
            self.assertIsNone(productos["Producto 2"]["notas"])
            payload = llamada.call_args.kwargs["json"]
            self.assertLessEqual(len(payload["pregunta"]), 1000)
            self.assertEqual(payload["productos"][0]["notas"], "Perfume floral de 50 ml.")

    def test_asistente_cajero_revocacion_y_opciones(self):
        from unittest.mock import patch
        import httpx
        self.app.config.update(CLOUDFLARE_WORKER_URL="https://test.workers.dev", WINAY_API_KEY="test-secret")
        url = "/api/productos/consulta?rol=CAJERO"
        r = self.client.get(url, headers=self.headers[2])
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(len(r.json["jornadas"]), 1)
        datos = {"rol": "CAJERO", "pregunta": "¿Qué hay?", "id_jornada": self.jornada.id_jornada}
        with patch("httpx.post", side_effect=httpx.ConnectError("offline")) as llamada:
            r = self.consulta(datos, user=2)
            self.assertEqual(r.status_code, 200, r.json)
            self.assertFalse(r.json["generada"])
            self.assertEqual(len(r.json["productos"]), 3)
            self.jc.estado = False
            db.session.commit()
            self.assertEqual(self.consulta(datos, user=2).status_code, 403)
            self.assertEqual(llamada.call_count, 1)

    def test_asistente_validacion_y_limites(self):
        from unittest.mock import patch
        self.assertEqual(self.client.post("/api/productos/consulta", json={}).status_code, 401)
        with patch("httpx.post") as llamada:
            for datos in ([], {}, {"rol": []}, {"rol": "ADMINISTRADOR", "pregunta": "x" * 701},
                          {"rol": "ADMINISTRADOR", "pregunta": "hola", "id_empresa": True}):
                self.assertEqual(self.consulta(datos).status_code, 400)
            self.assertEqual(self.consulta({"rol": "CAJERO", "pregunta": "hola"}, user=2).status_code, 400)
            for i in range(31):
                db.session.add(Producto(nombre=f"Extra {i}", cantidad=1, precio_u=10, rebaja=0,
                    fecha_ingreso=date.today(), estado=True, empresa_id_empresa=self.empresas[0].id_empresa))
            db.session.commit()
            self.assertEqual(self.consulta({"rol": "ADMINISTRADOR", "pregunta": "hola"}).status_code, 422)
            r = self.consulta({"rol": "ADMINISTRADOR", "pregunta": "hola", "buscar": "inexistente"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json["productos"], [])
            llamada.assert_not_called()

    def test_asistente_archivados_y_respuesta_invalida(self):
        from unittest.mock import patch
        import httpx
        self.app.config.update(CLOUDFLARE_WORKER_URL="https://test.workers.dev", WINAY_API_KEY="test-secret")
        self.productos[0].estado = False
        self.empresas[1].estado = False
        db.session.commit()
        respuesta = httpx.Response(200, text="Hello World", request=httpx.Request("POST", "https://test.workers.dev"))
        with patch("httpx.post", return_value=respuesta):
            r = self.consulta({"rol": "ADMINISTRADOR", "pregunta": "¿Qué hay?"})
            self.assertEqual(r.status_code, 200, r.json)
            self.assertFalse(r.json["generada"])
            self.assertEqual([p["nombre"] for p in r.json["productos"]], ["Producto 2"])



    def consulta_con_ventas(self, datos, user=0):
        from unittest.mock import patch
        import httpx
        self.app.config.update(CLOUDFLARE_WORKER_URL="https://test.workers.dev", WINAY_API_KEY="test-secret")
        respuesta = httpx.Response(200, json={"respuesta": "Resumen"}, request=httpx.Request("POST", "https://test.workers.dev"))
        with patch("httpx.post", return_value=respuesta):
            return self.consulta(datos, user=user)

    def test_consulta_ventas_importes_historicos_y_empresa(self):
        from datetime import datetime
        independiente = self.independiente()
        feria = self.grupal()
        qr = MetodoPago(nombre="QR", descripcion="test", estado=True)
        db.session.add(qr)
        db.session.flush()
        v = db.session.get(Venta, feria.json["venta"]["id"])
        v.metodos_pago_id_metodos = qr.id_metodos
        v.fecha = datetime(2026, 10, 15, 12)
        self.productos[0].precio_u = 999
        db.session.commit()
        r = self.consulta_con_ventas({"rol": "EMPRENDEDOR", "pregunta": "¿Cuánto vendí?"})
        self.assertEqual(r.status_code, 200, r.json)
        total = r.json["resumen_ventas"]
        self.assertEqual(total["ingreso_ventas"], 54)
        self.assertEqual(total["cantidad_ventas"], 2)
        self.assertEqual(total["unidades_vendidas"], 3)
        self.assertIsNone(total["ganancia_neta"])
        self.assertEqual({p["metodo"]: p["importe"] for p in total["metodos_pago"]}, {"Efectivo": 36, "QR": 18})
        self.assertEqual(total["ferias"][0]["importe"], 18)
        r = self.consulta_con_ventas({"rol": "ADMINISTRADOR", "pregunta": "¿Cuánto vendimos?"})
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 72)
        self.assertEqual(r.json["resumen_ventas"]["cantidad_ventas"], 2)
        self.assertEqual(r.json["resumen_ventas"]["unidades_vendidas"], 4)
        r = self.consulta_con_ventas({"rol": "EMPRENDEDOR", "pregunta": "¿Ventas?", "desde": "2026-10-15", "hasta": "2026-10-15"})
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 18)
        r = self.consulta_con_ventas({"rol": "EMPRENDEDOR", "pregunta": "¿Ventas?", "tipo": "INDEPENDIENTE"})
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 36)

    def test_consulta_feria_finalizada_archivado_y_cajero(self):
        self.grupal()
        self.productos[0].estado = False
        self.jp[0].estado = False
        self.jornada.estado = False
        self.jc.estado = False
        db.session.commit()
        datos = {"rol": "EMPRENDEDOR", "pregunta": "¿Ventas?", "id_jornada": self.jornada.id_jornada}
        r = self.consulta_con_ventas(datos)
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 18)
        self.assertEqual(r.json["resumen_ventas"]["jornada_seleccionada"]["estado"], "Finalizada")
        self.assertIn("Producto 0", [p["nombre"] for p in r.json["productos"]])
        datos["rol"] = "CAJERO"
        r = self.consulta_con_ventas(datos, user=2)
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 36)
        self.assertTrue(all(p["stock"] is None and p["precio"] is None for p in r.json["productos"]))
        self.assertEqual({p["nombre"] for p in r.json["productos"]}, {"Producto 0", "Producto 1"})
        r = self.client.get("/api/productos/consulta?rol=CAJERO", headers=self.headers[2])
        self.assertEqual(len(r.json["jornadas"]), 1)
        self.assertFalse(r.json["jornadas"][0]["estado"])

    def test_consulta_cajero_no_ve_ventas_ajenas(self):
        self.grupal()
        nueva = JornadaCajero(fecha=date.today(), estado=True, jornada_id_jornada=self.jornada.id_jornada, persona_id_per=self.users[0].id_per)
        db.session.add(nueva)
        db.session.commit()
        r = self.req("post", body={"id_jornada_cajero": nueva.id_jor_caj, "id_metodo_pago": self.pago.id_metodos,
            "detalles": [{"id_jornada_producto": self.jp[0].id_jor_prod, "cantidad": 1}]})
        self.assertEqual(r.status_code, 201, r.json)
        datos = {"rol": "CAJERO", "pregunta": "¿Cuánto vendí?", "id_jornada": self.jornada.id_jornada}
        r = self.consulta_con_ventas(datos, user=2)
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 36)
        self.assertEqual([v["usuario"] for v in r.json["resumen_ventas"]["vendedores"]], ["u2"])
        r = self.consulta_con_ventas(datos)
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 18)

    def test_consulta_ventas_validacion_y_ceros(self):
        from unittest.mock import patch
        with patch("httpx.post") as llamada:
            for campos in ({"desde": "2026-99-99"}, {"hasta": []}, {"desde": "2026-11-02", "hasta": "2026-11-01"},
                           {"tipo": "OTRO"}, {"tipo": "INDEPENDIENTE", "id_jornada": self.jornada.id_jornada}):
                r = self.consulta({"rol": "ADMINISTRADOR", "pregunta": "¿Ventas?", **campos})
                self.assertEqual(r.status_code, 400, r.json)
            llamada.assert_not_called()
        r = self.consulta_con_ventas({"rol": "EMPRENDEDOR", "pregunta": "¿Ventas?"})
        self.assertEqual(r.json["resumen_ventas"]["ingreso_ventas"], 0)
        self.assertEqual(r.json["resumen_ventas"]["cantidad_ventas"], 0)
        self.assertEqual(r.json["productos"][0]["ventas"]["metodos_pago"], [])



class GestionTest(BaseApiTest):
    """Flujos de gestión anteriores al cobro y límites de acceso entre roles."""

    def api(self, metodo, ruta, datos=None, usuario=0):
        headers = self.headers[usuario] if usuario is not None else {}
        return self.client.open("/api/" + ruta, method=metodo, headers=headers, json=datos)

    def datos_persona(self):
        return {"nombre": "Ana", "usuario": "ana", "contrasenia": "solo-en-pruebas",
                "roles": [self.roles[1].id_rol, self.roles[2].id_rol]}

    def nueva_jornada(self):
        datos = {"nombre": "Feria de prueba", "direccion": "Plaza", "fecha_inicio": "2026-09-21",
                 "fecha_fin": "2026-09-23"}
        respuesta = self.api("POST", "jornadas", datos)
        self.assertEqual(respuesta.status_code, 201, respuesta.json)
        return respuesta.json["jornada"]["id"]

    def test_registro_login_multirol_y_uso_del_token(self):
        datos = self.datos_persona()
        alta = self.api("POST", "personas", datos)
        self.assertEqual(alta.status_code, 201, alta.json)
        persona = Persona.query.filter_by(usuario="ana").one()
        self.assertNotEqual(persona.contrasenia, datos["contrasenia"])
        login = self.api("POST", "auth/login", datos, usuario=None)
        self.assertEqual(login.status_code, 200, login.json)
        self.assertCountEqual(login.json["usuario"]["roles"], ["CAJERO", "EMPRENDEDOR"])
        self.assertNotIn("contrasenia", login.json["usuario"])
        token = {"Authorization": "Bearer " + login.json["token"]}
        self.assertEqual(self.client.get("/api/empresas/mias", headers=token).status_code, 200)

    def test_login_rechaza_datos_incompletos_desconocidos_e_inactivos(self):
        datos = self.datos_persona()
        alta = self.api("POST", "personas", datos)
        self.assertEqual(alta.status_code, 201, alta.json)
        for nombre, clave, esperado in [("ana", "", 400), ("nadie", "prueba", 401),
                                         ("ana", "equivocada", 401)]:
            with self.subTest(usuario=nombre, estado=esperado):
                r = self.api("POST", "auth/login", {"usuario": nombre, "contrasenia": clave}, usuario=None)
                self.assertEqual(r.status_code, esperado)
                self.assertNotIn("token", r.json)
        ruta = "personas/" + str(alta.json["persona"]["id"])
        self.assertEqual(self.api("DELETE", ruta).status_code, 200)
        r = self.api("POST", "auth/login", datos, usuario=None)
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("token", r.json)
        self.assertEqual(self.api("PUT", ruta + "/reactivar").status_code, 200)
        self.assertEqual(self.api("POST", "auth/login", datos, usuario=None).status_code, 200)

    def test_usuario_duplicado_y_rol_inexistente_no_crean_registros(self):
        datos = self.datos_persona()
        for valores, estado in [({"usuario": "u0"}, 409), ({"roles": [99999]}, 404)]:
            with self.subTest(valores=valores):
                respuesta = self.api("POST", "personas", {**datos, **valores})
                self.assertEqual(respuesta.status_code, estado)
                self.assertEqual(Persona.query.count(), 4)

    def test_editar_roles_y_recuperar_solo_roles_habilitados(self):
        datos = self.datos_persona()
        alta = self.api("POST", "personas", datos)
        self.assertEqual(alta.status_code, 201, alta.json)
        ruta = "personas/" + str(alta.json["persona"]["id"])
        edicion = {"nombre": "Ana Pérez", "usuario": "ana", "roles": [self.roles[2].id_rol]}
        self.assertEqual(self.api("PUT", ruta, edicion).status_code, 200)
        self.assertEqual(self.api("POST", "auth/login", datos).json["usuario"]["roles"], ["CAJERO"])
        self.assertEqual(self.api("DELETE", f"roles/{self.roles[2].id_rol}").status_code, 200)
        self.assertEqual(self.api("POST", "auth/login", datos).json["usuario"]["roles"], [])
        self.assertEqual(self.api("PUT", f"roles/{self.roles[2].id_rol}/reactivar").status_code, 200)
        self.assertEqual(self.api("POST", "auth/login", datos).json["usuario"]["roles"], ["CAJERO"])

    def test_editar_nombre_con_roles_marcados_conserva_las_asignaciones(self):
        persona = self.users[0]
        ids_roles = [rol.id_rol for rol in self.roles]
        r = self.api("PUT", f"personas/{persona.id_per}",
                     {"nombre": "Nuevo nombre", "usuario": persona.usuario, "roles": ids_roles})
        self.assertEqual(r.status_code, 200, r.json)
        db.session.expire_all()
        self.assertEqual(persona.nombre, "Nuevo nombre")
        activos = RolPersona.query.filter_by(persona_id_per=persona.id_per, estado=True).all()
        self.assertCountEqual([asignacion.rol_id_rol for asignacion in activos], ids_roles)

    def test_edicion_sin_roles_se_rechaza_y_conserva_la_cuenta(self):
        persona = self.users[0]
        pid, nombre = persona.id_per, persona.nombre
        ids_roles = [rol.id_rol for rol in self.roles]
        r = self.api("PUT", f"personas/{pid}",
                     {"nombre": "Cambio inválido", "usuario": persona.usuario, "roles": []})
        self.assertEqual(r.status_code, 400, r.json)
        self.assertIn("rol", r.json["error"])
        db.session.remove()
        self.assertEqual(db.session.get(Persona, pid).nombre, nombre)
        activos = RolPersona.query.filter_by(persona_id_per=pid, estado=True).all()
        self.assertCountEqual([asignacion.rol_id_rol for asignacion in activos], ids_roles)

    def test_empresa_vinculada_visible_solo_a_su_integrante(self):
        persona = self.users[1]
        r = self.api("POST", "empresas", {"nombre": "Taller", "telefono": 555,
                                         "personas": [persona.id_per, persona.id_per]})
        self.assertEqual(r.status_code, 201, r.json)
        eid = r.json["empresa"]["id"]
        self.assertEqual(PersonaEmpresa.query.filter_by(empresa_id_empresa=eid).count(), 1)
        ruta = f"empresas/mias/{eid}"
        self.assertIn(eid, [e["id"] for e in self.api("GET", "empresas/mias", usuario=1).json["empresas"]])
        self.assertEqual(self.api("GET", ruta, usuario=1).status_code, 200)
        self.assertEqual(self.api("GET", ruta, usuario=0).status_code, 404)
        self.assertEqual(self.api("GET", ruta, usuario=2).status_code, 403)

    def test_empresa_rechaza_duplicado_y_revierte_alta_con_integrante_invalido(self):
        for nombre, personas, estado in [("EMPRESA 0", [], 409), ("Nueva", [self.users[1].id_per, 99999], 400)]:
            with self.subTest(nombre=nombre):
                r = self.api("POST", "empresas", {"nombre": nombre, "telefono": 555, "personas": personas})
                self.assertEqual(r.status_code, estado)
                self.assertEqual(Empresa.query.count(), 3)
                self.assertEqual(PersonaEmpresa.query.count(), 3)

    def test_inventario_crear_editar_archivar_y_recuperar(self):
        eid = self.empresas[1].id_empresa
        datos = {"nombre": "Perfume", "cantidad": 5, "precio_u": 10, "rebaja": 3,
                 "fecha_ingreso": "2026-09-20", "notas": "Aroma floral", "id_empresa": eid}
        alta = self.api("POST", "productos?ambito=propio", datos, usuario=1)
        self.assertEqual(alta.status_code, 201, alta.json)
        pid = alta.json["producto"]["id"]
        ruta = f"productos/{pid}"
        cambio = self.api("PUT", ruta + "?ambito=propio", {**datos, "nombre": "Perfume floral", "precio_u": 12}, usuario=1)
        self.assertEqual(cambio.status_code, 200, cambio.json)
        detalle = self.api("GET", ruta, usuario=1).json["producto"]
        self.assertEqual((detalle["precio_final"], detalle["notas"]), (9, "Aroma floral"))
        lista = f"productos/empresa/{eid}?buscar=floral&ambito=propio"
        self.assertEqual(self.api("DELETE", ruta, usuario=1).status_code, 200)
        self.assertEqual(self.api("GET", lista, usuario=1).json["productos"], [])
        archivados = self.api("GET", lista + "&estado=archivados", usuario=1).json["productos"]
        self.assertEqual([p["id"] for p in archivados], [pid])
        self.assertEqual(self.api("PUT", ruta + "/reactivar", usuario=1).status_code, 200)
        p = self.api("GET", lista, usuario=1).json["productos"][0]
        self.assertEqual((p["id"], p["cantidad"]), (pid, 5))

    def test_producto_invalido_o_de_empresa_ajena_no_se_crea(self):
        datos = {"nombre": "Nuevo", "cantidad": 1, "precio_u": 10, "fecha_ingreso": "2026-09-20",
                 "id_empresa": self.empresas[1].id_empresa}
        for cambio, estado in [({"cantidad": -1}, 400), ({"rebaja": 11}, 400),
                               ({"id_empresa": self.empresas[0].id_empresa}, 404)]:
            with self.subTest(cambio=cambio):
                r = self.api("POST", "productos?ambito=propio", {**datos, **cambio}, usuario=1)
                self.assertEqual(r.status_code, estado, r.json)
                self.assertEqual(Producto.query.count(), 3)

    def test_jornada_se_crea_sin_asignaciones_y_se_filtra_por_fecha(self):
        jid = self.nueva_jornada()
        self.assertEqual(JornadaCajero.query.filter_by(jornada_id_jornada=jid).count(), 0)
        self.assertEqual(JornadaProducto.query.filter_by(jornada_id_jornada=jid).count(), 0)
        cambio = {"nombre": "Feria ampliada", "direccion": "Centro", "fecha_inicio": "2026-09-21",
                  "fecha_fin": "2026-09-24"}
        self.assertEqual(self.api("PUT", f"jornadas/{jid}", cambio).status_code, 200)
        detalle = self.api("GET", f"jornadas/{jid}").json["jornada"]
        self.assertEqual((detalle["nombre"], detalle["fecha_fin"]), ("Feria ampliada", "2026-09-24"))
        for fecha, incluido in [("2026-09-24", True), ("2026-09-25", False)]:
            filas = self.api("GET", f"jornadas?estado=true&fecha={fecha}").json["jornadas"]
            self.assertEqual(jid in [j["id"] for j in filas], incluido)

    def test_jornada_rechaza_fechas_invalidas(self):
        for fin in ("2026-09-19", "no-es-fecha"):
            with self.subTest(fin=fin):
                r = self.api("POST", "jornadas", {"nombre": "Inválida", "direccion": "Centro",
                             "fecha_inicio": "2026-09-20", "fecha_fin": fin})
                self.assertEqual(r.status_code, 400)
                self.assertEqual(Jornada.query.count(), 1)

    def test_asignacion_multiple_retiro_y_reasignacion_de_cajeros(self):
        jid = self.nueva_jornada()
        ruta = f"jornadas/{jid}/cajeros"
        a, b = self.users[0].id_per, self.users[2].id_per
        self.assertEqual(self.api("POST", ruta, {"personas": [a, 99999]}).status_code, 400)
        self.assertEqual(self.api("GET", ruta).json["cajeros"], [])
        self.assertEqual(self.api("POST", ruta, {"personas": [a, b, b]}).status_code, 200)
        self.assertEqual(self.api("DELETE", f"{ruta}/{b}").status_code, 200)
        filas = self.api("GET", ruta).json["cajeros"]
        self.assertEqual({c["persona"]["id"]: c["estado"] for c in filas}, {a: True, b: False})
        self.assertEqual(self.api("POST", ruta, {"personas": [b]}).status_code, 200)
        filas = self.api("GET", ruta).json["cajeros"]
        self.assertEqual(len(filas), 2)
        self.assertTrue(all(c["estado"] for c in filas))

    def test_productos_de_feria_asignacion_multiple_sin_alterar_inventario(self):
        jid = self.nueva_jornada()
        eid = self.empresas[0].id_empresa
        alta = self.api("POST", "productos", {"nombre": "Segundo", "cantidad": 3, "precio_u": 8,
                        "fecha_ingreso": "2026-09-20", "id_empresa": eid})
        self.assertEqual(alta.status_code, 201, alta.json)
        a, b = self.productos[0].id_prod, alta.json["producto"]["id"]
        ruta = f"jornadas/{jid}/empresas/{eid}/productos"
        self.assertEqual(self.api("POST", ruta, {"productos": [a, self.productos[1].id_prod]}).status_code, 400)
        relaciones = JornadaProducto.query.filter_by(jornada_id_jornada=jid)
        self.assertEqual(relaciones.count(), 0)
        self.assertEqual(self.api("POST", ruta, {"productos": [a, b, b]}).status_code, 200)
        self.assertEqual(self.api("DELETE", f"jornadas/{jid}/productos/{a}").status_code, 200)
        self.assertFalse(relaciones.filter_by(producto_id_prod=a).one().estado)
        self.assertTrue(self.productos[0].estado)
        self.assertEqual(self.productos[0].cantidad, 10)
        self.assertEqual(self.api("POST", ruta, {"productos": [a]}).status_code, 200)
        self.assertEqual(relaciones.filter_by(estado=True).count(), 2)
        self.assertEqual(relaciones.count(), 2)

    def test_jornada_cerrada_rechaza_nuevas_asignaciones(self):
        jid = self.nueva_jornada()
        self.assertEqual(self.api("PUT", f"jornadas/{jid}/cerrar").status_code, 200)
        caja = self.api("POST", f"jornadas/{jid}/cajeros", {"personas": [self.users[2].id_per]})
        productos = self.api("POST", f"jornadas/{jid}/empresas/{self.empresas[0].id_empresa}/productos",
                             {"productos": [self.productos[0].id_prod]})
        self.assertEqual((caja.status_code, productos.status_code), (400, 400))
        self.assertEqual(JornadaProducto.query.filter_by(jornada_id_jornada=jid).count(), 0)
        self.assertEqual(JornadaCajero.query.filter_by(jornada_id_jornada=jid).count(), 0)

    def test_cobro_con_qr_o_billetera_se_conserva_en_el_reporte(self):
        for nombre in ("QR", "Billetera móvil"):
            with self.subTest(metodo=nombre):
                alta = self.api("POST", "metodos-pago", {"nombre": nombre, "descripcion": nombre})
                self.assertEqual(alta.status_code, 201, alta.json)
                mid = alta.json["metodo_pago"]["id"]
                cobro = {"id_jornada_cajero": self.jc.id_jor_caj, "id_metodo_pago": mid,
                         "detalles": [{"id_jornada_producto": self.jp[0].id_jor_prod, "cantidad": 1,
                                       "aplicar_descuento": False}]}
                self.assertEqual(self.api("POST", "ventas", cobro, usuario=2).status_code, 201)
                self.assertEqual(self.api("DELETE", f"metodos-pago/{mid}").status_code, 200)
                self.assertEqual(self.api("POST", "ventas", cobro, usuario=2).status_code, 404)
                reporte = self.api("GET", f"jornadas/{self.jornada.id_jornada}/reporte").json
                self.assertEqual(next(p for p in reporte["metodos_pago"] if p["nombre"] == alta.json["metodo_pago"]["nombre"])["total"], 20)

    def test_cuadre_feria_dos_empresas_por_qr(self):
        a, b = self.productos[:2]
        a.precio_u, a.rebaja, a.cantidad = Decimal("10"), Decimal("3"), 5
        b.precio_u, b.rebaja, b.cantidad = Decimal("8"), None, 4
        pago = MetodoPago(nombre="QR", descripcion="Prueba", estado=True)
        db.session.add(pago)
        db.session.commit()
        datos = {"id_jornada_cajero": self.jc.id_jor_caj, "id_metodo_pago": pago.id_metodos,
                 "detalles": [{"id_jornada_producto": self.jp[0].id_jor_prod, "cantidad": 2, "aplicar_descuento": True},
                              {"id_jornada_producto": self.jp[1].id_jor_prod, "cantidad": 1, "aplicar_descuento": False}]}
        r = self.api("POST", "ventas", datos, usuario=2)
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual(r.json["venta"]["total"], 22)
        db.session.expire_all()
        self.assertEqual((a.cantidad, b.cantidad), (3, 3))
        venta = Venta.query.one()
        self.assertEqual((venta.persona_id_per, venta.metodos_pago_id_metodos), (self.users[2].id_per, pago.id_metodos))
        rep = self.api("GET", f"jornadas/{self.jornada.id_jornada}/reporte").json
        totales = {e["id"]: e["total"] for e in rep["empresas"]}
        self.assertEqual((totales[a.empresa_id_empresa], totales[b.empresa_id_empresa]), (14, 8))
        self.assertTrue(rep["cuadra"])
        self.assertEqual(rep["total"], 22)

    def test_retirar_y_restaurar_acceso_a_empresa(self):
        empresa = self.empresas[1]
        eid = empresa.id_empresa
        ruta = f"empresas/{eid}"
        datos = {"nombre": "Taller actualizado", "telefono": 777, "direccion": "Plaza"}
        for personas, estado in [([], 404), ([self.users[1].id_per], 200)]:
            with self.subTest(personas=personas):
                r = self.api("PUT", ruta, {**datos, "personas": personas})
                self.assertEqual(r.status_code, 200, r.json)
                detalle = self.api("GET", f"empresas/mias/{eid}", usuario=1)
                self.assertEqual(detalle.status_code, estado)
        self.assertEqual(self.api("DELETE", ruta).status_code, 200)
        self.assertFalse(self.api("GET", ruta).json["empresa"]["estado"])
        self.assertEqual(self.api("PUT", ruta + "/reactivar").status_code, 200)
        self.assertTrue(self.api("GET", ruta).json["empresa"]["estado"])

    def test_retiro_de_cajero_preserva_el_cobro_y_bloquea_la_siguiente_venta(self):
        datos = {"id_jornada_cajero": self.jc.id_jor_caj, "id_metodo_pago": self.pago.id_metodos,
                 "detalles": [{"id_jornada_producto": self.jp[0].id_jor_prod, "cantidad": 1}]}
        self.assertEqual(self.api("POST", "ventas", datos, usuario=2).status_code, 201)
        r = self.api("DELETE", f"jornadas/{self.jornada.id_jornada}/cajeros/{self.users[2].id_per}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.api("POST", "ventas", datos, usuario=2).status_code, 403)
        self.assertEqual(Venta.query.one().persona_id_per, self.users[2].id_per)
        self.assertEqual(self.productos[0].cantidad, 9)

    def comprobar_limites_administrativos(self, usuario, esperado):
        casos = [
            ("personas", self.datos_persona()),
            ("empresas", {"nombre": "Empresa no autorizada", "telefono": 555}),
            ("jornadas", {"nombre": "Feria no autorizada", "direccion": "Centro",
                          "fecha_inicio": "2026-09-21", "fecha_fin": "2026-09-23"}),
            (f"jornadas/{self.jornada.id_jornada}/cajeros", {"personas": [self.users[0].id_per]}),
            (f"jornadas/{self.jornada.id_jornada}/empresas/{self.empresas[0].id_empresa}/productos",
             {"productos": [self.productos[0].id_prod]}),
            ("roles", {"nombre": "ROL_PRUEBA", "descripcion": "Prueba"}),
        ]
        for ruta, datos in casos:
            with self.subTest(ruta=ruta):
                r = self.api("POST", ruta, datos, usuario=usuario)
                self.assertEqual(r.status_code, esperado, f"POST {ruta} devolvió {r.status_code}")

    def test_revocar_rol_administrador_invalida_el_permiso_del_token_existente(self):
        admin = self.users[0]
        asignacion = RolPersona.query.filter_by(persona_id_per=admin.id_per, rol_id_rol=self.roles[0].id_rol).one()
        asignacion.estado = False
        db.session.commit()
        nombre = self.jornada.nombre
        respuesta = self.api("PUT", f"jornadas/{self.jornada.id_jornada}", {
            "nombre": "Cambio no autorizado", "direccion": "Plaza",
            "fecha_inicio": "2026-09-21", "fecha_fin": "2026-09-22",
        })
        self.assertEqual(respuesta.status_code, 403)
        db.session.expire_all()
        self.assertEqual(self.jornada.nombre, nombre)

    def test_acceso_a_perfil_propio_y_catalogos_compartidos(self):
        for usuario in (1, 2):
            with self.subTest(usuario=usuario):
                propio = self.api("GET", f"personas/{self.users[usuario].id_per}", usuario=usuario)
                self.assertEqual(propio.status_code, 200)
                ajeno = self.api("GET", f"personas/{self.users[0].id_per}", usuario=usuario)
                self.assertEqual(ajeno.status_code, 403)
                self.assertEqual(self.api("GET", "metodos-pago?estado=true", usuario=usuario).status_code, 200)

    def test_retiros_administrativos_no_modifican_datos_sin_permiso(self):
        for usuario, estado in ((None, 401), (1, 403)):
            with self.subTest(usuario=usuario):
                for ruta in (
                    f"personas/{self.users[0].id_per}", f"empresas/{self.empresas[0].id_empresa}",
                    f"jornadas/{self.jornada.id_jornada}/cajeros/{self.users[2].id_per}",
                    f"jornadas/{self.jornada.id_jornada}/productos/{self.productos[0].id_prod}",
                    f"roles/{self.roles[0].id_rol}", f"metodos-pago/{self.pago.id_metodos}",
                ):
                    with self.subTest(ruta=ruta):
                        self.assertEqual(self.api("DELETE", ruta, usuario=usuario).status_code, estado)
        db.session.expire_all()
        for registro in (self.users[0], self.empresas[0], self.jc, self.jp[0], self.roles[0], self.pago):
            self.assertTrue(registro.estado)

    def test_administracion_exige_sesion(self):
        self.comprobar_limites_administrativos(usuario=None, esperado=401)

    def test_administracion_exige_rol_administrador(self):
        self.comprobar_limites_administrativos(usuario=1, esperado=403)

class ReglasUnitariasTest(unittest.TestCase):
    def test_cantidades_de_venta_deben_ser_enteros_positivos(self):
        from app.services.venta_service import VentaError, VentaService
        self.assertEqual(VentaService.entero("2", "Cantidad"), 2)
        for valor in (0, -1, True, 1.5, "1.5", 2147483648):
            with self.subTest(valor=valor), self.assertRaises(VentaError):
                VentaService.entero(valor, "Cantidad")

    def test_importes_de_producto_son_decimales_finitos(self):
        from app.services.producto_service import ProductoService
        self.assertEqual(ProductoService._convertir_decimal("10.35", "Precio"), Decimal("10.35"))
        for valor in ("NaN", "Infinity", "texto"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                ProductoService._convertir_decimal(valor, "Precio")


if __name__ == "__main__":
    unittest.main()
