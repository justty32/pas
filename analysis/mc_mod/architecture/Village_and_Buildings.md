# Village & Building Management

The heart of Millénaire is its village system, where NPCs interact, trade, and build structures over time.

## 🏘️ Village Structure (`common.village`)
- **`Building`**: Represents an individual structure in a village. Tracks its level, resources, and current inhabitants.
- **`BuildingLocation`**: Stores coordinates, orientation, and boundaries for a planned or existing building.
- **`Village`**: The top-level manager for a collection of buildings and villagers. Handles reputation, community chests, and inter-village relations.
- **`BuildingManager`**: Coordinates construction tasks and resource allocation within a building or village.

## 📐 Building Plans (`common.buildingplan`)
Millénaire uses a unique system for defining buildings:
- **Plan Formats**: Originally used PNG-based floor plans where colors mapped to block types. Reborn may transition to more modern formats (e.g., NBT/JSON) while maintaining compatibility with legacy plans.
- **`BuildingPlan`**: Interprets the layout, required materials, and upgrade paths for a structure.
- **`BuildingBlock`**: A specialized representation of a block within a plan, allowing for metadata and cultural variations.
- **Upgrades**: Buildings can evolve through multiple levels (e.g., from a wooden hut to a stone house) by consuming resources collected by villagers.

## 🌍 World Generation
- **Village Placement**: Logic for finding suitable biomes and terrain for different culture types (e.g., Inuits in cold biomes, Mayans in jungles).
- **Lone Buildings**: Isolated structures (e.g., hermit huts, small farms) that exist outside of full villages.
