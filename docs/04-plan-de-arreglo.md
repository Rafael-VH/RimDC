# Plan de arreglo

Derivado de `03-auditoria.md`. Cubre los 22 hallazgos de la auditoría más 6 nuevos que aparecieron
al releer el código durante la planificación.

Fecha: 2026-09-28. Commit base: `8eef917`.

---

## La estrategia en tres líneas

1. **Tests antes que fixes.** Hay 0 tests sobre 946 líneas. Sin tests, cada arreglo es un "ojalá".
2. **Agrupar por costo de verificación, no por severidad.** El Python se testea en segundos; el C#
   no se puede testear sin arrancar RimWorld. Eso define el cronograma.
3. **Un commit por fase.** Cada commit se puede revisar y revertir sin arrastrar al resto.

---

## El criterio que define el orden

El orden natural de una auditoría es por severidad: crítico, alto, medio, bajo. **Acá no sirve**,
por una razón concreta:

| Lado | Cómo se verifica | Costo real |
|------|------------------|------------|
| Python (`bot/main.py`) | `pytest` + un server HTTP falso | **segundos**, corre en CI |
| C# (`ServerComponent.cs`) | `msbuild` + arrancar RimWorld + cargar partida | **minutos**, manual |

El C# no es testeable unitariamente sin una capa de indirección sobre `Pawn`, y construir esa capa
es un refactor en sí mismo. Consecuencia práctica: **cada fix de C# cuesta una sesión de juego**.
Arreglarlos de a uno es caro; agruparlos en una sola sesión de verificación es lo barato.

De ahí salen las fases: una sola sesión de juego para todos los fixes de C#, una sola corrida de
tests para todo el bot.

---

## Hallazgos nuevos (no estaban en la auditoría)

Aparecieron al releer `bot/main.py` completo para planificar. Los marco `N`.

| ID | Hallazgo | Archivo |
|----|----------|---------|
| N1 | `bot/characters/` nunca se crea. `os.listdir("characters")` revienta con `FileNotFoundError` en `/create_character` y `/clear_characters` en una clone nueva | `main.py:235,277` |
| N2 | `fastfetch` hace 3 `requests.get` **síncronos dentro de un `async def`** → bloquea el event loop de Discord. Un request lento congela el bot entero | `main.py:298-300` |
| N3 | Rutas relativas al CWD (`"characters/..."`). Si corrés `python bot/main.py` desde la raíz, busca `./characters/` | `main.py:29,34,235` |
| N4 | `server = "http://localhost:9891/"` hardcodeado, inconsistente con el approach de `.env` para TOKEN y GUILD | `main.py:14` |
| N5 | `discord.Object(os.getenv("GUILD") or 0)` → con GUILD vacío registra los comandos contra el guild `0`, que no existe. Falla opaco | `main.py:44` |
| N6 | Si el usuario ya tiene character, `/create_character` entra al `else` y responde "Request sent" sin hacer nada | `main.py:265-268` |

**N1 lo causé yo.** El fix de `.gitignore` de esta sesión quitó `bot/characters/` del repo. Antes el
directorio existía en el árbol; ahora una clone limpia no lo tiene. Hay que crearlo en código.

---

## Fase 0 — Andamiaje de verificación

**Por qué primero**: sin tests, todo lo demás es fe. Los tests que escribas en esta fase fallan
contra el código actual — y eso *es* el reporte de bugs, ejecutable.

**Archivos**: `bot/test_main.py`, `bot/requirements-dev.txt`

| Paso | Qué |
|------|-----|
| 0.1 | `pytest` + fixture de `http.server` en un puerto libre, que devuelve lo que el test quiera |
| 0.2 | Test que prova que `request_wrapper` no muta el dict default (M3) |
| 0.3 | Test que prova que el truncado a 6 chars ocurre **antes** del chequeo de duplicados (A3) |
| 0.4 | Test que prova que un nombre >6 chars igual collide con otro que comparta los primeros 6 (A3) |
| 0.5 | Test que prova que el bot levanta con el directorio `characters/` inexistente (N1) |
| 0.6 | Test que prova que un error de conexión del server no se traga silenciosamente (A1) |

**Verificación**: `pytest` en verde los primeros 4, en rojo el 5 y el 6. Rojo es el éxito de esta
fase: acabás de convertir 3 bugs invisibles en tests rojos.

**Commit**: `test: add pytest harness with fake server fixture`

**Esfuerzo**: 1–1.5 h. **Es el que más valor devuelve por hora de todo el plan.**

---

## Fase 1 — El bot: contrato y datos

Todo en `bot/main.py`. Todo verificado por los tests de la Fase 0. Un solo commit.

