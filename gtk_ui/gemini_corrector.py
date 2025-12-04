"""
GutenAI - Corrector ortográfico y gramatical con Gemini 1.5
Diseñado para ser consistente y respetar el estilo del autor
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import difflib

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
    print("[DEBUG] Gemini modules imported successfully")
except ImportError as e:
    HAS_GEMINI = False
    print(f"[ERROR] Failed to import Gemini modules: {e}")

class GeminiCorrector:
    """Corrector inteligente usando Gemini 2.5 Flash con prompts deterministas"""

    def __init__(self, api_key: str, cache_dir: str = None):
        print(f"[DEBUG GeminiCorrector] Inicializando con API key: {api_key[:10]}...")

        if not HAS_GEMINI:
            raise ImportError("pip install google-genai")

        self.api_key = api_key
        self.cache_dir = Path(cache_dir or "cache/correcciones")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configurar cliente Gemini 2.5
        try:
            self.client = genai.Client(api_key=api_key)
            print("[DEBUG GeminiCorrector] Cliente Gemini creado exitosamente")
        except Exception as e:
            print(f"[ERROR GeminiCorrector] Error creando cliente Gemini: {e}")
            raise

        # Contadores de uso
        self.consultas_realizadas = 0
        self.max_consultas_hora = 15

        # Cache en memoria
        self.cache_memoria: Dict[str, dict] = {}

    def corregir_texto(self, texto: str, idioma: str = "es") -> dict:
        """
        Corrige texto manteniendo consistencia y respetando el estilo original

        Returns:
            {
                "texto_corregido": str,
                "errores_encontrados": list,
                "cambios_aplicados": int,
                "fuente": "cache|gemini"
            }
        """
        # Verificar caché primero
        hash_texto = self._hash_texto(texto)
        if hash_texto in self.cache_memoria:
            return {**self.cache_memoria[hash_texto], "fuente": "cache"}

        # Verificar caché en disco
        resultado_cache = self._cargar_cache(hash_texto)
        if resultado_cache:
            self.cache_memoria[hash_texto] = resultado_cache
            return {**resultado_cache, "fuente": "cache"}

        # Verificar límite de consultas
        if self.consultas_realizadas >= self.max_consultas_hora:
            raise Exception(f"Límite de {self.max_consultas_hora} consultas/hora alcanzado")

        # Procesar con Gemini
        try:
            resultado = self._procesar_con_gemini(texto, idioma)

            # Validar respuesta
            if self._validar_correccion(texto, resultado["texto_corregido"]):
                # Guardar en cache
                self._guardar_cache(hash_texto, resultado)
                self.cache_memoria[hash_texto] = resultado
                self.consultas_realizadas += 1

                return {**resultado, "fuente": "gemini"}
            else:
                # Si la corrección es inválida, devolver original
                resultado_fallback = {
                    "texto_corregido": texto,
                    "errores_encontrados": [],
                    "cambios_aplicados": 0,
                    "advertencia": "Corrección de IA rechazada por validación"
                }
                return {**resultado_fallback, "fuente": "fallback"}

        except Exception as e:
            raise Exception(f"Error en corrección con Gemini: {e}")

    def _procesar_con_gemini(self, texto: str, idioma: str) -> dict:
        """Procesa texto con Gemini usando prompt determinista"""

        prompt = self._crear_prompt_deterministico(texto, idioma)

        try:
            # Usar Gemini 2.5 Flash con nueva API
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=2048,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking para consistencia
                )
            )

            # Parsear respuesta JSON con manejo robusto
            contenido_respuesta = response.text.strip()

            # Extraer JSON de la respuesta (manejo robusto)
            json_valido = self._extraer_json_robusto(contenido_respuesta)

            if not json_valido:
                raise Exception("No se pudo extraer JSON válido de la respuesta de Gemini")

            datos = json.loads(json_valido)

            # Aplicar correcciones al texto
            texto_corregido = self._aplicar_correcciones(texto, datos.get("errores", []))

            return {
                "texto_corregido": texto_corregido,
                "errores_encontrados": datos.get("errores", []),
                "cambios_aplicados": len(datos.get("errores", [])),
                "comentarios_ia": datos.get("comentarios", "")
            }

        except json.JSONDecodeError as e:
            raise Exception(f"Respuesta JSON inválida de Gemini: {e}")
        except Exception as e:
            raise Exception(f"Error llamando a Gemini: {e}")

    def _extraer_json_robusto(self, respuesta: str) -> str:
        """Extrae JSON válido de la respuesta de Gemini de forma robusta"""

        # 1. Limpiar markdown si existe
        if "```json" in respuesta:
            try:
                start = respuesta.find("```json") + 7
                end = respuesta.find("```", start)
                if end > start:
                    respuesta = respuesta[start:end].strip()
            except:
                pass

        # 2. Buscar bloques JSON válidos
        posibles_json = []

        # Buscar desde el primer {
        start_idx = respuesta.find('{')
        if start_idx != -1:
            # Intentar extraer JSON balanceado
            json_extraido = self._extraer_json_balanceado(respuesta[start_idx:])
            if json_extraido:
                posibles_json.append(json_extraido)

        # 3. Probar cada posible JSON
        for candidato in posibles_json:
            try:
                # Intentar parsear para validar
                json.loads(candidato)
                return candidato
            except:
                continue

        # 4. Último intento: limpiar y reparar JSON común
        return self._reparar_json_comun(respuesta)

    def _extraer_json_balanceado(self, texto: str) -> str:
        """Extrae JSON balanceando llaves"""
        if not texto.startswith('{'):
            return ""

        nivel = 0
        escape = False
        en_string = False

        for i, char in enumerate(texto):
            if escape:
                escape = False
                continue

            if char == '\\':
                escape = True
                continue

            if char == '"' and not escape:
                en_string = not en_string
                continue

            if not en_string:
                if char == '{':
                    nivel += 1
                elif char == '}':
                    nivel -= 1
                    if nivel == 0:
                        return texto[:i+1]

        return ""

    def _reparar_json_comun(self, respuesta: str) -> str:
        """Repara problemas comunes en JSON de respuestas de IA"""

        # Buscar patrones JSON simples y repararlos
        import re

        # Patrón para encontrar estructura básica
        pattern = r'\{\s*"errores"\s*:\s*\[(.*?)\]\s*(?:,\s*"comentarios"\s*:\s*"[^"]*")?\s*\}'

        match = re.search(pattern, respuesta, re.DOTALL)
        if match:
            try:
                # Construir JSON mínimo válido
                return '{"errores": [], "comentarios": "Respuesta parseada con modo de recuperación"}'
            except:
                pass

        # Fallback: JSON vacío pero válido
        return '{"errores": [], "comentarios": "No se pudieron extraer errores - JSON malformado"}'

    def _crear_prompt_deterministico(self, texto: str, idioma: str) -> str:
        """Crea un prompt muy específico para obtener resultados consistentes"""

        return f"""TAREA: Corrección ortográfica y gramatical en {idioma}

