using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Verse;
using RimWorld;
using HarmonyLib;

namespace RimWorldARPG.Examples
{
    /* 
     * 範例 1: WASD 角色移動控制
     * 實作思路: 透過 MapComponent 每幀監聽按鍵，並驅動 Pawn 的 Pather。
     */
    public class ARPG_ControlComponent : MapComponent
    {
        public ARPG_ControlComponent(Map map) : base(map) { }

        public override void MapComponentTick()
        {
            // 僅在玩家選中單一角色且處於特定模式時觸發
            Pawn selectedPawn = Find.Selector.SingleSelectedPawn;
            if (selectedPawn != null && selectedPawn.IsColonistPlayerControlled && !selectedPawn.Downed)
            {
                HandleWASDMovement(selectedPawn);
            }
        }

        private void HandleWASDMovement(Pawn pawn)
        {
            Vector3 direction = Vector3.zero;
            if (Input.GetKey(KeyCode.W)) direction += Vector3.forward;
            if (Input.GetKey(KeyCode.S)) direction += Vector3.back;
            if (Input.GetKey(KeyCode.A)) direction += Vector3.left;
            if (Input.GetKey(KeyCode.D)) direction += Vector3.right;

            if (direction != Vector3.zero)
            {
                // 計算目標格子 (目前的座標 + 方向向量)
                IntVec3 targetCell = (pawn.DrawPos + direction.normalized).ToIntVec3();
                
                // 如果目標格與當前格子不同，且可以通行
                if (targetCell != pawn.Position && targetCell.Walkable(pawn.Map))
                {
                    // 驅動路徑尋找器立即移動
                    pawn.pather.StartPath(targetCell, PathEndMode.OnCell);
                }
            }
        }
    }

    /* 
     * 範例 2: 近戰扇形範圍傷害 (Cleave)
     * 實作思路: 透過 Harmony Patch 攔截近戰攻擊，改為 AOE 判定。
     */
    [HarmonyPatch(typeof(Verb_MeleeAttack), "TryCastShot")]
    public static class Patch_MeleeCleave
    {
        [HarmonyPrefix]
        public static bool Prefix(Verb_MeleeAttack __instance, ref bool __result)
        {
            Pawn attacker = __instance.CasterPawn;
            LocalTargetInfo target = __instance.CurrentTarget;

            if (attacker == null || !target.HasThing) return true; // 執行原版邏輯

            // 獲取攻擊範圍內的目標 (假設我們有一種「巨劍」或特定技能)
            // 這裡簡化為以目標方向為中心的扇形
            float attackAngle = (target.Cell - attacker.Position).AngleFlat;
            float cleaveAngle = 60f; // 60度扇形
            float range = 2.9f;     // 近戰距離

            IEnumerable<Pawn> targets = attacker.Map.mapPawns.AllPawnsSpawned
                .Where(p => p.HostileTo(attacker) && !p.Downed)
                .Where(p => p.Position.DistanceTo(attacker.Position) <= range)
                .Where(p => Math.Abs(BoundAngle(p.Position.AngleFlat - attackAngle)) <= cleaveAngle / 2);

            foreach (var victim in targets)
            {
                // 執行傷害分配
                BattleLogEntry_MeleeCombat battleLogEntry_MeleeCombat = CreateBattleLog(__instance, attacker, victim);
                DamageInfo dinfo = new DamageInfo(DamageDefOf.Cut, 10f, 0f, -1f, attacker);
                victim.TakeDamage(dinfo).AssociateWithLog(battleLogEntry_MeleeCombat);
                
                // 播放特效
                MoteMaker.ThrowMicroSparks(victim.DrawPos, attacker.Map);
            }

            __result = true; 
            return false; // 攔截原版單體攻擊邏輯
        }

        private static float BoundAngle(float angle)
        {
            while (angle > 180) angle -= 360;
            while (angle < -180) angle += 360;
            return angle;
        }

        private static BattleLogEntry_MeleeCombat CreateBattleLog(Verb verb, Pawn attacker, Pawn victim)
        {
            // 實作戰鬥日誌紀錄 (略)
            return null; 
        }
    }

    /* 
     * 範例 3: 能量系統 (Mana)
     * 實作思路: 使用 ThingComp 擴充 Pawn 屬性。
     */
    public class CompManaPool : ThingComp
    {
        public float currentMana;
        public float maxMana = 100f;
        public float regenRate = 5f; // 每秒恢復

        public override void CompTick()
        {
            if (currentMana < maxMana)
            {
                currentMana = Math.Min(maxMana, currentMana + (regenRate / 60f));
            }
        }

        public override void PostExposeData()
        {
            base.PostExposeData();
            Scribe_Values.Look(ref currentMana, "currentMana", 0f);
            Scribe_Values.Look(ref maxMana, "maxMana", 100f);
        }
    }
}
