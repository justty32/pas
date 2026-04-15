/*
 * Taisei Project Tutorial Example: Basic Bullet Patterns
 * 
 * 展示如何使用 Task DSL 實現常見的彈幕模式：
 * 1. 定點圓形射擊 (Ring)
 * 2. 瞄準玩家射擊 (Aimed/Streaming)
 * 3. 螺旋路徑 (Spiral)
 * 4. 自定義移動邏輯 (Custom Move)
 */

#include "stages/common_imports.h"

// --- 模式 1: 簡單的圓形射擊 ---
TASK(pattern_ring, { BoxedEnemy e; int count; double speed; }) {
    Enemy *e = TASK_BIND(ARGS.e);
    double start_angle = rng_angle(); // 隨機起始角度

    for(int i = 0; i < ARGS.count; ++i) {
        double a = start_angle + (M_TAU / ARGS.count) * i;
        PROJECTILE(
            .proto = pp_ball,
            .pos = e->pos,
            .color = RGB(0.2, 0.8, 0.4),
            .move = move_linear(ARGS.speed * cdir(a))
        );
    }
    play_sfx("shot1");
}

// --- 模式 2: 瞄準玩家的流動射擊 (Streaming) ---
TASK(pattern_aimed_stream, { BoxedEnemy e; int burst; int interval; }) {
    Enemy *e = TASK_BIND(ARGS.e);

    for(int i = 0; i < ARGS.burst; ++i) {
        // 獲取指向玩家的單位向量
        cmplx aim = cnormalize(global.plr.pos - e->pos);
        
        PROJECTILE(
            .proto = pp_rice,
            .pos = e->pos,
            .color = RGB(1.0, 0.2, 0.2),
            .move = move_asymptotic_simple(aim * 3, 5) // 速度漸漸增加
        );

        play_sfx_loop("shot1_loop");
        WAIT(ARGS.interval);
    }
}

// --- 模式 3: 螺旋擴散 (Spiral) ---
TASK(pattern_spiral, { BoxedEnemy e; int duration; }) {
    Enemy *e = TASK_BIND(ARGS.e);
    double angle = 0;

    for(int t = 0; t < ARGS.duration; ++t) {
        angle += 0.2; // 每一幀旋轉一點
        
        PROJECTILE(
            .proto = pp_crystal,
            .pos = e->pos,
            .color = RGB(0.3, 0.3, 0.9),
            .move = move_linear(2 * cdir(angle))
        );

        if(t % 4 == 0) play_sfx_loop("shot1_loop");
        WAIT(1);
    }
}

// --- 整合：一個完整的敵人行為範例 ---
TASK(example_enemy_behavior, { cmplx start_pos; }) {
    // 生成一個大妖精 (espawn_big_fairy)
    Enemy *e = TASK_BIND(espawn_big_fairy(ARGS.start_pos, ITEMS(.points = 5, .power = 2)));
    
    // 進入屏幕
    e->move = move_from_towards(e->pos, VIEWPORT_W/2 + 100*I, 0.03);
    WAIT(80);
    e->move.velocity = 0;
    e->move.attraction = 0;

    // 階段 1: 先來幾圈圓形彈幕
    for(int i = 0; i < 4; ++i) {
        INVOKE_SUBTASK(pattern_ring, ENT_BOX(e), .count = 16, .speed = 1.5 + i*0.2);
        WAIT(30);
    }

    // 階段 2: 同時啟動螺旋和瞄準射擊 (並發任務)
    INVOKE_TASK(pattern_spiral, ENT_BOX(e), .duration = 120);
    WAIT(30);
    INVOKE_SUBTASK(pattern_aimed_stream, ENT_BOX(e), .burst = 10, .interval = 5);

    WAIT(60);

    // 逃離並銷毀
    e->move.acceleration = -0.05 * I + 0.02; // 向右上方加速
    STALL;
}
