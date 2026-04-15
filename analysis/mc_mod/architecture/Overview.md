# Project Overview - Millénaire Reborn

Millénaire Reborn is a comprehensive port of the "Millénaire" mod from Minecraft 1.12.2 (Forge) to 1.21.8 (Fabric). The mod's primary goal is to fill the Minecraft world with vibrant, historical human villages from various cultures around the year 1000 AD.

## 🎯 Project Goals
- **High Fidelity:** Restore all features from the original mod, including complex NPC AI, village growth, and quest systems.
- **Modern Standards:** Use Fabric's modern APIs (e.g., RegistryKey, Data Generation) for better performance and maintainability.
- **Clean Architecture:** Refactor the original monolithic classes into more modular, decoupled components.

## 🏗️ Core Packages (Planned/Current)
- `me.devupdates.millenaireReborn`: Root package containing entry points.
- `common.registry`: Centralized registration for all game objects.
- `common.entity`: NPC entities (MillVillager) and their rendering.
- `common.village`: Logic for village management, building placement, and growth.
- `common.buildingplan`: System for loading and interpreting building templates (PNG/JSON).
- `common.goal`: The complex AI system defining villager behaviors.
- `common.culture`: Definitions for the 7+ historical cultures.
- `common.network`: Custom packet handling for village/player synchronization.
- `common.quest`: Quest definitions and progression logic.

## 🔄 Porting Strategy
The project uses `OldSource/` as a reference for original logic.
1. **Registry & Assets:** Porting basic items and blocks (Phase 1-2 - *Complete*).
2. **Functionality:** Adding tool/armor/food logic (Phase 3 - *In Progress*).
3. **Entities & AI:** Porting the complex goal-based AI (Phase 5).
4. **World Gen:** Implementing the structure and village generation system (Phase 6).
5. **Gameplay:** Restoring trading, reputation, and quests (Phase 7).
