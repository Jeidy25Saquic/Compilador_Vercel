
from flask import Flask, render_template, request, jsonify
import os
import sys
import json

print("=== INICIANDO APLICACIÓN FLASK EN VERCEL ===")
print("Directorio actual:", os.getcwd())
print("Archivos en directorio:", os.listdir('.'))


sys.path.insert(0, os.getcwd())


try:
    from Lexico import AnalizadorLexico
    print("✓ AnalizadorLexico importado correctamente")
except ImportError as e:
    print(f"✗ Error importando Lexico: {e}")
    # Intentar importación alternativa
    try:
        from .Lexico import AnalizadorLexico
        print("✓ AnalizadorLexico importado (ruta relativa)")
    except ImportError:
        AnalizadorLexico = None
        print("✗ No se pudo importar AnalizadorLexico")

try:
    from Sintactico import AnalizadorSintactico
    print("✓ AnalizadorSintactico importado correctamente")
except ImportError as e:
    print(f"✗ Error importando Sintactico: {e}")
    try:
        from .Sintactico import AnalizadorSintactico
        print("✓ AnalizadorSintactico importado (ruta relativa)")
    except ImportError:
        AnalizadorSintactico = None
        print("✗ No se pudo importar AnalizadorSintactico")

try:
    from semantico import AnalizadorSemantico
    print("✓ AnalizadorSemantico importado correctamente")
except ImportError as e:
    print(f"✗ Error importando semantico: {e}")
    try:
        from .semantico import AnalizadorSemantico
        print("✓ AnalizadorSemantico importado (ruta relativa)")
    except ImportError:
        AnalizadorSemantico = None
        print("✗ No se pudo importar AnalizadorSemantico")


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'static') if os.path.exists(os.path.join(os.path.dirname(__file__), 'static')) else None

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)