El orden interno importa: **A1 va primero dentro de la fase** porque A2 depende de poder observar
si la request funcionó.

| # | ID | Qué | Por qué en este orden |
|---|----|-----|----------------------|
| 1 | N1 | `os.makedirs(..., exist_ok=True)` al arrancar | Loسببó el fix de `.gitignore` |
| 2 | C2 | `resppobresonse` → `response` | Una palabra |
| 3 | M3 | `params: dict \| None = None` | Una línea |
| 4 | N3 | `Path(__file__).parent` en vez de rutas relativas al CWD | Una línea |
| 5 | N4 | `server` desde `.env` | Una línea |
| 6 | B2 | `strip()` + rechazar espacios/nulos en el nick | 3 líneas |
| 7 | A3 | Truncar a 6 chars **antes** del chequeo de duplicados | Mover 4 líneas |
| 8 | N6 | `/create_character` con character existente: decir "ya tenés uno" | 2 líneas |
| 9 | **A1** | `send_request` devuelve la respuesta; los handlers muestran `resp.text` | **La piedra angular** |
| 10 | A2 | Escribir el archivo `characters/<id>` **después** del éxito | Depende de A1 |
| 11 | N2 | `fastfetch` a `asyncio.to_thread` | Depende de A1 |
| 12 | N5 | Fallar con mensaje claro si falta `GUILD` | 2 líneas |

**Por qué A1 es la piedra angular**: hoy el bot responde "Request sent" a todo, incluso con el juego
cerrado. Eso es lo que vuelve invisibles a C1, C3, A2 y M6. Cuando los handlers muestren la
respuesta real, de golpe tenés un canal de diagnóstico desde Discord.

**Verificación**: `pytest` en verde + arrancar el bot y usar 3 comandos con el server caído y
levantado, y ver que los mensajes difieren.

**Commit**: `fix(bot): propagate server responses and fix character creation`

**Esfuerzo**: 2–3 h.

---

## Fase 2 — El mod: fixes de crash

Todos en `ServerComponent.cs`. **Una sola sesión de juego para verificar los 8.** Son defensivos y
no cambian comportamiento esperado.

| # | ID | Qué | Líneas |
|---|----|-----|--------|
| 1 | C3 | Null-check en `case "arrest"`, copiando el guard de `kill`/`incapacite`/`rescue` | 3 |
| 2 | A4 | `serverThread?.IsAlive == true` y `listener?.IsListening == true` | 2 |
| 3 | M2 | Borrar `Thread.Abort()`. `listener.Close()` ya desbloquea el `GetContext()` | −2 |
| 4 | B3 | Borrar el `FinalizeInit()` vacío | −4 |
| 5 | M4 | `List<string>` → `ConcurrentQueue<string>` | 2 |
| 6 | M5 | `catch (Exception) {}` → `catch (HttpListenerException) { break; }` + log | 3 |
| 7 | B1 | `Log.Error(ex.Message)` → `Log.Error(ex)` para el stack trace | 1 |
| 8 | B5 | No loguear "Added new character" si `GenerateRandomPawn()` devolvió null | 3 |

**Verificación** (la sesión de juego, ~20 min):
1. `msbuild` compila sin warnings nuevos.
2. Arrancar con una partida cargada, puerto 9891 escuchando.
3. `/arrest NoExiste` → loguea el error, no crashea, y el bot muestra el mensaje.
4. Volver al menú principal → la transición de `GenScene.GoToMainMenu` no tira NRE (A4).
5. Cerrar el juego → el listener para limpio (M2, M5).

**Commit**: `fix(mod): guard against null pawns, null statics, and silent listener failures`

**Esfuerzo**: 1–1.5 h de código + 20 min de juego.

---

## Fase 3 — El canal seguro

**Depende de A1.** Si agregás auth sin que el bot lea respuestas, seguís sin ver los 401.

| ID | Qué |
|----|-----|
| C1 | Token compartido en un header, validado en `RequestListener()` antes de encolar. El bot lo manda en cada request |

**Cruza los dos archivos**: el mod valida, el bot envía. Cambia el contrato del canal, así que es un
commit que toca `ServerComponent.cs` y `main.py` juntos — no se puede partir.

**Verificación**: con el juego corriendo y el bot con el token correcto, todo funciona. Con el token
mal, cada comando muestra el rechazo. Sin header, también. Y un `curl` sin token recibe 401.

**Commit**: `feat: authenticate the local HTTP channel with a shared token`

**Esfuerzo**: 1 h. **Requiere volver a abrir el juego** → agrupalo con la Fase 2 si podés, o
aceptá el segundo viaje.

