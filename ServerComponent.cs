using System;
using System.Net;
using System.Threading;
using System.Collections.Concurrent;
using System.Collections.Generic;
using Verse;
using System.Linq;
using System.Collections.Specialized;
using RimWorld;
using HarmonyLib;

namespace ServerComponent
{
    public class ServerComponent : GameComponent
    {
        private void ProcessAction(string action, string data, string complement, Pawn pawn) 
        {
            switch (action) 
            {
                case "priority":
                  if(int.TryParse(complement, out int priority)) 
                  {
                    switch (data) 
                    {
                        case "cleaning":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Cleaning, priority);
                          break;

                        case "childcare":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Childcare, priority);
                          break;

                        case "construction":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Construction, priority);
                          break;

                        case "crafting":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Crafting, priority);
                          break;

                        case "darkstudy":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.DarkStudy, priority);
                          break;

                        case "doctor":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Doctor, priority);
                          break;

                        case "firefighter":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Firefighter, priority);
                          break;

                        case "fishing":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Fishing, priority);
                          break;

                        case "growing":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Growing, priority);
                          break;

                        case "handling":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Handling, priority);
                          break;

                        case "hauling":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Hauling, priority);
                          break;

                        case "hunting":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Hunting, priority);
                          break;

                        case "mining":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Mining, priority);
                          break;

                        case "plantcutting":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.PlantCutting, priority);
                          break;

                        case "research":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Research, priority);
                          break;

                        case "smithing":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Smithing, priority);
                          break;

                        case "warden":
                          pawn.workSettings.SetPriority(WorkTypeDefOf.Warden, priority);
                          break;
                    }
 
                  }
                  break;

                case "unequip_weapon":
                  if(pawn.equipment.Primary != null) 
                  {
                    bool state = pawn.equipment.TryDropEquipment(
                        pawn.equipment.Primary,
                        out var droppedWeapon,
                        pawn.Position,
                        forbid: false
                      );
                  }
                  break;

                case "strip":
                  if(pawn.apparel.WornApparel.Count > 0) 
                  {
                    pawn.apparel.TryDrop(
                        pawn.apparel.WornApparel.FirstOrDefault(),
                        out Apparel droppedApparel,
                        pawn.Position,
                        forbid: false
                    );
                  }
                  break;

                case "threat_response":
                  switch (data) {
                    case "attack":
                      pawn.playerSettings.hostilityResponse = HostilityResponseMode.Attack;
                      break;

                    case "flee":
                      pawn.playerSettings.hostilityResponse = HostilityResponseMode.Flee;
                      break;

                    case "ignore":
                      pawn.playerSettings.hostilityResponse = HostilityResponseMode.Ignore;
                      break;
                  }
                  break;

                case "equip_weapon":
                  Thing weapon = GenClosest.ClosestThingReachable(
                      pawn.Position,
                      pawn.Map,
                      ThingRequest.ForGroup(ThingRequestGroup.Weapon),
                      Verse.AI.PathEndMode.OnCell,
                      TraverseParms.For(pawn),
                      validator: t => !t.IsForbidden(pawn)
                  );

                  if(weapon != null) {
                    Verse.AI.Job equipJob = JobMaker.MakeJob(JobDefOf.Equip, weapon);
                    pawn.jobs.TryTakeOrderedJob(equipJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "equip_clothes":
                  Thing clothe = GenClosest.ClosestThingReachable(
                      pawn.Position,
                      pawn.Map,
                      ThingRequest.ForGroup(ThingRequestGroup.Apparel),
                      Verse.AI.PathEndMode.OnCell,
                      TraverseParms.For(pawn),
                      validator: t => !t.IsForbidden(pawn)
                  );

                  if(clothe != null) 
                  {
                    Verse.AI.Job equipJob = JobMaker.MakeJob(JobDefOf.Wear, clothe);
                    pawn.jobs.TryTakeOrderedJob(equipJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "eat":
                  Thing food = GenClosest.ClosestThingReachable(
                      pawn.Position,
                      pawn.Map,
                      ThingRequest.ForGroup(ThingRequestGroup.FoodSourceNotPlantOrTree),
                      Verse.AI.PathEndMode.OnCell,
                      TraverseParms.For(pawn),
                      validator: t => !t.IsForbidden(pawn) && t.IngestibleNow && pawn.WillEat(t)
                  );

                  if(food != null) {
                    Verse.AI.Job eatJob = JobMaker.MakeJob(JobDefOf.Ingest, food);
                    eatJob.count = FoodUtility.WillIngestStackCountOf(pawn, food.def, food.GetStatValue(StatDefOf.Nutrition));

                    pawn.jobs.TryTakeOrderedJob(eatJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "rest":
                  Building_Bed bed = RestUtility.FindBedFor(pawn);

                  if(bed != null) 
                  {
                    Verse.AI.Job restJob = JobMaker.MakeJob(JobDefOf.LayDown, bed);
                    restJob.targetA = bed;

                    pawn.jobs.TryTakeOrderedJob(restJob, Verse.AI.JobTag.SatisfyingNeeds);
                  }

                  break;

                case "kill":
                  Pawn selectedPawn = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                    p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(data, StringComparison.OrdinalIgnoreCase)
                  );

                  if(selectedPawn != null && !selectedPawn.Dead) {
                    Verse.AI.Job attackJob = JobMaker.MakeJob(JobDefOf.AttackMelee, selectedPawn);
                    attackJob.killIncappedTarget = true;
                  
                    pawn.jobs.TryTakeOrderedJob(attackJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "incapacite":
                  Pawn selectedPawn2 = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                    p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(data, StringComparison.OrdinalIgnoreCase)
                  );

                  if(selectedPawn2 != null && !selectedPawn2.Dead) {
                    Verse.AI.Job attackJob = JobMaker.MakeJob(JobDefOf.AttackMelee, selectedPawn2);
                    attackJob.killIncappedTarget = false;
                  
                    pawn.jobs.TryTakeOrderedJob(attackJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "equip_ranged_weapon":
                  Thing weapon2 = GenClosest.ClosestThingReachable(
                      pawn.Position,
                      pawn.Map,
                      ThingRequest.ForGroup(ThingRequestGroup.Weapon),
                      Verse.AI.PathEndMode.OnCell,
                      TraverseParms.For(pawn),
                      validator: t => !t.IsForbidden(pawn) && t.def.IsRangedWeapon
                  );

                  if(weapon2 != null) {
                    Verse.AI.Job equipJob = JobMaker.MakeJob(JobDefOf.Equip, weapon2);
                    pawn.jobs.TryTakeOrderedJob(equipJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "equip_melee_weapon":
                  Thing weapon3 = GenClosest.ClosestThingReachable(
                      pawn.Position,
                      pawn.Map,
                      ThingRequest.ForGroup(ThingRequestGroup.Weapon),
                      Verse.AI.PathEndMode.OnCell,
                      TraverseParms.For(pawn),
                      validator: t => !t.IsForbidden(pawn) && t.def.IsMeleeWeapon
                  );

                  if(weapon3 != null) {
                    Verse.AI.Job equipJob = JobMaker.MakeJob(JobDefOf.Equip, weapon3);
                    pawn.jobs.TryTakeOrderedJob(equipJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "rescue":
                  Pawn selectedPawn4 = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                    p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(data, StringComparison.OrdinalIgnoreCase)
                  );

                  if(selectedPawn4 != null && !selectedPawn4.Dead && selectedPawn4.Downed) {
                    Building_Bed bed2 = RestUtility.FindBedFor(selectedPawn4, pawn, checkSocialProperness: false, ignoreOtherReservations: false, guestStatus: selectedPawn4.GuestStatus);

                    if(bed2 != null) {
                      Verse.AI.Job rescueJob = JobMaker.MakeJob(JobDefOf.Rescue, selectedPawn4, bed2);
                      rescueJob.count = 1;

                      pawn.jobs.TryTakeOrderedJob(rescueJob, Verse.AI.JobTag.Misc);
                    }
                  }

                  break;

                case "arrest":
                  Pawn selectedPawn5 = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                    p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(data, StringComparison.OrdinalIgnoreCase)
                  );

                  Building_Bed prisonBed = RestUtility.FindBedFor(
                      selectedPawn5,
                      pawn,
                      checkSocialProperness: false,
                      ignoreOtherReservations: false,
                      guestStatus: selectedPawn5.GuestStatus
                  );

                  if(prisonBed != null) {
                    Verse.AI.Job arrestJob = JobMaker.MakeJob(JobDefOf.Arrest, selectedPawn5, prisonBed);
                    arrestJob.count = 1;

                    pawn.jobs.TryTakeOrderedJob(arrestJob, Verse.AI.JobTag.Misc);
                  }

                  break;

                case "shoot":
                  Pawn selectedPawn3 = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                    p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(data, StringComparison.OrdinalIgnoreCase)
                  );

                  if(selectedPawn3 != null) {
                    if(pawn.equipment.Primary != null && pawn.equipment.Primary.def.IsRangedWeapon) {
                      Verse.AI.Job shootJob = JobMaker.MakeJob(JobDefOf.AttackStatic, selectedPawn3);
                      pawn.jobs.TryTakeOrderedJob(shootJob, Verse.AI.JobTag.Misc);
                    }
                  }

                  break;
            }
        }

        private string getAction(string action, Pawn pawn) {
          if(action == "getskills") {
            string jsonResponse = "{" +
              $"\"shooting\":{pawn.skills.GetSkill(SkillDefOf.Shooting).Level}," +
              $"\"melee\":{pawn.skills.GetSkill(SkillDefOf.Melee).Level}," +
              $"\"construction\":{pawn.skills.GetSkill(SkillDefOf.Construction).Level}," +
              $"\"mining\":{pawn.skills.GetSkill(SkillDefOf.Mining).Level}," +
              $"\"cooking\":{pawn.skills.GetSkill(SkillDefOf.Cooking).Level}," +
              $"\"plants\":{pawn.skills.GetSkill(SkillDefOf.Plants).Level}," +
              $"\"animals\":{pawn.skills.GetSkill(SkillDefOf.Animals).Level}," +
              $"\"crafting\":{pawn.skills.GetSkill(SkillDefOf.Crafting).Level}," +
              $"\"artistic\":{pawn.skills.GetSkill(SkillDefOf.Artistic).Level}," +
              $"\"medical\":{pawn.skills.GetSkill(SkillDefOf.Medicine).Level}," +
              $"\"social\":{pawn.skills.GetSkill(SkillDefOf.Social).Level}," +
              $"\"intellectual\":{pawn.skills.GetSkill(SkillDefOf.Intellectual).Level}" +
            "}";

            return jsonResponse;

          } else if(action == "getneeds") {
            float foodLevel = pawn.needs.food != null ? pawn.needs.food.CurLevelPercentage : 0f;
            float restLevel = pawn.needs.rest != null ? pawn.needs.rest.CurLevelPercentage : 0f;
            float moodLevel = pawn.needs.mood != null ? pawn.needs.mood.CurLevelPercentage : 0f;

            string jsonResponse = "{" +
              $"\"mood\":{moodLevel}," +
              $"\"rest\":{restLevel}," +
              $"\"food\":{foodLevel}" +
            "}";

            return jsonResponse;

          } else if(action == "gethealth") {
            var healthConditions = pawn.health.hediffSet.hediffs.Select(h => 
              $"{{\"label\":\"{h.LabelCap}\",\"severity\":{h.Severity},\"part\":\"{(h.Part != null ? h.Part.Label : "General")}\"}}"
            ).ToList();

            string jsonResponse = "{ \"health\": [" + string.Join(",", healthConditions) + "] }";

            return jsonResponse;

          } else if(action == "getequipment") {
            List<string> itemsFormatted = new List<string>();

            if (pawn.equipment != null)
            {
                foreach (ThingWithComps eq in pawn.equipment.AllEquipmentListForReading)
                {
                    itemsFormatted.Add($"\"{eq.LabelCap}\"");
                }
            }

            if (pawn.apparel != null)
            {
                foreach (Apparel clothing in pawn.apparel.WornApparel)
                {
                    itemsFormatted.Add($"\"{clothing.LabelCap}\"");
                }
            }

            string itemsArray = string.Join(",", itemsFormatted);

            string jsonResponse = "{" +
                $"\"equipment\":[{itemsArray}]" +
            "}";

            return jsonResponse;
          }

          return "nothing here";
        }

        public static HttpListener listener;
        public static int totalPlayers;
        public static Thread serverThread;
        public static List<string> pendingCharacters = new List<string>();
        private static ConcurrentQueue<Action> actionQueue = new ConcurrentQueue<Action>();

        public override void FinalizeInit()
        {
          base.FinalizeInit();
        }

        private void SendResponse(HttpListenerContext ctx, string response) {
          byte[] buffer = System.Text.Encoding.UTF8.GetBytes(response);
          ctx.Response.ContentLength64 = buffer.Length;
          ctx.Response.OutputStream.Write(buffer, 0, buffer.Length);
          ctx.Response.OutputStream.Close();
        }

        public static Pawn GenerateRandomPawn(string nickname) {
          if(!ModsConfig.BiotechActive) {
            Log.Error("Biotech is not active...");
            return null;
          }

          Pawn newPawn = StartingPawnUtility.NewGeneratedStartingPawn();
          XenotypeDef randomXenotype = DefDatabase<XenotypeDef>.AllDefs.RandomElement();

          Pawn_GeneTracker genes = newPawn.genes;

          if(genes != null) {
            genes.SetXenotype(randomXenotype);
          }

          if (newPawn.Name is NameTriple nameTriple) {
              newPawn.Name = new NameTriple(nameTriple.First, nickname, nameTriple.Last);
          } else if (newPawn.Name is NameSingle nameSingle) {
              newPawn.Name = new NameSingle(nickname);
          }

          Log.Message("[ Server Mod ] name debug: " + nickname);

          return newPawn;
        }

        [HarmonyPatch(typeof(Page_ConfigureStartingPawns), "PreOpen")]
        public static class InjectCharacter {
          public static void Postfix() {
            // please work omfgggg
            if(Current.Game?.InitData == null) return;
            if(ServerComponent.pendingCharacters.Count == 0) return;

            foreach(var nickname in ServerComponent.pendingCharacters) {
              Pawn newPawn = ServerComponent.GenerateRandomPawn(nickname);

              Log.Message("[ Server Mod ] Creating new pawn...");

              if(newPawn != null) {
                Current.Game.InitData.startingAndOptionalPawns.Insert(0, newPawn);
                totalPlayers++;
                Current.Game.InitData.startingPawnCount = totalPlayers;

                Log.Message("[ Server Mod ] New pawn created!");
              }
            }

            ServerComponent.pendingCharacters.Clear();
          }
        }

        private void RequestListener() {
          while(listener.IsListening) {
            try {
              HttpListenerContext ctx = listener.GetContext();

              string requestUrl = ctx.Request.Url.AbsolutePath;
              NameValueCollection queryParams = ctx.Request.QueryString;

              string pawnNickname = queryParams["pawn"];
              string data = queryParams["data"].NullOrEmpty() ? "" : queryParams["data"];
              string complement = queryParams["complement"].NullOrEmpty() ? "" : queryParams["complement"];

              actionQueue.Enqueue(() => {
                Log.Message("[ Server Mod ] Executing action tree...");

                if(Current.Game != null && Current.Game.InitData != null) {
                  if(requestUrl[1..] == "create_character") {
                    var page = Find.WindowStack.WindowOfType<Page_ConfigureStartingPawns>();

                    if(page != null) 
                    {
                        Pawn newPawn = ServerComponent.GenerateRandomPawn(pawnNickname);

                        Log.Message("[ Server Mod ] Creating new pawn...");

                        if(newPawn != null) {
                          Current.Game.InitData.startingAndOptionalPawns.Insert(0, newPawn);
                          totalPlayers++;
                          Current.Game.InitData.startingPawnCount = totalPlayers;

                          Log.Message("[ Server Mod ] New pawn created!");
                        } 
                    } else {
                      pendingCharacters.Add(pawnNickname);
                    }

                    Log.Message($"[ Server Mod ] Added new character: {pawnNickname}");
                  }

                  SendResponse(ctx, "sent");
                  return;
                }

                Pawn selectedPawn = Find.CurrentMap.mapPawns.FreeColonists.FirstOrDefault(
                  p => p.Name is NameTriple nameTriple && nameTriple.Nick.Equals(pawnNickname, StringComparison.OrdinalIgnoreCase)
                );
                
                if(selectedPawn == null || selectedPawn.Dead) {
                  SendResponse(ctx, "Pawn dead or doesn't exists!!!");
                  return;
                }

                if(requestUrl == "/gethealth" || requestUrl == "/getskills" || requestUrl == "/getneeds" || requestUrl == "/getequipment") {
                  string response = getAction(requestUrl[1..], selectedPawn);
                  SendResponse(ctx, response);

                  return;
                }

                ProcessAction(requestUrl[1..], data, complement, selectedPawn);
                SendResponse(ctx, "Request sent");
              });
            } catch(Exception) {}
          }

          actionQueue.Enqueue(() => {
              Log.Message("[ Server Mod ] The server has been killed!");
          });
        }

        public override void ExposeData() 
        {
          base.ExposeData();
        }

        private void StartServer()
        {
          if(listener != null && listener.IsListening) {
            listener.Close();
          }

          totalPlayers = 0;

          listener = new HttpListener();
          listener.Prefixes.Add("http://localhost:9891/");
          listener.Start();

          serverThread = new Thread(RequestListener);
          serverThread.Start();

          Log.Message("[ Server Mod ] server instace created on http://localhost:9891");
        }

        public static void CloseServer() 
        {
          if(serverThread.IsAlive) {
            serverThread.Abort();
          }

          if(listener.IsListening) {
            listener.Close();
          }

          Log.Message("[ Server Mod ] Server instance cleaned");
        }

        public static void Update() {
          while(actionQueue.TryDequeue(out Action actionToExecute)) {
            try {
              Log.Message("[ Server Mod ] Trying to execute action on queue...");
              actionToExecute.Invoke();

            } catch(Exception ex) {
              Log.Error("[ Server Mod ] Error: " + ex.Message);
            }
          }
        }

        [HarmonyPatch(typeof(GenScene), nameof(GenScene.GoToMainMenu))]
        public static class GoToMainMenu 
        {
          public static void Prefix() 
          {
            CloseServer();
          }
        }

        public ServerComponent(Game game) {
          var harmony = new Harmony("com.hazu.rimworld.servermod");
          var original = AccessTools.Method(typeof(Root_Entry), "Update"); // primer parche para estar conectado al menú principal
          var postfix = AccessTools.Method(typeof(ServerComponent), nameof(Update));
          harmony.Patch(original, postfix: new HarmonyMethod(postfix));

          var original2 = AccessTools.Method(typeof(Root_Play), "Update"); // segundo parche para estar conectado en el juego principal
          harmony.Patch(original2, postfix: new HarmonyMethod(postfix));

          StartServer();

          harmony.PatchAll();
        }
    }
}
