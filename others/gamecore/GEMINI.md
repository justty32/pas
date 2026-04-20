# gamecore - Project Context

## Project Overview
`gamecore` is a multi-layered game engine and game project designed with a clear separation between frontend and backend. The project aims to implement three distinct scales of gameplay:
1.  **World Layer:** A tiled-based, turn-based strategy game (similar to Civilization V).
2.  **Region Layer:** A tactical layer that can be RTS-like, a tiled strategy game (similar to Battle for Wesnoth), or a menu-driven interface (similar to Mount & Blade).
3.  **Zone Layer:** High-detail gameplay ranging from 3D action (Skyrim/Minecraft-like) to 2D action (Rimworld-like) or JRPG (Tales of Maj'Eyal/Elona-like).

### Tech Stack
-   **Frontend:** [Godot Engine](https://godotengine.org/) (UI, Display, Input handling).
-   **Backend:** [GDExtension](https://docs.godotengine.org/en/stable/tutorials/scripting/gdextension/what_is_gdextension.html) with **C++** (Core game logic and heavy calculations).

## Architecture & Roadmap
The project follows a hierarchical "World -> Region -> Zone" structure. Logics are calculated in the C++ backend, while the Godot frontend handles immediate reactions and visual conclusions.

### Current Roadmap
1.  **Phase 1:** Implement a simple tiled-base, turn-based strategy game (World Layer).
2.  **Phase 2:** Implement a simple tile-based JRPG (Zone Layer).
3.  **Phase 3:** Implement a tiled-based strategy game for the Region Layer.

## Building and Running
> [!IMPORTANT]
> This project is currently in the conceptual/design phase. No build scripts or source code are present in the root directory yet.

-   **Godot Setup:** Requires Godot Engine (version to be determined, likely 4.x for GDExtension).
-   **C++ Backend:** Requires a C++ compiler and potentially `scons` for GDExtension builds.
-   **TODO:** Define specific build commands (e.g., `scons platform=linux`) once the project structure is initialized.

## Development Conventions
-   **Logic Separation:** All heavy game state logic must reside in the C++ backend.
-   **Frontend Responsibilities:** Godot should handle rendering, animations, and UI feedback based on the state provided by the C++ core.
-   **Coordinate Systems:**
    -   World Layer: Tile-based (non-hexagonal as per roadmap).
    -   Zone/Region: To be defined based on the chosen implementation (3D Action vs 2D Tile).
