# Auditoría de código

> **Qué se hizo con esto**: el plan de arreglo es
> [`04-plan-de-arreglo.md`](04-plan-de-arreglo.md) y el estado de ejecución está
> en [`05-implementacion.md`](05-implementacion.md).

Revisión completa de las 946 líneas de código de RimDC (604 C# + 342 Python),
commit `28c963b` (el árbol reescrito y saneado; el SHA original `bac16f4` ya no
existe en la rama).
Fecha: 2026-09-28.

Las correcciones de esta revisión están en `docs/04-plan-de-arreglo.md`. Los
hallazgos C1, A5, A4, M2, M4, M5, B1, B3 y B5 ya están resueltos.

## Resumen

| Severidad | Cantidad |
|-----------|----------|
| Crítico | 3 |
| Alto | 5 |
| Medio | 8 |
| Bajo | 6 |

**Veredicto**: la arquitectura es sólida y la separación de responsabilidades es correcta. Los
defectos están en los bordes — el canal de transporte, el contrato entre el bot y el servidor, y
la robustez ante inputs inválidos. El código nunca fue testeado: no hay un solo test, y los tres
críticos que encontré son alcanzables desde un slash command de Discord.

---

## Críticos

### C1 — El listener no autentica a nadie

**Archivo**: `ServerComponent.cs:546-548`

```csharp
listener = new HttpListener();
listener.Prefixes.Add("http://localhost:9891/");
listener.Start();
```

Cualquier proceso local puede mandar `GET /kill?pawn=Ana&data=Bob` y matar un colonist. No hay
token, ni header, ni validación de origen. La única "protección" es que el bind es a localhost.

**Por qué importa**: no es un riesgo teórico. Un `.exe` cualquiera, un script de Python, o
cualquier dependencia de un proyecto que compilaste puede leer la partida completa y controlar
colonists. El bind a localhost evita la red, no el proceso local.

**Fix**: token compartido en un header, validado en `RequestListener()` antes de encolar. Son ~5
líneas. Alternativa mínima: un query param `key` comparado contra un valor generado al arrancar.

**Esfuerzo**: bajo. **Riesgo de no hacerlo**: medio-alto, y crece si el juego alguna vez corre en
una máquina compartida o en red.

---

### C2 — Typo que rompe `equip_weapon` siempre

**Archivo**: `bot/main.py:126`

```python
await interaction.resppobresonse.send_message(   # ← debería ser response
    embed=create_embed_message("Request sent")
)
```

`AttributeError` en tiempo de ejecución. El comando `/equip_weapon` **falla el 100% de las
veces** que alguien lo usa. La request se manda igual (línea 124, antes del crash), así que el
efecto visible es: el colonist se equipa el arma, y Discord le muestra un error al usuario.

**Fix**: una palabra.

---

### C3 — `/arrest` con objetivo inexistente tira `NullReferenceException`

**Archivo**: `ServerComponent.cs:284-295`

```csharp
case "arrest":
  Pawn selectedPawn5 = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(...);

  Building_Bed prisonBed = RestUtility.FindBedFor(
      selectedPawn5,                    // ← puede ser null
      pawn,
      ...
      guestStatus: selectedPawn5.GuestStatus   // ← NRE acá
  );
```

`FirstOrDefault` devuelve `null` si no encuentra a nadie con ese nick, y no hay null-check. Es
**inconsistente con los casos hermanos**: `kill` (209), `incapacite` (223) y `rescue` (271) sí
validan `selectedPawn != null && !selectedPawn.Dead`. `arrest` se lo salteó.

Alcanzable con `/arrest NoExiste`. El `try/catch` de `Update()` (línea 575) lo atrapa y lo loguea,
así que no crashea el juego — pero el comando falla en silencio y no hay forma de que el usuario
se entere.

**Fix**: copiar el guard de los casos hermanos.

---

## Altos

### A1 — El bot nunca lee la respuesta del servidor

**Archivo**: `bot/main.py:38-41`, y todos los handlers

```python
def send_request(method: str, params: dict) -> None:
    requests.get(server + method, params=params)   # ← el return se descarta
```

Y en cada comando:

```python
request_wrapper("eat", {}, interaction.user.id)
await interaction.response.send_message(embed=create_embed_message("Request sent"))
```

El bot manda la request en un thread, no espera, no mira el body, y responde "Request sent" siempre.
El servidor tiene respuestas con contenido real — `"Pawn dead or doesn't exists!!!"`,
un error de Biotech, un JSON de stats — y **el bot las descarta todas**.

**Por qué importa**: es la causa raíz de por qué C1 es invisible. Si el bot leyera las respuestas,
la falta de autenticación y los fallos de Biotech se verían al instante. También significa que
**no hay forma de saber desde Discord si algo falló** — hay que ir a mirar el log de RimWorld.

**Fix**: `resp = requests.get(..., timeout=5)` y responder con `resp.text` si no es `"Request sent"`.

---

### A2 — `create_character` escribe el mapping antes de que la request funcione

**Archivo**: `bot/main.py:257-268`

```python
if not os.path.isfile(f"characters/{interaction.user.id}"):
    with open(f"characters/{interaction.user.id}", "w+") as f:
        f.write(nickname)          # ← escribe primero
    request_wrapper("create_character", {}, interaction.user.id)   # ← después intenta
    await interaction.response.send_message(...)
```

Si RimWorld no está corriendo, la request falla (ver C1 / A1), pero **el archivo ya quedó escrito**.
Queda un mapping apuntando a un colonist que nunca existió. El usuario cree que tiene personaje;
todos sus comandos devuelven "Pawn dead or doesn't exists!!!"; y `/create_character` ya no
reintenta porque el archivo existe (ver A3).

Estado corrupto, sin salida.

**Fix**: escribir el archivo solo después de una respuesta exitosa del servidor.

---

### A3 — Truncado de nombre DESPUÉS del chequeo de duplicados

**Archivo**: `bot/main.py:240` vs `bot/main.py:252-253`

```python
if nickname in registered_nicknames:   # 240 — chequea el nombre COMPLETO
    ...
    return
...
if len(nickname) > 6:                  # 252 — recién acá trunca
    nickname = nickname[:6]
```

Dos usuarios que submitting "Alejandro" y "Alexand" **pasan los dos el chequeo de duplicados**, y
después los dos se truncan a "Alexand". Resultado: dos archivos de usuario con el mismo contenido,
dos personas controlando el mismo colonist. El segundo que manda una orden le mueve el pawn al
primero.

Es el orden invertido al correcto. El truncar tiene que ir antes del chequeo.

**Fix**: mover el truncar arriba del `if nickname in registered_nicknames`.

---

### A4 — `CloseServer()` no valida nulos

**Archivo**: `ServerComponent.cs:556-567`

```csharp
public static void CloseServer()
{
  if(serverThread.IsAlive) {      // ← NRE si serverThread es null
    serverThread.Abort();
  }
  if(listener.IsListening) {      // ← NRE si listener es null
    listener.Close();
  }
}
```

`serverThread` y `listener` son `static` y solo se inicializan en `StartServer()`, que se llama
desde el constructor del `GameComponent`. `CloseServer()` se dispara desde un Harmony prefix sobre
`GenScene.GoToMainMenu` — que puede ejecutarse en una transición a menú donde el `GameComponent`
nunca llegó a construirse.

**Fix**: `if (serverThread?.IsAlive == true)` y `if (listener?.IsListening == true)`.

---

### A5 — El JSON se arma con interpolación de strings

**Archivo**: `ServerComponent.cs:324-389`

```csharp
string jsonResponse = "{" +
  $"\"shooting\":{pawn.skills.GetSkill(SkillDefOf.Shooting).Level}," +
  ...
```

Tres problemas en uno:

1. **Sin escaping.** `gethealth` intercala `h.LabelCap` crudo. Una hediff cuyo label tenga una
   comilla doble genera JSON inválido. `getequipment` hace lo mismo con `eq.LabelCap`.
2. **Separador decimal cultural.** `pawn.needs.food.CurLevelPercentage` es un `float`, y el
   `ToString()` implícito usa la cultura del sistema. En un sistema con coma decimal
   (Argentina, España, la mayoría de Europa) genera `0,75` — que no es JSON válido. El bot hace
   `.json()` sobre eso y revienta con `JSONDecodeError`.
3. **Sin librería.** Hay 66 endpoints JSON sin usar `System.Text.Json` o equivalente.

**Fix**: `System.Text.Json.JsonSerializer.Serialize` con un record. Más código, pero elimina
las tres categorías de bug de una.

---

## Medios

### M1 — I/O de red bloqueante en el main thread

**Archivo**: `ServerComponent.cs:475-524`

El `SendResponse(ctx, ...)` se llama **dentro del lambda encolado**, o sea en el main thread del
juego:

```csharp
actionQueue.Enqueue(() => {
    ...
    SendResponse(ctx, "sent");   // ← escribe en el socket, en el game tick
    return;
});
```

`SendResponse` hace `OutputStream.Write` + `Close()`. Es I/O de red bloqueante ejecutándose en el
tick del juego. Un cliente lento o colgado frena la simulación.

Compuesto por: la `HttpListenerContext` queda capturada en la cola. Si la cola se acumula, los
contextos se acumulan con ella. Y no hay tope — `RequestListener` acepta requests en bucle cerrado
y encola sin límite.

**Fix**: mover el `SendResponse` fuera del game thread, al final de `RequestListener`, guardando
la respuesta en un `TaskCompletionSource` que el lambda completa.

---

### M2 — `Thread.Abort()` es tan frágil como suena

**Archivo**: `ServerComponent.cs:558-560`

`Thread.Abort()` no existe en .NET Core / .NET 5+. Funciona acá solo porque RimWorld corre Mono.
Si el proyecto alguna vez se porta a un runtime moderno, esto es
`PlatformNotSupportedException` en el momento de cerrar el servidor.

Además es innecesario: el `Thread` está bloqueado en `listener.GetContext()`, y cerrar el
listener ya lo desbloquea. `listener.Close()` alcanza.

**Fix**: borrar el `Abort()`, dejar solo `listener.Close()`.

---

### M3 — Argumento mutable por defecto

**Archivo**: `bot/main.py:28`

```python
def request_wrapper(method: str, params: dict = {}, player_id: int = 0) -> None:
    params["pawn"] = content     # ← muta el default
```

El `params` por defecto es un `dict` compartido entre todas las llamadas que no lo pasan.
Hoy ningún caller lo omite (todos pasan un literal), así que no explota. Pero es una bomba de
reloj: el primer caller futuro que no pase `params` corrompe todos los demás.

**Fix**: `params: dict | None = None` y `params = params or {}`.

---

### M4 — `pendingCharacters` es un `List` sin lock

**Archivo**: `ServerComponent.cs:397`, `:445-459`, `:496`

**Corrección a una observación previa**: esto **no es una race condition hoy**. Las dos puntas
corren en el main thread — el `Add` (496) está dentro del lambda encolado, el `Clear` (459) en
el postfix de Harmony. Verificado.

El problema es la fragilidad: es un `List<string>` plano en una clase que tiene un thread de red
en la misma clase. Escenario de breakage: alguien agrega un `if (pendingCharacters.Contains(x))`
dentro de `RequestListener` para evitar duplicados, y ahora sí hay race — silenciosa, con
`List` no es atómico.

**Fix**: `ConcurrentQueue<string>`. Mismo costo, imposible de romper.

---

### M5 — `catch (Exception) {}` vacío en el loop del listener

**Archivo**: `ServerComponent.cs:525`

```csharp
} catch(Exception) {}
```

Traga todo silenciosamente. Si el listener lanza `HttpListenerException` de forma repetida, el
while loop itera en busy-spin sin loguear nada y sin salir.

**Por qué existe**: la idiomática de `GetContext()` sobre un listener que se puede cerrar desde
otro thread necesita un catch. Pero debería loguear.

**Fix**: `catch (HttpListenerException) { break; } catch (Exception ex) { Log.Error(ex.Message); }`.

---

### M6 — El servidor solo existe con una partida cargada

**Archivo**: `ServerComponent.cs:590-602`

El `StartServer()` está en el constructor de `ServerComponent`, que es un `GameComponent`. Los
`GameComponent` se instancian al **cargar una partida**. En el menú principal, el puerto 9891
no escucha nada.

Combinado con A1, esto es invisible: el bot responde "Request sent" a todo, incluso con el juego
cerrado.

**Documentación**: no está en ningún README. Es la primera pregunta que se va a hacer cualquiera
que clone el repo.

**Fix**: documentarlo. Mover el server al `Root_Entry` (que sí existe siempre) sería mejor
arquitectura, pero es un cambio más invasivo.

---

### M7 — El bot tiene un mapa de comandos hardcodeado que ya no coincide con el mod

**Archivo**: `bot/main.py:61-283` vs `ServerComponent.cs:16-320`

Los 16 comandos del bot están escritos a mano, cada uno con su string de ruta. Agregar una acción
al mod no la agrega al bot, y nadie lo detecta.

**Deriva actual**: el mod implementa `strip`, `equip_ranged_weapon` y `equip_melee_weapon` que
el bot sí expone, pero el **README no los documenta**. Y el mod implementa `getequipment` que el
bot **no expone** (solo lee `getskills`, `getneeds`, `gethealth`).

Comando decorativo: `/generate_random_race` (línea 179-228) devuelve un xenotipo al azar de una
**lista hardcodeada de 41 nombres en el bot**, que no tiene ninguna relación con el
`DefDatabase<XenotypeDef>.AllDefs.RandomElement()` que usa el server (línea 419). Dos fuentes de
verdad para el mismo concepto, que ya divergieron. El comando no toca el juego.

**Fix**: el mapeo comando→ruta debería ser una tabla, y la lista de xenotipos debería leerse del
server o eliminarse.

---

### M8 — El `.csproj` tiene rutas de Steam hardcodeadas a Linux

**Archivo**: `RimServer.csproj:8-13`

```xml
<HintPath>$(HOME)/.local/share/Steam/steamapps/common/RimWorld/RimWorldLinux_Data/Managed/Assembly-CSharp.dll</HintPath>
```

En Windows el build falla. El README lo admite en una línea entre paréntesis, pero no dice
*cómo* arreglarlo.

**Fix**: parametrizar con una property:

```xml
<HintPath>$(RimWorldManagedDir)/Assembly-CSharp.dll</HintPath>
```

y que el usuario la pase con `-p:RimWorldManagedDir=...` o un `Directory.Build.props` local.

---

## Bajos

### B1 — `catch (Exception)` también se traga las excepciones de negocio

**Archivo**: `ServerComponent.cs:575-577`. Loguea `ex.Message`, que no incluye el stack trace.
Un `NullReferenceException` en `arrest` (C3) loguea "Object reference not set..." sin decir
dónde. Agregar `ex` en vez de `ex.Message`.

### B2 — El truncado de nombres no valida caracteres

**Archivo**: `bot/main.py:252-253`. Solo corta a 6 chars. No hace `strip()`, ni rechaza espacios,
ni valida que el nombre sea usable como `NameTriple`. Un nick `"  a b"` pasa y genera un pawn con
ese nombre, que después no matchea el archivo porque el `Equals` es exacto.

### B3 — `FinalizeInit()` está vacío

**Archivo**: `ServerComponent.cs:400-403`. Override que solo llama a `base`. El server arranca en
el constructor, no acá. Sobra.

### B4 — Xenotipo elegido de todos los defs, sin validar

**Archivo**: `ServerComponent.cs:418-425`. `NewGeneratedStartingPawn()` ya genera un pawn con
xenotipo random; después `SetXenotype()` lo sobreescribe. El `Pawn_GeneTracker` del xenotipo
original queda ahí. Con xenotipos basados en genes, el resultado puede ser inconsistente.
Además `AllDefs` no filtra: incluye xenotipos de tipo ancient y gene-only.

### B5 — Log engañoso en la creación de pawn

**Archivo**: `ServerComponent.cs:499`. `Log.Message($"Added new character: {pawnNickname}")` se
ejecuta aunque `GenerateRandomPawn` haya devuelto `null` (Biotech inactivo). Dice que agregó un
personaje que no se agregó.

### B6 — No hay `.env.example`

**Archivo**: `bot/.env` ahora está gitignored (corregido el 2026-09-28), pero no quedó ningún
template. `bot/README.md` sigue diciendo "set your Discord server ID for the GUILD parameter" sin
decir de dónde sacar un archivo que ya no está en el repo. Un `.env.example` con `GUILD=` y
`TOKEN=` vacíos lo resuelve.

---

## Cobertura de tests

| Métrica | Valor |
|---------|-------|
| Archivos de test | 0 |
| Workflows de CI | 0 |
| Líneas de código | 946 |
| Cobertura | 0% |

No hay `test_*.py`, ni `pytest.ini`, ni `.github/workflows`, ni `Makefile`.

**Qué testear primero, si se decide testear** (en orden de valor por esfuerzo):

1. **Los parsers de URL.** La función de dispatch de `ServerComponent` es lógica pura y
   testeable sin arrancar RimWorld. Un fuzz de rutas desconocidas + `pawn` inexistente cubriría C3.
2. **La lógica de `request_wrapper` en el bot.** Con un servidor HTTP de test, se puede verificar
   que la request se arma bien y que la respuesta se propaga (arreglando A1).
3. **El truncado y duplicados de `create_character`.** Es lógica pura, 10 líneas, y tiene el bug A3.

El C# no es testeable unitariamente sin una capa de indirección sobre `Pawn` — que sería
refactor, no test. Empezar por el bot.

---

## Orden de arreglo sugerido

| # | ID | Esfuerzo | Por qué primero |
|---|-----|----------|-----------------|
| 1 | C2 | 1 palabra | Crash visible, trivial |
| 2 | C3 | 3 líneas | Crash alcanzable desde Discord |
| 3 | A1 | ~10 líneas | Destapa todos los demás problemas |
| 4 | A3 | mover 4 líneas | Corruption de datos |
| 5 | A4 | 2 líneas | Crash en transición de menú |
| 6 | A2 | reordenar | Depende de A1 para poder verificar |
| 7 | C1 | ~5 líneas | Seguridad |
| 8 | M3, M2, B6 | 1 línea cada uno | Limpieza |

A5 (serialización) es el más grande de todos y puede esperar: es un refactor, no un fix.
