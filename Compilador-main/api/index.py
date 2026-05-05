# api/index.py - PUNTO DE ENTRADA PRINCIPAL PARA VERCEL
import sys
import os

# Añadir el directorio padre al path para importar tus módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
import json

# ==================== CONFIGURACIÓN ====================
print("=== INICIANDO API DE VERCEL ===")
print("Directorio actual:", os.getcwd())
print("Archivos disponibles:", os.listdir('.'))

# ==================== IMPORTAR TUS MÓDULOS ====================
try:
    from Lexico import AnalizadorLexico
    from Sintactico import AnalizadorSintactico
    from semantico import AnalizadorSemantico
    print("✓ Todos los módulos importados correctamente")
except Exception as e:
    print(f"✗ Error en importaciones: {e}")
    # Crear versiones dummy para pruebas si es necesario
    AnalizadorLexico = None
    AnalizadorSintactico = None
    AnalizadorSemantico = None

# ==================== CREAR APP ====================
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))

# ==================== CARGAR TOKENS ====================
TOKENS_RESERVADOS = {}
token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens.json')
if os.path.exists(token_path):
    with open(token_path, 'r', encoding='utf-8') as f:
        TOKENS_RESERVADOS = json.load(f)
    print(f"✓ Tokens cargados: {len(TOKENS_RESERVADOS)}")

# ==================== INICIALIZAR ====================
analizador_lexico = AnalizadorLexico() if AnalizadorLexico else None

# ==================== RUTAS ====================

@app.route('/')
def index():
    """Página principal"""
    template_path = os.path.join(app.template_folder, 'index.html')
    print(f"Buscando template en: {template_path}")
    print(f"¿Existe? {os.path.exists(template_path)}")
    print(f"Archivos en templates: {os.listdir(app.template_folder) if os.path.exists(app.template_folder) else 'No existe'}")
    
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({"error": "Template no encontrado", "detalle": str(e)}), 500

@app.route('/health')
def health():
    """Endpoint de salud"""
    return jsonify({
        "status": "ok", 
        "message": "API funcionando en Vercel",
        "modules": {
            "lexico": AnalizadorLexico is not None,
            "sintactico": AnalizadorSintactico is not None,
            "semantico": AnalizadorSemantico is not None
        }
    })

@app.route('/analizar', methods=['POST'])
def analizar():
    """Análisis léxico"""
    if not analizador_lexico:
        return jsonify({"error": "Analizador léxico no disponible"}), 500
    
    codigo = request.json.get('codigo', '')
    tokens = analizador_lexico.analizar(codigo)
    
    resultado = []
    for lexema, tipo in tokens:
        resultado.append({
            'lexema': lexema,
            'tipo': tipo,
            'color': obtener_color_lexico(tipo)
        })
    
    return jsonify({
        'tokens': resultado,
        'estadisticas': {
            'errores': len([t for t in tokens if t[1] in ('ERROR_LEXICO', 'ERR_INV_DATE', 'ERR_INV_TIME')]),
            'tokens_unicos': len(set([t[0] for t in tokens])),
            'variables': len([t for t in tokens if t[1] == 'IDENTIFICADOR'])
        }
    })

@app.route('/analizar-sintactico', methods=['POST'])
def analizar_sintactico():
    """Análisis sintáctico"""
    if not AnalizadorSintactico:
        return jsonify({"error": "Analizador sintáctico no disponible"}), 500
    
    codigo = request.json.get('codigo', '')
    sint = AnalizadorSintactico()
    arbol, texto_arbol, exito, mensaje = sint.analizar(codigo)
    
    return jsonify({
        'exito': exito,
        'mensaje': mensaje,
        'texto_arbol': texto_arbol if exito else ''
    })

@app.route('/analizar-semantico', methods=['POST'])
def analizar_semantico():
    """Análisis semántico"""
    if not AnalizadorSemantico:
        return jsonify({"error": "Analizador semántico no disponible"}), 500
    
    codigo = request.json.get('codigo', '')
    sem = AnalizadorSemantico()
    tabla_simbolos, log_pasos, exito, mensaje, detalle_error = sem.analizar(codigo)
    
    return jsonify({
        'exito': exito,
        'mensaje': mensaje,
        'detalle_error': detalle_error
    })

def obtener_color_lexico(tipo):
    colores = {
        'PALABRA_RESERVADA': '#0a2472',
        'IDENTIFICADOR': '#1e3a8a',
        'DELIMITADOR': '#3b82f6',
        'NUMERO': '#22c55e',
        'ERROR_LEXICO': '#ef4444',
    }
    return colores.get(tipo, '#64748b')

# ==================== EXPORTAR APP ====================
# Esto es CRÍTICO para Vercel
app.debug = False