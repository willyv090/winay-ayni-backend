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


class VentasTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
