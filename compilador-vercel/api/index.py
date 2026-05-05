import os
import sys

# Asegurar que el directorio de la API esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify
from Lexico import AnalizadorLexico
from Sintactico import AnalizadorSintactico
from semantico import AnalizadorSemantico
import json

# Rutas absolutas basadas en la ubicación de este archivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, 'templates'),
    static_folder=os.path.join(ROOT_DIR, 'static'),
    static_url_path='/static'
)

analizador_lexico = AnalizadorLexico()

with open(os.path.join(BASE_DIR, 'tokens.json'), 'r', encoding='utf-8') as f:
    TOKENS_RESERVADOS = json.load(f)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analizar', methods=['POST'])
def analizar():
    codigo = request.json.get('codigo', '')
    tokens = analizador_lexico.analizar(codigo)

    resultado = []
    for lexema, tipo in tokens:
        resultado.append({
            'lexema': lexema,
            'tipo': tipo,
            'color': obtener_color_lexico(tipo)
        })

    tokens_unicos = len(set([t[0] for t in tokens]))
    variables = len([t for t in tokens if t[1] == 'IDENTIFICADOR'])

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


@app.route('/analizar-sintactico', methods=['POST'])
def analizar_sintactico():
    codigo = request.json.get('codigo', '')
    sint = AnalizadorSintactico()
    arbol, texto_arbol, exito, mensaje = sint.analizar(codigo)

    respuesta = {
        'exito': exito,
        'mensaje': mensaje,
        'texto_arbol': texto_arbol if exito else '',
        'arbol_json': arbol.a_dict() if exito else None,
    }

    if exito:
        respuesta['estadisticas'] = {
            'sentencias': len(arbol.hijos),
            'nodos_totales': contar_nodos(arbol),
            'profundidad': calcular_profundidad(arbol),
        }

    return jsonify(respuesta)


@app.route('/analizar-semantico', methods=['POST'])
def analizar_semantico():
    codigo = request.json.get('codigo', '')
    sem = AnalizadorSemantico()

    tabla_simbolos, log_pasos, exito, mensaje, detalle_error = sem.analizar(codigo)

    tabla_json = []
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

    log_json = [
        {
            'paso': paso['paso'],
            'accion': paso['accion'],
            'detalle': paso['detalle'],
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
            'total_usuarios': len([e for e in tabla_json if e['categoria'] == 'USUARIO']),
            'total_grupos': len([e for e in tabla_json if e['categoria'] == 'GRUPO']),
            'total_tareas': len([e for e in tabla_json if e['categoria'] == 'TAREA']),
            'total_listas': len([e for e in tabla_json if e['categoria'] in ('LISTA', 'VISTA')]),
        }

    return jsonify(respuesta)


def contar_nodos(nodo):
    return 1 + sum(contar_nodos(h) for h in nodo.hijos)


def calcular_profundidad(nodo):
    if not nodo.hijos:
        return 0
    return 1 + max(calcular_profundidad(h) for h in nodo.hijos)


def obtener_color_lexico(tipo):
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