TOKENS_RESERVADOS = {}
try:
    
    posibles_rutas = [
        os.path.join(os.path.dirname(__file__), 'tokens.json'),
        os.path.join(os.getcwd(), 'tokens.json'),
        'tokens.json'
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                TOKENS_RESERVADOS = json.load(f)
            print(f"✓ Tokens cargados exitosamente desde: {ruta}")
            print(f"  Total de patrones: {len(TOKENS_RESERVADOS)}")
            break
    else:
        print("⚠ No se encontró tokens.json, usando diccionario vacío")
        TOKENS_RESERVADOS = {}
        
except Exception as e:
    print(f"✗ Error cargando tokens.json: {e}")
    TOKENS_RESERVADOS = {}

# ==================== INICIALIZAR ANALIZADORES ====================
try:
    if AnalizadorLexico:
        analizador_lexico = AnalizadorLexico()
        print("✓ Analizador Léxico inicializado")
    else:
        analizador_lexico = None
        print("⚠ Analizador Léxico no disponible")
except Exception as e:
    print(f"✗ Error inicializando AnalizadorLexico: {e}")
    analizador_lexico = None



@app.route('/')
def index():
    """Página principal"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"✗ Error renderizando index.html: {e}")
        return jsonify({"error": "No se pudo cargar la página principal", "detalle": str(e)}), 500

@app.route('/health')
def health():
    """Endpoint para verificar que la app está funcionando"""
    return jsonify({
        "status": "ok",
        "message": "Aplicación Flask funcionando correctamente en Vercel",
        "analizadores": {
            "lexico": analizador_lexico is not None,
            "sintactico": AnalizadorSintactico is not None,
            "semantico": AnalizadorSemantico is not None
        }
    })

@app.route('/analizar', methods=['POST'])
def analizar():
    """Análisis léxico"""
    try:
        if not analizador_lexico:
            return jsonify({"error": "Analizador léxico no disponible"}), 500
            
        codigo = request.json.get('codigo', '')
        if not codigo:
            return jsonify({"error": "No se proporcionó código para analizar"}), 400
            
        tokens = analizador_lexico.analizar(codigo)
        
        resultado = []
        for lexema, tipo in tokens:
            resultado.append({
                'lexema': lexema,
                'tipo': tipo,
                'color': obtener_color_lexico(tipo)
            })
        
        tokens_unicos = len(set([t[0] for t in tokens])) if tokens else 0
        variables = len([t for t in tokens if t[1] == 'IDENTIFICADOR']) if tokens else 0
        
        conteo_tipos = {}
        for _, tipo in tokens:
            conteo_tipos[tipo] = conteo_tipos.get(tipo, 0) + 1
        
        return jsonify({
            'tokens': resultado,
            'estadisticas': {
                'errores': len([t for t in tokens if t[1] in ('ERROR_LEXICO', 'ERR_INV_DATE', 'ERR_INV_TIME')]),
                'advertencias': 0,
                'tokens_unicos': tokens_unicos,
                'variables': variables,
                'funciones': 0,
                'conteo_tipos': conteo_tipos
            }
        })
    except Exception as e:
        print(f"✗ Error en análisis léxico: {e}")
        return jsonify({"error": "Error en análisis léxico", "detalle": str(e)}), 500

@app.route('/analizar-sintactico', methods=['POST'])
def analizar_sintactico():
    """Análisis sintáctico"""
    try:
        if not AnalizadorSintactico:
            return jsonify({"error": "Analizador sintáctico no disponible"}), 500
            
        codigo = request.json.get('codigo', '')
        if not codigo:
            return jsonify({"error": "No se proporcionó código para analizar"}), 400
            
        sint = AnalizadorSintactico()
        arbol, texto_arbol, exito, mensaje = sint.analizar(codigo)
        
        respuesta = {
            'exito': exito,
            'mensaje': mensaje,
            'texto_arbol': texto_arbol if exito else '',
            'arbol_json': arbol.a_dict() if exito and arbol else None,
        }
        
        if exito and arbol:
            respuesta['estadisticas'] = {
                'sentencias': len(arbol.hijos) if hasattr(arbol, 'hijos') else 0,
                'nodos_totales': contar_nodos(arbol),
                'profundidad': calcular_profundidad(arbol),
            }
        
        return jsonify(respuesta)
    except Exception as e:
        print(f"✗ Error en análisis sintáctico: {e}")
        return jsonify({"error": "Error en análisis sintáctico", "detalle": str(e)}), 500

@app.route('/analizar-semantico', methods=['POST'])
def analizar_semantico():
    """Análisis semántico"""
    try:
        if not AnalizadorSemantico:
            return jsonify({"error": "Analizador semántico no disponible"}), 500
            
        codigo = request.json.get('codigo', '')
        if not codigo:
            return jsonify({"error": "No se proporcionó código para analizar"}), 400
            
        sem = AnalizadorSemantico()
        tabla_simbolos, log_pasos, exito, mensaje, detalle_error = sem.analizar(codigo)
        
        tabla_json = []
        if tabla_simbolos:
            for entrada in tabla_simbolos.a_lista():
                valor = entrada.get('valor', '—')
                if entrada.get('categoria') == 'GRUPO' and entrada.get('miembros'):
                    valor = '[' + ', '.join(entrada.get('miembros', [])) + ']'
                elif entrada.get('categoria') == 'LISTA' and entrada.get('descripcion') and entrada.get('descripcion') != '—':
                    valor = entrada.get('descripcion')
                
                grupo = entrada.get('grupo', '—')
                if grupo == '—' and entrada.get('contexto') and entrada.get('contexto') != '—':
                    grupo = entrada.get('contexto')
                
                activo = '—'
                if entrada.get('categoria') == 'USUARIO':
                    activo = entrada.get('sesion', 'inactiva')
                
                entrada_serializable = {
                    'identificador': entrada.get('identificador', '—'),
                    'categoria': entrada.get('categoria', '—'),
                    'tipo': entrada.get('tipo', '—'),
                    'valor': valor,
                    'estado': entrada.get('estado', 'PENDIENTE'),
                    'prioridad': entrada.get('prioridad', '—'),
                    'asignado_a': entrada.get('asignado_a', '—'),
                    'grupo': grupo,
                    'activo': activo,
                    'linea': entrada.get('linea', 0),
                }
                tabla_json.append(entrada_serializable)
        
        log_json = []
        if log_pasos:
            log_json = [
                {
                    'paso': paso.get('paso', 0),
                    'accion': paso.get('accion', ''),
                    'detalle': paso.get('detalle', ''),
                }
                for paso in log_pasos
            ]
        
        respuesta = {
            'exito': exito,
            'mensaje': mensaje,
            'detalle_error': detalle_error,
            'tabla_simbolos': tabla_json,
            'log_pasos': log_json,
        }
        
        if exito:
            respuesta['estadisticas'] = {
                'total_usuarios': len([e for e in tabla_json if e.get('categoria') == 'USUARIO']),
                'total_grupos': len([e for e in tabla_json if e.get('categoria') == 'GRUPO']),
                'total_tareas': len([e for e in tabla_json if e.get('categoria') == 'TAREA']),
                'total_listas': len([e for e in tabla_json if e.get('categoria') in ('LISTA', 'VISTA')]),
            }
        
        return jsonify(respuesta)
    except Exception as e:
        print(f"✗ Error en análisis semántico: {e}")
        return jsonify({"error": "Error en análisis semántico", "detalle": str(e)}), 500



def contar_nodos(nodo):
  
    if not nodo:
        return 0
    try:
        return 1 + sum(contar_nodos(h) for h in getattr(nodo, 'hijos', []))
    except:
        return 1

def calcular_profundidad(nodo):
    
    if not nodo:
        return 0
    try:
        hijos = getattr(nodo, 'hijos', [])
        if not hijos:
            return 0
        return 1 + max(calcular_profundidad(h) for h in hijos)
    except:
        return 0

def obtener_color_lexico(tipo):
    """Devuelve el color correspondiente para cada tipo de token"""
    colores = {
        'PALABRA_RESERVADA': '#0a2472',
        'IDENTIFICADOR': '#1e3a8a',
        'DELIMITADOR': '#3b82f6',
        'NUMERO': '#22c55e',
        'FECHA': '#86efac',
        'EXPR_FECHA': '#4ade80',
        'HORA': '#a3e635',
        'CADENA': '#e879f9',
        'OPERADOR_LOGICO': '#f59e0b',
        'OPERADOR_COMPARACION': '#fb923c',
        'OPERADOR': '#f97316',
        'TEXTO': '#475569',
        'SIMBOLO': '#f97316',
        'ERROR_LEXICO': '#ef4444',
        'ERR_INV_DATE': '#ef4444',
        'ERR_INV_TIME': '#ef4444',
    }
    return colores.get(tipo, '#64748b')

# ==================== MANEJO DE ERRORES GLOBAL ====================
@app.errorhandler(404)
def not_found(error):
    """Manejo de errores 404"""
    return jsonify({"error": "Ruta no encontrada", "mensaje": "Verifica que la URL sea correcta"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejo de errores 500"""
    return jsonify({"error": "Error interno del servidor", "mensaje": "Revisa los logs para más detalles"}), 500


if __name__ == '__main__':
    print("=== EJECUTANDO EN MODO LOCAL ===")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))