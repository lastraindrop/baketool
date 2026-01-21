# BakeTool Development Roadmap (v1.0 & Beyond)

This roadmap outlines the long-term vision for transforming BakeTool into a professional-grade baking middleware within Blender.

## Phase 1: Interactive Viewport (Quality of Life)
*   **Live Preview Shader**: Real-time visual confirmation of channel packing and baking results.
*   **Asynchronous Processing**: Ensure the Blender UI remains responsive during long bake sessions.
*   **UI/UX Modernization**: Transition from a property-list interface to a dedicated "Baking Workspace" tab.

## Phase 2: Intelligence & Optimization (Workflow Efficiency)
*   **Auto-Cage 2.0**: Intelligent proximity-based cage generation for High-to-Low poly baking.
*   **Automated Texel Density Management**: Smart integration with UV Packing workflows to normalize texel resolution across UDIM tiles.
*   **Material Semantic Parsing**: Preset auto-detection based on Blender material node structures.

## Phase 3: Engine Ecosystem (Integration)
*   **Advanced Game Engine Profiles**: One-click export profiles for Unreal Engine (Packed ORM), Unity (HDRP/URP), and Godot.
*   **Live Link Connection**: Direct asset bridging to Substance Painter and external game editors.
*   **Standardized API**: Formalize the `core.engine` API for 3rd-party plugin developers.

## Phase 4: High-End Production (Advanced Features)
*   **AI Denoising for Baking**: Specifically tuned denoising to preserve normal map details.
*   **Decal Baking Support**: Automatic projection of floating decals onto surface textures.
*   **Sparse UDIM/10k Support**: Efficient handling of extreme-resolution assets for film and high-end automotive visualization.

---

*Note: This roadmap is a living document and will be updated as community feedback and new Blender API features (like Grease Pencil 3.0 or geometry nodes updates) emerge.*