---

## Fase 4 — Transporte

| ID | Qué |
|----|-----|
| M1 | Mover `SendResponse` fuera del game thread. El lambda completa un `TaskCompletionSource`, y `RequestListener` escribe la respuesta al final |

Este es el **único refactor de threading real** del plan. `SendResponse` hoy hace `OutputStream.Write`
+ `Close()` dentro del tick del juego: un cliente lento frena la simulación.

Arranca también a resolver el segundo problema que menciona la auditoría: la `HttpListenerContext`
queda capturada en la cola, sin tope. Si la cola se acumula, los contextos se acumulan con ella.

**Verificación**: un script que mande una request y se desconecte a mitad, midiendo que el tick del
juego no se frena. Más: cargar la partida, mandar 50 requests seguidos, confirmar que el juego
sigue respondiendo.

**Commit**: `perf(mod): move HTTP response writing off the game thread`

**Esfuerzo**: 3–4 h. **Riesgo**: medio — es concurrencia. Hacelo con la partida guardada a mano.

---

## Fase 5 — JSON (sube de prioridad)

> La auditoría rated A5 como "Alto, puede esperar: es un refactor, no un fix".
> **Para esta máquina no es un refactor, es un bug activo.** Ver abajo.

Tu cultura de sistema es `es-BO`, coma decimal. `ServerComponent.cs:347-349` interpola `float`
crudo:

```csharp
$"\"food\":{foodLevel}"     // 0.75f.ToString() bajo es-BO  →  "food":0,75"
```

Y `bot/main.py:299` le hace `.json()` a eso. Resultado: **`/fastfetch` no te funciona hoy**. Y no es
el único: `gethealth` interpola `h.Severity`, que también es `float` (línea 356), y mete
`h.LabelCap` y `h.Part.Label` sin escapear. `/getneeds` y `/gethealth` **no pueden** devolver JSON
válido en una máquina `es-*`.

| ID | Qué |
|----|-----|
| A5 | `System.Text.Json.JsonSerializer.Serialize` sobre un record. Elimina las tres categorías de bug: escaping, separador cultural, y el JSON a mano |

**Alternativa de 2 líneas, si querés el fix rápido sin refactor**: formatear los floats con
invariante cultural donde se interpolan.

```csharp
$"\"food\":{foodLevel.ToString(CultureInfo.InvariantCulture)}"
```

Arregla tu `/fastfetch` hoy, pero deja el problema de escaping abierto. **Decisión tuya**: fix
mínimo ahora, `System.Text.Json` después.

**Verificación**: `/fastfetch` andando. Después: un pawn con una hediff cuyo label tenga comilla
double y ver que el JSON sigue parseando.

**Commit**: `fix(mod): serialize JSON with invariant culture and proper escaping`

**Esfuerzo**: 30 min el fix mínimo, 3–4 h el `System.Text.Json` completo.

---

## Fase 6 — Deriva y build

Independientes entre sí, bajo riesgo, se pueden hacer en cualquier momento.

| ID | Qué | Esfuerzo |
|----|-----|---------|
| B6 | `.env.example` con `GUILD=` y `TOKEN=` vacíos, más `SERVER=` si adoptás N4 | 10 min |
| M8 | Parametrizar `RimServer.csproj` con `$(RimWorldManagedDir)`, documentar cómo pasarla | 30 min |
| M6 | **Documentar** que el servidor solo escucha con una partida cargada. Moverlo a `Root_Entry` sería mejor arquitectura, pero es invasivo — recomiendo documentar y anotar el debt | 20 min |
| M7 | Convertir el mapeo comando→ruta en tabla. Decidir el destino de `/generate_random_race`: o lo conectás al server, o lo borras. Hoy no toca el juego | 1–2 h |

**Verificación**: build en Windows (M8), README cloneado en limpio (B6, M6).

**Commits**: uno por ítem. M7 probablemente dos: tabla primero, comando decorativo después.

---

## Fase 7 — C# testeable (opcional, no bloqueante)

Solo si querés cobertura de C#. No es un fix, es una inversión.

| ID | Qué |
|----|-----|
| — | Extraer la lógica de dispatch y de parseo de `ServerComponent` a una clase sin dependencia de `Pawn`. Recién ahí hay algo que testear |
| — | Workflow de CI que corra `pytest` en cada push |

El fuzz de rutas que menciona la auditoría es lo primero que se vuelve posible con esto, y es
justo lo que cubre C3.

**Esfuerzo**: 1 día. **Mi recomendación**: hacelo solo si el proyecto sigue vivo. Si RimDC es un
hobby al que volvés cada tanto, las Fases 0–6 te dan el 90% del valor por una fracción del effort.

