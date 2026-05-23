from flask import Flask, request, jsonify, send_from_directory
from supabase import create_client
import os

app = Flask(__name__, static_folder='static')

# Conexión a Supabase (los valores vienen de variables de entorno)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────
# RUTA PRINCIPAL: sirve el HTML
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    datos = request.json
    username = datos.get("username", "").strip()
    password = datos.get("password", "").strip()

    if not username or not password:
        return jsonify({"ok": False, "mensaje": "Completa usuario y contraseña"}), 400

    resultado = supabase.table("usuarios")\
        .select("*")\
        .eq("username", username)\
        .eq("password", password)\
        .execute()

    if resultado.data:
        return jsonify({"ok": True, "mensaje": "Login exitoso"})
    else:
        return jsonify({"ok": False, "mensaje": "Usuario o contraseña incorrectos"}), 401

# ─────────────────────────────────────────────
# CREAR PEDIDO
# ─────────────────────────────────────────────
@app.route("/api/pedidos", methods=["POST"])
def crear_pedido():
    datos = request.json
    cliente   = datos.get("nombre_cliente", "").strip()
    producto  = datos.get("nombre_producto", "").strip()
    cantidad  = int(datos.get("cantidad", 0))

    if not cliente or not producto or cantidad <= 0:
        return jsonify({"ok": False, "mensaje": "Datos incompletos"}), 400

    # Buscar el producto en la BD para saber su precio y stock
    prod = supabase.table("productos")\
        .select("*")\
        .eq("nombre", producto)\
        .execute()

    if not prod.data:
        return jsonify({"ok": False, "mensaje": "Producto no encontrado"}), 404

    p = prod.data[0]
    if p["stock"] < cantidad:
        return jsonify({"ok": False, "mensaje": f"Stock insuficiente. Solo hay {p['stock']} unidades"}), 400

    # Calcular total
    total = p["precio"] * cantidad

    # Guardar el pedido con estado "nuevo"
    nuevo_pedido = supabase.table("pedidos").insert({
        "nombre_cliente":  cliente,
        "nombre_producto": producto,
        "cantidad":        cantidad,
        "total":           total,
        "estado":          "nuevo"
    }).execute()

    # Descontar del inventario
    nuevo_stock = p["stock"] - cantidad
    supabase.table("productos")\
        .update({"stock": nuevo_stock})\
        .eq("id", p["id"])\
        .execute()

    return jsonify({"ok": True, "pedido": nuevo_pedido.data[0]})

# ─────────────────────────────────────────────
# VER TODOS LOS PEDIDOS
# ─────────────────────────────────────────────
@app.route("/api/pedidos", methods=["GET"])
def ver_pedidos():
    pedidos = supabase.table("pedidos")\
        .select("*")\
        .order("created_at", desc=True)\
        .execute()
    return jsonify(pedidos.data)

# ─────────────────────────────────────────────
# CAMBIAR ESTADO DEL PEDIDO
# ─────────────────────────────────────────────
@app.route("/api/pedidos/<int:pedido_id>/estado", methods=["PUT"])
def cambiar_estado(pedido_id):
    datos  = request.json
    nuevo  = datos.get("estado", "").strip()
    estados_validos = ["nuevo", "picking", "packed", "shipped"]

    if nuevo not in estados_validos:
        return jsonify({"ok": False, "mensaje": "Estado no válido"}), 400

    actualizado = supabase.table("pedidos")\
        .update({"estado": nuevo})\
        .eq("id", pedido_id)\
        .execute()

    return jsonify({"ok": True, "pedido": actualizado.data[0]})

# ─────────────────────────────────────────────
# VER PRODUCTOS (para llenar el selector)
# ─────────────────────────────────────────────
@app.route("/api/productos", methods=["GET"])
def ver_productos():
    productos = supabase.table("productos").select("*").execute()
    return jsonify(productos.data)

if __name__ == "__main__":
    app.run(debug=True)