REGLAS ESTRICTAS:
1. SOLO corregir errores ortográficos y gramaticales evidentes
2. NO cambiar el estilo, tono o estructura del autor
3. NO reformular frases que están correctas
4. MANTENER exactamente el mismo significado
5. NO agregar ni quitar información
6. CONSERVAR la puntuación original salvo errores evidentes

FORMATO DE RESPUESTA: Devolver ÚNICAMENTE JSON válido sin markdown, sin explicaciones adicionales.

TEXTO A CORREGIR:
{texto}

RESPUESTA - SOLO JSON VÁLIDO:
{{"errores":[{{"original":"palabra_error","corregido":"palabra_correcta","tipo":"ortografia","posicion_inicio":0,"razon":"error_específico"}}],"comentarios":"cambios_realizados"}}"""

    def _aplicar_correcciones(self, texto_original: str, errores: List[dict]) -> str:
        """Aplica las correcciones al texto original"""
        texto_resultado = texto_original

        # Ordenar errores por posición (de atrás hacia adelante para no alterar posiciones)
        errores_ordenados = sorted(errores, key=lambda e: e.get("posicion_inicio", 0), reverse=True)

        for error in errores_ordenados:
            original = error.get("original", "")
            corregido = error.get("corregido", "")

            if original and corregido and original in texto_resultado:
                # Reemplazar primera ocurrencia para ser más preciso
                texto_resultado = texto_resultado.replace(original, corregido, 1)

        return texto_resultado

    def _validar_correccion(self, original: str, corregido: str) -> bool:
        """Valida que la corrección sea razonable"""

        # 1. Verificar similitud (no debe cambiar más del 20%)
        similitud = difflib.SequenceMatcher(None, original, corregido).ratio()
        if similitud < 0.8:
            return False

        # 2. Verificar longitud (no debe cambiar más del 30%)
        if len(original) > 0:
            cambio_longitud = abs(len(corregido) - len(original)) / len(original)
            if cambio_longitud > 0.3:
                return False

        # 3. Verificar que no se eliminaron párrafos enteros
        parrafos_original = len(original.split('\n\n'))
        parrafos_corregido = len(corregido.split('\n\n'))
        if abs(parrafos_original - parrafos_corregido) > 1:
            return False

        return True

    def _hash_texto(self, texto: str) -> str:
        """Crea hash del texto para cache"""
        return hashlib.md5(texto.encode('utf-8')).hexdigest()

    def _cargar_cache(self, hash_contenido: str) -> Optional[dict]:
        """Carga resultado del cache en disco"""
        cache_file = self.cache_dir / f"{hash_contenido}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _guardar_cache(self, hash_contenido: str, resultado: dict):
        """Guarda resultado en cache en disco"""
        cache_file = self.cache_dir / f"{hash_contenido}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] No se pudo guardar cache: {e}")

    def obtener_estadisticas(self) -> dict:
        """Obtiene estadísticas de uso"""
        return {
            "consultas_realizadas": self.consultas_realizadas,
            "consultas_restantes": self.max_consultas_hora - self.consultas_realizadas,
            "cache_entradas": len(self.cache_memoria),
            "cache_directorio": str(self.cache_dir)
        }

    def reset_contadores(self):
        """Resetea contadores (usar con timer cada hora)"""
        self.consultas_realizadas = 0

    def procesar_con_prompt(self, texto: str, prompt_personalizado: str, idioma: str = "es") -> dict:
        """
        Procesa texto usando un prompt personalizado

        Returns:
            {
                "texto_corregido": str,
                "errores_encontrados": list,
                "cambios_aplicados": int,
                "fuente": "cache|gemini"
            }
        """
        print(f"[DEBUG GeminiCorrector] Procesando con prompt: '{prompt_personalizado}'")
        print(f"[DEBUG GeminiCorrector] Texto length: {len(texto)}")

        # Crear hash incluyendo el prompt para cache
        hash_contenido = self._hash_texto(texto + "|" + prompt_personalizado)

        # Verificar caché primero
        if hash_contenido in self.cache_memoria:
            print(f"[DEBUG GeminiCorrector] Resultado encontrado en cache memoria")
            return {**self.cache_memoria[hash_contenido], "fuente": "cache"}

        # Verificar caché en disco
        resultado_cache = self._cargar_cache(hash_contenido)
        if resultado_cache:
            print(f"[DEBUG GeminiCorrector] Resultado encontrado en cache disco")
            self.cache_memoria[hash_contenido] = resultado_cache
            return {**resultado_cache, "fuente": "cache"}

        # Verificar límite de consultas
        if self.consultas_realizadas >= self.max_consultas_hora:
            raise Exception(f"Límite de {self.max_consultas_hora} consultas/hora alcanzado")

        print(f"[DEBUG GeminiCorrector] Enviando a Gemini API...")

        # Procesar con Gemini
        try:
            resultado = self._procesar_con_gemini_personalizado(texto, prompt_personalizado, idioma)

            # Guardar en cache
            self._guardar_cache(hash_contenido, resultado)
            self.cache_memoria[hash_contenido] = resultado
            self.consultas_realizadas += 1

            return {**resultado, "fuente": "gemini"}

        except Exception as e:
            raise Exception(f"Error procesando con Gemini: {e}")

    def _procesar_con_gemini_personalizado(self, texto: str, prompt_personalizado: str, idioma: str) -> dict:
        """Procesa texto con Gemini usando prompt personalizado"""

        prompt = self._crear_prompt_personalizado(texto, prompt_personalizado, idioma)

        try:
            # Usar Gemini 2.5 Flash con nueva API
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Algo más de creatividad para tareas variadas
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=2048,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )

            # Obtener respuesta
            contenido_respuesta = response.text.strip()

            # Para prompts personalizados, la respuesta puede no ser JSON estructurado
            # Intentar extraer JSON primero, si falla usar texto directo
            json_valido = self._extraer_json_robusto(contenido_respuesta)

            if json_valido:
                # Respuesta estructurada (correcciones)
                datos = json.loads(json_valido)
                texto_procesado = self._aplicar_correcciones(texto, datos.get("errores", []))

                return {
                    "texto_corregido": texto_procesado,
                    "errores_encontrados": datos.get("errores", []),
                    "cambios_aplicados": len(datos.get("errores", [])),
                    "comentarios_ia": datos.get("comentarios", "")
                }
            else:
                # Respuesta de texto libre (traducciones, resúmenes, etc.)
                return {
                    "texto_corregido": contenido_respuesta,
                    "errores_encontrados": [],
                    "cambios_aplicados": 1,  # Indica que hubo transformación
                    "comentarios_ia": f"Procesado con prompt: {prompt_personalizado[:50]}..."
                }

        except json.JSONDecodeError:
            # Si hay error JSON pero tenemos contenido, usarlo como respuesta directa
            if contenido_respuesta:
                return {
                    "texto_corregido": contenido_respuesta,
                    "errores_encontrados": [],
                    "cambios_aplicados": 1,
                    "comentarios_ia": "Respuesta procesada como texto libre"
                }
            else:
                raise Exception("Respuesta vacía de Gemini")
        except Exception as e:
            raise Exception(f"Error llamando a Gemini: {e}")

    def _crear_prompt_personalizado(self, texto: str, prompt_personalizado: str, idioma: str) -> str:
        """Crea un prompt personalizado para diferentes tipos de procesamiento"""

        # Determinar si es una tarea de corrección estructurada o procesamiento libre
        es_correccion = any(palabra in prompt_personalizado.lower() for palabra in
                           ['corr', 'ortogr', 'gramática', 'errores'])

        if es_correccion:
            # Formato estructurado para correcciones
            return f"""TAREA: {prompt_personalizado} en {idioma}

