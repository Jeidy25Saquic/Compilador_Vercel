import json
import re
import os

_DIR = os.path.dirname(os.path.abspath(__file__))


class AnalizadorLexico:

    def __init__(self):
        try:
            # Buscar tokens.json en el mismo directorio que Lexico.py
            tokens_path = os.path.join(_DIR, "tokens.json")
            with open(tokens_path, "r", encoding="utf-8") as f:
                self.tokens = json.load(f)
        except Exception as e:
            print("Error cargando tokens.json:", e)
            self.tokens = {}

    def es_texto_libre(self, parte):
        """Devuelve True si la parte es una palabra de texto libre
        (no es reservada, no es número, fecha, hora, operador ni símbolo especial)."""
        if parte in self.tokens:
            return False
        if parte in ["(", ")", ",", ";", "+", "==", "!=", ">", "<", ">=", "<="]:
            return False
        if parte.startswith('"'):
            return False
        if re.fullmatch(r'\d+', parte):
            return False
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', parte):
            return False
        if re.fullmatch(r'\d{1,2}:\d{2}', parte):
            return False
        if re.fullmatch(r'HOY[+\-]\d+', parte):
            return False
        # Si llega hasta aquí, es texto libre (mayúsculas, minúsculas, acentos, guiones)
        if re.fullmatch(r'[A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-zÁÉÍÓÚáéíóúñÑ0-9_\-]*', parte):
            return True
        return False

    def analizar(self, texto):
        resultado = []

        # Normalizar operadores compuestos antes de separar
        texto = texto.replace("==", " == ").replace("!=", " != ") \
                     .replace(">=", " >= ").replace("<=", " <= ")

        texto = texto.replace("(", " ( ").replace(")", " ) ") \
            .replace(",", " , ").replace(";", " ; ") \
            .replace("+", " + ")

        partes = [p for p in texto.split() if p.strip()]

        dentro_parentesis = 0  # contador de anidación
        dentro_cadena = False
        cadena_actual = ""

        i = 0
        while i < len(partes):
            parte = partes[i]

            # Detectar inicio de cadena con comillas
            if parte.startswith('"') and not dentro_cadena:
                cadena_actual = parte
                if parte.endswith('"') and len(parte) > 1:
                    resultado.append((cadena_actual, "CADENA"))
                    cadena_actual = ""
                else:
                    dentro_cadena = True
                i += 1
                continue

            if dentro_cadena:
                cadena_actual += " " + parte
                if parte.endswith('"'):
                    resultado.append((cadena_actual, "CADENA"))
                    cadena_actual = ""
                    dentro_cadena = False
                i += 1
                continue

            if parte == "(":
                dentro_parentesis += 1
                resultado.append((parte, self.tokens.get(parte, "DELIMITADOR")))
                i += 1
                continue

            if parte == ")":
                dentro_parentesis = max(0, dentro_parentesis - 1)
                resultado.append((parte, self.tokens.get(parte, "DELIMITADOR")))
                i += 1
                continue

            # Dentro de paréntesis: agrupar palabras de texto libre consecutivas en un solo TEXTO
            if dentro_parentesis > 0 and self.es_texto_libre(parte):
                palabras = [parte]
                while i + 1 < len(partes) and self.es_texto_libre(partes[i + 1]):
                    i += 1
                    palabras.append(partes[i])
                lexema_completo = " ".join(palabras)
                resultado.append((lexema_completo, "TEXTO"))
                i += 1
                continue

            tipo = self.clasificar(parte, dentro_parentesis > 0)
            resultado.append((parte, tipo))
            i += 1

        return resultado

    def clasificar(self, lex, dentro_parentesis):
        lex = lex.strip()

        if not lex:
            return "ERROR_LEXICO"

        # Verificar en tabla de tokens directamente
        if lex in self.tokens:
            return self.tokens[lex]

        # Expresiones de fecha inteligente: HOY + N dias/semanas/meses
        if re.fullmatch(r'HOY[+\-]\d+', lex):
            return "EXPR_FECHA"

        # Hora en formato HH:MM
        if re.fullmatch(r'\d{1,2}:\d{2}', lex):
            horas, minutos = map(int, lex.split(':'))
            if 0 <= horas <= 23 and 0 <= minutos <= 59:
                return "HORA"
            return "ERR_INV_TIME"

        # Fecha fija YYYY-MM-DD
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', lex):
            if self.fecha_valida(lex):
                return "FECHA"
            return "ERR_INV_DATE"

        # Cadenas entre comillas dobles
        if re.fullmatch(r'"[^"]*"', lex):
            return "CADENA"

        # Número entero
        if lex.isdigit():
            return "NUMERO"

        # Palabras alfabéticas (con o sin acentos, mayúsculas o minúsculas)
        if re.fullmatch(r'[A-Za-zÁÉÍÓÚáéíóúñÑ][A-Za-zÁÉÍÓÚáéíóúñÑ0-9 _.\-]*', lex):
            # Dentro de paréntesis: cualquier palabra suelta es TEXTO
            if dentro_parentesis:
                return "TEXTO"
            # Fuera de paréntesis: solo minúsculas puras son IDENTIFICADOR
            if re.fullmatch(r'[a-z][a-z0-9_]*', lex):
                return "IDENTIFICADOR"
            return "TEXTO"

        # Símbolos y delimitadores
        if lex in ["(", ")", ",", ";", "-", "+", "==", "!=", ">", "<", ">=", "<="]:
            if lex in [",", "+", "-"]:
                return "SIMBOLO"
            if lex in ["==", "!=", ">", "<", ">=", "<="]:
                return "OPERADOR_COMPARACION"
            return "DELIMITADOR"

        return "ERROR_LEXICO"

    def fecha_valida(self, fecha):
        try:
            anio, mes, dia = map(int, fecha.split("-"))
            if 1 <= mes <= 12 and 1 <= dia <= 31:
                dias_por_mes = [31, 29 if self.es_bisiesto(anio) else 28, 31, 30, 31, 30,
                                31, 31, 30, 31, 30, 31]
                return dia <= dias_por_mes[mes - 1]
            return False
        except:
            return False

    def es_bisiesto(self, anio):
        return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)

    def mostrar_tabla(self, tokens):
        print("\n{:<30} {:<20}".format("LEXEMA", "TIPO DE TOKEN"))
        print("-" * 55)
        for lex, tipo in tokens:
            print("{:<30} {:<20}".format(lex, tipo))


if __name__ == "__main__":

    analizador = AnalizadorLexico()

    print("Ingrese el codigo (Enter vacío para terminar):\n")

    entrada = ""
    while True:
        linea = input()
        if linea == "":
            break
        entrada += linea + " "

    tokens = analizador.analizar(entrada)

    analizador.mostrar_tabla(tokens)