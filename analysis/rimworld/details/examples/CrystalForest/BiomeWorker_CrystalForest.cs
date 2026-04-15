using Verse;
using RimWorld;
using RimWorld.Planet;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：生態系分布規則。
/// 決定「晶礦森林」在大地圖上的出現位置。
/// </summary>
public class BiomeWorker_CrystalForest : BiomeWorker
{
    public override float GetScore(Tile tile, int tileID)
    {
        // 1. 基本條件：不生成在水面上
        if (tile.WaterCovered) return -100f;

        // 2. 氣候規則：
        // 我們希望它是一個神祕、微涼的森林
        // 最佳溫度: 0 到 12 度
        // 最佳降雨: 1500 到 2500 mm
        
        if (tile.temperature < -10f || tile.temperature > 15f) return 0f;
        if (tile.rainfall < 800f) return 0f;

        // 3. 計算分數：
        // 降雨越豐富，分數越高
        float score = 10f;
        score += (tile.rainfall - 800f) / 100f;

        // 4. 特色分布：如果附近有山脈，加成更高 (假設模擬晶礦在山區邊緣)
        if (tile.hilliness == Hilliness.SmallHills || tile.hilliness == Hilliness.LargeHills)
        {
            score += 15f;
        }

        return score;
    }
}
