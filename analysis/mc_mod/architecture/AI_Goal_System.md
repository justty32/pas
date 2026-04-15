# AI & Goal System

Millénaire NPCs are driven by a sophisticated "Goal" system rather than standard Minecraft AI tasks, allowing for highly complex and specialized behaviors.

## 🧠 The Goal System (`common.goal`)
- **`Goal`**: The base class for all NPC behaviors. Each goal defines its priority, prerequisites, and execution logic.
- **Goal Types**:
    - **Generic Goals**: Basic survival needs like `GoalSleep`, `GoalEat`.
    - **Economic Goals**: Resource gathering (`GoalLumbermanChopTrees`), crafting (`GoalIndianDryBrick`), and trading (`GoalBeSeller`).
    - **Construction Goals**: The complex multi-step process of building structures (`GoalConstructionStepByStep`).
    - **Social & Leisure**: Interactions between villagers (`GoalChildBecomeAdult`, leisure activities).
    - **Combat**: Defending the village or raiding others (`GoalDefendVillage`, `GoalRaidVillage`).

## 🚶 NPC Entity (`MillVillager`)
- **Data Tracking**: Each villager has a unique identity, profession, family, and inventory.
- **Pathfinding**: Custom pathfinding logic (optimized for village layouts and multi-level buildings).
- **Rendering**: Specialized models and textures that vary by culture, profession, and growth stage (child to adult).

## 📅 Porting Challenges
- **AI Refactoring**: Translating the legacy goal logic to Fabric/Minecraft 1.21.8 entity systems.
- **Performance**: Optimizing the pathfinding and decision-making for large villages with dozens of active NPCs.
