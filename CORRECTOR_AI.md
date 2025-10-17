# GutenAI - Corrector Ortográfico y Gramatical con IA

## 🧠 **Características del Corrector**

GutenAI integra **Google Gemini 2.5 Flash** para corrección avanzada de texto que va más allá de la simple ortografía:

### **Capacidades**
- ✅ **Corrección ortográfica**: Detecta y corrige errores de escritura
- ✅ **Corrección gramatical**: Identifica problemas de gramática y sintaxis
- ✅ **Análisis contextual**: Comprende el contexto para sugerencias precisas
- ✅ **Preservación de estilo**: Mantiene el tono y voz del autor original
- ✅ **Multiidioma**: Soporte para español, inglés, francés, alemán, italiano, portugués

### **Ventajas sobre correctores tradicionales**
- 🎯 **Inteligencia contextual**: No solo reglas, sino comprensión semántica
- 🔄 **Consistencia garantizada**: Sistema de caché y validación
- ⚡ **Eficiencia**: 15 consultas/hora suficientes para revisión por capítulos
- 🛡️ **Validación**: Rechaza cambios excesivos o inadecuados

## 🚀 **Instalación y Configuración**

### **1. Dependencias Requeridas**
```bash
# En tu entorno virtual de GutenAI
pip install google-genai beautifulsoup4
```

### **2. Obtener API Key de Gemini**
1. Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Inicia sesión con tu cuenta de Google
3. Crea una nueva API key (gratuita)
4. Copia la clave generada

### **3. Configurar en GutenAI**
1. Abre GutenAI
2. Ve a **Menú → Preferencias** (o `Ctrl+Shift+P`)
3. En la pestaña **"Inteligencia Artificial"**:
   - ✅ Habilita "Corrección con IA"
   - 📝 Pega tu API Key de Gemini
   - 🌍 Selecciona idioma de corrección (español por defecto)
4. Guarda los cambios

## 📝 **Cómo Usar el Corrector**

### **Método 1: Menú Contextual**
1. Selecciona texto en el editor (o todo el documento)
2. **Clic derecho** → **"Corregir con IA"**
3. Espera el análisis de Gemini
4. Revisa y aplica correcciones

### **Método 2: Atajo de Teclado**
1. Con texto abierto en el editor
2. Presiona **`Ctrl+Shift+C`**
3. Modal de corrección se abre automáticamente

### **Método 3: Menú Principal**
1. **Menú → Herramientas → Corrección con IA** (si implementado)

## 🔧 **Flujo de Corrección**

### **Proceso Paso a Paso**

1. **📖 Extracción de Texto**
   - El sistema extrae texto limpio del HTML/XHTML
   - Preserva estructura de párrafos
   - Ignora etiquetas de markup

2. **🤖 Análisis con Gemini**
   - Envía texto a Gemini 1.5 con prompt especializado
   - Recibe correcciones en formato JSON estructurado
   - Aplica validaciones de calidad

3. **👀 Revisión Visual**
   - Modal muestra texto original vs corregido
   - Lista errores encontrados con explicaciones
   - Permite edición manual adicional

4. **✅ Aplicación de Cambios**
   - Integra texto corregido de vuelta al HTML
   - Preserva estructura y etiquetas
   - Auto-guarda los cambios

### **Modal de Corrección**

