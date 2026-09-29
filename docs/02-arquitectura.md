# Arquitectura

## Vista general

```
┌──────────────────────────────────────────────────────────────┐
│  DISCORD  (proceso Python)                                    │
│                                                               │
│  main.py  ──►  lee bot/characters/<user_id>  ──►  "Ana"       │
│     │                                                           │
│     └──►  requests.get()  en un thread por comando             │
└─────────────────────────┬─────────────────────────────────────┘
                          │  HTTP GET · localhost:9891
                          │  ?pawn=Ana&data=Ana&complement=3
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  RIMWORLD  (proceso Mono/C#)                                  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Thread background:  RequestListener()                   │  │
│  │   HttpListener.GetContext()  →  parsea  →  ENCOLA      │  │
│  │   ⚠ NO toca la API de RimWorld. Solo encola.           │  │
│  └───────────────────────┬────────────────────────────────┘  │
│                          │  ConcurrentQueue<Action>            │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │ Main thread (game tick):  ServerComponent.Update()       │  │
│  │   drena la cola  →  busca el Pawn  →  ProcessAction()   │  │
│  │   ⚠ Manda la respuesta HTTP desde acá (I/O bloqueante)  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Harmony patches:                                             │
│    Root_Entry.Update   → postfix → Update()   (menú / carga) │
│    Root_Play.Update    → postfix → Update()   (en partida)   │
│    Page_ConfigureStartingPawns.PreOpen → crea pawns pendientes│
│    GenScene.GoToMainMenu (prefix) → CloseServer()             │
└──────────────────────────────────────────────────────────────┘
```

---

## La decisión de diseño central

**Por qué existe la cola.** La API de Verse / RimWorld asume que todo corre en el main thread.
Un `Pawn` es un objeto vivo: su `JobTracker`, su `Equipment`, su `Needs` se mutan cada tick desde
el juego. Si un thread de red los tocara, tendrías race conditions que aparecen como crashes
aleatorios o estados de pawn corruptos — el tipo de bug que nadie puede reproducir.

La solución que tomó el proyecto es la canónica para mods de RimWorld:

| Thread | Puede hacer | No puede hacer |
|--------|-------------|----------------|
| Background (HTTP) | Parsear la URL, leer query params, encolar un `Action` | Tocar `Pawn`, `Job`, `Map`, `Thing` |
| Main (game tick) | Todo lo de RimWorld | — (pero también escribe la respuesta HTTP) |

