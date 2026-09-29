# Qué es este proyecto

RimDC es un mod de RimWorld que convierte una partida colony-management en un juego cooperativo
controlado desde Discord. Cada jugador del servidor de Discord maneja **su propio colonist**,
con los mismos comandos que usaría dentro del juego: matar, arrestar, comer, dormir, equipar
armas, Rescue, cambiar prioridades de trabajo.

No es un mod que "manda notificaciones a Discord". Es un mod donde **Discord es el control remoto**.

---

## Las dos piezas

### 1. El mod C# — `ServerComponent.cs` (604 líneas)

Un mod de RimWorld 1.6 (`packageId: hazu.servermod.rimworld`, autor original: Hazu) que:

- Levanta un `HttpListener` en `http://localhost:9891/` al inicializarse.
- Recibe GETs con query parameters.
- Traduce cada request a una acción sobre un `Pawn`: tomar un job, cambiar la prioridad de un
  trabajo, setear la respuesta a amenazas.
- También expone datos: skills, necesidades, salud, equipment — que el bot renderiza en un embed.

No depende de Discord para nada. Es un servidor HTTP genérico que expone control sobre colonists.

### 2. El bot de Python — `bot/main.py` (342 líneas)

Un bot de Discord (`discord.py` 2.7.1) que:

- Registra slash commands en un guild configurable.
- Mapea cada `discord user ID` → el nombre de su colonist, guardándolo en un archivo plano.
- Traduce cada comando a un GET contra `http://localhost:9891/?pawn=<nombre>&data=<...>`.
- Renderiza la respuesta en un embed de Discord.

---

## Cómo se hablan

No usan WebSockets, ni una cola de mensajes, ni una base de datos. Es HTTP plano:

```
Jugador en Discord
      │
      │  /kill Ana
      ▼
┌──────────────────┐
│  Bot de Discord  │   lee bot/characters/<user_id>  →  "Ana"
└────────┬─────────┘
         │  GET http://localhost:9891/kill?pawn=Ana
         ▼
┌──────────────────┐
│  Mod de RimWorld │   busca el colonist cuyo NameTriple.Nick == "Ana"
└────────┬─────────┘
         │  pawn.jobs.TryTakeOrderedJob(JobDefOf.AttackMelee, Ana)
         ▼
   El colonist va a pegar a Ana
```

Todo es GET. No hay verbos HTTP, no hay paths REST, no hay body JSON de entrada. Los "parámetros"
van en el query string: `pawn` (quién), `data` (a quién / qué opción), `complement` (el entero
de prioridad de trabajo, 1 a 3).

---

## El flujo completo de una orden

1. El usuario escribe `/kill Ana` en Discord.
2. El bot busca `bot/characters/<su_user_id>`, lee el contenido: `"Ana"`.
3. Lanza un thread que hace `GET /kill?pawn=Ana&data=Ana`.
4. El `HttpListener` del mod recibe el request en su thread background.
5. El mod **encola** la acción en un `ConcurrentQueue<Action>` y sigue escuchando.
6. En el **main thread** del juego, un postfix de Harmony sobre `Root_Entry.Update` drena la cola
   y ejecuta la acción.
7. El mod busca el colonist cuyo nombre coincide con `"Ana"`.
8. Le asigna un job de ataque cuerpo a cuerpo.
9. El bot ya le había respondido "Request sent" al usuario, sin esperar nada.

Los pasos 6 y 7 están donde importa: la API de RimWorld **no es thread-safe**. El thread de
HTTP no puede tocar un `Pawn`. Por eso existe la cola. Ver [02-arquitectura.md](02-arquitectura.md).

---

## Lo que se puede hacer desde Discord

**Acciones** (modifican el juego):

| Comando | Qué hace |
|---------|----------|
| `/set_priority` | Cambia la prioridad de un tipo de trabajo (1 = máximo) |
| `/unequip_weapon` | Suelta el arma actual |
| `/strip` | Se quita la primera prenda |
| `/threat_response` | Cambia la reacción a amenazas: attack / flee / ignore |
| `/equip_weapon` | Equipa el arma más cercana alcanzable |
| `/equip_clothes` | Equipa la prenda más cercana alcanzable |
| `/eat` | Busca comida y se la come |
| `/rest` | Busca una cama y duerme |
| `/kill` | Ataca a un colonist con `killIncappedTarget = true` |
| `/incapacite` | Ataca a un colonist sin matarlo |
| `/shoot` | Dispara a un colonist con el arma de rango equipada |
| `/rescue` | Lleva a un downed colonist a una cama |
| `/arrest` | Arresta a un colonist y lo lleva a una celda |
| `/create_character` | Crea un colonist nuevo con el nombre elegido |

**Consultas** (leen el juego):

| Comando | Devuelve |
|---------|----------|
| `/fastfetch` | Embed con las 12 skills, 3 necesidades (mood/rest/food) y la lista de hediffs |

**Comando decorativo**: `/generate_random_race` devuelve un nombre de xenotipo al azar de una
lista hardcodeada. No toca el juego — ver hallazgo M7.

---

## Requisitos para jugar

- **RimWorld 1.6** con el DLC **Biotech** obligatorio. Sin Biotech, `create_character` falla:
  el mod hace `ModsConfig.BiotechActive` check y devuelve null.
- **.NET SDK** para compilar el mod.
- **Steam install path** de RimWorld accesible, porque el `.csproj` tiene las rutas de las DLL
  hardcodeadas (ver M8).
- **Python 3.11+** con las dependencias de `bot/requirements.txt`.
- **Discord Developer Portal**: crear una app, habilitar el intent de message content, tener el
  bot en el guild configurado.

## Cómo se levanta

1. `dotnet build -c Release` en la raíz.
2. Copiar el contenido de `bin/Release` a la carpeta `Assemblies/` del mod.
3. Activar el mod `RimServer` en RimWorld.
4. `cd bot` → `pip install -r requirements.txt` → configurar `.env` → `python main.py`.
5. **Cargar una partida de RimWorld.** El `HttpListener` se levanta en el constructor del
   `GameComponent`, que solo se instancia cuando hay una partida cargada. Antes de eso, el puerto
   9891 está cerrado y el bot no tiene a quién hablar.

El paso 5 es la trampa principal del proyecto. Está documentada en [03-auditoria.md](03-auditoria.md#m6).
