# RimServer

A mod to connect RimWorld with other applications by hosting an HTTP server on a secondary thread. (The project defaults to a Linux Steam install; on other platforms point the build at your own copy of RimWorld's managed assemblies, see the `RimWorldManagedDir` property in RimServer.csproj.)

# How to Install

1. Compile the C# code. On anything other than the default Linux path:

```sh
dotnet build -c Release /p:RimWorldManagedDir="<path to RimWorld's Managed folder>"
```

```sh
dotnet build -c Release
```

1. Move all the contents of bin/Release to Assemblies.

```
mv bin/Release/* Assemblies
```

1. Go to the mods section in RimWorld and enable the RimServer mod.

1. Set a shared secret. The mod reads `RIMDC_TOKEN` from its environment and
   the bot sends the same value, so both processes must see the identical string.
   On Windows:

```sh
setx RIMDC_TOKEN "pick-something-long-and-random"
```

   Restart RimWorld afterwards. If the variable is missing the mod does not open
   its port at all and logs why, rather than serving unauthenticated.

# How to Use

The HTTP server is listening on localhost:9891. Requests are authenticated, so
every call needs the shared token in an `Authorization` header:

```sh
curl -H "Authorization: Bearer $RIMDC_TOKEN" localhost:9891/eat?pawn=Ana
```

Without it you get `401 Unauthorized`. The routes (handled with GET and query
parameters) are:

+ /priority (example: localhost:9891?pawn=pawn_name&data=attack)
+ /unequip_weapon
+ /equip_weapon
+ /threat_response (you can send "attack", "flee", "ignore" in the query parameters, for example: localhost:9891?pawn=pawn_name&data=attack)
+ /eat
+ /rest
+ /kill (example: localhost:9891?pawn=pawn_name&data=enemy_name)
+ /equip_clothes
+ /incapacite example: localhost:9891?pawn=pawn_name&data=enemy_name
+ /rescue (example: localhost:9891?pawn=pawn_name&data=target_name)
+ /shoot (example: localhost:9891?pawn=pawn_name&data=enemy_name)
+ /arrest (example: localhost:9891?pawn=pawn_name&data=target_name)
+ /create_character (example: localhost:9891?pawn=pawn_name)

(these routes return data!!)

+ /getskills
+ /getneeds
+ /gethealth
+ /getequipment

(By default, the "pawn" query parameter containing the pawn's name must be added to all routes to identify it.)
