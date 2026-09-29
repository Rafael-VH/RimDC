# RimServer

A mod to connect RimWorld with other applications by hosting an HTTP server on a secondary thread. (The project is adapted for Linux by default, although it could likely be made to work on Windows as well with a few adjustments to the RimServer.csproj file.)

# How to Install

1. Compile the C# code.

```sh
dotnet build -c Release
```

1. Move all the contents of bin/Release to Assemblies.

```
mv bin/Release/* Assemblies
```

1. Go to the mods section in RimWorld and enable the RimServer mod.

# How to Use

The HTTP server is listening on localhost:9891. You can send requests to that server (For some reason, I decided to handle the methods using GET and query parameters.); the routes that will perform actions are:

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