```
┌─────────────────────────────────────────────────────────┐
│ GutenAI - Corrector Inteligente                     [X] │
├─────────────────────────────────────────────────────────┤
│ Consultas: 3/15 | Cache: 12 entradas    [Corregir IA] │
├─────────────────────┬───────────────────────────────────┤
│ Texto Original      │ Texto Corregido                   │
│                     │                                   │
│ Hola, este es un    │ Hola, este es un texto con        │
│ texot con algunos   │ algunos errores de ortografía.    │
│ herrores de         │ También tiene faltas de           │
│ hortografia.        │ puntuación y algunos errores      │
│ Tambien tiene...    │ gramaticales.                     │
├─────────────────────┴───────────────────────────────────┤
│ Errores Encontrados:                                    │
│ • texot → texto (Ortografía)                           │
│ • herrores → errores (Ortografía)                      │
│ • hortografia → ortografía (Ortografía)                │
│ • Tambien → También (Puntuación: falta tilde)          │
├─────────────────────────────────────────────────────────┤
│                               [Cancelar] [Aplicar ✓]   │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ **Configuración Avanzada**

### **Parámetros del Corrector**
- **Temperature**: 0.1 (muy conservador para consistencia)
- **Validación de similitud**: >80% (rechaza cambios excesivos)
- **Validación de longitud**: ±30% máximo
- **Cache automático**: Evita consultas repetidas

### **Límites y Cuotas**
- **API Gratuita**: 15 consultas por hora
- **Tamaño máximo**: ~2000 palabras por consulta
- **Cache persistente**: Ilimitado en disco local

### **Idiomas Soportados**
- 🇪🇸 **Español** (es) - Por defecto
- 🇺🇸 **English** (en)
- 🇫🇷 **Français** (fr)
- 🇩🇪 **Deutsch** (de)
- 🇮🇹 **Italiano** (it)
- 🇵🇹 **Português** (pt)

## 🛡️ **Sistema de Validación**

### **Protecciones Incluidas**
1. **Validación de cambios**: Rechaza modificaciones excesivas
2. **Preservación de estilo**: Mantiene tono del autor
3. **Cache inteligente**: Evita inconsistencias
4. **Fallback seguro**: Si algo falla, conserva texto original

### **Archivo de Cache**
```
~/.config/gutenai/cache/correcciones/
├── a1b2c3d4.json  # Hash de texto → corrección
├── e5f6g7h8.json
└── ...
```

## 🚨 **Solución de Problemas**

### **Error: "API key no configurada"**
- Ve a Preferencias → IA → Configura tu API key de Gemini

### **Error: "Límite de consultas alcanzado"**
- Espera 1 hora para que se resetee el contador
- O usa cache de correcciones anteriores

### **Error: "Conexión fallida"**
- Verifica conexión a internet
- Comprueba que la API key es válida

### **Respuestas inconsistentes**
- El sistema incluye validación automática
- Si detecta cambios excesivos, los rechaza
- Usa cache para evitar variaciones

### **Texto mal integrado al HTML**
- Reporta el problema (es un área de mejora)
- Por ahora, revisa manualmente después de aplicar

## 📊 **Estadísticas de Uso**

El corrector rastrea:
- Consultas realizadas en la sesión actual
- Consultas restantes en la hora
- Entradas en cache
- Errores corregidos por tipo

## 🔮 **Desarrollos Futuros**

### **Mejoras Planificadas**
- 🔧 **Integración HTML mejorada**: Mejor preservación de markup
- 📚 **Corrección por párrafos**: Para textos muy largos
- 🎯 **Corrección selectiva**: Solo ortografía, solo gramática, etc.
- 📈 **Métricas avanzadas**: Estadísticas de calidad de texto
- 🤖 **Otros modelos IA**: Claude, GPT-4, etc.

### **Funciones Experimentales**
- ✨ **Mejora de estilo**: Sugerencias de reformulación
- 📖 **Análisis de coherencia**: Detectar problemas narrativos
- 🎯 **Corrección específica por género**: Novela, ensayo, técnico

---

## 💡 **Consejos de Uso**

1. **Correge por capítulos**: Divide textos largos para mejor precisión
2. **Revisa siempre**: La IA es muy buena, pero no perfecta
3. **Usa cache**: Los textos similares se corrigen instantáneamente
4. **Configura idioma**: Asegúrate de seleccionar el idioma correcto
5. **Backup regular**: Exporta EPUBs corregidos como respaldo

¡Disfruta de la corrección inteligente en GutenAI! 🚀