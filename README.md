# Prompt Regression Lab 🧪

Detecta qué requisitos deja de cumplir una respuesta de IA al cambiar tu prompt, modelo o recuperación de contexto. Compara **respuestas ya guardadas** con reglas explícitas y genera un informe JSON por caso.

Creado el **22 de octubre de 2026**. Python 3.10+; **sin dependencias externas ni llamadas a APIs**.

## El problema que resuelve

Dos versiones pueden aprobar 2 de 3 casos y, aun así, la nueva haber perdido una cita que antes incluía. La demo reproduce ese escenario: mejora el formato JSON, pero rompe la cita del caso `lore-source`. El informe identifica ambas cosas.

## Probar

```bash
git clone https://github.com/alvaroalcalaa/prompt-regression-lab.git
cd prompt-regression-lab
python evaluate.py examples/suite.json examples/candidate.json --baseline examples/baseline.json --out report.json
```

**Ese comando termina con código 1 de forma intencional:** la respuesta candidata incumple una regla. La salida muestra:

- Baseline: 2/3 casos aprobados.
- Candidata: 2/3 casos aprobados.
- Regresión: `lore-source` (falta `[1]`).
- Mejora: `structured-answer` (ahora devuelve JSON).

Para ejecutar un ejemplo que pasa todos los casos:

```bash
python evaluate.py examples/suite.json examples/passing.json
python -m unittest -v
```

En algunos equipos utiliza `python3`. La carpeta de salida debe existir.

## Crear tus casos

La suite es una lista JSON. Cada caso necesita exactamente `id`, `prompt` y `rules`:

```json
[
  {
    "id": "respuesta-con-fuente",
    "prompt": "Responde con la fuente [1].",
    "rules": {
      "contains_all": ["[1]"],
      "forbidden_any": ["fuente inventada"],
      "max_chars": 300
    }
  }
]
```

Las respuestas son un objeto JSON cuyas claves coinciden con los IDs y cuyos valores son **textos**, incluso cuando el texto contiene JSON:

```json
{
  "respuesta-con-fuente": "La respuesta está documentada. [1]"
}
```

`prompt` sirve de documentación del caso: esta herramienta **no ejecuta el prompt**. Guarda las salidas de tu propio flujo y evalúalas aquí.

## Reglas soportadas

| Regla | Qué comprueba |
|---|---|
| `contains_all` | Todas las subcadenas aparecen, ignorando mayúsculas con Unicode casefold |
| `forbidden_any` | Ninguna subcadena de la lista aparece |
| `max_chars` | Longitud máxima del texto bruto en caracteres Python |
| `json_keys` | JSON estricto de nivel superior tipo objeto, con todas las claves indicadas |

Una regla de lista debe tener al menos un texto no vacío. Un caso aprueba si cumple todas sus reglas. Una respuesta ausente **suspende** y permanece en el denominador. IDs de respuesta desconocidos y reglas mal escritas provocan error en lugar de ignorarse.

El analizador rechaza claves JSON duplicadas y constantes no estándar como `NaN`. No acepta bloques Markdown como si fueran JSON. `json_keys` permite claves adicionales y no valida los tipos de sus valores.

## Comparación y códigos de salida

La baseline y la candidata se evalúan contra **la misma suite actual**. Regresión = caso antes aprobado que ahora falla; mejora = caso antes fallido que ahora aprueba. Cambios internos entre dos casos fallidos aparecen en el detalle de reglas, pero no se etiquetan como regresiones.

| Código | Significado |
|---|---|
| 0 | Todos los casos candidatos cumplen las reglas |
| 1 | Uno o más casos candidatos fallan |
| 2 | Error de entrada, configuración o escritura |

El código 1 se devuelve también sin baseline. Esto permite usarlo en una integración continua como una prueba normal. `--out` evita sobrescribir entradas y exporta los detalles; el JSON también sale por consola.

## Límites honestos

Son comprobaciones **sintácticas**, no una evaluación semántica de la inteligencia del modelo. Una cita `[1]` presente no demuestra que respalde la afirmación. Una frase prohibida puede aparecer negada o citada y aun así fallar. Una respuesta correcta con sinónimos puede fallar `contains_all`; no se normalizan acentos ni espacios.

El porcentaje mide **casos aprobados**, no exactitud factual, calidad global, seguridad ni resistencia a prompt injection. Los ejemplos son respuestas ficticias redactadas a mano, no resultados reales de un modelo. El programa carga los archivos en memoria y está pensado para suites pequeñas y archivos locales de confianza.

## Pruebas y extensiones

Las pruebas cubren regresiones con igual puntuación global, datos ausentes, reglas inválidas, Unicode, restricciones de formato, límites de longitud y ejecución real del CLI con códigos de salida.

Puedes añadir un adaptador que capture respuestas de tu proveedor, métricas de coste/latencia o validación de citas contra documentos. Mantén esas comprobaciones diferenciadas de las reglas de texto.
