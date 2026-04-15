# Content Registration & Asset Pipeline

The registration system in Millénaire Reborn is designed to handle a massive amount of content (163+ items, 200+ blocks) efficiently using Fabric's Registry API.

## 📦 Registry System (`common.registry`)
- **`MillRegistry`**: A utility class providing helper methods for registration, ensuring consistent naming and namespace handling.
- **`MillItems`**: Central hub for all item registrations. Items are categorized by their respective cultures (Norman, Byzantine, etc.).
- **`MillBlocks`**: Registers all custom blocks, including culture-specific building materials.
- **`MillCustomMaterials`**: Defines `ToolMaterial` and `ArmorMaterial` for various historical tiers.
- **`MillCreativeTabs`**: Organizes items into multiple creative tabs, one for each culture, providing a clean user experience.
- **`MillFoodItemBuilder`**: A specialized builder for defining food properties (hunger, saturation, effects) concisely.

## 🎨 Asset Management
The mod heavily utilizes **Fabric Data Generation** to automate asset creation:
- **Models & Blockstates**: Automatically generated for items and simple blocks.
- **Localization**: English and German translations are managed through datagen or structured JSON files.
- **Item Model Descriptions**: Uses the 1.21.8 system for complex item rendering and variants.

## 🔨 Planned Improvements
- **Dynamic Block Properties**: Porting the complex block behavior from `OldSource` (e.g., specialized crafting blocks).
- **Custom Item Functionality**: Implementing unique behaviors for special items like the *Negation Wand* or *Amulets*.