---

## Tabla maestra

Los 28 hallazgos, con fase, verificación y tamaño.

| ID | Hallazgo | Fase | Verificación | Tamaño |
|----|----------|------|--------------|--------|
| C1 | Listener sin auth | 3 | curl + juego | M |
| C2 | Typo `resppobresonse` | 1 | pytest | XS |
| C3 | `/arrest` sin null-check | 2 | juego | S |
| A1 | Bot nunca lee la respuesta | 1 | pytest | M |
| A2 | Mapping escrito antes del éxito | 1 | pytest | S |
| A3 | Truncado después del dedup | 1 | pytest | S |
| A4 | `CloseServer` sin null-checks | 2 | juego | XS |
| A5 | JSON con interpolación | 5 | juego + `/fastfetch` | S / L |
| M1 | I/O bloqueante en main thread | 4 | script de carga | L |
| M2 | `Thread.Abort()` frágil | 2 | juego | XS |
| M3 | Dict mutable por defecto | 1 | pytest | XS |
| M4 | `List` sin lock (fragilidad) | 2 | juego | XS |
| M5 | `catch` vacío | 2 | juego | XS |
| M6 | Server solo con partida cargada | 6 | doc | XS |
| M7 | Mapa de comandos desincronizado | 6 | manual | M |
| M8 | Rutas Steam hardcodeadas | 6 | build Windows | S |
| B1 | `ex.Message` sin stack trace | 2 | juego | XS |
| B2 | Nick sin validar | 1 | pytest | S |
| B3 | `FinalizeInit()` vacío | 2 | juego | XS |
| B4 | Xenotipo sin validar | — | requiere saber de defs | M |
| B5 | Log engañoso | 2 | juego | XS |
| B6 | Sin `.env.example` | 6 | clone limpio | XS |
| N1 | `characters/` nunca se crea | 1 | pytest | XS |
| N2 | `fastfetch` bloquea el event loop | 1 | pytest | S |
| N3 | Rutas relativas al CWD | 1 | pytest | XS |
| N4 | URL del server hardcodeada | 1 | pytest | XS |
| N5 | `GUILD` vacío → `Object(0)` | 1 | arranque | XS |
| N6 | `/create_character` miente | 1 | pytest | XS |

`XS` una línea · `S` hasta 10 · `M` hasta 30 · `L` media jornada o más.

---

## Decisiones que necesito de vos

1. **A5**: ¿fix mínimo de cultura ahora (30 min, arregla tu `/fastfetch` hoy) o `System.Text.Json`
   completo (3–4 h, cierra las tres categorías)?
2. **B4**: requiere saber cómo querés que se elijan xenotipos con Biotech. `AllDefs` sin filtrar
   incluye ancient y gene-only. ¿Hay un criterio claro, o lo dejamos anotado?
3. **M6**: ¿documentamos que el server solo existe con partida cargada, o lo movemos a `Root_Entry`?
4. **M7**: ¿`/generate_random_race` se conecta al server o se borra? Hoy devuelve un nombre al azar
   de una lista de 41 que no tiene relación con los defs reales, y no toca el juego.
5. **Fase 7**: ¿el proyecto sigue vivo? Si es un hobby al que volvés, decime y la saco del plan.

---

## Lo que NO está en este plan

- **Tests de C#**: requiere refactor previo. Fase 7, opcional.
- **CI**: solo tiene sentido con tests. Viene después de la Fase 0.
- **`Root_Entry` para el server**: mejora real de arquitectura, pero mezclada con el resto de los
  fixes de threading genera un diff imposible de revisar. Anotado como debt.
- **Rotar el token de Discord**: no hizo falta, el `.env` commiteado eran placeholders.
- **Reescribir el historial de nuevo**: el commit viejo ya no está en ninguna rama. El objeto
  "suelto" en GitHub se resuelve con Support, no con git.

---

## Secuencia recomendada

```
Fase 0  tests           1.5 h    ─┐
Fase 1  bot             2.5 h    ─┘  sin abrir el juego
Fase 6  docs + build    1.5 h    ─┘

Fase 2  mod crash       1.5 h    ─┐
Fase 3  canal seguro    1 h      ─┴─ una sesión de juego
Fase 5  JSON (mínimo)   0.5 h    ─┘

Fase 4  transporte      3.5 h        sesión de juego dedicada
Fase 7  C# testeable    1 día       opcional
```

**Las dos primeras fases te dan el 70% del valor sin abrir RimWorld una sola vez.** Empezá ahí.
