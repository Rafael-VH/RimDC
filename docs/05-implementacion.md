# Implementación del plan: qué se hizo

> **Para qué existe este archivo**: el plan dice qué arreglar. Este dice qué se
> arregló de verdad, con qué evidencia, y qué se encontró en el camino.
> La próxima sesión que abra el repo debería poder responder "en qué estado está
> esto" sin leer ocho commits.

**Rama**: `main` · **Plan**: [`04-plan-de-arreglo.md`](04-plan-de-arreglo.md) ·
**Auditoría**: [`03-auditoria.md`](03-auditoria.md) · **Fecha**: 2026-09-28

---

## TL;DR

| | |
|---|---|
| Hallazgos cerrados | **24 de 28** |
| A medio cerrar | 2 (M6, M7) |
| Sin implementar, por decisión de producto | 2 (M1, B4) |
| Commits | 10, uno por fase más documentación |
| Tests del bot | 25, verdes |
| Build del mod | 0 warnings, 0 errores |
| **Sin verificar** | **todo lo que necesita el juego corriendo** |

La línea honesta: **el código compila y la lógica está probada aislada, pero
nada de esto se ha visto funcionar dentro de RimWorld.** Hay una lista de
verificación en [la sección final](#qué-no-se-verificó-y-por-qué-importa).

---

## Los commits

| Commit | Fase | Qué resuelve |
|--------|------|--------------|
| `bf74176` | 0 | Andamiaje: harness pytest, seams, 7 tests **en rojo** contra el código viejo |
| `7244a9d` | 1 | 12 hallazgos del bot. `send_request` pasa a ser async de verdad |
| `f05ac4b` | 6 | Build portable fuera de Linux, `.env.example`, docs de comandos |
| `806ce28` | 2 | 8 fixes de crash y silencios en el mod |
| `a5e60fc` | 5 | JSON válido bajo culturas con coma decimal |
| `412631b` | 3 | Token compartido en el puerto HTTP |
| `3d1f691` | — | La auditoría apuntaba a un SHA que ya no existe |
| `22edaae` | — | Checklist de runtime y el bug diferido, anotados en el plan |
| `24fc8c7` | — | Informe de implementación: qué se hizo, con qué evidencia, qué se encontró |
| `ce39cc6` | — | `/fastfetch` pedía el mismo campo dos veces en el camino de error |

---

## Estado de los 28 hallazgos

### Fase 1 — el bot (12, `7244a9d`)

Todos con test que falla antes del fix y pasa después.

| ID | Hallazgo | Qué se hizo |
|----|----------|-------------|
| A1 | El bot nunca leía la respuesta del mod | `send_request` devuelve el texto real; los 16 handlers lo muestran |
| A2 | El mapping se escribía antes del éxito | Se persiste solo tras confirmación del mod |
| A3 | Truncado después del dedup | `"Alexandria"` y `"Alexandr"` colisionaban; ahora trunca antes de comparar |
| C2 | Typo `resppobresonse` | Smoke test parametrizado sobre los 16 handlers |
| M3 | Dict mutable por defecto | `params: dict \| None = None`, copia fresca por llamada |
| B2 | Nickname sin validar | Validación antes de tocar disco |
| N1 | `characters/` nunca se creaba | N1 **lo causé yo** al sanear el repo en una fase anterior |
| N2 | `fastfetch` bloqueaba el event loop | Las 3 llamadas pasan por `asyncio.to_thread` |
| N3 | Rutas relativas al CWD | `DATA_DIR` anclado a `Path(__file__).parent` |
| N4 | URL del server hardcodeada | Sale de `.env` con default |
| N5 | `GUILD` vacío → `Object(0)` | Falla al arrancar con un mensaje que dice qué hacer |
| N6 | `/create_character` mentía | Responde el motivo real |

### Fase 2 — el mod: crashes (8, `806ce28`)

| ID | Hallazgo | Qué se hizo |
|----|----------|-------------|
| C3 | `/arrest` sin null-check | Guard de null/muerto, igual que sus cinco hermanos |
| A4 | `CloseServer` sin null-checks | `listener?.Close()` |
| M2 | `Thread.Abort()` frágil | **Eliminado.** Cerrar el listener ya desbloquea `GetContext()` |
| M4 | `List` sin lock | `ConcurrentQueue` + `TryDequeue` |
| M5 | `catch` vacío | `HttpListenerException` específico; el resto se loguea |
| B1 | `ex.Message` sin stack trace | Se loguea la excepción completa |
| B3 | `FinalizeInit()` vacío | Eliminado (junto con un `ExposeData()` vacío) |
| B5 | Log engañoso | No dice "creado" si el pawn no se creó |

### Fase 3 — el canal seguro (1, `412631b`)

| ID | Hallazgo | Qué se hizo |
|----|----------|-------------|
| C1 | Listener sin autenticación | `Authorization: Bearer $RIMDC_TOKEN`, 401 antes de encolar |

### Fase 5 — JSON (1, `a5e60fc`)

| ID | Hallazgo | Qué se hizo |
|----|----------|-------------|
| A5 | JSON con interpolación | `JsonNumber` (InvariantCulture) + `JsonString` (escaping) |

### Fase 6 — deriva y build (2 de 4, `f05ac4b`)

| ID | Hallazgo | Estado |
|----|----------|--------|
| M8 | Rutas Steam hardcodeadas | **Cerrado.** `RimWorldManagedDir` con error accionable |
| B6 | Sin `.env.example` | **Cerrado.** Plantilla creada |
| M6 | El server solo existe con partida cargada | **A medio.** Documentado; la alternativa (moverlo a `Root_Entry`) sigue sin decidir |
| M7 | Mapa de comandos desincronizado | **A medio.** Documentados los 2 comandos que nunca llegan al mod; la lista completa de xenotipos sin verificar sigue abierta |

---

## Lo que se encontró implementando el plan

Esta es la parte que no estaba en la auditoría, y es la razón de que el plan
haya cresido. Aparece acá y no en `03-auditoria.md` porque la auditoría describe
el código **antes** de tocarlo.

### 1. El bug de cultura estaba activo en tu máquina

No era un hallazgo teórico de "qué pasa si el usuario tiene otra locale". Con
`es-BO`, el mod emitía `{"mood":1,"rest":0,5,"food":0,75}` y `json.loads` lo
rechazaba. **`/fastfetch` ya estaba roto en tu PC antes de este trabajo.**

La lección que generaliza: `0,75` no es un número JSON. Cualquier float
interpolado a mano en cualquier idioma con coma decimal rompe el endpoint. Por
eso los helpers `JsonNumber`/`JsonString` viven en un solo lugar.

### 2. `gethealth` estaba roto por dos vías, no una

La auditoría señaló la coma decimal. Al arreglarlo apareció lo segundo: los
labels de hediffs y partes se interpolaban **sin escapar**. Un label con comilla
—y RimWorld tiene varios, más cualquier mod que agregue los suyos— rompía el
documento igual. El fix de cultura solo no alcanzaba.

### 3. `Thread.Abort()` no existe en .NET Core

El plan lo llamaba "frágil". Es peor: **no compila**. La solución obvia
(quitar el `Abort`) no alcanza sola, porque el hilo queda estacionado en
`GetContext()` para siempre. Hace falta cerrar el listener **y** atrapar el
`HttpListenerException` que eso dispara, si no el bucle `while` se repite.

### 4. `pendingCharacters` era una carrera real

`List<string>` escrita por el hilo HTTP y enumerada por el hilo del juego en el
próximo `Page_ConfigureStartingPawns`. La auditoría lo marcan como "fragilidad"
en el peor sentido de la palabra: no es un code smell, es un
`InvalidOperationException` esperando el momento exacto. `ConcurrentQueue` +
`TryDequeue` lo elimina y de paso quita el `Clear()` final, que era la otra
ventana.

### 5. El "fix" de `FinalizeInit()` era peor que el código

B3 decía "override vacío". La solución literal —agregar una guarda o comentario
que justifique que está vacío— habría sido ruido. Lo correcto era borrarlo. Lo
mismo con un `ExposeData()` vacío que apareció al leer el contexto.

### 6. El token no podía ir en `ModSettings`

La decisión obvia para un mod de RimWorld es una pantalla de settings. Es
imposible acá: **RimWorld no puede leer el `.env` del bot y el bot no puede leer
un ajuste del mod.** No hay canal común. Termina siendo una variable de entorno
que ambos procesos ven.

Consecuencia: el valor se configura en **dos lugares** (el `.env` del bot y el
entorno de Windows). Es el costo de esa decisión, y es el motivo por el que el
mod tiene que **fallar cerrado**.

### 7. "Fail closed" fue una decisión, no un default

La versión ingenua de C1 es: si no hay token, seguir como antes. Eso
**reintroduce el agujero que el commit está cerrando**. Si `RIMDC_TOKEN` no está,
el mod no abre el puerto y lo dice en el log. Un usuario que configuró mal ve
"el mod no arrancó" en vez de un bot que anda con un puerto abierto.

### 8. `README.md` mentía sobre cómo usar el mod

No estaba en la auditoría. El README raíz describía endpoints sin mencionar
autenticación, y los ejemplos de `curl` de esa sección dejarían de funcionar sin
token. Se actualizó en `412631b`.

### 9. Un finding del plan resultó ser autoinfligido

N1 (`characters/` nunca se crea) lo causé yo: el fix de `.gitignore` de una fase
anterior quitó el directorio del repo, y antes su existencia en el árbol tapaba
el bug. Vale la pena dejarlo anotado porque explica por qué la auditoría lo
reportó como `FileNotFoundError` y no como algo más sutil.

---

## Cómo se verificó

| Qué | Cómo | Resultado |
|-----|------|-----------|
| Bot: contrato y datos | `pytest` | 25 passed |
| Mod: compila | `dotnet build -c Release /p:RimWorldManagedDir="..."` | 0 warnings, 0 errores |
| A5 (cultura) | Consola temporal bajo `es-BO`, parseando con `System.Text.Json` | JSON viejo rechazado, nuevo válido |
| C1 (auth) | Consola temporal, 15 casos de header + gate | 15/15 |
| C1 (extremo a extremo) | Fixture HTTP real en pytest | Header `Bearer` llega al servidor |

### La técnica: probar C# sin abrir RimWorld

Dos de las verificaciones no son tests del repo — son consolas temporales en
`%TEMP%` que **replican la función** y la ejercitan. Sirvieron porque:

- `IsAuthorized` es parsing de strings. Un bug ahí te deja afuera del mod o,
  peor, te deja entrar. Ninguno de los dos outcomes se ven en el compilador.
- `InvariantCulture` es una garantía de la BCL. Lo que hay que probar es que
  **el código la usa**, no que la BCL funcione.

Compilan contra .NET pelado, sin assemblies de RimWorld, en segundos. Cuando
exista un proyecto de tests C# (fase 7), esto se convierte en tests reales; hasta
entonces es evidencia de que el fix hace lo que dice.

**No** son sustitutos de jugar. Solo cubren la lógica que se puede ejercitar sin
el juego.

---

## Qué no se verificó, y por qué importa

RimWorld abierto, partida cargada. Está en el plan como checklist; va acá
porque es la limitación real de este trabajo.

- [ ] El mod lee `RIMDC_TOKEN` y abre el puerto; sin la variable no lo abre
- [ ] `curl` sin header → 401; con header → ejecuta
- [ ] `/fastfetch` devuelve stats legibles
- [ ] `/create_character` con Biotech activo **e** inactivo
- [ ] Ida y vuelta del menú principal no rompe el listener

Lo que más me preocupa de esta lista: **C1 y A5 dependen de que el proceso de
RimWorld herede la variable de entorno.** `setx` la escribe para procesos
**futuros**. Si RimWorld ya estaba abierto, la tiene que cerrar y volver a
abrir. El código está bien; el despliegue es lo que puede fallar.

---

## Deuda que se dejó conscientemente

Nada de esto es un olvido: son decisiones o límites, con el motivo escrito.

| Ítem | Por qué quedó así |
|------|-------------------|
| **M1** — I/O bloqueante en el main thread | Fase 4, la más grande. No se tocó sin medir |
| **B4** — xenotipo sin validar | `AllDefs` sin filtrar incluye ancient y gene-only. Necesita un criterio de producto tuyo |
| **M7** — `/generate_random_race` | Devuelve un nombre al azar de una lista de 41, sin relación con los defs reales. ¿Conectar o borrar? |
| **M6** — server solo con partida cargada | Mitigado con docs. La alternativa es mover el arranque a `Root_Entry` |
| **A5 completo** — `System.Text.Json` | El fix mínimo cierra cultura y escaping. El serializer completo cerraría **A4** (cero interpolación) y **M7** de raíz. Vale cuando el proyecto cresca |
| **Fase 7** — C# testeable | Necesita refactor previo |

### El bug de objetivos enemigos

`kill`, `incapacite`, `rescue`, `shoot` y `arrest` resuelven su objetivo con
`Find.CurrentMap.mapPawns.FreeColonists`. **Solo pueden alcanzar colonos.** El
README los documenta con `data=enemy_name`, que nunca va a coincidir.

**Decidido: no se toca hasta tener runtime.** No es un fix de crash, es un
cambio de comportamiento, y el criterio correcto depende de si querés que
sirvan para colonos, para enemigos, o para ambos con un selector.

Nota sobre el costo de la decisión: el fix es una línea —cambiar
`FreeColonists` por `Pawns`— pero cambiaría el comportamiento de cinco acciones
sin poder probarlas. Eso es exactamente el escenario donde un cambio "obvio" se
convierte en un bug nuevo.

---

## Un bug encontrado y corregido durante la Fase 5

`/fastfetch` hacía **dos** requests por campo en el camino de error: uno dentro
de `json.loads` y otro dentro de `describe` cuando el primero fallaba.

```python
# antes
stats[field] = json.loads(await send_request(field, {"pawn": pawn}))
except ValueError:
    describe(await send_request(field, {"pawn": pawn}))   # segundo request
```

No estaba en el plan. Lo detecté leyendo el código durante la Fase 5 y lo dejé
anotado sin tocar, para no ampliar alcance a mitad de una fase. Se corrigió
después (`ce39cc6`), con un test que falla contra el código viejo.

Lo que lo hace peor que un request de más: el mensaje que veía el usuario venía
de una **segunda llamada**, que podía dar un resultado distinto al que falló el
parseo. No era solo lentitud, era inconsistencia.

Y es justamente el camino que más se usa: el error es lo que pasa cuando el
pawn está muerto o el puerto está cerrado.

### La disciplina del test rojo

El test recorre ese camino a propósito —el fixture responde `sent`, que no es
JSON— y afirma que llegó **exactamente un** request. Lo verifiqué revirtiendo el
fix: contra el código viejo falla mostrando dos requests idénticos a `/skills`.

Un test que no falla contra el bug que dice cubrir no es un test, es decoración.

---

## Cómo reproducir la verificación

```sh
# Tests del bot (24, ~19s)
cd bot
venv\Scripts\python.exe -m pytest -q

# Build del mod
dotnet build -c Release /p:RimWorldManagedDir="E:\SteamLibrary\steamapps\common\RimWorld\RimWorldWin64_Data\Managed"

# Verificar que el token cierra el puerto
setx RIMDC_TOKEN "algo-largo-y-aleatorio"   # reiniciar RimWorld después
curl -i localhost:9891/eat?pawn=Ana          # 401 sin header
curl -i -H "Authorization: Bearer $RIMDC_TOKEN" localhost:9891/eat?pawn=Ana
```

> **Trampa conocida**: tu config de permisos tiene `*.env.*` en `deny`, que pisa
> el `allow` más específico de `.env.example`. Por eso la plantilla todavía no
> tiene la línea `RIMDC_TOKEN` y hay que agregarla a mano. Con el patrón
> `*.env` en vez de `*.env.*` se resuelve.

---

## Una reflexión sobre el orden

Que el plan pusiera "Fase 0 es tests" resultó ser la decisión correcta y por
razones que no estaban previstas. En la Fase 0 escribí los tests **antes** de
arreglar nada, y tres de ellos fallaron de formas que la auditoría no había
previsto — uno porque el bug interactuaba con el `.gitignore` que yo mismo había
tocado (N1).

Es tentador arrancar por los fixes grandes. Los tests primero: es lo que
convierte "esto debería andar" en "esto anda, y te lo demuestro".
