#!/usr/bin/env python3
"""
Script de prueba para las funciones de estadísticas
"""
import re
from bs4 import BeautifulSoup

def extract_text_from_html(html_content: str) -> str:
    """Extrae texto limpio del HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Buscar solo el contenido del body
    body = soup.find('body')
    if body is None:
        body = soup

    # Remover elementos no-texto
    for elemento in body(['script', 'style', 'meta', 'link', 'title', 'head']):
        elemento.decompose()

    # Extraer texto
    texto = body.get_text(separator=' ', strip=True)

    # Limpiar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)

    return texto.strip()

def count_words(text: str) -> int:
    """Cuenta palabras en el texto"""
    if not text or not text.strip():
        return 0

    words = [w for w in text.split() if w.strip()]
    return len(words)

# HTML de prueba
test_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Chapter</title>
    <style>body { color: black; }</style>
</head>
<body>
    <h1>Capítulo 1</h1>
    <p>Este es un párrafo de prueba con varias palabras.</p>
    <p>Este es otro párrafo con más contenido para contar.</p>
    <div>
        <p>Y un tercer párrafo dentro de un div.</p>
    </div>
</body>
</html>
"""

print("=== PRUEBA DE EXTRACCIÓN DE TEXTO ===\n")
print(f"HTML original: {len(test_html)} caracteres\n")

texto = extract_text_from_html(test_html)
print(f"Texto extraído: {len(texto)} caracteres")
print(f"Texto: {texto}\n")

palabras = count_words(texto)
print(f"Palabras contadas: {palabras}")
print(f"Esperado: ~20 palabras")

# Verificar
if palabras > 15:
    print("\n✅ PRUEBA EXITOSA")
else:
    print("\n❌ PRUEBA FALLIDA")