REGLAS:
1. Mantener el significado original
2. Ser preciso y conservador
3. Documentar cambios realizados

FORMATO DE RESPUESTA: JSON válido sin markdown.

TEXTO A PROCESAR:
{texto}

RESPUESTA JSON:
{{"errores":[{{"original":"texto_original","corregido":"texto_corregido","tipo":"tipo_cambio","razon":"explicación"}}],"comentarios":"resumen_cambios"}}"""
        else:
            # Formato libre para otras tareas
            return f"""TAREA: {prompt_personalizado}

IDIOMA: {idioma}

INSTRUCCIONES:
- Sigue exactamente la tarea solicitada
- Mantén la calidad y precisión
- Responde solo con el resultado final

TEXTO A PROCESAR:
{texto}

RESPUESTA:"""


def extraer_texto_html(html_content: str) -> str:
    """Extrae texto limpio SOLO del body del HTML/XHTML para corrección"""
    import re  # Asegurar que re está disponible siempre

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Buscar solo el contenido del body
        body = soup.find('body')
        if body is None:
            # Si no hay body, buscar div principal o usar todo pero sin head
            head = soup.find('head')
            if head:
                head.decompose()
            body = soup

        # Remover elementos no-texto del body
        for elemento in body(['script', 'style', 'meta', 'link', 'title']):
            elemento.decompose()

        # Extraer solo texto visible del body
        texto_limpio = body.get_text(separator=' ', strip=True)

        # Limpiar espacios múltiples
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

        return texto_limpio.strip()

    except ImportError:
        # Fallback sin BeautifulSoup - extraer solo body
        import re

        # Buscar content entre <body> y </body>
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            contenido = body_match.group(1)
        else:
            # Si no hay body tags, usar todo pero sin head
            head_match = re.search(r'<head[^>]*>.*?</head>', html_content, re.DOTALL | re.IGNORECASE)
            if head_match:
                contenido = html_content.replace(head_match.group(0), '')
            else:
                contenido = html_content

        # Remover tags HTML básicos
        texto = re.sub(r'<[^>]+>', ' ', contenido)
        # Limpiar espacios
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar con tu API key de Gemini
    api_key = "TU_API_KEY_AQUI"

    corrector = GeminiCorrector(api_key)

    texto_ejemplo = """
    Hola, este es un texot con algunos herrores de hortografia.
    Tambien tiene falats de puntuacion y algunnos errores gramaticales.
    """

    try:
        resultado = corrector.corregir_texto(texto_ejemplo)
        print("Texto corregido:")
        print(resultado["texto_corregido"])
        print(f"\nErrores encontrados: {resultado['cambios_aplicados']}")
        print(f"Fuente: {resultado['fuente']}")

    except Exception as e:
        print(f"Error: {e}")