El patrón es correcto. El defecto es que la frontera está en el lugar equivocado para la última
etapa: la **escritura de la respuesta** quedó del lado del main thread. Ver [M1](#m1).

---

## Los dos estados del servidor

El listener no está siempre activo, y esto no es evidente leyendo el código.

### Estado 1 — Sin partida cargada

`ServerComponent` es un `GameComponent`. Los `GameComponent` se construyen cuando RimWorld carga
una partida. Antes de eso, **el constructor nunca corrió, el listener no existe, y el puerto 9891
no escucha nada**.

Consecuencia: el bot de Discord está vivo y responde a los comandos con "Request sent", pero la
request HTTP falla con `ConnectionRefused` porque nadie escucha. El bot nunca se entera porque
nunca lee la respuesta. Ver [A1](#a1).

### Estado 2 — Pantalla de creación de colonist

`Current.Game != null && Current.Game.InitData != null`. El listener está vivo y hay early-return:

```csharp
if(Current.Game != null && Current.Game.InitData != null) {
    if(requestUrl[1..] == "create_character") { /* crear pawn */ }
    SendResponse(ctx, "sent");
    return;   // ← TODO lo demás sale acá
}
```

En esta pantalla, **cualquier request que no sea `create_character` devuelve "sent" y no hace
nada**. Es intencional —no se puede pelear en la pantalla de creación— pero no está documentado
en ningún lado.

### Estado 3 — En partida

`Find.CurrentMap` existe. Acá funciona todo. Es el estado normal de juego.

---

## El ciclo de vida de un colonist

`create_character` tiene dos caminos, y solo uno funciona en la práctica:

**Camino A — el usuario ya está en la pantalla de creación (funciona)**

```
GET /create_character?pawn=Ana
  → la página Page_ConfigureStartingPawns está abierta
  → GenerateRandomPawn("Ana")
      → StartingPawnUtility.NewGeneratedStartingPawn()   pawn random
      → SetXenotype(random de DefDatabase<XenotypeDef>)   sobreescribe
      → renombra a NameTriple(First, "Ana", Last)
  → Current.Game.InitData.startingAndOptionalPawns.Insert(0, pawn)
  → totalPlayers++  ·  startingPawnCount = totalPlayers
  → SendResponse("sent")
```

**Camino B — el usuario no está en esa pantalla (se encola para después)**

```
GET /create_character?pawn=Ana
  → la página NO está abierta
  → pendingCharacters.Add("Ana")
  → SendResponse("sent")

  ...más tarde, el usuario abre la pantalla de creación...
  → Harmony postfix sobre Page_ConfigureStartingPawns.PreOpen
  → por cada nombre en pendingCharacters: GenerateRandomPawn + insert
  → pendingCharacters.Clear()
```

`pendingCharacters` es un `List<string>` plano. Hoy no hay race porque **las dos puntas corren en
el main thread** (el `Add` está dentro del lambda encolado, el `Clear` en el postfix de Harmony).
Pero es un `List` sin lock en una clase que tiene un thread de red metros más arriba: cualquier
lectura futura desde el listener lo rompe en silencio. Ver [M4](#m4).

---

## El contrato de identidad

Este es el punto más frágil del diseño.

```
discord user ID (int)  ──►  bot/characters/347903091816923136
                                    │
                                    └── contenido: "Ana"
                                              │
                          GET /kill?pawn=Ana ──┘
                                              │
                          Find.CurrentMap.mapPawns.FreeColonists
                              .FirstOrDefault(p => p.Name is NameTriple nt
                                                  && nt.Nick.Equals("Ana", OrdinalIgnoreCase))
```

Tres consequências que importan:

1. **El match es por NICK, no por ID.** Si un jugador renombra su colonist en el juego, el archivo
   `characters/` sigue apuntando al nombre viejo y todos sus comandos devuelven
   "Pawn dead or doesn't exists!!!". El usuario tiene que volver a correr `/create_character`.

2. **No hay un ID estable.** RimWorld no expone un identificador externo para un `Pawn`, así que
   el nick es lo único disponible. Es un workaround razonable, no una decisión de diseño tomada a
   la ligera.

3. **El nombre es la única credencial.** Como el listener no valida quién manda la request (C1),
   el nick funciona como token de acceso: cualquiera que sepa el nombre de un colonist puede
  controlarlo. Y los nombres se filtran en Discord con cada comando, así que no es un secreto.

---

## Persistencia: por qué hay archivos

El bot no usa base de datos. Guarda un archivo por usuario en `bot/characters/`, con el nombre
del colonist como contenido. Se borran todos con `/clear_characters`, que exige permiso de
administrador.

Los archivos están en el path relativo `characters/`, así que **el bot hay que correrlo desde
dentro de `bot/`**, no desde la raíz del repo.

---

## Puertos, constantes y números mágicos

| Constante | Dónde | Valor |
|-----------|-------|-------|
| Puerto HTTP | `ServerComponent.cs:547` y `bot/main.py:14` | `9891` |
| Prefijo del listener | `ServerComponent.cs:547` | `http://localhost:9891/` |
| Límite de longitud de nick | `bot/main.py:252` | 6 caracteres |
| Timeout de request | — | **ninguno** |
| Concurrencia | 1 thread de listener, 1 cola sin límite | |

El puerto está hardcodeado en los dos lados, en dos lenguajes, sin configuración compartida.
Cambiarlo implica editar dos archivos en dos idiomas distintos.

---

## Dependencias

### Mod C#

| Dependencia | Versión | Origen |
|-------------|---------|--------|
| `Lib.Harmony` | 2.4.2 | NuGet |
| `Assembly-CSharp.dll` | la de tu install | Referencia a DLL, no paquete |
| `UnityEngine.CoreModule.dll` | la de tu install | Referencia a DLL, no paquete |

`netstandard2.1` como target framework. `AppendTargetFrameworkToOutputPath=false` para que la
salida sea `bin/Release` en vez de `bin/Release/netstandard2.1`.

### Bot Python

16 paquetes pinneados a versión exacta en `bot/requirements.txt`, de los cuales 4 son relevantes:
`discord.py`, `requests`, `python-dotenv`. Los otros 13 son transitivos.

---

## Lo que este diseño NO tiene

- **Autenticación** de quién envía la request.
- **Rate limiting.** El listener acepta requests en bucle cerrado; la cola no tiene tope.
- **Tests.** Cero. Ni un archivo de test, ni un `pytest`, ni un `test_*.py`.
- **CI.** Cero. No hay `.github/workflows`.
- **Logging estructurado.** Todo es `Log.Message` con strings interpolados. No hay forma de
  consultar "qué pasó" sin abrir el log de RimWorld a mano.
- **Manejo de errores en el bot.** Ningún `try/except` alrededor de los handlers de comando. Si uno
  tira, `discord.py` lo loguea y el usuario no ve nada.
