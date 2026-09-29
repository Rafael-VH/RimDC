# Auditoría RimDC

Auditoría completa del repo, hecha el 2026-09-28 sobre `C:\Users\rafae\Documents\GitHub\RimDC`
(commit `bac16f4` — "First commit").

| Documento | Para qué |
|-----------|----------|
| [01-que-es-este-proyecto.md](01-que-es-este-proyecto.md) | Entender qué hace el proyecto, de punta a punta |
| [02-arquitectura.md](02-arquitectura.md) | Cómo está partido, qué habla con qué, y por qué |
| [03-auditoria.md](03-auditoria.md) | Hallazgos con severidad, archivo y línea |
| [diagramas/PLAN.md](diagramas/PLAN.md) | Qué diagramas faltan y para qué sirve cada uno |

## Resumen ejecutivo

RimDC son **dos procesos que se hablan por HTTP en localhost**: un mod de RimWorld escrito en C#
y un bot de Discord escrito en Python. El mod expone un `HttpListener` en el puerto 9891 y ejecuta
acciones sobre los colonists del jugador. El bot traduce slash commands de Discord a GETs contra
ese puerto.

El diseño general es correcto y la separación de responsabilidades es limpia. **Los problemas
están en los bordes**: el canal no tiene autenticación, el bot nunca lee las respuestas del
servidor, y hay dos crashes alcanzables desde un comando de Discord.

946 líneas de código, cero tests, cero CI.

## Hallazgos por severidad

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| Crítico | 3 | C1, C2, C3 |
| Alto | 5 | A1–A5 |
| Medio | 8 | M1–M8 |
| Bajo | 6 | B1–B6 |

Detalle y evidencia en [03-auditoria.md](03-auditoria.md).

## Lo primero que hay que arreglar

1. **C1** — el listener no autentica a nadie. Cualquier proceso local mueve cualquier colonist.
2. **C2** — `interaction.resppobresonse` (typo) rompe el comando `equip_weapon` siempre.
3. **C3** — `/arrest` con un objetivo inexistente tira `NullReferenceException`.

## Metodología

- Lectura completa de las 946 líneas de código (604 C# + 342 Python). Sin muestreo.
- `git ls-files` para inventario de archivos y detección de secretos trackeados.
- Inspección de la configuración de build (`.csproj`), metadatos del mod (`About.xml`) y los
  requirements del bot.
- Búsqueda de tests y workflows de CI: **ninguno encontrado**.
- Los diagramas no se authoring acá: `diagramas/PLAN.md` define el estándar y lo que falta.
