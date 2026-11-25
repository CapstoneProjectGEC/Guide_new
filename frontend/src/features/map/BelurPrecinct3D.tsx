import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  TempleAttraction,
  UNESCO_COMPLEX_STRUCTURES,
  TEMPLE_ARCHITECTURAL_FEATURES,
  TempleArchitecturalFeature,
  UI_STRINGS,
} from "@/theme/tokens";
import {
  Compass,
  RotateCcw,
  Sun,
  Sunset,
  Moon,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Info,
  Camera,
  Layers,
  Sparkles,
  Eye,
} from "lucide-react";

export type LightingPreset = "droneDaylight" | "goldenHour" | "dusk";

interface BelurPrecinct3DProps {
  selectedAttraction: TempleAttraction;
  onSelectAttraction: (attraction: TempleAttraction) => void;
  selectedArchitectureFeature?: TempleArchitecturalFeature | null;
  onSelectArchitectureFeature?: (feature: TempleArchitecturalFeature) => void;
  activeLayer?: "complex" | "architecture";
  onLayerChange?: (layer: "complex" | "architecture") => void;
  language: "kn" | "en";
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  isDark: boolean;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

interface BeaconNode {
  id: string;
  type: "complex" | "architecture";
  nameEn: string;
  nameKn: string;
  categoryEn?: string;
  categoryKn?: string;
  position: THREE.Vector3;
  cameraOffset: THREE.Vector3;
  lookAt: THREE.Vector3;
}

export const BelurPrecinct3D: React.FC<BelurPrecinct3DProps> = ({
  selectedAttraction,
  onSelectAttraction,
  selectedArchitectureFeature,
  onSelectArchitectureFeature,
  activeLayer = "complex",
  onLayerChange,
  language,
  isFullscreen,
  onToggleFullscreen,
  isDark,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [lighting, setLighting] = useState<LightingPreset>("droneDaylight");
  const [isAutoRotating, setIsAutoRotating] = useState<boolean>(false);
  const [hoveredNode, setHoveredNode] = useState<BeaconNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const [activeCameraPreset, setActiveCameraPreset] = useState<"top" | "side" | "front" | "gopura" | "anatomy">("top");

  const t = UI_STRINGS[language];

  // References across render loop
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const complexBeaconsRef = useRef<THREE.Group[]>([]);
  const architectureBeaconsRef = useRef<THREE.Group[]>([]);
  const clickableObjectsRef = useRef<THREE.Object3D[]>([]);

  // 1. Top View (Aerial Drone View - Image 4): matches real aerial photograph perspective looking West-Southwest
  const topViewPos = useMemo(() => new THREE.Vector3(0, 52, 60), []);
  const topViewLook = useMemo(() => new THREE.Vector3(0, 2, -2), []);

  // 2. Side Angle View (Temple Detail - Image 3): shows tiered star Jagati plinth, perforated Jali lattice, and eaves
  const sideViewPos = useMemo(() => new THREE.Vector3(17, 5.2, 10), []);
  const sideViewLook = useMemo(() => new THREE.Vector3(2, 3.8, 0), []);

  // 3. Front Elevation View (Matches real panoramic photo media_1793860799907_c18594ef.jpg):
  // Straight-on eye-level view from the East courtyard facing the main temple entrance facade
  const templeFrontViewPos = useMemo(() => new THREE.Vector3(2, 3.6, 15.8), []);
  const templeFrontViewLook = useMemo(() => new THREE.Vector3(2, 3.2, 5.5), []);

  // 4. Front Gopura View (Mahadvara - Image 2): looking up at the 7-tiered golden Raya Gopura
  const gopuraViewPos = useMemo(() => new THREE.Vector3(2, 5.5, 46), []);
  const gopuraViewLook = useMemo(() => new THREE.Vector3(2, 12, 29), []);

  // 5. Architecture Layer Default View: focused close-up on Main Temple interior anatomy
  const archViewPos = useMemo(() => new THREE.Vector3(2, 10, 14), []);
  const archViewLook = useMemo(() => new THREE.Vector3(2, 3.8, 1), []);

  const cameraTargetRef = useRef<{
    pos: THREE.Vector3;
    look: THREE.Vector3;
    animating: boolean;
  }>({
    pos: topViewPos.clone(),
    look: topViewLook.clone(),
    animating: false,
  });

  // Dynamic light references
  const dirLightRef = useRef<THREE.DirectionalLight | null>(null);
  const hemiLightRef = useRef<THREE.HemisphereLight | null>(null);
  const diyaLightsRef = useRef<THREE.PointLight[]>([]);

  // 18 UNESCO Complex Sites Spatial Mapping (Figure 2.5 UNESCO Nomination Dossier)
  const complexNodes: BeaconNode[] = useMemo(
    () => [
      {
        id: "chennakeshava-main-temple",
        type: "complex",
        nameEn: "1. Chennakeshava Main Temple",
        nameKn: "೧. ಚೆನ್ನಕೇಶವ ಮುಖ್ಯ ದೇವಾಲಯ",
        categoryEn: "Main Shrine",
        categoryKn: "ಮುಖ್ಯ ಗರ್ಭಗುಡಿ",
        position: new THREE.Vector3(2, 7.5, -2),
        cameraOffset: new THREE.Vector3(2, 3.6, 15.8),
        lookAt: new THREE.Vector3(2, 3.2, 5.5),
      },
      {
        id: "kappe-chennigaraya",
        type: "complex",
        nameEn: "2. Kappe Chennigaraya Temple",
        nameKn: "೨. ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ದೇವಾಲಯ",
        categoryEn: "Subsidiary Shrine",
        categoryKn: "ರಾಣಿ ಶಾಂತಲಾದೇವಿ ಸನ್ನಿಧಿ",
        position: new THREE.Vector3(-26.5, 5.2, 3),
        cameraOffset: new THREE.Vector3(-26.5, 4.8, 17.5),
        lookAt: new THREE.Vector3(-26.5, 2.8, 3),
      },
      {
        id: "vira-narayana",
        type: "complex",
        nameEn: "3. Vira Narayana Temple",
        nameKn: "೩. ವೀರನಾರಾಯಣ ದೇವಾಲಯ",
        categoryEn: "Vaishnava Shrine",
        categoryKn: "ವೈಷ್ಣವ ದೇವಾಲಯ",
        position: new THREE.Vector3(2, 4.8, -25.5),
        cameraOffset: new THREE.Vector3(2.5, 3.2, -17.0),
        lookAt: new THREE.Vector3(2.0, 2.4, -25.0),
      },
      {
        id: "saumyanayaki",
        type: "complex",
        nameEn: "4. Saumyanayaki Temple",
        nameKn: "೪. ಸೌಮ್ಯನಾಯಕಿ ದೇವಾಲಯ",
        categoryEn: "Goddess Shrine",
        categoryKn: "ದೇವಿಯ ಸನ್ನಿಧಿ",
        position: new THREE.Vector3(-18, 6.2, -21),
        cameraOffset: new THREE.Vector3(-10, 8.5, -13),
        lookAt: new THREE.Vector3(-18, 3.2, -21),
      },
      {
        id: "ranganayaki-andal",
        type: "complex",
        nameEn: "5. Ranganayaki / Andal Temple",
        nameKn: "೫. ರಂಗನಾಯಕಿ / ಆಂಡಾಳ್ ಸನ್ನಿಧಿ",
        categoryEn: "Subsidiary Shrine",
        categoryKn: "ಆಂಡಾಳ್ ಸನ್ನಿಧಿ",
        position: new THREE.Vector3(18.5, 6.2, -20.5),
        cameraOffset: new THREE.Vector3(24.5, 3.8, -9.5),
        lookAt: new THREE.Vector3(18.5, 2.8, -20.5),
      },
      {
        id: "vasudeva-sarovara",
        type: "complex",
        nameEn: "6. Vasudeva Sarovara",
        nameKn: "೬. ವಾಸುದೇವ ಸರೋವರ (ಕಲ್ಯಾಣಿ)",
        categoryEn: "Temple Tank",
        categoryKn: "ಪವಿತ್ರ ತೀರ್ಥ",
        position: new THREE.Vector3(36.6, 2.2, 19.6),
        cameraOffset: new THREE.Vector3(44, 8.5, 29),
        lookAt: new THREE.Vector3(36.6, -0.5, 19.6),
      },
      {
        id: "mahadvara",
        type: "complex",
        nameEn: "7. Mahadvara (Raya Gopura)",
        nameKn: "೭. ಮಹಾದ್ವಾರ (ರಾಯ ಗೋಪುರ)",
        categoryEn: "Main Entrance",
        categoryKn: "ಮುಖ್ಯ ಪ್ರವೇಶದ್ವಾರ",
        position: new THREE.Vector3(2, 12, 29),
        cameraOffset: new THREE.Vector3(2, 6.0, 46),
        lookAt: new THREE.Vector3(2, 12, 29),
      },
      {
        id: "elephant-gate",
        type: "complex",
        nameEn: "8. Elephant Gate",
        nameKn: "೮. ಆನೆ ಬಾಗಿಲು (ದ್ವಾರ)",
        categoryEn: "Secondary Entrance",
        categoryKn: "ಉಪ ಪ್ರವೇಶ ದ್ವಾರ",
        position: new THREE.Vector3(-39, 4, 16),
        cameraOffset: new THREE.Vector3(-48, 10, 18),
        lookAt: new THREE.Vector3(-39, 3, 16),
      },
      {
        id: "garuda-shrine-dvaja-stambha",
        type: "complex",
        nameEn: "9. Garuda Shrine and Dvaja Stambha",
        nameKn: "೯. ಗರುಡ ಮಂಟಪ ಮತ್ತು ಧ್ವಜಸ್ತಂಭ",
        categoryEn: "Garuda & Flagstaff",
        categoryKn: "ಗರುಡ ಸನ್ನಿಧಿ ಮತ್ತು ಧ್ವಜಸ್ತಂಭ",
        position: new THREE.Vector3(2, 3.5, 17.15),
        cameraOffset: new THREE.Vector3(2.0, 2.3, 13.5),
        lookAt: new THREE.Vector3(2.0, 1.6, 17.15),
      },
      {
        id: "deepa-stambha",
        type: "complex",
        nameEn: "10. Deepa Stambha (Gravity Pillar)",
        nameKn: "೧೦. ದೀಪಸ್ತಂಭ (ಗುರುತ್ವಾಕರ್ಷಣಾ ಸ್ತಂಭ)",
        categoryEn: "Lamp Pillar",
        categoryKn: "ಏಕಶಿಲಾ ಸ್ತಂಭ",
        position: new THREE.Vector3(-13, 7, 15),
        cameraOffset: new THREE.Vector3(-6, 9, 22),
        lookAt: new THREE.Vector3(-13, 5, 15),
      },
      {
        id: "vyaule-mandapa",
        type: "complex",
        nameEn: "11. Vyaule Mandapa",
        nameKn: "೧೧. ವ್ಯಾಳೆ ಮಂಟಪ (ಉಯ್ಯಾಲೆ ಮಂಟಪ)",
        categoryEn: "Swing Pavilion",
        categoryKn: "ಉಯ್ಯಾಲೆ ಮಂಟಪ",
        position: new THREE.Vector3(-20.5, 5.5, 21.0),
        cameraOffset: new THREE.Vector3(-14.5, 4.2, 27.5),
        lookAt: new THREE.Vector3(-20.5, 2.8, 21.0),
      },
      {
        id: "south-eastern-pavilion",
        type: "complex",
        nameEn: "12. South-Eastern Pavilion",
        nameKn: "೧೨. ಆಗ್ನೇಯ ಮಂಟಪ",
        categoryEn: "Ancillary Structures",
        categoryKn: "ಪಾರ್ಶ್ವ ವಿಶ್ರಾಂತಿ ಮಂಟಪ",
        position: new THREE.Vector3(-9.8, 6.0, 26.0),
        cameraOffset: new THREE.Vector3(-13.0, 4.2, 13.5),
        lookAt: new THREE.Vector3(-9.8, 2.8, 26.0),
      },
      {
        id: "north-pavilion",
        type: "complex",
        nameEn: "13. North Pavilion",
        nameKn: "೧೩. ಉತ್ತರ ಮಂಟಪ",
        categoryEn: "Pavilion",
        categoryKn: "ಉತ್ತರ ಮಂಟಪ",
        position: new THREE.Vector3(25.0, 5.5, 2.0),
        cameraOffset: new THREE.Vector3(30.0, 4.2, 8.5),
        lookAt: new THREE.Vector3(25.0, 2.8, 2.0),
      },
      {
        id: "muzrai-office",
        type: "complex",
        nameEn: "14. Muzrai Office",
        nameKn: "೧೪. ಮುಜರಾಯಿ ಕಚೇರಿ (ಐತಿಹಾಸಿಕ ಕಟ್ಟಡ)",
        categoryEn: "Historic Complex Structure",
        categoryKn: "ಐತಿಹಾಸಿಕ ಆಡಳಿತ ಕಟ್ಟಡ",
        position: new THREE.Vector3(-28, 5.2, 26.0),
        cameraOffset: new THREE.Vector3(-22, 4.2, 12.5),
        lookAt: new THREE.Vector3(-28, 2.6, 26.0),
      },
      {
        id: "granary",
        type: "complex",
        nameEn: "15. Granary",
        nameKn: "೧೫. ಧಾನ್ಯ ಸಂಗ್ರಹಾಗಾರ (ಕಣಜ)",
        categoryEn: "Storage Structure",
        categoryKn: "ಐತಿಹಾಸಿಕ ಕಣಜ",
        position: new THREE.Vector3(33.8, 5.5, -26.8),
        cameraOffset: new THREE.Vector3(33.8, 10, -16.8),
        lookAt: new THREE.Vector3(33.8, 2.8, -26.8),
      },
      {
        id: "kalyana-mandapa",
        type: "complex",
        nameEn: "16. Kalyana Mandapa",
        nameKn: "೧೬. ಕಲ್ಯಾಣ ಮಂಟಪ",
        categoryEn: "Ceremonial Pavilion",
        categoryKn: "ವಿವಾಹ ಮಂಟಪ",
        position: new THREE.Vector3(-30.5, 5.5, -19),
        cameraOffset: new THREE.Vector3(-24.5, 8.5, -6),
        lookAt: new THREE.Vector3(-30.5, 2.8, -19),
      },
      {
        id: "east-pavilion",
        type: "complex",
        nameEn: "17. East Pavilion",
        nameKn: "೧೭. ಪೂರ್ವ ಮಂಟಪ",
        categoryEn: "Pavilion",
        categoryKn: "ಪೂರ್ವ ಮಂಟಪ",
        position: new THREE.Vector3(22.0, 3.8, 26.0),
        cameraOffset: new THREE.Vector3(12.0, 4.5, 15.0),
        lookAt: new THREE.Vector3(19.5, 2.4, 26.0),
      },
      {
        id: "rampart-wall",
        type: "complex",
        nameEn: "18. Rampart Wall",
        nameKn: "೧೮. ಪ್ರಾಕಾರದ ಕೋಟೆ ಗೋಡೆ",
        categoryEn: "Enclosure Wall",
        categoryKn: "ಪ್ರಾಕಾರ ಸುತ್ತುಗೋಡೆ",
        position: new THREE.Vector3(2, 4.5, 30),
        cameraOffset: new THREE.Vector3(2, 20, 50),
        lookAt: new THREE.Vector3(2, 3, 0),
      },
    ],
    []
  );

  // 6 Main Temple Architectural Exploration Zones (Figure 2.41 INTACH Architectural Plan)
  const architectureNodes: BeaconNode[] = useMemo(
    () =>
      TEMPLE_ARCHITECTURAL_FEATURES.map((feat) => ({
        id: feat.id,
        type: "architecture",
        nameEn: feat.featureEn,
        nameKn: feat.featureKn,
        categoryEn: feat.categoryEn,
        categoryKn: feat.categoryKn,
        position: new THREE.Vector3(...feat.pinPos),
        cameraOffset: new THREE.Vector3(...feat.cameraPos),
        lookAt: new THREE.Vector3(...feat.cameraLook),
      })),
    []
  );

  const focusOnNode = useCallback((node: BeaconNode) => {
    cameraTargetRef.current = {
      pos: node.cameraOffset.clone(),
      look: node.lookAt.clone(),
      animating: true,
    };
  }, []);

  // Camera presets
  const handleSetTopView = useCallback(() => {
    setActiveCameraPreset("top");
    cameraTargetRef.current = {
      pos: topViewPos.clone(),
      look: topViewLook.clone(),
      animating: true,
    };
  }, [topViewPos, topViewLook]);

  const handleSetSideAngle = useCallback(() => {
    setActiveCameraPreset("side");
    cameraTargetRef.current = {
      pos: sideViewPos.clone(),
      look: sideViewLook.clone(),
      animating: true,
    };
  }, [sideViewPos, sideViewLook]);

  const handleSetTempleFrontView = useCallback(() => {
    setActiveCameraPreset("front");
    cameraTargetRef.current = {
      pos: templeFrontViewPos.clone(),
      look: templeFrontViewLook.clone(),
      animating: true,
    };
  }, [templeFrontViewPos, templeFrontViewLook]);

  const handleSetGopuraView = useCallback(() => {
    setActiveCameraPreset("gopura");
    cameraTargetRef.current = {
      pos: gopuraViewPos.clone(),
      look: gopuraViewLook.clone(),
      animating: true,
    };
  }, [gopuraViewPos, gopuraViewLook]);

  const handleSetAnatomyView = useCallback(() => {
    setActiveCameraPreset("anatomy");
    cameraTargetRef.current = {
      pos: archViewPos.clone(),
      look: archViewLook.clone(),
      animating: true,
    };
  }, [archViewPos, archViewLook]);

  // Handle selected structure updates from parent
  useEffect(() => {
    if (activeLayer === "complex") {
      const node = complexNodes.find((m) => m.id === selectedAttraction.id);
      if (node) focusOnNode(node);
    } else if (activeLayer === "architecture" && selectedArchitectureFeature) {
      const node = architectureNodes.find((m) => m.id === selectedArchitectureFeature.id);
      if (node) focusOnNode(node);
    }
  }, [selectedAttraction, selectedArchitectureFeature, activeLayer, complexNodes, architectureNodes, focusOnNode]);

  // Update visible beacons when switching layers
  useEffect(() => {
    complexBeaconsRef.current.forEach((b) => (b.visible = activeLayer === "complex"));
    architectureBeaconsRef.current.forEach((b) => (b.visible = activeLayer === "architecture"));
    if (activeLayer === "architecture") {
      handleSetAnatomyView();
    } else {
      handleSetTopView();
    }
  }, [activeLayer, handleSetAnatomyView, handleSetTopView]);

  // Main Three.js Scene Setup & Render Loop
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const bgSky = isDark ? 0x120d0b : 0xe8eef5;
    scene.background = new THREE.Color(bgSky);
    scene.fog = new THREE.FogExp2(bgSky, 0.0055);

    // 2. Camera setup matching aerial drone view
    const initialWidth = container.clientWidth || window.innerWidth;
    const initialHeight = container.clientHeight || window.innerHeight;
    const camera = new THREE.PerspectiveCamera(40, initialWidth / initialHeight, 0.5, 600);
    camera.position.copy(topViewPos);
    cameraRef.current = camera;

    // 3. WebGL Renderer with High-DPI and Full-Screen Stretch
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(initialWidth, initialHeight, false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    rendererRef.current = renderer;

    // Ensure canvas styles guarantee 100% full screen fill
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    renderer.domElement.style.position = "absolute";
    renderer.domElement.style.top = "0";
    renderer.domElement.style.left = "0";
    container.appendChild(renderer.domElement);

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2.05;
    controls.minDistance = 5;
    controls.maxDistance = 150;
    controls.target.copy(topViewLook);
    controlsRef.current = controls;

    controls.addEventListener("start", () => {
      setIsAutoRotating(false);
      cameraTargetRef.current.animating = false;
    });

    // 5. Procedural Canvas Textures (100% Offline)
    // A. Courtyard Flagstone Paving (multi-toned granite & sandstone ashlar slabs matching Image 5)
    const courtCanvas = document.createElement("canvas");
    courtCanvas.width = 512;
    courtCanvas.height = 512;
    const cCtx = courtCanvas.getContext("2d");
    if (cCtx) {
      cCtx.fillStyle = "#c7ccd0"; // Bright grey-sandy mortar seams
      cCtx.fillRect(0, 0, 512, 512);

      const granitePalette = [
        "#a6b1ba",
        "#949fa9",
        "#b5bec6",
        "#87929c",
        "#9da8b1",
        "#7d8791",
      ];
      const warmSandstonePalette = ["#cab4a1", "#bfa692", "#b39f8e"];

      // Deterministic pseudo-random helper for consistent natural ashlar paving
      let seed = 4219;
      const rand = () => {
        seed = (seed * 16807) % 2147483647;
        return (seed - 1) / 2147483646;
      };

      const rowHeights = [40, 44, 38, 46, 42, 40, 44, 38, 46, 42, 46, 46]; // sums to 512
      let curY = 0;
      rowHeights.forEach((rh, rIdx) => {
        let curX = 0;
        const rowShift = rIdx % 2 === 1 ? 26 : 0;
        while (curX < 512) {
          const rw = Math.min(512 - curX, Math.round(44 + rand() * 44));
          const slabW = curX === 0 && rowShift > 0 ? Math.min(512, rowShift + rw) : rw;
          const isWarm = rand() < 0.22;
          const baseColor = isWarm
            ? warmSandstonePalette[Math.floor(rand() * warmSandstonePalette.length)]
            : granitePalette[Math.floor(rand() * granitePalette.length)];

          cCtx.fillStyle = baseColor;
          cCtx.fillRect(curX + 1.5, curY + 1.5, Math.max(2, slabW - 3), Math.max(2, rh - 3));

          // Subtle shadow edge along slab perimeter
          cCtx.strokeStyle = "rgba(75, 72, 68, 0.32)";
          cCtx.lineWidth = 1;
          cCtx.strokeRect(curX + 2, curY + 2, Math.max(1, slabW - 4), Math.max(1, rh - 4));

          curX += slabW;
        }
        curY += rh;
      });

      // Natural mineral stone grain speckle across courtyard slabs
      for (let i = 0; i < 11000; i++) {
        const px = rand() * 512;
        const py = rand() * 512;
        const light = rand() > 0.5;
        cCtx.fillStyle = light ? "rgba(235, 240, 245, 0.16)" : "rgba(65, 70, 75, 0.14)";
        cCtx.fillRect(px, py, 2, 2);
      }
    }
    const courtTexture = new THREE.CanvasTexture(courtCanvas);
    courtTexture.wrapS = THREE.RepeatWrapping;
    courtTexture.wrapT = THREE.RepeatWrapping;
    courtTexture.repeat.set(12, 9);

    // B. Outer Asphalt Road Texture
    const roadCanvas = document.createElement("canvas");
    roadCanvas.width = 256;
    roadCanvas.height = 256;
    const rCtx = roadCanvas.getContext("2d");
    if (rCtx) {
      rCtx.fillStyle = "#4a4a4d";
      rCtx.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 4000; i++) {
        const rx = Math.random() * 256;
        const ry = Math.random() * 256;
        rCtx.fillStyle = Math.random() > 0.5 ? "#58585c" : "#3c3c40";
        rCtx.fillRect(rx, ry, 2, 2);
      }
    }
    const roadTexture = new THREE.CanvasTexture(roadCanvas);
    roadTexture.wrapS = THREE.RepeatWrapping;
    roadTexture.wrapT = THREE.RepeatWrapping;
    roadTexture.repeat.set(20, 20);



    // D. Hoysala Pierced Stone Jali Lattice Screen Texture (Detail from Front Photos)
    const jaliCanvas = document.createElement("canvas");
    jaliCanvas.width = 128;
    jaliCanvas.height = 128;
    const jCtx = jaliCanvas.getContext("2d");
    if (jCtx) {
      jCtx.fillStyle = "#8e8070"; // Warm weathered sandstone-schist screen frame
      jCtx.fillRect(0, 0, 128, 128);
      for (let y = 16; y < 128; y += 32) {
        for (let x = 16; x < 128; x += 32) {
          jCtx.fillStyle = "#161310"; // Deep perforated star/diamond opening
          jCtx.beginPath();
          jCtx.moveTo(x, y - 9);
          jCtx.lineTo(x + 9, y);
          jCtx.lineTo(x, y + 9);
          jCtx.lineTo(x - 9, y);
          jCtx.closePath();
          jCtx.fill();
        }
      }
      jCtx.strokeStyle = "#685c4f";
      jCtx.lineWidth = 1.5;
      for (let i = 0; i <= 128; i += 32) {
        jCtx.beginPath();
        jCtx.moveTo(i, 0);
        jCtx.lineTo(i, 128);
        jCtx.stroke();
        jCtx.beginPath();
        jCtx.moveTo(0, i);
        jCtx.lineTo(128, i);
        jCtx.stroke();
      }
    }
    const jaliTexture = new THREE.CanvasTexture(jaliCanvas);
    jaliTexture.wrapS = THREE.RepeatWrapping;
    jaliTexture.wrapT = THREE.RepeatWrapping;
    jaliTexture.repeat.set(3, 1.8);

    // D2. Kappe Chennigaraya Pierced Diamond-Lattice Jali Screen Texture (Color Graded)
    const kappeJaliCanvas = document.createElement("canvas");
    kappeJaliCanvas.width = 128;
    kappeJaliCanvas.height = 128;
    const kjCtx = kappeJaliCanvas.getContext("2d");
    if (kjCtx) {
      kjCtx.fillStyle = "#d5cbbe"; // Light weathered soapstone/sandstone lattice screen frame
      kjCtx.fillRect(0, 0, 128, 128);
      for (let row = 0; row < 4; row++) {
        for (let col = 0; col < 4; col++) {
          const cx = 16 + col * 32;
          const cy = 16 + row * 32;
          // Perforated star opening shadow rim
          kjCtx.fillStyle = "#4a4238";
          kjCtx.beginPath();
          kjCtx.moveTo(cx, cy - 9);
          kjCtx.lineTo(cx + 9, cy);
          kjCtx.lineTo(cx, cy + 9);
          kjCtx.lineTo(cx - 9, cy);
          kjCtx.closePath();
          kjCtx.fill();
          // Deep perforated diamond star hole
          kjCtx.fillStyle = "#14110e";
          kjCtx.beginPath();
          kjCtx.moveTo(cx, cy - 7.5);
          kjCtx.lineTo(cx + 7.5, cy);
          kjCtx.lineTo(cx, cy + 7.5);
          kjCtx.lineTo(cx - 7.5, cy);
          kjCtx.closePath();
          kjCtx.fill();
        }
      }
      kjCtx.strokeStyle = "#8e8374";
      kjCtx.lineWidth = 1.5;
      kjCtx.strokeRect(1, 1, 126, 126);
    }
    const kappeJaliTexture = new THREE.CanvasTexture(kappeJaliCanvas);
    kappeJaliTexture.wrapS = THREE.RepeatWrapping;
    kappeJaliTexture.wrapT = THREE.RepeatWrapping;
    kappeJaliTexture.repeat.set(2, 1.5);

    // D3. Kappe Chennigaraya Carved Rosette Double-Door Texture (Color Graded)
    const kappeDoorCanvas = document.createElement("canvas");
    kappeDoorCanvas.width = 128;
    kappeDoorCanvas.height = 256;
    const kdCtx = kappeDoorCanvas.getContext("2d");
    if (kdCtx) {
      kdCtx.fillStyle = "#885743"; // Rich polished warm teak/rosewood doors
      kdCtx.fillRect(0, 0, 128, 256);
      kdCtx.strokeStyle = "#4d2d21";
      kdCtx.lineWidth = 4;
      kdCtx.strokeRect(4, 4, 120, 248);
      // Center double-door seam
      kdCtx.beginPath();
      kdCtx.moveTo(64, 4);
      kdCtx.lineTo(64, 252);
      kdCtx.stroke();
      // 2 columns x 5 rows of gleaming circular carved brass rosette medallions
      for (let r = 0; r < 5; r++) {
        for (const cx of [34, 94]) {
          const cy = 28 + r * 50;
          kdCtx.fillStyle = "#cfa04a"; // Outer antique brass rosette petals
          kdCtx.beginPath();
          kdCtx.arc(cx, cy, 14, 0, Math.PI * 2);
          kdCtx.fill();
          kdCtx.fillStyle = "#f0cf7e"; // Bright gleaming gold/brass carved highlights
          kdCtx.beginPath();
          kdCtx.arc(cx, cy, 9, 0, Math.PI * 2);
          kdCtx.fill();
          kdCtx.fillStyle = "#54391e"; // Inner recessed ring
          kdCtx.beginPath();
          kdCtx.arc(cx, cy, 4.5, 0, Math.PI * 2);
          kdCtx.fill();
          kdCtx.fillStyle = "#ffe4a0"; // Raised central dome stud
          kdCtx.beginPath();
          kdCtx.arc(cx, cy, 2, 0, Math.PI * 2);
          kdCtx.fill();
        }
      }
    }
    const kappeDoorTexture = new THREE.CanvasTexture(kappeDoorCanvas);

    // D4. Veera Narayana Weathered Paneled Timber Double-Door Texture (Matching media_1794550779392_86769c8b.png)
    const viraDoorCanvas = document.createElement("canvas");
    viraDoorCanvas.width = 128;
    viraDoorCanvas.height = 256;
    const vdCtx = viraDoorCanvas.getContext("2d");
    if (vdCtx) {
      // Warm dusty peach-terracotta weathered timber base
      vdCtx.fillStyle = "#a87465";
      vdCtx.fillRect(0, 0, 128, 256);

      // Fine wood grain streaks
      for (let i = 0; i < 600; i++) {
        vdCtx.fillStyle = Math.random() > 0.5 ? "#b88374" : "#986557";
        vdCtx.fillRect(Math.random() * 128, Math.random() * 256, 1.5, 4);
      }

      // Outer heavy doorframe border
      vdCtx.strokeStyle = "#5a3a30";
      vdCtx.lineWidth = 4;
      vdCtx.strokeRect(3, 3, 122, 250);

      // Center vertical meeting stile / mullion seam
      vdCtx.fillStyle = "#523329";
      vdCtx.fillRect(60, 4, 8, 248);
      vdCtx.strokeStyle = "#3c221a";
      vdCtx.lineWidth = 1.5;
      vdCtx.strokeRect(60, 4, 8, 248);

      // 6 recessed rectangular panels (2 columns x 3 rows) matching user's photo
      for (let r = 0; r < 3; r++) {
        const py = 16 + r * 78;
        const pH = 66;
        for (const px of [10, 72]) {
          const pW = 46;
          // Outer shadow of recess
          vdCtx.fillStyle = "#694236";
          vdCtx.fillRect(px, py, pW, pH);

          // Beveled border
          vdCtx.strokeStyle = "#c59485";
          vdCtx.lineWidth = 2;
          vdCtx.strokeRect(px + 2, py + 2, pW - 4, pH - 4);

          // Inner raised field
          vdCtx.fillStyle = "#b48071";
          vdCtx.fillRect(px + 4, py + 4, pW - 8, pH - 8);

          // Subtle internal vertical panel lines
          vdCtx.strokeStyle = "#9e6c5e";
          vdCtx.lineWidth = 1;
          vdCtx.beginPath();
          vdCtx.moveTo(px + pW / 2, py + 6);
          vdCtx.lineTo(px + pW / 2, py + pH - 6);
          vdCtx.stroke();
        }
      }

      // Horizontal wrought-iron locking bar & hasp across center (visible in photo)
      vdCtx.fillStyle = "#2b2624";
      vdCtx.fillRect(16, 124, 96, 8);
      vdCtx.strokeStyle = "#47403c";
      vdCtx.lineWidth = 1;
      vdCtx.strokeRect(16, 124, 96, 8);

      // Center iron chain / padlock fixture
      vdCtx.fillStyle = "#1e1b1a";
      vdCtx.fillRect(58, 120, 12, 16);
      vdCtx.fillStyle = "#8a7e72";
      vdCtx.beginPath();
      vdCtx.arc(64, 128, 2.5, 0, Math.PI * 2);
      vdCtx.fill();
    }
    const viraDoorTexture = new THREE.CanvasTexture(viraDoorCanvas);

    // E. Tiered Horizontal Relief Frieze Texture (Adhisthana of Jagati & Temple Dado)
    const friezeCanvas = document.createElement("canvas");
    friezeCanvas.width = 256;
    friezeCanvas.height = 64;
    const fCtx = friezeCanvas.getContext("2d");
    if (fCtx) {
      fCtx.fillStyle = "#887b6b"; // Warm carved chloritic schist stone
      fCtx.fillRect(0, 0, 256, 64);
      fCtx.strokeStyle = "#362f28";
      fCtx.lineWidth = 2;
      [16, 32, 48].forEach((y) => {
        fCtx.beginPath();
        fCtx.moveTo(0, y);
        fCtx.lineTo(256, y);
        fCtx.stroke();
      });
      fCtx.fillStyle = "#564c42";
      for (let x = 4; x < 256; x += 12) {
        fCtx.fillRect(x, 4, 6, 8); // Elephants
        fCtx.fillRect(x + 2, 20, 6, 8); // Lions/Yalis
        fCtx.fillRect(x, 36, 6, 8); // Horses
        fCtx.fillRect(x + 3, 52, 6, 8); // Narrative Frieze
      }
    }
    const friezeTexture = new THREE.CanvasTexture(friezeCanvas);
    friezeTexture.wrapS = THREE.RepeatWrapping;
    friezeTexture.wrapT = THREE.RepeatWrapping;
    friezeTexture.repeat.set(8, 1);

    // F. Intricate Hoysala Aedicule / Miniature Shikhara Shrine Relief Texture (Matching User Photos)
    const shrineCanvas = document.createElement("canvas");
    shrineCanvas.width = 256;
    shrineCanvas.height = 256;
    const sCtx = shrineCanvas.getContext("2d");
    if (sCtx) {
      sCtx.fillStyle = "#544c45"; // Base chloritic schist stone
      sCtx.fillRect(0, 0, 256, 256);

      // Fine horizontal stone courses
      sCtx.strokeStyle = "#38322c";
      sCtx.lineWidth = 1.5;
      for (let y = 0; y < 256; y += 16) {
        sCtx.beginPath();
        sCtx.moveTo(0, y);
        sCtx.lineTo(256, y);
        sCtx.stroke();
      }

      // Sculpted schist weathering & texture noise
      for (let i = 0; i < 3500; i++) {
        const sx = Math.random() * 256;
        const sy = Math.random() * 256;
        sCtx.fillStyle = Math.random() > 0.5 ? "rgba(95, 87, 80, 0.45)" : "rgba(35, 30, 26, 0.45)";
        sCtx.fillRect(sx, sy, 2, 2);
      }

      // Ornamental Chaitya / Gavaksha Horseshoe Arch Motifs
      sCtx.strokeStyle = "#2c2622";
      sCtx.lineWidth = 2;
      sCtx.fillStyle = "#322b26";
      for (let y = 8; y < 256; y += 32) {
        for (let x = 8; x < 256; x += 32) {
          sCtx.beginPath();
          sCtx.arc(x + 8, y + 8, 6, Math.PI, 0);
          sCtx.lineTo(x + 14, y + 20);
          sCtx.lineTo(x + 2, y + 20);
          sCtx.closePath();
          sCtx.fill();
          sCtx.stroke();
        }
      }
    }
    const shrineTexture = new THREE.CanvasTexture(shrineCanvas);
    shrineTexture.wrapS = THREE.RepeatWrapping;
    shrineTexture.wrapT = THREE.RepeatWrapping;
    shrineTexture.repeat.set(2, 2);

    // G. Hoysala Makaratorana Entrance Lintel & Dvarapala Relief Texture (Matching Front View Photo)
    const toranaCanvas = document.createElement("canvas");
    toranaCanvas.width = 256;
    toranaCanvas.height = 128;
    const toCtx = toranaCanvas.getContext("2d");
    if (toCtx) {
      toCtx.fillStyle = "#4c443e";
      toCtx.fillRect(0, 0, 256, 128);

      toCtx.strokeStyle = "#2e2824";
      toCtx.lineWidth = 3;
      toCtx.strokeRect(4, 4, 248, 120);

      // Central dancing deity arch niche
      toCtx.beginPath();
      toCtx.arc(128, 64, 32, Math.PI, 0);
      toCtx.lineTo(160, 110);
      toCtx.lineTo(96, 110);
      toCtx.closePath();
      toCtx.fillStyle = "#38312c";
      toCtx.fill();
      toCtx.stroke();

      // Swirling Makara floriated tails flanking left and right
      toCtx.strokeStyle = "#6b6056";
      toCtx.lineWidth = 2.5;
      for (let r = 12; r < 50; r += 8) {
        toCtx.beginPath();
        toCtx.arc(64, 64, r, 0.4, 2.8);
        toCtx.stroke();
        toCtx.beginPath();
        toCtx.arc(192, 64, r, 0.3, 2.7);
        toCtx.stroke();
      }

      // Miniature relief figures on lower lintel band
      toCtx.fillStyle = "#2a2420";
      for (let x = 16; x < 240; x += 18) {
        toCtx.fillRect(x, 100, 8, 18);
      }
    }
    const toranaTexture = new THREE.CanvasTexture(toranaCanvas);

    // H. Raya Gopura 7-Tiered Golden Stucco Frieze Texture (Matching media_1793858207384_6c3858be.jpg)
    const gopuraTierCanvas = document.createElement("canvas");
    gopuraTierCanvas.width = 256;
    gopuraTierCanvas.height = 256;
    const gtCtx = gopuraTierCanvas.getContext("2d");
    if (gtCtx) {
      gtCtx.fillStyle = "#dfb858"; // Warm golden-yellow stucco
      gtCtx.fillRect(0, 0, 256, 256);

      // Stucco texture stippling & mineral grain
      for (let i = 0; i < 3000; i++) {
        const gx = Math.random() * 256;
        const gy = Math.random() * 256;
        gtCtx.fillStyle = Math.random() > 0.5 ? "rgba(255, 230, 150, 0.35)" : "rgba(165, 120, 45, 0.28)";
        gtCtx.fillRect(gx, gy, 2, 2);
      }

      // Horizontal cornice mouldings (Kapota courses)
      gtCtx.strokeStyle = "#a8782a";
      gtCtx.lineWidth = 2.5;
      [32, 64, 96, 128, 160, 192, 224].forEach((y) => {
        gtCtx.beginPath();
        gtCtx.moveTo(0, y);
        gtCtx.lineTo(256, y);
        gtCtx.stroke();
      });

      // Miniature sculpted deity relief figures along the frieze bands
      gtCtx.fillStyle = "#8a5f22";
      for (const y of [48, 112, 176, 240]) {
        for (let x = 8; x < 256; x += 20) {
          // Head / crown
          gtCtx.beginPath();
          gtCtx.arc(x + 5, y - 6, 2.5, 0, Math.PI * 2);
          gtCtx.fill();
          // Body / standing deity torso
          gtCtx.fillRect(x + 3, y - 3, 4, 7);
          // Legs
          gtCtx.fillRect(x + 2, y + 4, 2, 4);
          gtCtx.fillRect(x + 6, y + 4, 2, 4);
        }
      }

      // Decorative horseshoe Chaitya / Kudu arches along eaves
      gtCtx.strokeStyle = "#8b6222";
      gtCtx.lineWidth = 1.5;
      for (const y of [26, 90, 154, 218]) {
        for (let x = 6; x < 256; x += 24) {
          gtCtx.beginPath();
          gtCtx.arc(x + 6, y, 4, Math.PI, 0);
          gtCtx.stroke();
        }
      }
    }
    const gopuraTierTexture = new THREE.CanvasTexture(gopuraTierCanvas);
    gopuraTierTexture.wrapS = THREE.RepeatWrapping;
    gopuraTierTexture.wrapT = THREE.RepeatWrapping;
    gopuraTierTexture.repeat.set(1, 1);

    // I. Raya Gopura Weathered Granite Gateway Base Texture (Matching media_1793858207384_6c3858be.jpg)
    const gopuraBaseCanvas = document.createElement("canvas");
    gopuraBaseCanvas.width = 256;
    gopuraBaseCanvas.height = 256;
    const gbCtx = gopuraBaseCanvas.getContext("2d");
    if (gbCtx) {
      gbCtx.fillStyle = "#4a423b"; // Weathered dark grey-brown ashlar granite
      gbCtx.fillRect(0, 0, 256, 256);

      // Granite mineral noise & weathering
      for (let i = 0; i < 4000; i++) {
        const bx = Math.random() * 256;
        const by = Math.random() * 256;
        gbCtx.fillStyle = Math.random() > 0.5 ? "rgba(105, 95, 85, 0.45)" : "rgba(35, 30, 26, 0.45)";
        gbCtx.fillRect(bx, by, 2, 2);
      }

      // Ashlar horizontal stone courses
      gbCtx.strokeStyle = "#28231f";
      gbCtx.lineWidth = 2.0;
      for (let y = 0; y <= 256; y += 32) {
        gbCtx.beginPath();
        gbCtx.moveTo(0, y);
        gbCtx.lineTo(256, y);
        gbCtx.stroke();
      }

      // Vertical stone joints (staggered ashlar pattern)
      for (let row = 0; row < 8; row++) {
        const y = row * 32;
        const offset = (row % 2) * 32;
        for (let x = offset; x < 256; x += 64) {
          gbCtx.beginPath();
          gbCtx.moveTo(x, y);
          gbCtx.lineTo(x, y + 32);
          gbCtx.stroke();
        }
      }

      // Lower horizontal band of carved pilasters with standing deity figures
      gbCtx.fillStyle = "#332c26";
      for (let x = 10; x < 256; x += 28) {
        gbCtx.fillRect(x, 196, 12, 26); // niche recess
        gbCtx.fillStyle = "#5c5248";
        gbCtx.fillRect(x + 4, 198, 4, 22); // standing deity relief
        gbCtx.fillStyle = "#332c26";
      }
    }
    const gopuraBaseTexture = new THREE.CanvasTexture(gopuraBaseCanvas);
    gopuraBaseTexture.wrapS = THREE.RepeatWrapping;
    gopuraBaseTexture.wrapT = THREE.RepeatWrapping;
    gopuraBaseTexture.repeat.set(2, 2);

    // J. Raya Gopura Window Opening & Vertical Grill Texture
    const gopuraWindowCanvas = document.createElement("canvas");
    gopuraWindowCanvas.width = 128;
    gopuraWindowCanvas.height = 128;
    const gwCtx = gopuraWindowCanvas.getContext("2d");
    if (gwCtx) {
      gwCtx.fillStyle = "#120f0d"; // Deep shadow cavity
      gwCtx.fillRect(0, 0, 128, 128);

      // Iron security grill vertical bars
      gwCtx.strokeStyle = "#7c7267";
      gwCtx.lineWidth = 3.0;
      for (let x = 16; x < 128; x += 18) {
        gwCtx.beginPath();
        gwCtx.moveTo(x, 0);
        gwCtx.lineTo(x, 128);
        gwCtx.stroke();
      }

      // Horizontal cross-ties
      gwCtx.strokeStyle = "#5a5046";
      gwCtx.lineWidth = 2.0;
      [24, 64, 104].forEach((y) => {
        gwCtx.beginPath();
        gwCtx.moveTo(0, y);
        gwCtx.lineTo(128, y);
        gwCtx.stroke();
      });
    }
    const gopuraWindowTexture = new THREE.CanvasTexture(gopuraWindowCanvas);

    // 6. Calibrated Materials
    const gopuraBaseStoneMat = new THREE.MeshStandardMaterial({
      color: 0x544c45, // Weathered dark grey-brown ashlar granite base (Image 2)
      roughness: 0.84,
      metalness: 0.12,
      map: gopuraBaseTexture,
    });

    const gopuraStoneMat = new THREE.MeshStandardMaterial({
      color: 0xe0ba5a, // Warm golden-yellow stucco of the 7 tiers (Image 2)
      roughness: 0.65,
      metalness: 0.14,
      map: gopuraTierTexture,
      side: THREE.DoubleSide,
    });

    const gopuraCorniceMat = new THREE.MeshStandardMaterial({
      color: 0xc89e42, // Rich amber-gold for horizontal eaves & kapotas
      roughness: 0.58,
      metalness: 0.18,
      side: THREE.DoubleSide,
    });

    const gopuraWindowMat = new THREE.MeshStandardMaterial({
      color: 0x161311,
      roughness: 0.90,
      metalness: 0.15,
      map: gopuraWindowTexture,
    });

    const gopuraGrillMat = new THREE.MeshStandardMaterial({
      color: 0x36322e,
      roughness: 0.40,
      metalness: 0.75,
    });

    const gopuraMedallionRimMat = new THREE.MeshStandardMaterial({
      color: 0xce4e1b, // Vermilion-orange outer rim of Sudarshana Chakra medallion (Image 2)
      roughness: 0.45,
      metalness: 0.35,
    });

    const mainTempleSoapstoneMat = new THREE.MeshStandardMaterial({
      color: 0x7a6f63, // Warm weathered sandstone-schist matching front elevation photos
      roughness: 0.82,
      metalness: 0.14,
    });

    const portalPinkPillarMat = new THREE.MeshStandardMaterial({
      color: 0x9c7262, // Reddish-pinkish sandstone/granite doorway & colonnade pillars (see photo)
      roughness: 0.45,
      metalness: 0.24,
    });

    const mainRoofEaveMat = new THREE.MeshStandardMaterial({
      color: 0x4b433c, // Deep shadowed Kapota overhanging cornice eaves
      roughness: 0.88,
      metalness: 0.14,
    });

    const shrineStoneMat = new THREE.MeshStandardMaterial({
      color: 0xd8ccc0,
      roughness: 0.80,
      metalness: 0.14,
      map: shrineTexture,
    });

    const shrineNicheMat = new THREE.MeshStandardMaterial({
      color: 0x161312, // Deep shadow in sanctum niche
      roughness: 0.95,
      metalness: 0.05,
    });

    const toranaMat = new THREE.MeshStandardMaterial({
      color: 0xe8ddd0,
      roughness: 0.78,
      metalness: 0.14,
      map: toranaTexture,
    });

    const jaliMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.86,
      metalness: 0.12,
      map: jaliTexture,
    });

    const kappeJaliMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.86,
      metalness: 0.12,
      map: kappeJaliTexture,
    });

    const kappeDoorMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.72,
      metalness: 0.10,
      map: kappeDoorTexture,
    });

    const kappeStoneMat = new THREE.MeshStandardMaterial({
      color: 0x9b9083, // Authentic warm weathered soapstone/schist with golden-grey undertones (Images 1 & 2)
      roughness: 0.76,
      metalness: 0.12,
    });

    const kappeEaveMat = new THREE.MeshStandardMaterial({
      color: 0x3e3731, // Deep crisp shadowed Kapota overhanging cornice eaves
      roughness: 0.88,
      metalness: 0.14,
    });

    const kappePillarMat = new THREE.MeshStandardMaterial({
      color: 0x36322f, // Polished dark chloritic schist for lathe-turned porch columns (Images 1 & 2)
      roughness: 0.38,
      metalness: 0.38,
    });

    const kappePlinthMat = new THREE.MeshStandardMaterial({
      color: 0x726a60, // Weathered ashlar granite Jagati plinth & step deck
      roughness: 0.86,
      metalness: 0.12,
    });

    const gravityPillarMat = new THREE.MeshStandardMaterial({
      color: 0x86776e, // Authentic weathered pinkish-grey monolithic granite shaft (media_1794551627037_fa2d3f60.jpg)
      roughness: 0.82,
      metalness: 0.12,
    });

    const friezeMat = new THREE.MeshStandardMaterial({
      color: 0xd8ccc0,
      roughness: 0.85,
      map: friezeTexture,
    });

    const polishedPillarMat = new THREE.MeshStandardMaterial({
      color: 0x24201e, // Lathe-turned polished black schist
      roughness: 0.32,
      metalness: 0.48,
    });

    const goldKalashaMat = new THREE.MeshStandardMaterial({
      color: 0xdeb841,
      roughness: 0.18,
      metalness: 0.88,
    });

    const darkBronzeMat = new THREE.MeshStandardMaterial({
      color: 0xe6b84c, // Burnished brass-gold plating of Dvaja Stambha (matching Image 3 photo)
      emissive: 0x52390a,
      emissiveIntensity: 0.35,
      roughness: 0.28,
      metalness: 0.65,
    });

    const safetyRailMat = new THREE.MeshStandardMaterial({
      color: 0xd4a017, // Bright yellow protective courtyard barrier railing (Image 1, 2, 3)
      roughness: 0.35,
      metalness: 0.45,
    });

    const coirCarpetMat = new THREE.MeshStandardMaterial({
      color: 0xc47e3a, // Natural golden-brown coconut coir / jute runner (media_1793860799907_c18594ef.jpg)
      roughness: 0.95,
      metalness: 0.05,
    });

    // Natural Water Blue Texture with procedural gentle ripples and sun caustics
    const waterCanvas = document.createElement("canvas");
    waterCanvas.width = 256;
    waterCanvas.height = 256;
    const wCtx = waterCanvas.getContext("2d");
    if (wCtx) {
      wCtx.fillStyle = "#1e88e5"; // Vibrant natural water blue
      wCtx.fillRect(0, 0, 256, 256);
      wCtx.strokeStyle = "rgba(224, 247, 250, 0.55)";
      wCtx.lineWidth = 2.5;
      for (let r = 10; r < 240; r += 26) {
        wCtx.beginPath();
        wCtx.ellipse(128, 128, r, r * 0.72, 0, 0, Math.PI * 2);
        wCtx.stroke();
      }
      wCtx.strokeStyle = "rgba(13, 71, 161, 0.35)";
      wCtx.lineWidth = 3;
      for (let r = 22; r < 230; r += 26) {
        wCtx.beginPath();
        wCtx.ellipse(128, 128, r, r * 0.72, 0, 0, Math.PI * 2);
        wCtx.stroke();
      }
    }
    const waterTexture = new THREE.CanvasTexture(waterCanvas);
    waterTexture.wrapS = THREE.RepeatWrapping;
    waterTexture.wrapT = THREE.RepeatWrapping;
    waterTexture.repeat.set(3, 3);

    const pushkaraniWaterMat = new THREE.MeshStandardMaterial({
      color: 0x1e88e5, // Vibrant natural clear water blue (Image request: "only color should be water blue")
      emissive: 0x09527f, // Subtle luminous aquatic glow so water is brilliantly visible even in shadow
      emissiveIntensity: 0.38,
      map: waterTexture,
      roughness: 0.18,
      metalness: 0.05,
      side: THREE.DoubleSide,
    });

    const tankAshlarMat = new THREE.MeshStandardMaterial({
      color: 0x4a443e, // Weathered grey-brown ashlar granite blocks
      roughness: 0.90,
    });

    const tankSubmergedStoneMat = new THREE.MeshStandardMaterial({
      color: 0x2c2723, // Dark wet submerged stone
      roughness: 0.75,
    });



    const asphaltMat = new THREE.MeshStandardMaterial({
      color: 0x444447,
      roughness: 0.92,
      map: roadTexture,
    });

    // 7. Lighting matching sunny daytime capture
    const hemiLight = new THREE.HemisphereLight(0xfff7ea, 0x4d4239, 0.85);
    hemiLight.position.set(0, 60, 0);
    scene.add(hemiLight);
    hemiLightRef.current = hemiLight;

    const dirLight = new THREE.DirectionalLight(0xfff5e4, 2.1);
    dirLight.position.set(35, 55, 40);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 180;
    const d = 60;
    dirLight.shadow.camera.left = -d;
    dirLight.shadow.camera.right = d;
    dirLight.shadow.camera.top = d;
    dirLight.shadow.camera.bottom = -d;
    dirLight.shadow.bias = -0.0003;
    scene.add(dirLight);
    dirLightRef.current = dirLight;

    // Diyas / lamps at key sanctums
    const diyas: THREE.PointLight[] = [];
    [
      new THREE.Vector3(2, 4.5, -4),
      new THREE.Vector3(2, 3.5, 2),
      new THREE.Vector3(-22, 3.5, 3),
      new THREE.Vector3(-4, 7.5, 13),
      new THREE.Vector3(6, 4.5, 29),
      new THREE.Vector3(2, 4.5, -24),
      new THREE.Vector3(-18, 5, -22),
    ].forEach((pos) => {
      const pLight = new THREE.PointLight(0xffa133, 0.35, 20, 2);
      pLight.position.copy(pos);
      scene.add(pLight);
      diyas.push(pLight);
    });
    diyaLightsRef.current = diyas;

    // 8. 3D Architectural Precinct Construction
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // A. Outer Landscape & Surrounding Roads
    const outerGroundGeo = new THREE.PlaneGeometry(220, 180);
    const outerGroundMat = new THREE.MeshStandardMaterial({
      color: 0x827d73,
      roughness: 0.95,
    });
    const outerGround = new THREE.Mesh(outerGroundGeo, outerGroundMat);
    outerGround.rotation.x = -Math.PI / 2;
    outerGround.position.y = -0.2;
    outerGround.receiveShadow = true;
    worldGroup.add(outerGround);

    // Ring roads wrapping around complex
    const roadE = new THREE.Mesh(new THREE.PlaneGeometry(16, 130), asphaltMat);
    roadE.rotation.x = -Math.PI / 2;
    roadE.position.set(0, -0.15, 42);
    roadE.receiveShadow = true;
    worldGroup.add(roadE);

    const roadS = new THREE.Mesh(new THREE.PlaneGeometry(150, 16), asphaltMat);
    roadS.rotation.x = -Math.PI / 2;
    roadS.position.set(50, -0.15, 0);
    roadS.rotation.z = Math.PI / 2;
    roadS.receiveShadow = true;
    worldGroup.add(roadS);

    const roadW = new THREE.Mesh(new THREE.PlaneGeometry(16, 130), asphaltMat);
    roadW.rotation.x = -Math.PI / 2;
    roadW.position.set(-48, -0.15, 0);
    roadW.receiveShadow = true;
    worldGroup.add(roadW);

    // B. Courtyard Flagstone Ground (Inner Sacred Area)
    // B. Courtyard Flagstone Ground (Inner Sacred Area)
    // Fits cleanly inside the inner face of the 4 Rampart Walls (zero leak onto outer roads)
    const courtGeo = new THREE.PlaneGeometry(88.2, 62.2);
    const courtMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      roughness: 0.85,
      map: courtTexture,
    });
    const court = new THREE.Mesh(courtGeo, courtMat);
    court.rotation.x = -Math.PI / 2;
    court.position.set(2, 0.05, -3.0);
    court.receiveShadow = true;
    worldGroup.add(court);

    // C. Rampart Wall #18 (Enclosure Wall & Pillared Cloisters)
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x5a534c,
      roughness: 0.85,
    });
    const createWall = (w: number, h: number, d: number, x: number, z: number) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
      mesh.position.set(x, h / 2, z);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      worldGroup.add(mesh);
    };
    // North & South walls span seamlessly between West outer face (Z = -35.9) and East outer face (Z = 29.9)
    // Full precinct outer bounding box: X [-43.9 to 47.9], Z [-35.9 to 29.9]
    createWall(1.8, 3.8, 65.8, 47.0, -3.0); // North wall
    createWall(1.8, 3.8, 65.8, -43.0, -3.0); // South wall
    createWall(91.8, 3.8, 1.8, 2.0, -35.0); // West wall - flush with North & South outer corners
    createWall(39.4, 3.8, 1.8, -24.2, 29.0); // East wall South - flush from South corner (-43.9) to Gopura (-4.5)
    createWall(39.4, 3.8, 1.8, 28.2, 29.0); // East wall North - flush from Gopura (8.5) to North corner (47.9)

    // Rounded coping stone courses on wall tops (matching wide panoramic photo)
    const createCoping = (w: number, d: number, x: number, z: number) => {
      const coping = new THREE.Mesh(new THREE.BoxGeometry(w, 0.25, d), wallMat);
      coping.position.set(x, 3.8 + 0.125, z);
      coping.castShadow = true;
      coping.receiveShadow = true;
      worldGroup.add(coping);
    };
    createCoping(2.0, 65.8, 47.0, -3.0);
    createCoping(2.0, 65.8, -43.0, -3.0);
    createCoping(91.8, 2.0, 2.0, -35.0);
    createCoping(39.4, 2.0, -24.2, 29.0);
    createCoping(39.4, 2.0, 28.2, 29.0);

    // Authentic Pillared Cloister Verandas (Prakara Colonnade matching reference Image 2 & Image 1)
    // Features: 3-tier continuous stepped ashlar plinth, dark recessed corridor gallery,
    // closely spaced square-octagonal carved granite pillars with cross-arm bracket capitals,
    // longitudinal architrave beam, overhanging Kapota eave, and cornice parapet.
    const cloisterStoneMat = new THREE.MeshStandardMaterial({
      color: 0x8d8070, // Warm weathered sandstone-granite matching cloister photos
      roughness: 0.85,
      metalness: 0.12,
    });
    const cloisterEaveMat = new THREE.MeshStandardMaterial({
      color: 0x524a42,
      roughness: 0.88,
      metalness: 0.12,
    });
    const cloisterGalleryShadowMat = new THREE.MeshStandardMaterial({
      color: 0x25201c, // Deep shadowed interior veranda gallery along rampart wall
      roughness: 0.95,
    });

    // Shared pillar geometries for zero-overhead instancing across ~70 cloister columns
    const cFootGeo = new THREE.BoxGeometry(0.42, 0.58, 0.42);
    const cOctLowerGeo = new THREE.CylinderGeometry(0.185, 0.205, 0.48, 8);
    const cMidBlockGeo = new THREE.BoxGeometry(0.38, 0.54, 0.38);
    const cOctUpperGeo = new THREE.CylinderGeometry(0.18, 0.19, 0.44, 8);
    const cAbacusGeo = new THREE.BoxGeometry(0.42, 0.22, 0.42);
    const cBracketXGeo = new THREE.BoxGeometry(0.92, 0.24, 0.34);
    const cBracketZGeo = new THREE.BoxGeometry(0.34, 0.24, 0.92);

    const createCloisterSection = (
      axis: "x" | "z",
      wallEdge: number,
      inwardDir: 1 | -1,
      startCoord: number,
      endCoord: number,
      colStart: number,
      colEnd: number
    ) => {
      const length = Math.abs(endCoord - startCoord);
      const midAxis = (startCoord + endCoord) / 2;

      const makeBox = (
        inwardStart: number,
        inwardEnd: number,
        yBottom: number,
        yTop: number,
        mat: THREE.Material,
        castShadow = true
      ) => {
        const perpSize = Math.abs(inwardEnd - inwardStart);
        const perpCenter = wallEdge + inwardDir * ((inwardStart + inwardEnd) / 2);
        const h = yTop - yBottom;
        const cy = (yBottom + yTop) / 2;

        const w = axis === "z" ? perpSize : length;
        const d = axis === "z" ? length : perpSize;
        const cx = axis === "z" ? perpCenter : midAxis;
        const cz = axis === "z" ? midAxis : perpCenter;

        const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
        mesh.position.set(cx, cy, cz);
        mesh.castShadow = castShadow;
        mesh.receiveShadow = true;
        worldGroup.add(mesh);
      };

      // 1. 3-Tier Continuous Stepped Ashlar Stone Plinth Base (Y = 0.05 up to 0.76)
      makeBox(0.0, 4.90, 0.05, 0.28, cloisterStoneMat, false);
      makeBox(0.0, 4.55, 0.28, 0.52, cloisterStoneMat, false);
      makeBox(0.0, 4.20, 0.52, 0.76, cloisterStoneMat, false);

      // 2. Shadowed Interior Gallery Wall Backing & Dividing Pilasters along Rampart Wall
      makeBox(0.0, 0.22, 0.76, 3.50, cloisterGalleryShadowMat, false);

      // 3. Longitudinal Stone Architrave Beam (Uttira), Roof Slab, Overhanging Kapota Eave & Parapet
      makeBox(3.52, 3.98, 3.28, 3.50, cloisterStoneMat, true);
      makeBox(0.0, 4.28, 3.50, 3.74, cloisterStoneMat, true);
      makeBox(3.85, 4.68, 3.44, 3.60, cloisterEaveMat, true);
      makeBox(3.78, 4.34, 3.74, 3.90, cloisterStoneMat, true);

      // 4. Closely Spaced Carved Square-Octagonal Pillars with Cross-Arm Bracket Capitals
      const colSpan = Math.abs(colEnd - colStart);
      const colCount = Math.max(2, Math.round(colSpan / 2.45));
      const colPerpPos = wallEdge + inwardDir * 3.75;

      for (let i = 0; i <= colCount; i++) {
        const axisPos = colStart + (i * (colEnd - colStart)) / colCount;
        const px = axis === "z" ? colPerpPos : axisPos;
        const pz = axis === "z" ? axisPos : colPerpPos;
        addCloisterColumn(px, 0.76, pz, 1.0, worldGroup);
      }
    };

    const addCloisterColumn = (
      px: number,
      py: number,
      pz: number,
      scaleY = 1.0,
      parent: THREE.Group = worldGroup
    ) => {
      const pGroup = new THREE.Group();
      pGroup.position.set(px, py, pz);
      pGroup.scale.set(1, scaleY, 1);

      const foot = new THREE.Mesh(cFootGeo, cloisterStoneMat);
      foot.position.y = 0.29;
      foot.castShadow = true;
      pGroup.add(foot);

      const oct1 = new THREE.Mesh(cOctLowerGeo, cloisterStoneMat);
      oct1.position.y = 0.82;
      oct1.castShadow = true;
      pGroup.add(oct1);

      const midBox = new THREE.Mesh(cMidBlockGeo, cloisterStoneMat);
      midBox.position.y = 1.33;
      midBox.castShadow = true;
      pGroup.add(midBox);

      const oct2 = new THREE.Mesh(cOctUpperGeo, cloisterStoneMat);
      oct2.position.y = 1.82;
      oct2.castShadow = true;
      pGroup.add(oct2);

      const abacus = new THREE.Mesh(cAbacusGeo, cloisterStoneMat);
      abacus.position.y = 2.15;
      abacus.castShadow = true;
      pGroup.add(abacus);

      const brX = new THREE.Mesh(cBracketXGeo, cloisterStoneMat);
      brX.position.y = 2.38;
      brX.castShadow = true;
      pGroup.add(brX);

      const brZ = new THREE.Mesh(cBracketZGeo, cloisterStoneMat);
      brZ.position.y = 2.38;
      brZ.castShadow = true;
      pGroup.add(brZ);

      parent.add(pGroup);
    };

    // Deploy seamless Cloister Colonnade matching precinct Rampart Walls & leaving clear opening for Elephant Gate:
    // South-West Wing (from West Wall -34.1 up to Elephant Gate opening at Z = 13.2)
    createCloisterSection("z", -42.1, 1, -34.1, 13.2, -30.35, 12.6);
    // South-East Wing (from Elephant Gate at Z = 18.8 up to East Wall 28.1)
    createCloisterSection("z", -42.1, 1, 18.8, 28.1, 19.5, 27.3);
    // East-South Corner Left Wing (from South-East Cloister -37.9 to Muzrai Office -33.2)
    createCloisterSection("x", 28.1, -1, -37.9, -33.2, -36.0, -33.8);
    // East-South Middle Wing (between Muzrai Office -22.8 and South-Eastern Pavilion -13.8)
    createCloisterSection("x", 28.1, -1, -22.8, -13.8, -21.2, -15.2);
    // West Wing (butt-joined cleanly between South inner face -37.9 and North inner face 41.9)
    createCloisterSection("x", -34.1, 1, -37.9, 41.9, -35.8, 39.8);
    // North Wing (from West Wall -34.1 down to Z = 11.3, meeting Vasudeva Sarovara seamlessly)
    createCloisterSection("z", 46.1, -1, -34.1, 11.3, -30.35, 10.6);

    // Pierced Stone Jali Screens along East-South Middle Cloister Gallery Wall (seen right-of-center in Image 1)
    [-20.2, -16.8].forEach((jx) => {
      const wallJaliPanel = new THREE.Mesh(new THREE.BoxGeometry(2.1, 1.45, 0.25), kappeJaliMat);
      wallJaliPanel.position.set(jx, 2.05, 27.78);
      worldGroup.add(wallJaliPanel);
    });

    // Helper: Stellate Star Polygon Generator
    const createStarShape = (points: number, innerR: number, outerR: number): THREE.Shape => {
      const shape = new THREE.Shape();
      const step = Math.PI / points;
      for (let i = 0; i < points * 2; i++) {
        const r = i % 2 === 0 ? outerR : innerR;
        const angle = i * step;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;
        if (i === 0) shape.moveTo(x, y);
        else shape.lineTo(x, y);
      }
      shape.closePath();
      return shape;
    };

    // Helper: Stellate Jagati Star Polygon Generator with East, North & South Stairway Openings
    // Cuts back East (i=24), North (i=0), and South (i=16) star points so all 3 entrances have
    // uninterrupted staircases descending to the courtyard pavement (matching Image 1 side portal).
    const createJagatiStarShape = (innerR: number, outerR: number): THREE.Shape => {
      const shape = new THREE.Shape();
      const points = 16;
      const step = Math.PI / points;
      let started = false;

      const v23X = Math.cos(23 * step) * innerR;
      const v25X = Math.cos(25 * step) * innerR;
      const v31Y = Math.sin(31 * step) * innerR;
      const v1Y = Math.sin(1 * step) * innerR;
      const v15Y = Math.sin(15 * step) * innerR;
      const v17Y = Math.sin(17 * step) * innerR;

      for (let i = 0; i < points * 2; i++) {
        if (i === 0) {
          // North Entrance Portal (+X): Cut back to x = 7.4
          if (!started) {
            shape.moveTo(7.4, v31Y);
            shape.lineTo(7.4, v1Y);
            started = true;
          } else {
            shape.lineTo(7.4, v31Y);
            shape.lineTo(7.4, v1Y);
          }
          continue;
        }
        if (i === 16) {
          // South Entrance Portal (-X): Cut back to x = -7.4
          shape.lineTo(-7.4, v15Y);
          shape.lineTo(-7.4, v17Y);
          continue;
        }
        if (i === 24) {
          // East Entrance Portal (+Z): Cut back to doorway landing (y = -7.2)
          shape.lineTo(v23X, -7.2);
          shape.lineTo(v25X, -7.2);
          continue;
        }

        const r = i % 2 === 0 ? outerR : innerR;
        const angle = i * step;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;

        if (!started) {
          shape.moveTo(x, y);
          started = true;
        } else {
          shape.lineTo(x, y);
        }
      }
      shape.closePath();
      return shape;
    };

    // =========================================================================
    // 1. CHENNAKESHAVA MAIN TEMPLE (Detailing matching Image 3 Side Angle)
    // =========================================================================
    const mainTempleGroup = new THREE.Group();
    mainTempleGroup.position.set(2, 0, -2);
    worldGroup.add(mainTempleGroup);

    // Stellate Jagati (Feature #6 Jagati): 3-Tier Relief Plinth (Image 3)
    // Tier 1: Lower Adhisthana Plinth with sculpted frieze relief
    const starShape1 = createJagatiStarShape(13.5, 16.5);
    const jagatiLower = new THREE.Mesh(
      new THREE.ExtrudeGeometry(starShape1, { depth: 0.6, bevelEnabled: true, bevelSize: 0.2 }),
      friezeMat
    );
    jagatiLower.rotation.x = -Math.PI / 2;
    jagatiLower.position.y = 0.6;
    jagatiLower.castShadow = true;
    jagatiLower.receiveShadow = true;
    mainTempleGroup.add(jagatiLower);

    // Tier 2: Middle Moulding
    const starShapeMid = createJagatiStarShape(12.8, 15.6);
    const jagatiMid = new THREE.Mesh(
      new THREE.ExtrudeGeometry(starShapeMid, { depth: 0.35, bevelEnabled: true, bevelSize: 0.1 }),
      mainTempleSoapstoneMat
    );
    jagatiMid.rotation.x = -Math.PI / 2;
    jagatiMid.position.y = 0.95;
    jagatiMid.castShadow = true;
    mainTempleGroup.add(jagatiMid);

    // Tier 3: Upper Circumambulatory Terrace (Pradakshina Patha)
    const starShape2 = createJagatiStarShape(11.5, 14.5);
    const jagatiUpper = new THREE.Mesh(
      new THREE.ExtrudeGeometry(starShape2, { depth: 0.55, bevelEnabled: true, bevelSize: 0.15 }),
      mainTempleSoapstoneMat
    );
    jagatiUpper.rotation.x = -Math.PI / 2;
    jagatiUpper.position.y = 1.5;
    jagatiUpper.castShadow = true;
    jagatiUpper.receiveShadow = true;
    mainTempleGroup.add(jagatiUpper);

    // =========================================================================
    // Authentic Hoysala Miniature Shikhara Shrines (Bhadravalokana Kutas / Aedicules)
    // 100% matched to real photographs (media_1793856819294_da1d2a4c.png & media_1793856866817_f6ddb609.png)
    // =========================================================================
    const createHoysalaMiniatureShrine = (
      x: number,
      y: number,
      z: number,
      rotY: number,
      scale = 1.0,
      parent: THREE.Group = mainTempleGroup
    ) => {
      const shrineGroup = new THREE.Group();
      shrineGroup.position.set(x, y, z);
      shrineGroup.rotation.y = rotY;
      shrineGroup.scale.set(scale, scale, scale);

      // 1. Adhisthana (Moulded Plinth Base, calibrated height = 0.26)
      const upana = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.10, 0.85), friezeMat);
      upana.position.y = 0.05;
      upana.castShadow = true;
      upana.receiveShadow = true;
      shrineGroup.add(upana);

      const kumuda = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.09, 0.78), friezeMat);
      kumuda.position.y = 0.145;
      kumuda.castShadow = true;
      shrineGroup.add(kumuda);

      const pattika = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.08, 0.82), shrineStoneMat);
      pattika.position.y = 0.23;
      pattika.castShadow = true;
      shrineGroup.add(pattika);

      // 2. Mandapa / Sanctum Cell (Mid-body, calibrated height = 0.50)
      const niche = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.48, 0.52), shrineNicheMat);
      niche.position.set(0, 0.51, 0);
      shrineGroup.add(niche);

      const idol = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.32, 10), polishedPillarMat);
      idol.position.set(0, 0.45, 0);
      shrineGroup.add(idol);

      // 4 Carved Lathe-Turned Corner Pilasters
      [
        [-0.30, -0.30],
        [0.30, -0.30],
        [-0.30, 0.30],
        [0.30, 0.30],
      ].forEach(([px, pz]) => {
        const col = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.48, 10), polishedPillarMat);
        col.position.set(px, 0.51, pz);
        col.castShadow = true;
        shrineGroup.add(col);

        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.055, 0.015, 8, 10), polishedPillarMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.set(px, 0.72, pz);
        shrineGroup.add(ring);
      });

      // Front Carved Doorframe Jambs (Dvara Shakha with Dvarapala figures)
      const leftJamb = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.48, 0.12), shrineStoneMat);
      leftJamb.position.set(-0.22, 0.51, 0.28);
      leftJamb.castShadow = true;
      shrineGroup.add(leftJamb);

      const rightJamb = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.48, 0.12), shrineStoneMat);
      rightJamb.position.set(0.22, 0.51, 0.28);
      rightJamb.castShadow = true;
      shrineGroup.add(rightJamb);

      // Carved Torana Lintel above the door
      const lintel = new THREE.Mesh(new THREE.BoxGeometry(0.60, 0.10, 0.14), shrineStoneMat);
      lintel.position.set(0, 0.73, 0.28);
      lintel.castShadow = true;
      shrineGroup.add(lintel);

      // Side and Rear Wall Sculpted Relief Slabs
      const rearWall = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.48, 0.08), shrineStoneMat);
      rearWall.position.set(0, 0.51, -0.27);
      rearWall.castShadow = true;
      shrineGroup.add(rearWall);

      const leftWall = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.48, 0.52), shrineStoneMat);
      leftWall.position.set(-0.27, 0.51, 0);
      leftWall.castShadow = true;
      shrineGroup.add(leftWall);

      const rightWall = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.48, 0.52), shrineStoneMat);
      rightWall.position.set(0.27, 0.51, 0);
      rightWall.castShadow = true;
      shrineGroup.add(rightWall);

      // 3. Double-Tiered Overhanging Chhajja (Stone Cornice Eaves, height = 0.15)
      const chhajja1 = new THREE.Mesh(new THREE.BoxGeometry(0.98, 0.08, 0.98), shrineStoneMat);
      chhajja1.position.y = 0.81;
      chhajja1.castShadow = true;
      shrineGroup.add(chhajja1);

      const chhajja2 = new THREE.Mesh(new THREE.BoxGeometry(0.88, 0.07, 0.88), shrineStoneMat);
      chhajja2.position.y = 0.88;
      chhajja2.castShadow = true;
      shrineGroup.add(chhajja2);

      // 4. Stepped Pyramidal Shikhara Tower (4 Tiers with Gavaksha Chaitya arches, height = 0.50)
      const tierDims = [
        { w: 0.78, h: 0.14, y: 0.99, gW: 0.34, gH: 0.11 },
        { w: 0.64, h: 0.13, y: 1.12, gW: 0.28, gH: 0.10 },
        { w: 0.50, h: 0.12, y: 1.24, gW: 0.22, gH: 0.09 },
        { w: 0.36, h: 0.10, y: 1.35, gW: 0.15, gH: 0.07 },
      ];

      tierDims.forEach(({ w, h, y, gW, gH }) => {
        const tierMesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), shrineStoneMat);
        tierMesh.position.y = y;
        tierMesh.castShadow = true;
        shrineGroup.add(tierMesh);

        // Ornamental Gavaksha Chaitya horseshoe arch projection on all 4 faces
        [
          [0, (w / 2) + 0.025, 0],
          [0, -(w / 2) - 0.025, Math.PI],
          [(w / 2) + 0.025, 0, Math.PI / 2],
          [-(w / 2) - 0.025, 0, -Math.PI / 2],
        ].forEach(([gx, gz, gRot]) => {
          const arch = new THREE.Mesh(new THREE.BoxGeometry(gW, gH, 0.06), shrineStoneMat);
          arch.position.set(gx, y, gz);
          arch.rotation.y = gRot;
          arch.castShadow = true;
          shrineGroup.add(arch);
        });
      });

      // 5. Crown: Fluted Amalaka Stone + Kalasha Finial (height = 0.26)
      const amalaka = new THREE.Mesh(new THREE.CylinderGeometry(0.20, 0.23, 0.08, 16), shrineStoneMat);
      amalaka.position.y = 1.44;
      amalaka.castShadow = true;
      shrineGroup.add(amalaka);

      const kalashaCushion = new THREE.Mesh(new THREE.TorusGeometry(0.10, 0.02, 8, 16), goldKalashaMat);
      kalashaCushion.rotation.x = Math.PI / 2;
      kalashaCushion.position.y = 1.51;
      shrineGroup.add(kalashaCushion);

      const stupikaCone = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.20, 12), goldKalashaMat);
      stupikaCone.position.y = 1.62;
      stupikaCone.castShadow = true;
      shrineGroup.add(stupikaCone);

      parent.add(shrineGroup);
      return shrineGroup;
    };

    // A. Deploy Miniature Shrines around the 16-point Stellate Jagati Terrace Points
    // (Calibrated height, facing outward, matching media_1793857428658_51acaa03.jpg)
    const stepAngle = (Math.PI * 2) / 16;
    for (let s = 0; s < 16; s++) {
      if (s === 0 || s === 4 || s === 8 || s === 12) continue; // Skip all 4 cardinal portal axes (North, East, South, West)
      const angle = s * stepAngle;
      const kx = Math.cos(angle) * 13.0;
      const kz = Math.sin(angle) * 13.0;
      createHoysalaMiniatureShrine(kx, 2.05, kz, -angle - Math.PI / 2, 0.95, mainTempleGroup);
    }

    // B. Deploy 3 Entrance Stairways with Sculpted Elephant Balustrades & Flanking Shrines
    // (Matches real entrance elevation in media_1793857428658_51acaa03.jpg & media_1793861820894_5fb5ad04.jpg)
    const createEntranceStairway = (rotY: number, cx: number, cz: number) => {
      const stairGroup = new THREE.Group();
      stairGroup.position.set(cx, 0, cz);
      stairGroup.rotation.y = rotY;

      if (rotY === 0) {
        // Grand East Entrance Stairway: 10 wide stone steps descending from doorway (y = 2.40)
        // down to courtyard pavement (y = 0), matching media_1793861820894_5fb5ad04.jpg (Image 2)
        const stepCounts = 10;
        const totalHeight = 2.40;
        const totalDepth = 6.8;
        const stepW = 4.8;
        const tread = totalDepth / stepCounts; // 0.68m per tread

        for (let st = 0; st < stepCounts; st++) {
          const stepH = ((st + 1) / stepCounts) * totalHeight;
          const stepZ = 6.46 - st * tread;
          const stepMesh = new THREE.Mesh(
            new THREE.BoxGeometry(stepW, stepH, tread + 0.08),
            mainTempleSoapstoneMat
          );
          stepMesh.position.set(0, stepH / 2, stepZ);
          stepMesh.castShadow = true;
          stepMesh.receiveShadow = true;
          stairGroup.add(stepMesh);

          // Carpet strip on central path of each stone step
          const stepCarpet = new THREE.Mesh(
            new THREE.BoxGeometry(1.8, 0.02, tread - 0.04),
            coirCarpetMat
          );
          stepCarpet.position.set(0, stepH + 0.01, stepZ);
          stepCarpet.receiveShadow = true;
          stairGroup.add(stepCarpet);
        }

        // Low Stepped Cheek Curbs & Carved Upper Yali/Elephant Balustrades (matching photos)
        [-2.52, 2.52].forEach((bx) => {
          const balustrade = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.42, 6.2), mainTempleSoapstoneMat);
          balustrade.position.set(bx, 1.30, 3.25);
          balustrade.rotation.x = 0.34; // Slopes smoothly down from top landing (-Z) to ground (+Z)
          balustrade.castShadow = true;
          stairGroup.add(balustrade);

          // Upper Guardian Yali / Elephant sitting at top landing beside upper shrines
          const upperGuard = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.65, 0.72), friezeMat);
          upperGuard.position.set(bx > 0 ? 1.85 : -1.85, 2.58, 0.45);
          upperGuard.castShadow = true;
          stairGroup.add(upperGuard);

          // Lower Carved Stone Elephant at foot of stairs (facing courtyard)
          const elephantBody = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.55, 0.80), friezeMat);
          elephantBody.position.set(bx, 0.38, 6.45);
          elephantBody.castShadow = true;
          stairGroup.add(elephantBody);

          const elephantHead = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 10), friezeMat);
          elephantHead.position.set(bx, 0.54, 6.92);
          stairGroup.add(elephantHead);

          const elephantTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.04, 0.44, 8), friezeMat);
          elephantTrunk.position.set(bx, 0.32, 7.02);
          elephantTrunk.rotation.x = 0.35;
          stairGroup.add(elephantTrunk);
        });

        // Lower Flanking Miniature Shrines sitting on courtyard floor (y = 0.05) cleanly outside Jagati
        createHoysalaMiniatureShrine(-3.25, 0.05, 6.75, 0, 1.05, stairGroup);
        createHoysalaMiniatureShrine(3.25, 0.05, 6.75, 0, 1.05, stairGroup);

        // Upper Flanking Miniature Shrines at Jagati terrace level flanking doorway (y = 2.05)
        createHoysalaMiniatureShrine(-2.7, 2.05, 0.3, 0, 0.95, stairGroup);
        createHoysalaMiniatureShrine(2.7, 2.05, 0.3, 0, 0.95, stairGroup);

        // Courtyard Coir Runner Carpet leading to bottom of steps
        const courtyardRunner = new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 0.035, 6.2),
          coirCarpetMat
        );
        courtyardRunner.position.set(0, 0.018, 9.8);
        courtyardRunner.receiveShadow = true;
        stairGroup.add(courtyardRunner);
      } else {
        // North & South Side Entrance Stairways: 8 wide granite steps descending from y = 2.40 to y = 0.0
        // Matches Image 1 (media_1794477359287_0d4cb89f.jpg)
        const stepCounts = 8;
        const totalHeight = 2.40;
        const totalDepth = 5.4;
        const stepW = 3.3;
        const tread = totalDepth / stepCounts;

        for (let st = 0; st < stepCounts; st++) {
          const stepH = ((st + 1) / stepCounts) * totalHeight;
          const stepZ = 5.15 - st * tread;
          const stepMesh = new THREE.Mesh(
            new THREE.BoxGeometry(stepW, stepH, tread + 0.08),
            mainTempleSoapstoneMat
          );
          stepMesh.position.set(0, stepH / 2, stepZ);
          stepMesh.castShadow = true;
          stepMesh.receiveShadow = true;
          stairGroup.add(stepMesh);
        }

        // Low sloped cheek curbs + upper landing elephant/yali guards (NO backward-tilted wedges)
        [-1.78, 1.78].forEach((bx) => {
          const balustrade = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.40, 5.2), mainTempleSoapstoneMat);
          balustrade.position.set(bx, 1.28, 2.75);
          balustrade.rotation.x = 0.38;
          balustrade.castShadow = true;
          stairGroup.add(balustrade);

          const upperGuard = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.58, 0.68), friezeMat);
          upperGuard.position.set(bx > 0 ? 1.55 : -1.55, 2.55, 0.55);
          upperGuard.castShadow = true;
          stairGroup.add(upperGuard);

          const elephantBody = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.48, 0.72), friezeMat);
          elephantBody.position.set(bx, 0.34, 5.55);
          elephantBody.castShadow = true;
          stairGroup.add(elephantBody);
        });

        // Lower flanking shrines inside the open 5.26m courtyard channel (resting solidly at y = 0.05)
        createHoysalaMiniatureShrine(-2.22, 0.05, 5.25, 0, 0.90, stairGroup);
        createHoysalaMiniatureShrine(2.22, 0.05, 5.25, 0, 0.90, stairGroup);
        createHoysalaMiniatureShrine(-2.45, 2.05, 0.45, 0, 0.95, stairGroup);
        createHoysalaMiniatureShrine(2.45, 2.05, 0.45, 0, 0.95, stairGroup);
      }

      mainTempleGroup.add(stairGroup);
    };

    // East Main Entrance Stairway (aligned with facade at z = 7.2)
    createEntranceStairway(0, 0, 7.2);
    // North Entrance Stairway (centered cleanly in cutback channel Z = 0)
    createEntranceStairway(Math.PI / 2, 7.2, 0.0);
    // South Entrance Stairway (centered cleanly in cutback channel Z = 0)
    createEntranceStairway(-Math.PI / 2, -7.2, 0.0);

    // Navaranga Central Hall: Core Body + Stepped Flat Terraced Roof (matching photos, no outer dome)
    const navarangaLower = new THREE.Mesh(new THREE.BoxGeometry(12.6, 1.45, 12.6), friezeMat);
    navarangaLower.position.set(0, 2.78, 0.4);
    navarangaLower.castShadow = true;
    navarangaLower.receiveShadow = true;
    mainTempleGroup.add(navarangaLower);

    const navarangaJali = new THREE.Mesh(new THREE.BoxGeometry(12.2, 1.65, 12.2), mainTempleSoapstoneMat);
    navarangaJali.position.set(0, 4.28, 0.4);
    navarangaJali.castShadow = true;
    mainTempleGroup.add(navarangaJali);

    // Navaranga Stepped Horizontal Roof Slabs (receding cleanly inward toward Garbhagriha)
    const navEave = new THREE.Mesh(new THREE.BoxGeometry(13.6, 0.24, 12.8), mainRoofEaveMat);
    navEave.position.set(0, 5.08, 0.2);
    navEave.castShadow = true;
    mainTempleGroup.add(navEave);

    const navParapet1 = new THREE.Mesh(new THREE.BoxGeometry(12.4, 0.22, 11.8), mainTempleSoapstoneMat);
    navParapet1.position.set(0, 5.28, 0.1);
    navParapet1.castShadow = true;
    mainTempleGroup.add(navParapet1);

    const navParapet2 = new THREE.Mesh(new THREE.BoxGeometry(11.0, 0.20, 10.6), mainTempleSoapstoneMat);
    navParapet2.position.set(0, 5.46, 0.0);
    navParapet2.castShadow = true;
    mainTempleGroup.add(navParapet2);

    // Helper: Build Recessed Hoysala Wing Bay with Adhisthana Mouldings, Ribbed Dado, Jali Screen & Lathe Pillars
    const addEastWingBay = (
      bx: number,
      bz: number,
      bw: number,
      bd: number,
      wallTopY: number,
      eaveY: number,
      pillarXs: number[]
    ) => {
      // Lower Adhisthana Friezes (Y = 2.05 to Y = 3.15)
      const adhiBase = new THREE.Mesh(new THREE.BoxGeometry(bw, 1.12, bd), friezeMat);
      adhiBase.position.set(bx, 2.61, bz);
      adhiBase.castShadow = true;
      adhiBase.receiveShadow = true;
      mainTempleGroup.add(adhiBase);

      [2.22, 2.52, 2.82, 3.12].forEach((my) => {
        const course = new THREE.Mesh(
          new THREE.BoxGeometry(bw + 0.14, 0.09, bd + 0.14),
          my === 2.52 || my === 3.12 ? mainRoofEaveMat : mainTempleSoapstoneMat
        );
        course.position.set(bx, my, bz);
        mainTempleGroup.add(course);
      });

      // Carved Kakshasana Ribbed Dado Band (Y = 3.18 to Y = 3.56)
      const dadoPanel = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.06, 0.38, bd + 0.06), friezeMat);
      dadoPanel.position.set(bx, 3.37, bz);
      mainTempleGroup.add(dadoPanel);

      const ribCount = Math.max(5, Math.floor(bw * 4));
      for (let r = 0; r < ribCount; r++) {
        const rx = bx - bw / 2 + 0.14 + (r * (bw - 0.28)) / Math.max(1, ribCount - 1);
        const rib = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.34, 0.08), mainTempleSoapstoneMat);
        rib.position.set(rx, 3.37, bz + bd / 2 + 0.04);
        mainTempleGroup.add(rib);
      }

      // Upper Pierced Stone Jali Lattice Screen (Y = 3.56 up to wallTopY)
      const jaliH = wallTopY - 3.56;
      const wingJali = new THREE.Mesh(new THREE.BoxGeometry(bw - 0.12, jaliH, 0.22), jaliMat);
      wingJali.position.set(bx, 3.56 + jaliH / 2, bz + bd / 2 - 0.08);
      wingJali.castShadow = true;
      mainTempleGroup.add(wingJali);

      // Backing stone wall inside wing
      const wingWallBack = new THREE.Mesh(new THREE.BoxGeometry(bw - 0.10, jaliH, bd - 0.15), mainTempleSoapstoneMat);
      wingWallBack.position.set(bx, 3.56 + jaliH / 2, bz - 0.08);
      mainTempleGroup.add(wingWallBack);

      // Pinkish-Sandstone Lathe-Turned Columns + Bracket Capitals & Madanika Figures
      pillarXs.forEach((px) => {
        const pBase = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.28, 0.32), mainTempleSoapstoneMat);
        pBase.position.set(px, 3.32, bz + bd / 2 + 0.06);
        mainTempleGroup.add(pBase);

        const pShaft = new THREE.Mesh(
          new THREE.CylinderGeometry(0.14, 0.16, jaliH + 0.05, 14),
          portalPinkPillarMat
        );
        pShaft.position.set(px, 3.46 + jaliH / 2, bz + bd / 2 + 0.06);
        pShaft.castShadow = true;
        mainTempleGroup.add(pShaft);

        const pCap = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.20, 0.40), mainRoofEaveMat);
        pCap.position.set(px, wallTopY - 0.05, bz + bd / 2 + 0.08);
        mainTempleGroup.add(pCap);

        const madanika = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.42, 0.16), shrineStoneMat);
        madanika.position.set(px, wallTopY - 0.18, bz + bd / 2 + 0.22);
        madanika.rotation.x = 0.48;
        mainTempleGroup.add(madanika);
      });

      // Stepped Overhanging Kapota Eave & Parapet Cornice Slab above wing
      const wingEave = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.65, 0.20, bd + 0.95), mainRoofEaveMat);
      wingEave.position.set(bx, eaveY, bz + 0.25);
      wingEave.castShadow = true;
      mainTempleGroup.add(wingEave);

      const wingParapet = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.25, 0.22, bd + 0.55), mainTempleSoapstoneMat);
      wingParapet.position.set(bx, eaveY + 0.20, bz + 0.12);
      wingParapet.castShadow = true;
      mainTempleGroup.add(wingParapet);
    };

    // Middle Flanking Jali Wings (Left & Right, matching media_1794476214453_b66a0b6a.jpg)
    addEastWingBay(-5.05, 6.75, 2.55, 1.35, 4.92, 5.04, [-3.90, -5.05, -6.22]);
    addEastWingBay(5.05, 6.75, 2.55, 1.35, 4.92, 5.04, [3.90, 5.05, 6.22]);

    // Outer Corner Receding Wing Bays (Stepped further back & lower on left & right)
    addEastWingBay(-7.15, 5.75, 1.85, 1.45, 4.58, 4.68, [-6.40, -7.92]);
    addEastWingBay(7.15, 5.75, 1.85, 1.45, 4.58, 4.68, [6.40, 7.92]);

    // =========================================================================
    // Grand Central East Entrance Facade (Mukhamandapa)
    // 100% accurate to media_1794476245044_e8dab8b7.jpg & media_1794476214453_b66a0b6a.jpg
    // =========================================================================
    const frontFacadeGroup = new THREE.Group();
    frontFacadeGroup.position.set(0, 0, 7.5);
    mainTempleGroup.add(frontFacadeGroup);

    // 1. Portal Wall Structure & Adhisthana Base Flanking Doorway
    const portalBackingWall = new THREE.Mesh(new THREE.BoxGeometry(7.2, 3.25, 0.90), mainTempleSoapstoneMat);
    portalBackingWall.position.set(0, 3.68, -0.35);
    portalBackingWall.castShadow = true;
    portalBackingWall.receiveShadow = true;
    frontFacadeGroup.add(portalBackingWall);

    // Deep Central Dark Doorway Portal Opening
    const doorInner = new THREE.Mesh(new THREE.BoxGeometry(1.62, 2.38, 1.25), shrineNicheMat);
    doorInner.position.set(0, 3.22, -0.32);
    frontFacadeGroup.add(doorInner);

    // Ornate Carved Dvara-Shakha Frame & Pinkish Lathe-Turned Entrance Pilasters (visible in photo!)
    [-0.96, 0.96].forEach((px) => {
      const doorPilasterBase = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.28, 0.28), mainTempleSoapstoneMat);
      doorPilasterBase.position.set(px, 2.18, 0.16);
      frontFacadeGroup.add(doorPilasterBase);

      const doorPilasterShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.11, 0.13, 2.05, 14),
        portalPinkPillarMat
      );
      doorPilasterShaft.position.set(px, 3.30, 0.16);
      doorPilasterShaft.castShadow = true;
      frontFacadeGroup.add(doorPilasterShaft);

      const doorPilasterCap = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.18, 0.32), mainRoofEaveMat);
      doorPilasterCap.position.set(px, 4.38, 0.16);
      frontFacadeGroup.add(doorPilasterCap);
    });

    // Multi-Banded Carved Lintel & Semicircular Makara Torana Tympanum Arch
    const portalLintel = new THREE.Mesh(new THREE.BoxGeometry(2.45, 0.26, 0.30), mainRoofEaveMat);
    portalLintel.position.set(0, 4.46, 0.16);
    portalLintel.castShadow = true;
    frontFacadeGroup.add(portalLintel);

    const makaratorana = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.92, 0.24), toranaMat);
    makaratorana.position.set(0, 4.92, 0.14);
    makaratorana.castShadow = true;
    frontFacadeGroup.add(makaratorana);

    // Arched Makara Torana Tympanum Crest (curved crown visible above doorway)
    const toranaArch = new THREE.Mesh(
      new THREE.CylinderGeometry(1.15, 1.15, 0.20, 20, 1, false, 0, Math.PI),
      friezeMat
    );
    toranaArch.rotation.z = Math.PI / 2;
    toranaArch.rotation.y = Math.PI / 2;
    toranaArch.position.set(0, 4.58, 0.18);
    frontFacadeGroup.add(toranaArch);

    // Intricately Carved Relief Panels Left & Right of Torana + 4 Miniature Diamond Windows below
    [-2.42, 2.42].forEach((rx) => {
      const reliefPanel = new THREE.Mesh(new THREE.BoxGeometry(2.05, 1.35, 0.22), friezeMat);
      reliefPanel.position.set(rx, 4.45, 0.12);
      reliefPanel.castShadow = true;
      frontFacadeGroup.add(reliefPanel);

      // 4 small diamond perforation accents along middle belt (clearly seen in close-up photo)
      const diamondStrip = new THREE.Mesh(new THREE.BoxGeometry(1.90, 0.45, 0.16), jaliMat);
      diamondStrip.position.set(rx, 3.65, 0.14);
      frontFacadeGroup.add(diamondStrip);

      // Horizontal carved base bands below upper miniature shrines
      const portalAdhi = new THREE.Mesh(new THREE.BoxGeometry(2.15, 1.15, 0.34), friezeMat);
      portalAdhi.position.set(rx, 2.62, 0.10);
      frontFacadeGroup.add(portalAdhi);
    });

    // Sculpted Dvarapala & Devi Guardian Figures flanking doorway
    [-1.36, 1.36].forEach((dx) => {
      const dvPedestal = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.28, 0.32), friezeMat);
      dvPedestal.position.set(dx, 2.18, 0.18);
      frontFacadeGroup.add(dvPedestal);

      const dvHalo = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.10, 14), shrineStoneMat);
      dvHalo.rotation.x = Math.PI / 2;
      dvHalo.position.set(dx, 2.85, 0.14);
      frontFacadeGroup.add(dvHalo);

      const dvBody = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 0.95, 12), shrineStoneMat);
      dvBody.position.set(dx, 2.75, 0.20);
      dvBody.castShadow = true;
      frontFacadeGroup.add(dvBody);

      const dvCrown = new THREE.Mesh(new THREE.ConeGeometry(0.11, 0.26, 10), mainTempleSoapstoneMat);
      dvCrown.position.set(dx, 3.35, 0.20);
      frontFacadeGroup.add(dvCrown);
    });

    // 2. 4 Stout Pinkish-Sandstone Portal Columns & Madanika Bracket Figures under Deep Eave
    [-3.52, -1.72, 1.72, 3.52].forEach((px) => {
      const colBase = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.32, 0.42), mainTempleSoapstoneMat);
      colBase.position.set(px, 3.25, 0.42);
      frontFacadeGroup.add(colBase);

      const colShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.16, 0.19, 1.72, 16),
        portalPinkPillarMat
      );
      colShaft.position.set(px, 4.25, 0.42);
      colShaft.castShadow = true;
      frontFacadeGroup.add(colShaft);

      // Carved Torus Rings on Lathe-Turned Column Shaft
      [3.75, 4.25, 4.65].forEach((ry) => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.20, 0.035, 8, 16), mainRoofEaveMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.set(px, ry, 0.42);
        frontFacadeGroup.add(ring);
      });

      const colCap = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.24, 0.48), mainRoofEaveMat);
      colCap.position.set(px, 5.18, 0.42);
      frontFacadeGroup.add(colCap);

      // Angled Salabhanjika / Madanika Bracket Figure directly beneath eave overhang (see photo!)
      const madanika = new THREE.Mesh(new THREE.BoxGeometry(0.20, 0.58, 0.20), shrineStoneMat);
      madanika.position.set(px, 5.02, 0.68);
      madanika.rotation.x = 0.52;
      madanika.castShadow = true;
      frontFacadeGroup.add(madanika);
    });

    // 3. Tallest Projecting Central Overhanging Kapota Eave & Double Cornice Skirt
    const frontChhajjaMain = new THREE.Mesh(new THREE.BoxGeometry(8.1, 0.24, 2.5), mainRoofEaveMat);
    frontChhajjaMain.position.set(0, 5.42, 0.35);
    frontChhajjaMain.castShadow = true;
    frontChhajjaMain.receiveShadow = true;
    frontFacadeGroup.add(frontChhajjaMain);

    const frontEaveTrim = new THREE.Mesh(new THREE.BoxGeometry(7.7, 0.14, 2.2), friezeMat);
    frontEaveTrim.position.set(0, 5.26, 0.30);
    frontFacadeGroup.add(frontEaveTrim);

    // Upturned Corner Eave Scrolls (left & right corners of overhanging eave)
    [-4.0, 4.0].forEach((cx) => {
      const tip = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.24, 6), mainTempleSoapstoneMat);
      tip.position.set(cx, 5.62, 1.56);
      frontFacadeGroup.add(tip);
    });

    // 4. Two Flat Stepped Horizontal Stone Parapet Tiers + Central Carved Skyline Crest
    // Exact flat stepped silhouette seen in media_1794476214453_b66a0b6a.jpg & media_1794476245044_e8dab8b7.jpg
    const parapetTier1 = new THREE.Mesh(new THREE.BoxGeometry(7.5, 0.20, 2.1), mainTempleSoapstoneMat);
    parapetTier1.position.set(0, 5.64, 0.25);
    parapetTier1.castShadow = true;
    frontFacadeGroup.add(parapetTier1);

    const parapetTier2 = new THREE.Mesh(new THREE.BoxGeometry(6.9, 0.18, 1.85), friezeMat);
    parapetTier2.position.set(0, 5.83, 0.20);
    parapetTier2.castShadow = true;
    frontFacadeGroup.add(parapetTier2);

    // Central Carved Rooftop Sculpture Crest (Seated central figure + attendants at top center)
    const crestBase = new THREE.Mesh(new THREE.BoxGeometry(2.15, 0.32, 0.45), mainTempleSoapstoneMat);
    crestBase.position.set(0, 6.08, 0.45);
    crestBase.castShadow = true;
    frontFacadeGroup.add(crestBase);

    const crestCenterFigure = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 0.44, 10), shrineStoneMat);
    crestCenterFigure.position.set(0, 6.32, 0.45);
    crestCenterFigure.castShadow = true;
    frontFacadeGroup.add(crestCenterFigure);

    [-0.58, 0.58].forEach((ax) => {
      const crestAttendant = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.34, 0.32), shrineStoneMat);
      crestAttendant.position.set(ax, 6.26, 0.45);
      frontFacadeGroup.add(crestAttendant);
    });

    // Lathe-Turned Pillars inside Navaranga (Srikara & Indrakantha Pillars, Fig 2.22)
    const createLathePillar = (px: number, pz: number) => {
      const pGroup = new THREE.Group();
      pGroup.position.set(px, 1.5, pz);

      const base = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.6, 0.7), mainTempleSoapstoneMat);
      base.position.y = 0.3;
      pGroup.add(base);

      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.28, 2.2, 24), polishedPillarMat);
      shaft.position.y = 1.7;
      pGroup.add(shaft);

      [1.1, 1.4, 1.8, 2.1].forEach((ry) => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.32, 0.06, 12, 24), polishedPillarMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.y = ry;
        pGroup.add(ring);
      });

      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.26, 0.4, 16), polishedPillarMat);
      cap.position.y = 2.9;
      pGroup.add(cap);

      mainTempleGroup.add(pGroup);
    };
    createLathePillar(-2.5, -1);
    createLathePillar(2.5, -1);
    createLathePillar(-2.5, 3);
    createLathePillar(2.5, 3);

    // =========================================================================
    // Antarala Vestibule & Garbhagriha Sanctum (Features #1 & #2)
    // Properly fitted to the Jagati terrace floor (y = 2.05) and integrated
    // with the Navaranga rear wall, matching the real Belur Chennakeshava architecture
    // =========================================================================

    // A. Antarala (Vestibule Connector between Navaranga and Garbhagriha)
    // Spans z = -5.6 to z = -7.4 (centered at z = -6.5)
    const antaralaGroup = new THREE.Group();
    antaralaGroup.position.set(0, 0, -6.5);

    // Antarala Lower Adhisthana Frieze (y = 2.05 to 3.25)
    const antaralaLower = new THREE.Mesh(new THREE.BoxGeometry(6.4, 1.2, 2.0), friezeMat);
    antaralaLower.position.set(0, 2.65, 0);
    antaralaLower.castShadow = true;
    antaralaLower.receiveShadow = true;
    antaralaGroup.add(antaralaLower);

    // Antarala Upper Soapstone Wall (y = 3.25 to 5.1)
    const antaralaUpper = new THREE.Mesh(new THREE.BoxGeometry(6.0, 1.85, 2.0), mainTempleSoapstoneMat);
    antaralaUpper.position.set(0, 4.18, 0);
    antaralaUpper.castShadow = true;
    antaralaGroup.add(antaralaUpper);

    // Antarala Overhanging Chhajja Eaves (y = 5.2)
    const antaralaEaves = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.35, 2.2), mainTempleSoapstoneMat);
    antaralaEaves.position.set(0, 5.2, 0);
    antaralaEaves.castShadow = true;
    antaralaGroup.add(antaralaEaves);

    // Hoysala Royal Sala Emblem Crest on Antarala roof
    const salaEmblem = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.8, 0.6), mainTempleSoapstoneMat);
    salaEmblem.position.set(0, 5.75, 0);
    salaEmblem.castShadow = true;
    antaralaGroup.add(salaEmblem);

    mainTempleGroup.add(antaralaGroup);

    // B. Garbhagriha (Stellate Sanctum Sanctorum)
    // Centered at z = -9.5, resting firmly on the Jagati terrace floor (y = 2.05)
    // Star radius: inner 3.2, outer 4.3 (fits with circumambulatory walkway on Jagati)
    const garbhagrihaGroup = new THREE.Group();
    garbhagrihaGroup.position.set(0, 0, -9.5);

    // 1. Lower Adhisthana Star Frieze Plinth (y = 2.05 to 3.25)
    const gStarLower = createStarShape(16, 3.2, 4.3);
    const garbhagrihaLower = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gStarLower, { depth: 1.2, bevelEnabled: true, bevelSize: 0.1 }),
      friezeMat
    );
    garbhagrihaLower.rotation.x = -Math.PI / 2;
    garbhagrihaLower.position.y = 2.05;
    garbhagrihaLower.castShadow = true;
    garbhagrihaLower.receiveShadow = true;
    garbhagrihaGroup.add(garbhagrihaLower);

    // 2. Upper Sculpted Soapstone Star Walls with deity niches (y = 3.25 to 5.1)
    const gStarUpper = createStarShape(16, 3.0, 4.1);
    const garbhagrihaUpper = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gStarUpper, { depth: 1.85, bevelEnabled: true, bevelSize: 0.08 }),
      mainTempleSoapstoneMat
    );
    garbhagrihaUpper.rotation.x = -Math.PI / 2;
    garbhagrihaUpper.position.y = 3.25;
    garbhagrihaUpper.castShadow = true;
    garbhagrihaUpper.receiveShadow = true;
    garbhagrihaGroup.add(garbhagrihaUpper);

    // 3. Double-Tiered Overhanging Chhajja Stone Eaves (matching Navaranga eaves)
    const gChhajjaLowerStar = createStarShape(16, 3.6, 4.7);
    const gChhajjaLower = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gChhajjaLowerStar, { depth: 0.25, bevelEnabled: true, bevelSize: 0.05 }),
      mainTempleSoapstoneMat
    );
    gChhajjaLower.rotation.x = -Math.PI / 2;
    gChhajjaLower.position.y = 5.1;
    gChhajjaLower.castShadow = true;
    garbhagrihaGroup.add(gChhajjaLower);

    const gChhajjaUpperStar = createStarShape(16, 3.4, 4.4);
    const gChhajjaUpper = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gChhajjaUpperStar, { depth: 0.25, bevelEnabled: true, bevelSize: 0.05 }),
      mainTempleSoapstoneMat
    );
    gChhajjaUpper.rotation.x = -Math.PI / 2;
    gChhajjaUpper.position.y = 5.35;
    gChhajjaUpper.castShadow = true;
    garbhagrihaGroup.add(gChhajjaUpper);

    // 4. Low-Stepped Stone Slab Roof Terrace (as seen in Belur drone & side photographs)
    const gRoofStar = createStarShape(16, 2.5, 3.4);
    const gRoofTerrace = new THREE.Mesh(
      new THREE.ExtrudeGeometry(gRoofStar, { depth: 0.35, bevelEnabled: true, bevelSize: 0.08 }),
      mainTempleSoapstoneMat
    );
    gRoofTerrace.rotation.x = -Math.PI / 2;
    gRoofTerrace.position.y = 5.6;
    gRoofTerrace.castShadow = true;
    garbhagrihaGroup.add(gRoofTerrace);

    // 5. Traditional Low Hoysala Stone Stupika / Kalasha Finial
    const stupikaBase = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.45, 0.3, 16), mainTempleSoapstoneMat);
    stupikaBase.position.y = 6.1;
    stupikaBase.castShadow = true;
    garbhagrihaGroup.add(stupikaBase);

    const stupikaFinial = new THREE.Mesh(new THREE.ConeGeometry(0.25, 0.5, 16), goldKalashaMat);
    stupikaFinial.position.y = 6.5;
    stupikaFinial.castShadow = true;
    garbhagrihaGroup.add(stupikaFinial);

    mainTempleGroup.add(garbhagrihaGroup);

    // Authentic North & South Side Entrance Portals (Dvara Mandapas) & Wing Jali Bays
    // Replaces floating table-box porches; 100% matched to Image 1 (media_1794477359287_0d4cb89f.jpg)
    const createSideFacade = (sideDir: 1 | -1) => {
      const sideGroup = new THREE.Group();
      sideGroup.position.set(sideDir * 6.25, 0, 0.0);
      sideGroup.rotation.y = sideDir * (Math.PI / 2);

      // 1. Central Portal Backing Wall & Ornate Rosette Entrance Doorway
      const sBackWall = new THREE.Mesh(new THREE.BoxGeometry(5.6, 3.25, 0.90), mainTempleSoapstoneMat);
      sBackWall.position.set(0, 3.68, 0.35);
      sBackWall.castShadow = true;
      sBackWall.receiveShadow = true;
      sideGroup.add(sBackWall);

      const sDoorOuter = new THREE.Mesh(new THREE.BoxGeometry(1.72, 2.38, 0.20), friezeMat);
      sDoorOuter.position.set(0, 3.20, 0.78);
      sideGroup.add(sDoorOuter);

      const sDoorLeaf = new THREE.Mesh(new THREE.BoxGeometry(1.32, 2.15, 0.12), kappeDoorMat);
      sDoorLeaf.position.set(0, 3.15, 0.85);
      sideGroup.add(sDoorLeaf);

      // Pinkish-red lathe-turned doorway pilasters (matching side portal photo)
      [-0.86, 0.86].forEach((px) => {
        const sPil = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 2.05, 14), portalPinkPillarMat);
        sPil.position.set(px, 3.28, 0.88);
        sPil.castShadow = true;
        sideGroup.add(sPil);
      });

      // Heavy Carved Lintel + Makara Torana Tympanum Arch above door
      const sLintel = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.24, 0.28), mainRoofEaveMat);
      sLintel.position.set(0, 4.42, 0.88);
      sideGroup.add(sLintel);

      const sTorana = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.88, 0.22), toranaMat);
      sTorana.position.set(0, 4.88, 0.86);
      sTorana.castShadow = true;
      sideGroup.add(sTorana);

      // Flanking Sculpted Relief Panels, Diamond Jali Insets & Dvarapala Guardians
      [-1.95, 1.95].forEach((rx) => {
        const relief = new THREE.Mesh(new THREE.BoxGeometry(1.45, 1.25, 0.20), friezeMat);
        relief.position.set(rx, 4.45, 0.84);
        sideGroup.add(relief);

        const dStrip = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.42, 0.16), kappeJaliMat);
        dStrip.position.set(rx, 3.65, 0.85);
        sideGroup.add(dStrip);

        const baseCourse = new THREE.Mesh(new THREE.BoxGeometry(1.55, 1.15, 0.30), friezeMat);
        baseCourse.position.set(rx, 2.62, 0.80);
        sideGroup.add(baseCourse);
      });

      [-1.22, 1.22].forEach((dx) => {
        const dvBody = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.14, 0.90, 10), shrineStoneMat);
        dvBody.position.set(dx, 2.75, 0.88);
        sideGroup.add(dvBody);
      });

      // 2. 4 Pinkish-Sandstone Portal Columns & Madanika Bracket Figures under Deep Eave
      [-2.68, -1.52, 1.52, 2.68].forEach((px) => {
        const cBase = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.28, 0.36), mainTempleSoapstoneMat);
        cBase.position.set(px, 3.25, 1.12);
        sideGroup.add(cBase);

        const cShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.17, 1.72, 14), portalPinkPillarMat);
        cShaft.position.set(px, 4.24, 1.12);
        cShaft.castShadow = true;
        sideGroup.add(cShaft);

        const cCap = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.22, 0.42), mainRoofEaveMat);
        cCap.position.set(px, 5.16, 1.12);
        sideGroup.add(cCap);

        const sMadanika = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.52, 0.18), shrineStoneMat);
        sMadanika.position.set(px, 5.00, 1.36);
        sMadanika.rotation.x = 0.50;
        sideGroup.add(sMadanika);
      });

      // 3. Dramatic Broad Overhanging Side Kapota Eave & 2 Flat Stepped Parapet Tiers
      const sideEaveMain = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.22, 2.35), mainRoofEaveMat);
      sideEaveMain.position.set(0, 5.40, 0.95);
      sideEaveMain.castShadow = true;
      sideGroup.add(sideEaveMain);

      const sideEaveTrim = new THREE.Mesh(new THREE.BoxGeometry(6.2, 0.14, 2.10), friezeMat);
      sideEaveTrim.position.set(0, 5.25, 0.90);
      sideGroup.add(sideEaveTrim);

      const sideParapet1 = new THREE.Mesh(new THREE.BoxGeometry(5.9, 0.20, 1.95), mainTempleSoapstoneMat);
      sideParapet1.position.set(0, 5.60, 0.85);
      sideGroup.add(sideParapet1);

      const sideParapet2 = new THREE.Mesh(new THREE.BoxGeometry(5.3, 0.18, 1.70), friezeMat);
      sideParapet2.position.set(0, 5.78, 0.80);
      sideGroup.add(sideParapet2);

      // 4. Left & Right Recessed Side Wing Bays with Diamond Jali Screens (eliminates stretched horizontal stripes)
      [-4.25, 4.25].forEach((wx) => {
        const adhi = new THREE.Mesh(new THREE.BoxGeometry(2.75, 1.12, 0.70), friezeMat);
        adhi.position.set(wx, 2.61, 0.15);
        sideGroup.add(adhi);

        const dado = new THREE.Mesh(new THREE.BoxGeometry(2.78, 0.38, 0.72), friezeMat);
        dado.position.set(wx, 3.37, 0.15);
        sideGroup.add(dado);

        const wJali = new THREE.Mesh(new THREE.BoxGeometry(2.65, 1.32, 0.22), kappeJaliMat);
        wJali.position.set(wx, 4.22, 0.42);
        sideGroup.add(wJali);

        const wBack = new THREE.Mesh(new THREE.BoxGeometry(2.65, 1.32, 0.55), mainTempleSoapstoneMat);
        wBack.position.set(wx, 4.22, 0.08);
        sideGroup.add(wBack);

        [-1.15, 0, 1.15].forEach((dx) => {
          const wCol = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.15, 1.38, 12), portalPinkPillarMat);
          wCol.position.set(wx + dx, 4.18, 0.56);
          wCol.castShadow = true;
          sideGroup.add(wCol);
        });

        const wEave = new THREE.Mesh(new THREE.BoxGeometry(3.15, 0.20, 1.35), mainRoofEaveMat);
        wEave.position.set(wx, 5.02, 0.42);
        wEave.castShadow = true;
        sideGroup.add(wEave);

        const wParapet = new THREE.Mesh(new THREE.BoxGeometry(2.85, 0.20, 1.10), mainTempleSoapstoneMat);
        wParapet.position.set(wx, 5.20, 0.35);
        sideGroup.add(wParapet);
      });

      mainTempleGroup.add(sideGroup);
    };
    createSideFacade(1); // North Side Entrance & Wing Bays (+X)
    createSideFacade(-1); // South Side Entrance & Wing Bays (-X)

    // =========================================================================
    // 2. KAPPE CHENNIGARAYA TEMPLE (#2)
    // Positioned cleanly in South Courtyard (-26.5, 0, 3) with generous clearance
    // from both Chennakeshava Main Temple (North) and South Cloister (South).
    // 100% Architecturally faithful to media_1794475618986_0a9ff9cd.jpg:
    // stellate stepped Jagati, East stairway with twin elephant balustrades,
    // rosette double-door + Dvarapalas, pierced diamond Jali screens with
    // ribbed Kakshasana dado, lathe-turned pillars, and flat stepped Kapota roof.
    // =========================================================================
    const kappeGroup = new THREE.Group();
    kappeGroup.position.set(-26.5, 0, 3);
    worldGroup.add(kappeGroup);

    const createKappeStarShape = (innerR: number, outerR: number): THREE.Shape => {
      const shape = new THREE.Shape();
      const points = 8;
      const step = Math.PI / points;
      const v11X = Math.cos(11 * step) * innerR;
      const v13X = Math.cos(13 * step) * innerR;
      for (let i = 0; i < points * 2; i++) {
        if (i === 12) {
          // Open East stairway portal at +Z (y = -3.7 in 2D shape space)
          shape.lineTo(v11X, -3.7);
          shape.lineTo(v13X, -3.7);
          continue;
        }
        const r = i % 2 === 0 ? outerR : innerR;
        const angle = i * step;
        const x = Math.cos(angle) * r;
        const y = Math.sin(angle) * r;
        if (i === 0) shape.moveTo(x, y);
        else shape.lineTo(x, y);
      }
      shape.closePath();
      return shape;
    };

    // A. Multi-Tiered Stellate Jagati Platform (Y = 0.05 up to Y = 1.50)
    const kappeJagatiLower = new THREE.Mesh(
      new THREE.ExtrudeGeometry(createKappeStarShape(5.3, 6.7), {
        depth: 0.55,
        bevelEnabled: true,
        bevelThickness: 0.15,
        bevelSize: 0.12,
      }),
      friezeMat
    );
    kappeJagatiLower.rotation.x = -Math.PI / 2;
    kappeJagatiLower.position.y = 0.20;
    kappeJagatiLower.castShadow = true;
    kappeJagatiLower.receiveShadow = true;
    kappeGroup.add(kappeJagatiLower);

    const kappeJagatiMid = new THREE.Mesh(
      new THREE.ExtrudeGeometry(createKappeStarShape(5.05, 6.45), {
        depth: 0.20,
        bevelEnabled: true,
        bevelThickness: 0.06,
        bevelSize: 0.06,
      }),
      kappeStoneMat
    );
    kappeJagatiMid.rotation.x = -Math.PI / 2;
    kappeJagatiMid.position.y = 0.94;
    kappeJagatiMid.castShadow = true;
    kappeJagatiMid.receiveShadow = true;
    kappeGroup.add(kappeJagatiMid);

    const kappeJagatiUpper = new THREE.Mesh(
      new THREE.ExtrudeGeometry(createKappeStarShape(4.85, 6.20), {
        depth: 0.22,
        bevelEnabled: true,
        bevelThickness: 0.05,
        bevelSize: 0.05,
      }),
      kappeStoneMat
    );
    kappeJagatiUpper.rotation.x = -Math.PI / 2;
    kappeJagatiUpper.position.y = 1.23;
    kappeJagatiUpper.castShadow = true;
    kappeJagatiUpper.receiveShadow = true;
    kappeGroup.add(kappeJagatiUpper);

    // B. Front East Staircase (7 solid granite steps + upper corner plinths)
    for (let s = 0; s < 7; s++) {
      const stepMesh = new THREE.Mesh(
        new THREE.BoxGeometry(3.6, 0.22, 0.52),
        tankAshlarMat
      );
      stepMesh.position.set(0, 0.11 + s * 0.21, 6.6 - s * 0.45);
      stepMesh.castShadow = true;
      stepMesh.receiveShadow = true;
      kappeGroup.add(stepMesh);
    }

    // Upper staircase corner plinth blocks (matching foreground photo)
    [-1.75, 1.75].forEach((px) => {
      const topPlinth = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.24, 0.55), kappePlinthMat);
      topPlinth.position.set(px, 1.60, 4.25);
      topPlinth.castShadow = true;
      kappeGroup.add(topPlinth);
    });

    // Twin Carved Stone Elephant Balustrades (Gaja) at bottom of East steps
    // 100% Architecturally faithful to Reference Images (media_1794551263207_a6ff5547.jpg):
    // - Molded stepped ashlar stone pedestal (pitha)
    // - 4 sturdy pillar legs with carved padaka anklets
    // - Muscular rounded barrel body, shoulder and rump curves, natural hanging tail
    // - Intricately carved saddle blanket (jhul) with floral borders and draped cloth flaps
    // - Multi-strand beaded chest harness / necklace with hanging stone bells (ghanta)
    // - Expressive head with twin frontal temple lobes (gajakumbha) and forehead medallion
    // - Fanned curved ears, forward-pointing ivory tusks & articulated 4-segment trunk curling down onto the pedestal
    [-2.08, 2.08].forEach((ex) => {
      const gajaBalustrade = new THREE.Group();
      gajaBalustrade.position.set(ex, 0.05, 6.25);

      // 1. Molded Stepped Ashlar Pedestal (Pitha)
      const pBase = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.16, 1.45), tankAshlarMat);
      pBase.position.y = 0.08;
      pBase.castShadow = true;
      pBase.receiveShadow = true;
      gajaBalustrade.add(pBase);

      const pMid = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.14, 1.38), kappeEaveMat);
      pMid.position.y = 0.23;
      pMid.castShadow = true;
      pMid.receiveShadow = true;
      gajaBalustrade.add(pMid);

      const pTop = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.12, 1.42), kappeStoneMat);
      pTop.position.y = 0.36;
      pTop.castShadow = true;
      pTop.receiveShadow = true;
      gajaBalustrade.add(pTop);

      // 2. Four Sturdy Pillar Legs with Carved Padaka Anklets
      [-0.22, 0.22].forEach((lx) => {
        [-0.34, 0.30].forEach((lz) => {
          // Foot base cushion
          const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.10, 12), kappeStoneMat);
          foot.position.set(lx, 0.47, lz);
          foot.castShadow = true;
          gajaBalustrade.add(foot);

          // Carved ornamental anklet (padaka / ghungroo ring)
          const anklet = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 0.06, 12), friezeMat);
          anklet.position.set(lx, 0.54, lz);
          gajaBalustrade.add(anklet);

          // Sturdy leg column
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 0.38, 12), kappeStoneMat);
          leg.position.set(lx, 0.73, lz);
          leg.castShadow = true;
          gajaBalustrade.add(leg);
        });
      });

      // 3. Rounded Muscular Torso, Shoulders & Rump
      // Horizontal barrel torso
      const gajaTorso = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.36, 0.74, 16), kappeStoneMat);
      gajaTorso.rotation.x = Math.PI / 2;
      gajaTorso.position.set(0, 1.02, -0.02);
      gajaTorso.castShadow = true;
      gajaBalustrade.add(gajaTorso);

      // Rounded shoulder bulges
      [-0.22, 0.22].forEach((sx) => {
        const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), kappeStoneMat);
        shoulder.position.set(sx, 1.04, 0.24);
        shoulder.castShadow = true;
        gajaBalustrade.add(shoulder);
      });

      // Rounded hindquarters / rump
      const gajaRump = new THREE.Mesh(new THREE.SphereGeometry(0.32, 12, 12), kappeStoneMat);
      gajaRump.position.set(0, 1.02, -0.34);
      gajaRump.castShadow = true;
      gajaBalustrade.add(gajaRump);

      // Natural hanging tail
      const gajaTail = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.02, 0.46, 8), kappeStoneMat);
      gajaTail.position.set(0, 0.82, -0.56);
      gajaTail.rotation.x = -0.25;
      gajaBalustrade.add(gajaTail);

      // 4. Intricately Carved Saddle Blanket / Caparison (Jhul)
      const gajaBlanketTop = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.08, 0.58), friezeMat);
      gajaBlanketTop.position.set(0, 1.25, -0.02);
      gajaBlanketTop.castShadow = true;
      gajaBalustrade.add(gajaBlanketTop);

      // Under-belly cinch girth band connecting the saddle blanket
      const girthBand = new THREE.Mesh(new THREE.CylinderGeometry(0.365, 0.365, 0.12, 16, 1, true, 0, Math.PI), friezeMat);
      girthBand.rotation.x = Math.PI / 2;
      girthBand.rotation.z = Math.PI;
      girthBand.position.set(0, 1.02, -0.02);
      gajaBalustrade.add(girthBand);

      // Draped side cloth flaps with scalloped fringe
      [-0.34, 0.34].forEach((bx) => {
        const flap = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.34, 0.54), friezeMat);
        flap.position.set(bx, 1.02, -0.02);
        flap.castShadow = true;
        gajaBalustrade.add(flap);

        const fringe = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.56), kappeEaveMat);
        fringe.position.set(bx, 0.83, -0.02);
        gajaBalustrade.add(fringe);

        // Hanging carved tassels at blanket corners (Image 1)
        [-0.24, 0.24].forEach((tz) => {
          const tassel = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.045, 0.12, 8), darkBronzeMat);
          tassel.position.set(bx + (bx > 0 ? 0.02 : -0.02), 0.74, -0.02 + tz);
          tassel.castShadow = true;
          gajaBalustrade.add(tassel);
        });
      });

      // 5. Multi-Strand Carved Necklace & Chest Girdle with Hanging Bell (Ghanta)
      const neckCollar = new THREE.Mesh(new THREE.BoxGeometry(0.66, 0.08, 0.12), friezeMat);
      neckCollar.position.set(0, 0.94, 0.36);
      neckCollar.castShadow = true;
      gajaBalustrade.add(neckCollar);

      const upperNeckCollar = new THREE.Mesh(new THREE.BoxGeometry(0.60, 0.06, 0.10), friezeMat);
      upperNeckCollar.position.set(0, 1.04, 0.38);
      gajaBalustrade.add(upperNeckCollar);

      // Hanging bells (ghanta) across chest (front center and both flanks)
      [-0.24, 0, 0.24].forEach((bellX) => {
        const bell = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.075, 0.12, 8), darkBronzeMat);
        bell.position.set(bellX, 0.84, bellX === 0 ? 0.38 : 0.35);
        bell.castShadow = true;
        gajaBalustrade.add(bell);
      });

      // 6. Sculpted Hoysala Head, Forehead Medallion & Gajakumbha Temples
      const gajaHead = new THREE.Mesh(new THREE.SphereGeometry(0.28, 14, 14), kappeStoneMat);
      gajaHead.position.set(0, 1.18, 0.44);
      gajaHead.castShadow = true;
      gajaBalustrade.add(gajaHead);

      // Twin frontal temple domes (Gajakumbha)
      [-0.10, 0.10].forEach((kx) => {
        const kumbha = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 10), kappeStoneMat);
        kumbha.position.set(kx, 1.34, 0.46);
        kumbha.castShadow = true;
        gajaBalustrade.add(kumbha);
      });

      // Forehead jewelry band / Mukuta & central rosette medallion
      const foreheadJewel = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.06, 0.10), friezeMat);
      foreheadJewel.position.set(0, 1.28, 0.58);
      gajaBalustrade.add(foreheadJewel);

      const foreheadMedallion = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.04, 12), darkBronzeMat);
      foreheadMedallion.rotation.x = Math.PI / 2;
      foreheadMedallion.position.set(0, 1.24, 0.62);
      gajaBalustrade.add(foreheadMedallion);

      // Fanned curved ears
      [-0.26, 0.26].forEach((earX) => {
        const gajaEar = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.32, 0.22), kappeStoneMat);
        gajaEar.position.set(earX, 1.16, 0.38);
        gajaEar.rotation.y = earX > 0 ? 0.32 : -0.32;
        gajaEar.castShadow = true;
        gajaBalustrade.add(gajaEar);
      });

      // 7. Forward-Pointing Ivory Tusks
      [-0.12, 0.12].forEach((tx) => {
        const tusk = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.02, 0.26, 8), toranaMat);
        tusk.position.set(tx, 0.98, 0.60);
        tusk.rotation.x = 0.52;
        tusk.rotation.y = tx > 0 ? 0.12 : -0.12;
        tusk.castShadow = true;
        gajaBalustrade.add(tusk);
      });

      // 8. Articulated 4-Segment Curved Trunk Sweeping Down to Pedestal
      const trunk1 = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.085, 0.28, 10), kappeStoneMat);
      trunk1.position.set(0, 1.00, 0.58);
      trunk1.rotation.x = 0.42;
      trunk1.castShadow = true;
      gajaBalustrade.add(trunk1);

      const trunk2 = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.07, 0.26, 10), kappeStoneMat);
      trunk2.position.set(0, 0.80, 0.66);
      trunk2.rotation.x = 0.15;
      trunk2.castShadow = true;
      gajaBalustrade.add(trunk2);

      const trunk3 = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.055, 0.26, 10), kappeStoneMat);
      trunk3.position.set(0, 0.60, 0.69);
      trunk3.rotation.x = -0.15;
      trunk3.castShadow = true;
      gajaBalustrade.add(trunk3);

      // Curled trunk tip resting on pedestal
      const trunkTip = new THREE.Mesh(new THREE.TorusGeometry(0.065, 0.035, 8, 12, Math.PI * 1.3), kappeStoneMat);
      trunkTip.rotation.y = Math.PI / 2;
      trunkTip.position.set(0, 0.47, 0.67);
      trunkTip.castShadow = true;
      gajaBalustrade.add(trunkTip);

      // Sacred lotus bud offering held reverently in trunk curl (Image 1)
      const lotusBud = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 10), friezeMat);
      lotusBud.position.set(0, 0.48, 0.70);
      lotusBud.castShadow = true;
      gajaBalustrade.add(lotusBud);

      kappeGroup.add(gajaBalustrade);
    });

    // C. Stepped Multi-Bay Temple Wall Structure & Sanctum
    // 1. Rear & Core Mandapa / Garbhagriha Body (Y = 1.50 to Y = 4.30)
    const kappeCoreWall = new THREE.Mesh(new THREE.BoxGeometry(7.6, 2.85, 6.4), kappeStoneMat);
    kappeCoreWall.position.set(0, 2.92, -0.45);
    kappeCoreWall.castShadow = true;
    kappeCoreWall.receiveShadow = true;
    kappeGroup.add(kappeCoreWall);

    // West Sanctum Rear Projection (Garbhagriha) & North/South Side Projections
    const kappeWestSanctum = new THREE.Mesh(new THREE.BoxGeometry(5.6, 2.80, 1.4), kappeStoneMat);
    kappeWestSanctum.position.set(0, 2.90, -4.15);
    kappeWestSanctum.castShadow = true;
    kappeGroup.add(kappeWestSanctum);

    [-4.15, 4.15].forEach((sx) => {
      const sideBay = new THREE.Mesh(new THREE.BoxGeometry(1.1, 2.75, 4.2), kappeStoneMat);
      sideBay.position.set(sx, 2.88, -0.2);
      sideBay.castShadow = true;
      kappeGroup.add(sideBay);

      const sideJali = new THREE.Mesh(new THREE.BoxGeometry(0.12, 1.15, 3.2), kappeJaliMat);
      sideJali.position.set(sx + (sx > 0 ? 0.56 : -0.56), 3.65, -0.2);
      kappeGroup.add(sideJali);
    });

    // Helper: Add Adhisthana Mouldings + Kakshasana Dado + Jali Screen on Front Bays
    const addKappeFrontBay = (bx: number, bz: number, bw: number, bd: number, jaliH: number) => {
      const bayWall = new THREE.Mesh(new THREE.BoxGeometry(bw, 1.15, bd), kappeStoneMat);
      bayWall.position.set(bx, 2.08, bz);
      bayWall.castShadow = true;
      bayWall.receiveShadow = true;
      kappeGroup.add(bayWall);

      // 4 crisp horizontal Adhisthana shadow/cornice courses
      [1.62, 1.90, 2.18, 2.46].forEach((my) => {
        const moulding = new THREE.Mesh(
          new THREE.BoxGeometry(bw + 0.16, 0.10, bd + 0.16),
          my === 1.90 || my === 2.46 ? kappeEaveMat : kappeStoneMat
        );
        moulding.position.set(bx, my, bz);
        kappeGroup.add(moulding);
      });

      // Carved Kakshasana balustrade dado with miniature vertical ribs
      const dadoBand = new THREE.Mesh(new THREE.BoxGeometry(bw + 0.08, 0.42, bd + 0.08), friezeMat);
      dadoBand.position.set(bx, 2.86, bz);
      kappeGroup.add(dadoBand);

      const ribCount = Math.max(4, Math.floor(bw * 4));
      for (let r = 0; r < ribCount; r++) {
        const rx = bx - bw / 2 + 0.14 + (r * (bw - 0.28)) / Math.max(1, ribCount - 1);
        const rib = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.36, 0.08), kappeStoneMat);
        rib.position.set(rx, 2.86, bz + bd / 2 + 0.05);
        kappeGroup.add(rib);
      }

      // Pierced Diamond-Lattice Jali Window Screen
      const jaliScreen = new THREE.Mesh(new THREE.BoxGeometry(bw - 0.18, jaliH, 0.14), kappeJaliMat);
      jaliScreen.position.set(bx, 3.07 + jaliH / 2, bz + bd / 2 - 0.04);
      kappeGroup.add(jaliScreen);
    };

    // Middle Projecting Jali Bays (Left & Right of Entrance Portal)
    addKappeFrontBay(-2.38, 3.15, 1.85, 1.10, 1.28);
    addKappeFrontBay(2.38, 3.15, 1.85, 1.10, 1.28);

    // Outer Receding Wing Bays (Stepped back as shown in photo)
    addKappeFrontBay(-4.05, 2.15, 1.55, 1.40, 1.12);
    addKappeFrontBay(4.05, 2.15, 1.55, 1.40, 1.12);

    // Lathe-Turned Hoysala Pillars along Front Facade (Color Graded)
    const addKappePillar = (px: number, pz: number, hScale = 1.0) => {
      const pBase = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.30, 0.32), kappePlinthMat);
      pBase.position.set(px, 2.75, pz);
      kappeGroup.add(pBase);

      const pShaft = new THREE.Mesh(
        new THREE.CylinderGeometry(0.13, 0.15, 1.25 * hScale, 16),
        kappePillarMat
      );
      pShaft.position.set(px, 2.90 + 0.62 * hScale, pz);
      pShaft.castShadow = true;
      kappeGroup.add(pShaft);

      // Lathe-turned bell disc rings on columns (matching photo)
      const pDisc = new THREE.Mesh(
        new THREE.CylinderGeometry(0.20, 0.20, 0.08, 16),
        kappePillarMat
      );
      pDisc.position.set(px, 2.90 + 0.85 * hScale, pz);
      kappeGroup.add(pDisc);

      const pCap = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.22, 0.40), kappeEaveMat);
      pCap.position.set(px, 2.90 + 1.32 * hScale, pz);
      kappeGroup.add(pCap);
    };
    [-1.48, -3.26].forEach((px) => addKappePillar(px, 3.68, 1.0));
    [1.48, 3.26].forEach((px) => addKappePillar(px, 3.68, 1.0));
    [-3.45, -4.75, 3.45, 4.75].forEach((px) => addKappePillar(px, 2.82, 0.88));

    // D. Central Entrance Portal, Rosette Double Doors & Flanking Dvarapalas
    const portalBacking = new THREE.Mesh(new THREE.BoxGeometry(2.95, 2.90, 0.90), kappeStoneMat);
    portalBacking.position.set(0, 2.95, 3.05);
    kappeGroup.add(portalBacking);

    const doorFrameOuter = new THREE.Mesh(new THREE.BoxGeometry(1.64, 2.38, 0.24), friezeMat);
    doorFrameOuter.position.set(0, 2.70, 3.48);
    kappeGroup.add(doorFrameOuter);

    const doorPanel = new THREE.Mesh(new THREE.BoxGeometry(1.18, 2.10, 0.10), kappeDoorMat);
    doorPanel.position.set(0, 2.58, 3.58);
    kappeGroup.add(doorPanel);

    // Ornate carved lintel (Uttaranga) + top canopy bracket above doorway
    const doorLintel = new THREE.Mesh(new THREE.BoxGeometry(2.25, 0.36, 0.36), kappeStoneMat);
    doorLintel.position.set(0, 3.92, 3.56);
    doorLintel.castShadow = true;
    kappeGroup.add(doorLintel);

    const centralCanopy = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.22, 0.35), friezeMat);
    centralCanopy.position.set(0, 4.24, 3.72);
    kappeGroup.add(centralCanopy);

    // Sculpted Dvarapala Guardians flanking left and right of doorway
    [-1.06, 1.06].forEach((dx) => {
      const dPedestal = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.25, 0.34), kappeEaveMat);
      dPedestal.position.set(dx, 1.62, 3.56);
      kappeGroup.add(dPedestal);

      const dBody = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.18, 0.72, 12), kappePillarMat);
      dBody.position.set(dx, 2.10, 3.58);
      dBody.castShadow = true;
      kappeGroup.add(dBody);

      const dCrown = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.26, 8), kappeStoneMat);
      dCrown.position.set(dx, 2.56, 3.58);
      kappeGroup.add(dCrown);
    });

    // E. Authentic Flat Multi-Tiered Horizontal Cornice Roof (Kapota Eaves + Stepped Parapet)
    // Main Forward Projecting Overhanging Kapota Eave (NO conical spire, matching photo)
    const frontMainEave = new THREE.Mesh(new THREE.BoxGeometry(7.2, 0.22, 4.5), kappeEaveMat);
    frontMainEave.position.set(0, 4.46, 1.90);
    frontMainEave.castShadow = true;
    frontMainEave.receiveShadow = true;
    kappeGroup.add(frontMainEave);

    const frontEaveSkirt = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.12, 4.2), friezeMat);
    frontEaveSkirt.position.set(0, 4.32, 1.85);
    kappeGroup.add(frontEaveSkirt);

    // Upturned corner Nasika eave finials (visible at left & right eave tips in photo)
    [-3.55, 3.55].forEach((fx) => {
      const cornerTip = new THREE.Mesh(new THREE.ConeGeometry(0.10, 0.26, 6), kappeStoneMat);
      cornerTip.position.set(fx, 4.65, 4.10);
      kappeGroup.add(cornerTip);
    });

    // Stepped-back outer Wing & Sanctum Eaves
    const wingEave = new THREE.Mesh(new THREE.BoxGeometry(9.9, 0.20, 5.0), kappeEaveMat);
    wingEave.position.set(0, 4.24, 0.10);
    wingEave.castShadow = true;
    kappeGroup.add(wingEave);

    const rearEave = new THREE.Mesh(new THREE.BoxGeometry(7.8, 0.20, 4.6), kappeEaveMat);
    rearEave.position.set(0, 4.24, -2.55);
    rearEave.castShadow = true;
    kappeGroup.add(rearEave);

    // 3 Receding Horizontal Flat Parapet Roof Courses above the Eaves
    const roofTier1 = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.20, 4.05), kappeStoneMat);
    roofTier1.position.set(0, 4.66, 1.80);
    roofTier1.castShadow = true;
    kappeGroup.add(roofTier1);

    const roofTier2 = new THREE.Mesh(new THREE.BoxGeometry(5.9, 0.18, 3.70), friezeMat);
    roofTier2.position.set(0, 4.84, 1.75);
    roofTier2.castShadow = true;
    kappeGroup.add(roofTier2);

    const roofTier3 = new THREE.Mesh(new THREE.BoxGeometry(5.3, 0.16, 3.30), kappeStoneMat);
    roofTier3.position.set(0, 5.01, 1.70);
    roofTier3.castShadow = true;
    kappeGroup.add(roofTier3);

    // Matching stepped rear roof parapet over the sanctum & outer bays
    const rearParapet1 = new THREE.Mesh(new THREE.BoxGeometry(8.8, 0.18, 4.6), kappeStoneMat);
    rearParapet1.position.set(0, 4.43, -0.45);
    kappeGroup.add(rearParapet1);

    const rearParapet2 = new THREE.Mesh(new THREE.BoxGeometry(7.2, 0.18, 5.4), friezeMat);
    rearParapet2.position.set(0, 4.61, -1.35);
    kappeGroup.add(rearParapet2);

    const rearParapetCap = new THREE.Mesh(new THREE.BoxGeometry(6.2, 0.16, 4.6), kappeStoneMat);
    rearParapetCap.position.set(0, 4.78, -1.55);
    kappeGroup.add(rearParapetCap);

    // =========================================================================
    // 3. VIRA NARAYANA TEMPLE (#3)
    // 100% Architecturally accurate to Reference Images 1 & 2:
    // - Ekakuta Hoysala shrine with authentic low flat/stepped parapet roof (NO CONE TOWER)
    // - Elevated multi-tier stepped Adhisthana Jagati platform with open circumambulation walkway
    // - Wide 6-step East entrance flight flanked by twin massive stepped rectangular stone balustrades
    // - Warm reddish-brown double wooden paneled entrance door with molded stone jambs
    // - Two prominent lathe-turned bell-molded engaged columns flanking the entrance portal
    // - Sculpted deity panels (rathikas) and miniature shikhara reliefs across all facades
    // - Staggered Hoysala offset bays (projections and recesses) along walls
    // - Double-tier overhanging Kapota eaves and stepped ashlar parapet roof with rod finial
    // - Authentic: NO blue ASI signboard
    // =========================================================================
    const viraGroup = new THREE.Group();
    viraGroup.position.set(2, 0, -25.5);
    worldGroup.add(viraGroup);

    const viraPlinthMat = new THREE.MeshStandardMaterial({
      color: 0x6e675f, // Weathered dark grey ashlar granite for stepped Jagati & balustrades (Images 1 & 2)
      roughness: 0.88,
      metalness: 0.12,
    });
    const viraDoorMat = new THREE.MeshStandardMaterial({
      color: 0xffffff, // Full rendering of procedural 6-panel weathered peach-terracotta timber door (media_1794550779392_86769c8b.png)
      map: viraDoorTexture,
      roughness: 0.72,
      metalness: 0.10,
    });
    const viraPillarMat = new THREE.MeshStandardMaterial({
      color: 0x3a3530, // Lathe-turned dark soapstone engaged entrance columns & bell moldings (Images 1 & 2)
      roughness: 0.40,
      metalness: 0.32,
    });
    const viraRoofMat = new THREE.MeshStandardMaterial({
      color: 0x7d7367, // Weathered ashlar masonry for flat stepped parapet roof (Images 1 & 2)
      roughness: 0.90,
      metalness: 0.10,
    });

    // A. Multi-Tier Stepped Adhisthana Jagati Platform (Images 1 & 2)
    const viraJagatiLower = new THREE.Mesh(new THREE.BoxGeometry(8.6, 0.30, 8.2), friezeMat);
    viraJagatiLower.position.set(0, 0.20, -0.10);
    viraJagatiLower.castShadow = true;
    viraJagatiLower.receiveShadow = true;
    viraGroup.add(viraJagatiLower);

    const viraJagatiMid = new THREE.Mesh(new THREE.BoxGeometry(8.2, 0.30, 7.8), mainRoofEaveMat);
    viraJagatiMid.position.set(0, 0.50, -0.10);
    viraJagatiMid.castShadow = true;
    viraJagatiMid.receiveShadow = true;
    viraGroup.add(viraJagatiMid);

    const viraJagatiUpper = new THREE.Mesh(new THREE.BoxGeometry(8.4, 0.30, 8.0), viraPlinthMat);
    viraJagatiUpper.position.set(0, 0.80, -0.10);
    viraJagatiUpper.castShadow = true;
    viraJagatiUpper.receiveShadow = true;
    viraGroup.add(viraJagatiUpper);

    // B. Wide 6-Step East Entrance Flight & Twin Massive Stepped Balustrades (Images 1 & 2)
    for (let st = 0; st < 6; st++) {
      const sH = ((st + 1) / 6) * 0.90;
      const sZ = 5.50 - st * 0.27;
      const step = new THREE.Mesh(new THREE.BoxGeometry(2.4, sH, 0.30), viraPlinthMat);
      step.position.set(0, 0.05 + sH / 2, sZ);
      step.castShadow = true;
      step.receiveShadow = true;
      viraGroup.add(step);
    }

    // Twin Massive Stepped Rectangular Balustrades flanking the stairs (Image 1 & 2)
    [-1.55, 1.55].forEach((bx) => {
      const balBase = new THREE.Mesh(new THREE.BoxGeometry(0.70, 0.35, 1.70), viraPlinthMat);
      balBase.position.set(bx, 0.22, 4.65);
      balBase.castShadow = true;
      balBase.receiveShadow = true;
      viraGroup.add(balBase);

      const balMid = new THREE.Mesh(new THREE.BoxGeometry(0.64, 0.35, 1.60), mainRoofEaveMat);
      balMid.position.set(bx, 0.55, 4.65);
      balMid.castShadow = true;
      balMid.receiveShadow = true;
      viraGroup.add(balMid);

      const balUpper = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.30, 1.65), viraPlinthMat);
      balUpper.position.set(bx, 0.85, 4.65);
      balUpper.castShadow = true;
      balUpper.receiveShadow = true;
      viraGroup.add(balUpper);

      const balCap = new THREE.Mesh(new THREE.BoxGeometry(0.60, 0.22, 1.55), viraPlinthMat);
      balCap.position.set(bx, 1.10, 4.65);
      balCap.castShadow = true;
      viraGroup.add(balCap);
    });

    // C. Temple Body & Base Molded Frieze Courses
    const viraWallBase1 = new THREE.Mesh(new THREE.BoxGeometry(6.6, 0.16, 6.4), friezeMat);
    viraWallBase1.position.set(0, 1.03, -0.10);
    viraWallBase1.castShadow = true;
    viraGroup.add(viraWallBase1);

    const viraWallBase2 = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.14, 6.3), mainRoofEaveMat);
    viraWallBase2.position.set(0, 1.18, -0.10);
    viraGroup.add(viraWallBase2);

    const viraWallBase3 = new THREE.Mesh(new THREE.BoxGeometry(6.65, 0.16, 6.45), friezeMat);
    viraWallBase3.position.set(0, 1.33, -0.10);
    viraWallBase3.castShadow = true;
    viraGroup.add(viraWallBase3);

    const viraCore = new THREE.Mesh(new THREE.BoxGeometry(6.4, 2.30, 6.2), mainTempleSoapstoneMat);
    viraCore.position.set(0, 2.50, -0.10);
    viraCore.castShadow = true;
    viraCore.receiveShadow = true;
    viraGroup.add(viraCore);

    // D. Front Facade & Recessed Entrance Porch (100% matched to media_1794550779392_86769c8b.png)
    // Sheltered Deep Recessed Entrance Porch (Z = 2.40 to 3.05)
    // Recessed side jamb walls flanking doorway
    [-0.85, 0.85].forEach((jx) => {
      const porchJamb = new THREE.Mesh(new THREE.BoxGeometry(0.18, 2.35, 0.65), mainTempleSoapstoneMat);
      porchJamb.position.set(jx, 2.10, 2.73);
      porchJamb.castShadow = true;
      viraGroup.add(porchJamb);
    });

    // Recessed stone threshold landing step (udumbara)
    const viraThreshold = new THREE.Mesh(new THREE.BoxGeometry(1.50, 0.20, 0.55), viraPlinthMat);
    viraThreshold.position.set(0, 0.95, 2.68);
    viraThreshold.receiveShadow = true;
    viraGroup.add(viraThreshold);

    // Inner stone doorframe inside recess
    const viraDoorFrame = new THREE.Mesh(new THREE.BoxGeometry(1.40, 2.22, 0.14), mainRoofEaveMat);
    viraDoorFrame.position.set(0, 2.06, 2.44);
    viraDoorFrame.castShadow = true;
    viraGroup.add(viraDoorFrame);

    // 6-Panel Weathered Dusty Terracotta Double Wooden Door (media_1794550779392_86769c8b.png)
    const viraDoorPanels = new THREE.Mesh(new THREE.BoxGeometry(1.18, 2.04, 0.05), viraDoorMat);
    viraDoorPanels.position.set(0, 1.97, 2.43);
    viraDoorPanels.castShadow = true;
    viraGroup.add(viraDoorPanels);

    // Stone lintel beam over recessed doorway
    const viraLintelBeam = new THREE.Mesh(new THREE.BoxGeometry(1.55, 0.22, 0.24), mainTempleSoapstoneMat);
    viraLintelBeam.position.set(0, 3.12, 2.45);
    viraLintelBeam.castShadow = true;
    viraGroup.add(viraLintelBeam);

    // Horizontal white tube/beam band visible directly above doorway in user photo
    const viraLintelTube = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.08, 0.10), toranaMat);
    viraLintelTube.position.set(0, 3.25, 2.48);
    viraGroup.add(viraLintelTube);

    // Recessed porch ceiling slab
    const viraPorchCeiling = new THREE.Mesh(new THREE.BoxGeometry(1.65, 0.15, 0.65), mainRoofEaveMat);
    viraPorchCeiling.position.set(0, 3.32, 2.72);
    viraGroup.add(viraPorchCeiling);

    // Two Prominent Lathe-Turned Engaged Columns Flanking the Doorway (media_1794550779392_86769c8b.png)
    const viraColBaseGeo = new THREE.BoxGeometry(0.42, 0.55, 0.42);
    const viraColOctRingGeo = new THREE.CylinderGeometry(0.20, 0.21, 0.14, 8);
    const viraColDrumGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.50, 16);
    const viraColDiscGeo = new THREE.CylinderGeometry(0.26, 0.26, 0.12, 16);
    const viraColNeckGeo = new THREE.CylinderGeometry(0.16, 0.18, 0.38, 16);
    const viraColFlaredGeo = new THREE.CylinderGeometry(0.24, 0.16, 0.22, 16);
    const viraColCapGeo = new THREE.BoxGeometry(0.50, 0.18, 0.50);

    [-1.02, 1.02].forEach((cx) => {
      const colG = new THREE.Group();
      colG.position.set(cx, 0.95, 3.16);

      const cBase = new THREE.Mesh(viraColBaseGeo, viraPlinthMat);
      cBase.position.y = 0.27;
      cBase.castShadow = true;
      colG.add(cBase);

      const cRing = new THREE.Mesh(viraColOctRingGeo, viraPlinthMat);
      cRing.position.y = 0.61;
      colG.add(cRing);

      const cDrum = new THREE.Mesh(viraColDrumGeo, viraPillarMat);
      cDrum.position.y = 0.92;
      cDrum.castShadow = true;
      colG.add(cDrum);

      const cDisc = new THREE.Mesh(viraColDiscGeo, viraPillarMat);
      cDisc.position.y = 1.22;
      colG.add(cDisc);

      const cNeck = new THREE.Mesh(viraColNeckGeo, viraPlinthMat);
      cNeck.position.y = 1.47;
      colG.add(cNeck);

      const cFlared = new THREE.Mesh(viraColFlaredGeo, viraPillarMat);
      cFlared.position.y = 1.77;
      colG.add(cFlared);

      const cCap = new THREE.Mesh(viraColCapGeo, mainTempleSoapstoneMat);
      cCap.position.y = 1.97;
      cCap.castShadow = true;
      colG.add(cCap);

      viraGroup.add(colG);
    });

    // Projecting stone canopy architrave beam & Kapota eave over the two entrance columns
    const viraCanopyBeam = new THREE.Mesh(new THREE.BoxGeometry(2.35, 0.20, 0.45), mainTempleSoapstoneMat);
    viraCanopyBeam.position.set(0, 3.12, 3.16);
    viraCanopyBeam.castShadow = true;
    viraGroup.add(viraCanopyBeam);

    const viraCanopyEave = new THREE.Mesh(new THREE.BoxGeometry(2.55, 0.20, 0.55), mainRoofEaveMat);
    viraCanopyEave.position.set(0, 3.32, 3.20);
    viraCanopyEave.castShadow = true;
    viraGroup.add(viraCanopyEave);

    // Front Facade Sculpted Walls (Flanking Left & Right of Entrance)
    [-1, 1].forEach((side) => {
      // 1. Molded Adhisthana base friezes under deity panels
      const bFrieze = new THREE.Mesh(new THREE.BoxGeometry(1.70, 0.22, 0.25), friezeMat);
      bFrieze.position.set(side * 2.18, 1.05, 3.02);
      bFrieze.castShadow = true;
      viraGroup.add(bFrieze);

      const bKumuda = new THREE.Mesh(new THREE.BoxGeometry(1.72, 0.15, 0.26), mainTempleSoapstoneMat);
      bKumuda.position.set(side * 2.18, 1.22, 3.03);
      bKumuda.castShadow = true;
      viraGroup.add(bKumuda);

      const bKaksha = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.20, 0.28), mainRoofEaveMat);
      bKaksha.position.set(side * 2.18, 1.38, 3.04);
      bKaksha.castShadow = true;
      viraGroup.add(bKaksha);

      // 2. Inner deity niche panel (Rathika) with standing carved deity figure & halo
      const innerFrame = new THREE.Mesh(new THREE.BoxGeometry(0.48, 1.10, 0.22), mainTempleSoapstoneMat);
      innerFrame.position.set(side * 1.70, 2.05, 3.04);
      innerFrame.castShadow = true;
      viraGroup.add(innerFrame);

      const innerDeity = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.90, 0.26), shrineStoneMat);
      innerDeity.position.set(side * 1.70, 2.05, 3.06);
      innerDeity.castShadow = true;
      viraGroup.add(innerDeity);

      const innerHalo = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.10, 12), mainTempleSoapstoneMat);
      innerHalo.rotation.x = Math.PI / 2;
      innerHalo.position.set(side * 1.70, 2.52, 3.06);
      viraGroup.add(innerHalo);

      const innerTowerRelief = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.55, 0.25), mainTempleSoapstoneMat);
      innerTowerRelief.position.set(side * 1.70, 2.85, 3.04);
      innerTowerRelief.castShadow = true;
      viraGroup.add(innerTowerRelief);

      // 3. Center dividing fluted pilaster
      const divPilaster = new THREE.Mesh(new THREE.BoxGeometry(0.22, 2.15, 0.26), mainTempleSoapstoneMat);
      divPilaster.position.set(side * 2.18, 2.38, 3.06);
      divPilaster.castShadow = true;
      viraGroup.add(divPilaster);

      const divPilasterCap = new THREE.Mesh(new THREE.BoxGeometry(0.30, 0.18, 0.28), mainRoofEaveMat);
      divPilasterCap.position.set(side * 2.18, 3.12, 3.06);
      viraGroup.add(divPilasterCap);

      // 4. Outer deity niche panel with standing carved deity figure & halo
      const outerFrame = new THREE.Mesh(new THREE.BoxGeometry(0.48, 1.10, 0.22), mainTempleSoapstoneMat);
      outerFrame.position.set(side * 2.65, 2.05, 3.04);
      outerFrame.castShadow = true;
      viraGroup.add(outerFrame);

      const outerDeity = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.90, 0.26), shrineStoneMat);
      outerDeity.position.set(side * 2.65, 2.05, 3.06);
      outerDeity.castShadow = true;
      viraGroup.add(outerDeity);

      const outerHalo = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.10, 12), mainTempleSoapstoneMat);
      outerHalo.rotation.x = Math.PI / 2;
      outerHalo.position.set(side * 2.65, 2.52, 3.06);
      viraGroup.add(outerHalo);

      const outerTowerRelief = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.55, 0.25), mainTempleSoapstoneMat);
      outerTowerRelief.position.set(side * 2.65, 2.85, 3.04);
      outerTowerRelief.castShadow = true;
      viraGroup.add(outerTowerRelief);

      // 5. Chamfered 45° Stellate Corner Bay (Connecting front to side walls: media_1794550779392_86769c8b.png)
      const cornerWall = new THREE.Mesh(new THREE.BoxGeometry(0.55, 2.30, 0.24), mainTempleSoapstoneMat);
      cornerWall.position.set(side * 3.12, 2.40, 2.78);
      cornerWall.rotation.y = -side * (Math.PI / 4);
      cornerWall.castShadow = true;
      viraGroup.add(cornerWall);

      const cornerNiche = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.85, 0.18), shrineStoneMat);
      cornerNiche.position.set(side * 3.12, 2.20, 2.78);
      cornerNiche.rotation.y = -side * (Math.PI / 4);
      cornerNiche.castShadow = true;
      viraGroup.add(cornerNiche);
    });

    // E. Side and Rear Walls (South, North, West Facades: Hoysala Offset Bays & Niches)
    [-3.22, 3.22].forEach((sx) => {
      // Central projecting Bhadra bay
      const bhadra = new THREE.Mesh(new THREE.BoxGeometry(0.28, 2.20, 2.40), mainTempleSoapstoneMat);
      bhadra.position.set(sx, 2.45, -0.10);
      bhadra.castShadow = true;
      viraGroup.add(bhadra);

      const sideNiche = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.88, 0.80), shrineStoneMat);
      sideNiche.position.set(sx, 2.25, -0.10);
      viraGroup.add(sideNiche);

      [-1.8, 1.8].forEach((pz) => {
        const sidePilaster = new THREE.Mesh(new THREE.BoxGeometry(0.24, 2.15, 0.26), mainTempleSoapstoneMat);
        sidePilaster.position.set(sx, 2.45, -0.10 + pz);
        sidePilaster.castShadow = true;
        viraGroup.add(sidePilaster);
      });
    });

    // Rear West wall projecting central bay
    const rearBhadra = new THREE.Mesh(new THREE.BoxGeometry(2.40, 2.20, 0.28), mainTempleSoapstoneMat);
    rearBhadra.position.set(0, 2.45, -3.22);
    rearBhadra.castShadow = true;
    viraGroup.add(rearBhadra);

    const rearNiche = new THREE.Mesh(new THREE.BoxGeometry(0.80, 0.88, 0.18), shrineStoneMat);
    rearNiche.position.set(0, 2.25, -3.22);
    viraGroup.add(rearNiche);

    [-1.8, 1.8].forEach((px) => {
      const rearPilaster = new THREE.Mesh(new THREE.BoxGeometry(0.26, 2.15, 0.24), mainTempleSoapstoneMat);
      rearPilaster.position.set(px, 2.45, -3.22);
      rearPilaster.castShadow = true;
      viraGroup.add(rearPilaster);
    });

    // F. Double-Tier Overhanging Kapota Eaves & Stepped Flat Parapet Roof (NO CONE TOWER! Images 1 & 2)
    const viraLowerEave = new THREE.Mesh(new THREE.BoxGeometry(6.9, 0.22, 6.7), mainRoofEaveMat);
    viraLowerEave.position.set(0, 3.76, -0.10);
    viraLowerEave.castShadow = true;
    viraGroup.add(viraLowerEave);

    const viraRoofNeck = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.18, 6.3), viraRoofMat);
    viraRoofNeck.position.set(0, 3.96, -0.10);
    viraRoofNeck.castShadow = true;
    viraGroup.add(viraRoofNeck);

    const viraUpperEave = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.22, 6.6), mainRoofEaveMat);
    viraUpperEave.position.set(0, 4.16, -0.10);
    viraUpperEave.castShadow = true;
    viraGroup.add(viraUpperEave);

    // Stepped flat ashlar parapet roof (Images 1 & 2)
    const viraRoofTier1 = new THREE.Mesh(new THREE.BoxGeometry(6.4, 0.28, 6.2), viraRoofMat);
    viraRoofTier1.position.set(0, 4.41, -0.10);
    viraRoofTier1.castShadow = true;
    viraGroup.add(viraRoofTier1);

    const viraRoofTier2 = new THREE.Mesh(new THREE.BoxGeometry(5.8, 0.32, 5.6), viraRoofMat);
    viraRoofTier2.position.set(0, 4.71, -0.10);
    viraRoofTier2.castShadow = true;
    viraGroup.add(viraRoofTier2);

    const viraRoofTop = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.26, 5.0), viraRoofMat);
    viraRoofTop.position.set(0, 5.00, -0.10);
    viraRoofTop.castShadow = true;
    viraGroup.add(viraRoofTop);

    // Weathered central stone finial base block (Image 1)
    const viraFinialBase = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.24, 0.85), viraPlinthMat);
    viraFinialBase.position.set(0, 5.25, -0.10);
    viraFinialBase.castShadow = true;
    viraGroup.add(viraFinialBase);

    // Slender metal rod / finial spike visible at top of roof (Images 1 & 2)
    const viraRoofSpike = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.03, 0.65, 8), darkBronzeMat);
    viraRoofSpike.position.set(0, 5.68, -0.10);
    viraRoofSpike.castShadow = true;
    viraGroup.add(viraRoofSpike);

    // =========================================================================
    // 4. SAUMYANAYAKI TEMPLE (#4)
    // 100% Architecturally accurate to Reference Images 1 & 2:
    // - Multi-tiered stepped Dravida-Hoysala Vimana tower with sculpted talas,
    //   vaulted domical crown, and gleaming golden Kalasha finial (Image 1)
    // - Deep ashlar sanctum walls with pilaster bays, niches & enclosed inner portal
    // - Grand open hypostyle Mukhamandapa on elevated stepped Adhisthana plinth
    //   with devotee sitting ledges and wide central East staircase with carved
    //   elephant / yali terminal balustrades (Image 2)
    // - Authentic Hoysala lathe-turned circular bell columns & bracket capitals (podigai)
    // - Heavy architrave beams with distinctive protruding stone water spout gargoyles (pranalas)
    // - Signature curved barrel-vaulted cambered plastered roof with Kalasha finial spike (Images 1 & 2)
    // =========================================================================
    const saumyaGroup = new THREE.Group();
    saumyaGroup.position.set(-18, 0, -22);
    worldGroup.add(saumyaGroup);

    const saumyaPlinthMat = new THREE.MeshStandardMaterial({
      color: 0x767069, // Weathered greyish-brown granite plinth, steps & pillar bases (Images 1 & 2)
      roughness: 0.86,
      metalness: 0.12,
    });
    const saumyaPillarShaftMat = new THREE.MeshStandardMaterial({
      color: 0x36322e, // Deep lathe-turned soapstone/schist column drums & bell moldings (Images 1 & 2)
      roughness: 0.38,
      metalness: 0.35,
    });
    const saumyaBeamMat = new THREE.MeshStandardMaterial({
      color: 0x585048, // Heavy ashlar stone lintels & architrave beams
      roughness: 0.85,
      metalness: 0.14,
    });
    const saumyaVaultedRoofMat = new THREE.MeshStandardMaterial({
      color: 0xc8bda8, // Signature weathered buff plastered barrel-vaulted cambered roof (Images 1 & 2)
      roughness: 0.92,
      metalness: 0.04,
    });
    const saumyaGargoyleMat = new THREE.MeshStandardMaterial({
      color: 0x5a524a, // Projecting stone makara/elephant water spout gargoyles (Image 1)
      roughness: 0.85,
      metalness: 0.15,
    });

    // A. Multi-Course Stepped Adhisthana Plinth (spanning Z = -5.1 to +6.4)
    // Mandapa section plinth (Z = -0.5 to +6.4)
    const mandapaPlinthLower = new THREE.Mesh(new THREE.BoxGeometry(8.4, 0.30, 7.1), friezeMat);
    mandapaPlinthLower.position.set(0, 0.20, 2.95);
    mandapaPlinthLower.castShadow = true;
    mandapaPlinthLower.receiveShadow = true;
    saumyaGroup.add(mandapaPlinthLower);

    const mandapaPlinthUpper = new THREE.Mesh(new THREE.BoxGeometry(8.1, 0.55, 6.8), saumyaPlinthMat);
    mandapaPlinthUpper.position.set(0, 0.575, 2.95);
    mandapaPlinthUpper.castShadow = true;
    mandapaPlinthUpper.receiveShadow = true;
    saumyaGroup.add(mandapaPlinthUpper);

    // Side sitting ledges / benches (as seen in Image 1 where devotees sit along the plinth edge)
    [-4.25, 4.25].forEach((lx) => {
      const plinthLedge = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.35, 7.0), saumyaPlinthMat);
      plinthLedge.position.set(lx, 0.22, 2.95);
      plinthLedge.receiveShadow = true;
      saumyaGroup.add(plinthLedge);
    });

    // B. Front East Entrance Staircase & Carved Guardian Balustrades (Image 2)
    for (let st = 0; st < 5; st++) {
      const sH = ((st + 1) / 5) * 0.80;
      const sZ = 7.60 - st * 0.28;
      const step = new THREE.Mesh(new THREE.BoxGeometry(2.8, sH, 0.32), saumyaPlinthMat);
      step.position.set(0, 0.05 + sH / 2, sZ);
      step.castShadow = true;
      step.receiveShadow = true;
      saumyaGroup.add(step);
    }

    [-1.55, 1.55].forEach((bx) => {
      const bSlope = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.42, 1.45), saumyaPlinthMat);
      bSlope.position.set(bx, 0.52, 7.00);
      bSlope.rotation.x = 0.45;
      bSlope.castShadow = true;
      saumyaGroup.add(bSlope);

      const bTerminal = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.54, 0.42), saumyaPlinthMat);
      bTerminal.position.set(bx, 0.32, 7.65);
      bTerminal.castShadow = true;
      saumyaGroup.add(bTerminal);

      const bScroll = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.34, 12), saumyaPlinthMat);
      bScroll.rotation.z = Math.PI / 2;
      bScroll.position.set(bx, 0.32, 7.82);
      bScroll.castShadow = true;
      saumyaGroup.add(bScroll);
    });

    // C. Open Pillared Mukhamandapa (24 Ornate Hoysala Columns: Images 1 & 2)
    const saumyaColBaseGeo = new THREE.BoxGeometry(0.44, 0.62, 0.44);
    const saumyaColOctRingGeo = new THREE.CylinderGeometry(0.20, 0.22, 0.14, 8);
    const saumyaColDrumGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.52, 16);
    const saumyaColBellDiscGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.12, 16);
    const saumyaColNeckGeo = new THREE.CylinderGeometry(0.15, 0.18, 0.40, 16);
    const saumyaColPhalakaGeo = new THREE.CylinderGeometry(0.25, 0.15, 0.22, 16);
    const saumyaColCapGeo = new THREE.BoxGeometry(0.56, 0.18, 0.56);
    const saumyaColBracketArmGeo = new THREE.BoxGeometry(0.82, 0.12, 0.22);
    const saumyaColBracketArmZGeo = new THREE.BoxGeometry(0.22, 0.12, 0.82);

    const addSaumyaPillar = (px: number, pz: number) => {
      const pCol = new THREE.Group();
      pCol.position.set(px, 0.85, pz);

      const base = new THREE.Mesh(saumyaColBaseGeo, saumyaPlinthMat);
      base.position.y = 0.31;
      base.castShadow = true;
      pCol.add(base);

      const octRing = new THREE.Mesh(saumyaColOctRingGeo, saumyaPlinthMat);
      octRing.position.y = 0.69;
      pCol.add(octRing);

      const drum = new THREE.Mesh(saumyaColDrumGeo, saumyaPillarShaftMat);
      drum.position.y = 1.02;
      drum.castShadow = true;
      pCol.add(drum);

      const bellDisc = new THREE.Mesh(saumyaColBellDiscGeo, saumyaPillarShaftMat);
      bellDisc.position.y = 1.34;
      pCol.add(bellDisc);

      const neck = new THREE.Mesh(saumyaColNeckGeo, saumyaPlinthMat);
      neck.position.y = 1.60;
      pCol.add(neck);

      const phalaka = new THREE.Mesh(saumyaColPhalakaGeo, saumyaPillarShaftMat);
      phalaka.position.y = 1.91;
      pCol.add(phalaka);

      const abacus = new THREE.Mesh(saumyaColCapGeo, saumyaBeamMat);
      abacus.position.y = 2.11;
      abacus.castShadow = true;
      pCol.add(abacus);

      // 4-way cross bracket arms (podigai)
      const brX = new THREE.Mesh(saumyaColBracketArmGeo, saumyaBeamMat);
      brX.position.y = 2.22;
      brX.castShadow = true;
      pCol.add(brX);

      const brZ = new THREE.Mesh(saumyaColBracketArmZGeo, saumyaBeamMat);
      brZ.position.y = 2.22;
      brZ.castShadow = true;
      pCol.add(brZ);

      saumyaGroup.add(pCol);
    };

    // Front colonnade (Z = 5.8) - 6 columns across front facade (Image 2)
    [-3.5, -2.1, -0.7, 0.7, 2.1, 3.5].forEach((px) => addSaumyaPillar(px, 5.8));

    // Side outer colonnades along Z (Image 1)
    [4.3, 2.8, 1.3, -0.2].forEach((pz) => {
      addSaumyaPillar(-3.5, pz);
      addSaumyaPillar(3.5, pz);
    });

    // Interior hypostyle columns supporting ceiling and aisle
    [4.3, 2.8, 1.3, -0.2].forEach((pz) => {
      addSaumyaPillar(-2.1, pz);
      addSaumyaPillar(2.1, pz);
    });

    // Sanctum entrance portal flanking columns at Z = -0.2
    [-0.7, 0.7].forEach((px) => addSaumyaPillar(px, -0.2));

    // D. Architrave Lintels (Uttira) & Ceiling Beams
    [-3.5, 3.5].forEach((lx) => {
      const beamL = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.26, 6.4), saumyaBeamMat);
      beamL.position.set(lx, 3.30, 2.80);
      beamL.castShadow = true;
      saumyaGroup.add(beamL);
    });
    [-2.1, 2.1].forEach((lx) => {
      const beamIn = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.24, 6.2), saumyaBeamMat);
      beamIn.position.set(lx, 3.30, 2.80);
      beamIn.castShadow = true;
      saumyaGroup.add(beamIn);
    });
    [5.8, 4.3, 2.8, 1.3, -0.2].forEach((pz) => {
      const beamT = new THREE.Mesh(new THREE.BoxGeometry(7.4, 0.24, 0.34), saumyaBeamMat);
      beamT.position.set(0, 3.30, pz);
      beamT.castShadow = true;
      saumyaGroup.add(beamT);
    });

    // Protruding Stone Water Spouts / Makara Gargoyles (Images 1 & 2)
    [5.8, 4.3, 2.8, 1.3, -0.2].forEach((pz) => {
      [1, -1].forEach((side) => {
        const sx = side * 3.5;
        const spout = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.15, 0.18), saumyaGargoyleMat);
        spout.position.set(sx + side * 0.28, 3.34, pz);
        spout.castShadow = true;
        saumyaGroup.add(spout);

        const strut = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.12, 0.14), saumyaGargoyleMat);
        strut.position.set(sx + side * 0.14, 3.22, pz);
        strut.rotation.z = side * 0.40;
        strut.castShadow = true;
        saumyaGroup.add(strut);
      });
    });

    // E. Overhanging Kapota Eave & Signature Vaulted Cambered Roof (Images 1 & 2)
    const saumyaMandapaEave = new THREE.Mesh(new THREE.BoxGeometry(8.6, 0.22, 7.2), mainRoofEaveMat);
    saumyaMandapaEave.position.set(0, 3.54, 2.80);
    saumyaMandapaEave.castShadow = true;
    saumyaGroup.add(saumyaMandapaEave);

    // Arched barrel-vaulted roof shape (smooth arched camber across X extruded along Z)
    const camberShape = new THREE.Shape();
    camberShape.moveTo(-4.1, 0);
    camberShape.quadraticCurveTo(-2.0, 0.62, 0, 0.68);
    camberShape.quadraticCurveTo(2.0, 0.62, 4.1, 0);
    camberShape.lineTo(4.1, -0.06);
    camberShape.lineTo(-4.1, -0.06);
    camberShape.closePath();

    const camberGeo = new THREE.ExtrudeGeometry(camberShape, {
      depth: 6.8,
      bevelEnabled: true,
      bevelSegments: 3,
      steps: 1,
      bevelSize: 0.12,
      bevelThickness: 0.12,
    });
    const saumyaVaultedRoof = new THREE.Mesh(camberGeo, saumyaVaultedRoofMat);
    saumyaVaultedRoof.position.set(0, 3.65, -0.4);
    saumyaVaultedRoof.castShadow = true;
    saumyaVaultedRoof.receiveShadow = true;
    saumyaGroup.add(saumyaVaultedRoof);

    // Slender Roof Finial Rod (clearly visible in Image 2)
    const roofFinial = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.85, 8), darkBronzeMat);
    roofFinial.position.set(0, 4.80, 5.2);
    roofFinial.castShadow = true;
    saumyaGroup.add(roofFinial);

    // F. Rear Sanctum (Garbhagriha) Ashlar Walls & Deity Relinquary Niches (Z = -5.1 to -0.5)
    const saumyaSanctumBase = new THREE.Mesh(new THREE.BoxGeometry(6.6, 0.80, 4.6), saumyaPlinthMat);
    saumyaSanctumBase.position.set(0, 0.45, -2.8);
    saumyaSanctumBase.receiveShadow = true;
    saumyaGroup.add(saumyaSanctumBase);

    const saumyaSanctumCore = new THREE.Mesh(new THREE.BoxGeometry(6.2, 2.60, 4.4), friezeMat);
    saumyaSanctumCore.position.set(0, 2.15, -2.8);
    saumyaSanctumCore.castShadow = true;
    saumyaSanctumCore.receiveShadow = true;
    saumyaGroup.add(saumyaSanctumCore);

    // Wall Pilasters & Niches on South (-X), North (+X), and West (-Z)
    [-3.16, 3.16].forEach((sx) => {
      [-1.5, -2.8, -4.1].forEach((sz) => {
        const pilaster = new THREE.Mesh(new THREE.BoxGeometry(0.24, 2.45, 0.28), mainTempleSoapstoneMat);
        pilaster.position.set(sx, 2.15, sz);
        pilaster.castShadow = true;
        saumyaGroup.add(pilaster);
      });
      const niche = new THREE.Mesh(new THREE.BoxGeometry(0.20, 1.20, 0.80), shrineNicheMat);
      niche.position.set(sx, 2.10, -2.8);
      saumyaGroup.add(niche);
    });

    [-1.6, 0, 1.6].forEach((wx) => {
      const pilasterW = new THREE.Mesh(new THREE.BoxGeometry(0.28, 2.45, 0.24), mainTempleSoapstoneMat);
      pilasterW.position.set(wx, 2.15, -5.04);
      pilasterW.castShadow = true;
      saumyaGroup.add(pilasterW);
    });

    // Sanctum Entrance Portal facing into the mandapa (at Z = -0.58)
    const saumyaDoorwayFrame = new THREE.Mesh(new THREE.BoxGeometry(1.65, 2.15, 0.24), mainTempleSoapstoneMat);
    saumyaDoorwayFrame.position.set(0, 1.93, -0.58);
    saumyaDoorwayFrame.castShadow = true;
    saumyaGroup.add(saumyaDoorwayFrame);

    const saumyaDoorwayDarkNiche = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.75, 0.16), shrineNicheMat);
    saumyaDoorwayDarkNiche.position.set(0, 1.73, -0.54);
    saumyaGroup.add(saumyaDoorwayDarkNiche);

    // Sanctum Kapota Eave
    const saumyaSanctumEave = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.22, 5.0), mainRoofEaveMat);
    saumyaSanctumEave.position.set(0, 3.54, -2.8);
    saumyaSanctumEave.castShadow = true;
    saumyaGroup.add(saumyaSanctumEave);

    // G. Multi-Tiered Dravida-Hoysala Vimana Shikhara & Golden Kalasha (Image 1 left side)
    const saumyaVimanaGroup = new THREE.Group();
    saumyaVimanaGroup.position.set(0, 3.65, -2.8);
    saumyaGroup.add(saumyaVimanaGroup);

    // Tala 1 (Storey 1)
    const saumyaTala1Core = new THREE.Mesh(new THREE.BoxGeometry(4.8, 0.82, 4.0), shrineStoneMat);
    saumyaTala1Core.position.y = 0.41;
    saumyaTala1Core.castShadow = true;
    saumyaVimanaGroup.add(saumyaTala1Core);

    const kuta1Offsets: [number, number][] = [
      [-2.15, -1.75], [2.15, -1.75], [-2.15, 1.75], [2.15, 1.75],
      [0, -1.85], [0, 1.85], [-2.25, 0], [2.25, 0],
    ];
    kuta1Offsets.forEach(([kx, kz]) => {
      const kuta = new THREE.Mesh(new THREE.BoxGeometry(0.70, 0.72, 0.70), mainTempleSoapstoneMat);
      kuta.position.set(kx, 0.41, kz);
      kuta.castShadow = true;
      saumyaVimanaGroup.add(kuta);
    });

    const tala1Cornice = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.16, 4.2), mainRoofEaveMat);
    tala1Cornice.position.y = 0.90;
    tala1Cornice.castShadow = true;
    saumyaVimanaGroup.add(tala1Cornice);

    // Tala 2 (Storey 2)
    const saumyaTala2Core = new THREE.Mesh(new THREE.BoxGeometry(3.7, 0.75, 3.2), shrineStoneMat);
    saumyaTala2Core.position.y = 1.35;
    saumyaTala2Core.castShadow = true;
    saumyaVimanaGroup.add(saumyaTala2Core);

    const kuta2Offsets: [number, number][] = [
      [-1.65, -1.35], [1.65, -1.35], [-1.65, 1.35], [1.65, 1.35],
      [0, -1.45], [0, 1.45], [-1.75, 0], [1.75, 0],
    ];
    kuta2Offsets.forEach(([kx, kz]) => {
      const kuta = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.64, 0.58), mainTempleSoapstoneMat);
      kuta.position.set(kx, 1.35, kz);
      kuta.castShadow = true;
      saumyaVimanaGroup.add(kuta);
    });

    const tala2Cornice = new THREE.Mesh(new THREE.BoxGeometry(3.9, 0.15, 3.4), mainRoofEaveMat);
    tala2Cornice.position.y = 1.80;
    tala2Cornice.castShadow = true;
    saumyaVimanaGroup.add(tala2Cornice);

    // Tala 3 (Storey 3)
    const saumyaTala3Core = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.65, 2.5), shrineStoneMat);
    saumyaTala3Core.position.y = 2.20;
    saumyaTala3Core.castShadow = true;
    saumyaVimanaGroup.add(saumyaTala3Core);

    const tala3Cornice = new THREE.Mesh(new THREE.BoxGeometry(2.95, 0.14, 2.65), mainRoofEaveMat);
    tala3Cornice.position.y = 2.58;
    tala3Cornice.castShadow = true;
    saumyaVimanaGroup.add(tala3Cornice);

    // Griva (Neck)
    const saumyaGriva = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.22, 0.38, 16), saumyaPlinthMat);
    saumyaGriva.position.y = 2.84;
    saumyaVimanaGroup.add(saumyaGriva);

    // Shikhara Vaulted Dome Crown (Image 1)
    const saumyaShikharaDome = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 1.42, 0.78, 16), shrineStoneMat);
    saumyaShikharaDome.position.y = 3.32;
    saumyaShikharaDome.castShadow = true;
    saumyaVimanaGroup.add(saumyaShikharaDome);

    // 4 Kudu / Gavaksha horseshoe arched gables along the 4 directions
    [[0, -1.25], [0, 1.25], [-1.25, 0], [1.25, 0]].forEach(([gx, gz]) => {
      const kudu = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.52, 0.36), mainTempleSoapstoneMat);
      kudu.position.set(gx, 3.32, gz);
      kudu.castShadow = true;
      saumyaVimanaGroup.add(kudu);
    });

    // Golden Kalasha & Stupi Finial
    const saumyaKalashaBase = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.42, 0.15, 16), goldKalashaMat);
    saumyaKalashaBase.position.y = 3.78;
    saumyaVimanaGroup.add(saumyaKalashaBase);

    const saumyaKalashaPot = new THREE.Mesh(new THREE.SphereGeometry(0.28, 16, 16), goldKalashaMat);
    saumyaKalashaPot.position.y = 3.98;
    saumyaVimanaGroup.add(saumyaKalashaPot);

    const saumyaKalashaNeck = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.20, 0.18, 16), goldKalashaMat);
    saumyaKalashaNeck.position.y = 4.18;
    saumyaVimanaGroup.add(saumyaKalashaNeck);

    const saumyaStupiNeedle = new THREE.Mesh(new THREE.ConeGeometry(0.10, 0.42, 16), goldKalashaMat);
    saumyaStupiNeedle.position.y = 4.46;
    saumyaVimanaGroup.add(saumyaStupiNeedle);

    // =========================================================================
    // 5. RANGANAYAKI / ANDAL TEMPLE (#5)
    // 100% Architecturally accurate to Images 2–4 (no blue ASI signboard):
    // 4-course stepped Adhisthana plinth, curved S-scroll staircase balustrades,
    // 12-pillar open Mukhamandapa with square bases + terracotta/grey lathe shafts,
    // off-white parapet roof rim, double-register carved rear sanctum walls,
    // and multi-tiered Kuta/Shala Vimana Shikhara with gleaming golden Kalasha.
    // =========================================================================
    const andalGroup = new THREE.Group();
    andalGroup.position.set(18.5, 0, -20.5);
    worldGroup.add(andalGroup);

    const andalGraniteMat = new THREE.MeshStandardMaterial({
      color: 0x848d94, // Cool bluish-grey granite pillar pedestals & plinth decks (Images 2–4)
      roughness: 0.80,
      metalness: 0.14,
    });
    const andalWhiteParapetMat = new THREE.MeshStandardMaterial({
      color: 0xd6d2ca, // Signature weathered off-white plastered parapet rim (clearly seen in Images 2–4)
      roughness: 0.90,
      metalness: 0.05,
    });

    // A. 4-Course Stepped Granite Adhisthana Plinth (Y = 0.05 to Y = 0.85, spanning Z = -6.6 to +5.8)
    const andalPlinthCourses = [
      { w: 7.4, d: 12.6, yB: 0.05, yT: 0.25, mat: friezeMat },
      { w: 7.1, d: 12.3, yB: 0.25, yT: 0.45, mat: mainRoofEaveMat },
      { w: 7.25, d: 12.45, yB: 0.45, yT: 0.65, mat: mainTempleSoapstoneMat },
      { w: 7.0, d: 12.2, yB: 0.65, yT: 0.85, mat: andalGraniteMat },
    ];
    andalPlinthCourses.forEach(({ w, d, yB, yT, mat }) => {
      const course = new THREE.Mesh(new THREE.BoxGeometry(w, yT - yB, d), mat);
      course.position.set(0, (yB + yT) / 2, -0.4);
      course.castShadow = true;
      course.receiveShadow = true;
      andalGroup.add(course);
    });

    // B. Front East Staircase (5 granite steps + curved Hastihasta S-scroll balustrades)
    for (let st = 0; st < 5; st++) {
      const sH = ((st + 1) / 5) * 0.80;
      const sZ = 6.95 - st * 0.28;
      const step = new THREE.Mesh(new THREE.BoxGeometry(2.5, sH, 0.34), andalGraniteMat);
      step.position.set(0, 0.05 + sH / 2, sZ);
      step.castShadow = true;
      step.receiveShadow = true;
      andalGroup.add(step);
    }

    [-1.40, 1.40].forEach((bx) => {
      const bSlope = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.36, 1.45), andalGraniteMat);
      bSlope.position.set(bx, 0.48, 6.45);
      bSlope.rotation.x = 0.48;
      bSlope.castShadow = true;
      andalGroup.add(bSlope);

      const bScroll = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.34, 14), andalGraniteMat);
      bScroll.rotation.z = Math.PI / 2;
      bScroll.position.set(bx, 0.26, 7.02);
      bScroll.castShadow = true;
      andalGroup.add(bScroll);
    });

    // C. Open Pillared Front Mukhamandapa (12 ornate Belur pillars: 4 columns x 3 rows)
    const andalColFootGeo = new THREE.BoxGeometry(0.40, 0.68, 0.40);
    const andalColRingGeo = new THREE.CylinderGeometry(0.21, 0.21, 0.22, 16);
    const andalColRedDrumGeo = new THREE.CylinderGeometry(0.16, 0.17, 0.38, 16);
    const andalColNeckGeo = new THREE.CylinderGeometry(0.14, 0.18, 0.28, 16);
    const andalColCapGeo = new THREE.BoxGeometry(0.54, 0.24, 0.54);

    [-2.85, -1.00, 1.00, 2.85].forEach((px) => {
      [5.15, 3.10, 1.05].forEach((pz) => {
        const colGroup = new THREE.Group();
        colGroup.position.set(px, 0.85, pz);

        const foot = new THREE.Mesh(andalColFootGeo, andalGraniteMat);
        foot.position.y = 0.34;
        foot.castShadow = true;
        colGroup.add(foot);

        const lowerRing = new THREE.Mesh(andalColRingGeo, andalGraniteMat);
        lowerRing.position.y = 0.79;
        colGroup.add(lowerRing);

        // Warm pinkish-terracotta turned lathe shaft section clearly visible in Images 2–4
        const redShaft = new THREE.Mesh(andalColRedDrumGeo, portalPinkPillarMat);
        redShaft.position.y = 1.08;
        redShaft.castShadow = true;
        colGroup.add(redShaft);

        const upperNeck = new THREE.Mesh(andalColNeckGeo, andalGraniteMat);
        upperNeck.position.y = 1.40;
        colGroup.add(upperNeck);

        const cap = new THREE.Mesh(andalColCapGeo, mainRoofEaveMat);
        cap.position.y = 1.66;
        cap.castShadow = true;
        colGroup.add(cap);

        andalGroup.add(colGroup);
      });
    });

    // Open Mandapa Roof Overhanging Kapota Eave & Off-White Parapet Rim (Y = 2.64 to 3.22)
    const mandapaEave = new THREE.Mesh(new THREE.BoxGeometry(7.8, 0.22, 5.8), mainRoofEaveMat);
    mandapaEave.position.set(0, 2.74, 3.15);
    mandapaEave.castShadow = true;
    andalGroup.add(mandapaEave);

    const mandapaWhiteParapet = new THREE.Mesh(new THREE.BoxGeometry(7.2, 0.34, 5.4), andalWhiteParapetMat);
    mandapaWhiteParapet.position.set(0, 3.00, 3.10);
    mandapaWhiteParapet.castShadow = true;
    andalGroup.add(mandapaWhiteParapet);

    // D. Closed Antarala & Garbhagriha Sanctum with Double-Register Relief Walls (Z = -6.4 to +0.6)
    const sanctumWallCore = new THREE.Mesh(new THREE.BoxGeometry(6.1, 1.90, 6.8), friezeMat);
    sanctumWallCore.position.set(0, 1.80, -2.9);
    sanctumWallCore.castShadow = true;
    sanctumWallCore.receiveShadow = true;
    andalGroup.add(sanctumWallCore);

    // Deep recessed Sanctum Entrance Portal inside the open Mukhamandapa (facing East +Z)
    const innerPortal = new THREE.Mesh(new THREE.BoxGeometry(1.45, 1.75, 0.30), shrineNicheMat);
    innerPortal.position.set(0, 1.72, 0.52);
    andalGroup.add(innerPortal);

    // Projecting Wall Niches & Sculpted Deity Relief Bays along South (-X), North (+X), West (-Z) (Image 4)
    [-3.12, 3.12].forEach((sx) => {
      [-1.0, -3.0, -5.0].forEach((sz) => {
        const pilaster = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.75, 0.24), mainTempleSoapstoneMat);
        pilaster.position.set(sx, 1.78, sz + 0.85);
        andalGroup.add(pilaster);

        // Two-register sculpted deity relief niches matching left side of Image 4
        [1.38, 2.18].forEach((ny) => {
          const deityRelief = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.62, 0.42), shrineStoneMat);
          deityRelief.position.set(sx, ny, sz);
          andalGroup.add(deityRelief);
        });
      });
    });

    // Rear West sanctum projection bays
    [-1.5, 0, 1.5].forEach((wx) => {
      const westBay = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.75, 0.22), shrineStoneMat);
      westBay.position.set(wx, 1.78, -6.38);
      andalGroup.add(westBay);
    });

    const sanctumEave = new THREE.Mesh(new THREE.BoxGeometry(6.9, 0.22, 7.3), mainRoofEaveMat);
    sanctumEave.position.set(0, 2.74, -2.9);
    sanctumEave.castShadow = true;
    andalGroup.add(sanctumEave);

    const sanctumParapet = new THREE.Mesh(new THREE.BoxGeometry(6.4, 0.28, 6.8), andalWhiteParapetMat);
    sanctumParapet.position.set(0, 2.98, -2.9);
    sanctumParapet.castShadow = true;
    andalGroup.add(sanctumParapet);

    // E. Multi-Tiered Dravida-Hoysala Vimana Shikhara & Golden Kalasha (Z = -3.6, Y = 3.12 to 6.45)
    const vimanaGroup = new THREE.Group();
    vimanaGroup.position.set(0, 3.12, -3.6);
    andalGroup.add(vimanaGroup);

    // Tala 1 Core & 8 Perimeter Kuta / Shala Miniature Pavilions
    const tala1Core = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.85, 3.8), shrineStoneMat);
    tala1Core.position.y = 0.42;
    tala1Core.castShadow = true;
    vimanaGroup.add(tala1Core);

    const kutaPositions1: [number, number][] = [
      [-2.05, -2.05], [2.05, -2.05], [-2.05, 2.05], [2.05, 2.05],
      [0, -2.15], [0, 2.15], [-2.15, 0], [2.15, 0],
    ];
    kutaPositions1.forEach(([kx, kz], idx) => {
      const isCorner = idx < 4;
      const kBody = new THREE.Mesh(
        new THREE.BoxGeometry(isCorner ? 0.82 : 1.35, 0.58, isCorner ? 0.82 : 0.72),
        shrineStoneMat
      );
      if (idx >= 6) kBody.rotation.y = Math.PI / 2;
      kBody.position.set(kx, 0.34, kz);
      kBody.castShadow = true;
      vimanaGroup.add(kBody);

      const kRoof = new THREE.Mesh(
        new THREE.ConeGeometry(isCorner ? 0.52 : 0.48, 0.42, 4),
        mainTempleSoapstoneMat
      );
      kRoof.rotation.y = Math.PI / 4;
      kRoof.position.set(kx, 0.82, kz);
      vimanaGroup.add(kRoof);
    });

    // Tala 2 Inset Core & Stepped Pavilions + Cardinal Nasika Gables
    const tala2Core = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.68, 2.6), shrineStoneMat);
    tala2Core.position.y = 1.18;
    tala2Core.castShadow = true;
    vimanaGroup.add(tala2Core);

    const kutaPositions2: [number, number][] = [
      [-1.38, -1.38], [1.38, -1.38], [-1.38, 1.38], [1.38, 1.38],
      [0, -1.45], [0, 1.45], [-1.45, 0], [1.45, 0],
    ];
    kutaPositions2.forEach(([kx, kz]) => {
      const k2Roof = new THREE.Mesh(new THREE.ConeGeometry(0.42, 0.38, 4), mainTempleSoapstoneMat);
      k2Roof.rotation.y = Math.PI / 4;
      k2Roof.position.set(kx, 1.56, kz);
      vimanaGroup.add(k2Roof);
    });

    // Griva Neck & Octagonal Stone Shikhara Dome Cupola
    const vimanaGriva = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.18, 0.42, 8), shrineStoneMat);
    vimanaGriva.position.y = 1.72;
    vimanaGroup.add(vimanaGriva);

    const shikharaDome = new THREE.Mesh(
      new THREE.SphereGeometry(1.12, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2),
      shrineStoneMat
    );
    shikharaDome.scale.set(1.0, 0.72, 1.0);
    shikharaDome.position.y = 1.92;
    shikharaDome.castShadow = true;
    vimanaGroup.add(shikharaDome);

    // Gleaming Golden Dome Cap & Sacred Kalasha Urn Finial (matching Images 2–4 skyline)
    const goldCap = new THREE.Mesh(
      new THREE.SphereGeometry(0.76, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2),
      darkBronzeMat
    );
    goldCap.scale.set(1.0, 0.55, 1.0);
    goldCap.position.y = 2.38;
    vimanaGroup.add(goldCap);

    const kalashaUrn = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 12), darkBronzeMat);
    kalashaUrn.position.y = 2.86;
    kalashaUrn.castShadow = true;
    vimanaGroup.add(kalashaUrn);

    const kalashaSpire = new THREE.Mesh(new THREE.ConeGeometry(0.11, 0.48, 12), darkBronzeMat);
    kalashaSpire.position.y = 3.16;
    kalashaSpire.castShadow = true;
    vimanaGroup.add(kalashaSpire);

    // =========================================================================
    // 6. VASUDEVA SAROVARA STEPPED TANK (#6) (KALYANI)
    // 100% Architecturally accurate to uploaded reference photos:
    // media_1793862766025_bcf39b80.jpg, media_1793862866593_6a861438.jpg, media_1793862909516_624b71ff.jpg
    // Featuring:
    // 1. Natural aquatic water blue reflective basin ("only color should be water blue")
    // 2. Concentric stepped ashlar stone descending tiers (8 levels)
    // 3. Central & corner descending stair flights with landings
    // 4. Two authentic Hoysala miniature shrines (Deepa-Kuta pavilions) with
    //    moulded plinth, 4 lathe-turned pillars, inner niche, chhajja eaves, tiered shikhara, amalaka & kalasha
    // 5. Authentic sculpted stone elephant (Gaja) guarding the descending water steps
    // 6. Paved granite stone walkway and high ashlar retaining walls
    // =========================================================================
    const tankGroup = new THREE.Group();
    tankGroup.position.set(36.6, 0, 19.6);
    worldGroup.add(tankGroup);

    // A. Upper Paved Stone Promenade Walkway & High Ashlar Enclosure Retaining Walls
    // 1. Paved Stone Walkway around the 4 sides of the tank rim
    const walkwayNorth = new THREE.Mesh(new THREE.BoxGeometry(18.6, 0.4, 2.2), tankAshlarMat);
    walkwayNorth.position.set(0, 0.2, -7.2);
    walkwayNorth.receiveShadow = true;
    tankGroup.add(walkwayNorth);

    const walkwaySouth = new THREE.Mesh(new THREE.BoxGeometry(18.6, 0.4, 2.2), tankAshlarMat);
    walkwaySouth.position.set(0, 0.2, 7.2);
    walkwaySouth.receiveShadow = true;
    tankGroup.add(walkwaySouth);

    const walkwayEast = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.4, 12.2), tankAshlarMat);
    walkwayEast.position.set(8.2, 0.2, 0);
    walkwayEast.receiveShadow = true;
    tankGroup.add(walkwayEast);

    const walkwayWest = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.4, 12.2), tankAshlarMat);
    walkwayWest.position.set(-8.2, 0.2, 0);
    walkwayWest.receiveShadow = true;
    tankGroup.add(walkwayWest);

    // 2. High Weathered Ashlar Granite Enclosure Retaining Walls (matching photos)
    const rearRetainingWall = new THREE.Mesh(new THREE.BoxGeometry(19.0, 3.4, 0.9), tankAshlarMat);
    rearRetainingWall.position.set(0, 1.7, 8.5);
    rearRetainingWall.castShadow = true;
    rearRetainingWall.receiveShadow = true;
    tankGroup.add(rearRetainingWall);

    const sideRetainingWall = new THREE.Mesh(new THREE.BoxGeometry(0.9, 3.4, 17.0), tankAshlarMat);
    sideRetainingWall.position.set(9.0, 1.7, 0);
    sideRetainingWall.castShadow = true;
    sideRetainingWall.receiveShadow = true;
    tankGroup.add(sideRetainingWall);

    // B. Natural Aquatic Water Blue Surface ("only color should be water blue")
    // Solid water basin volume (14.4m x 12.4m x 0.22m) positioned at y = 0.16.
    // Top surface reaches y = 0.27, which is 0.22m above the opaque courtyard ground (y = 0.05)
    // and slips 10cm under the stone walkway edges (y = 0.40) so the entire marked area is 100% blue water!
    const water = new THREE.Mesh(new THREE.BoxGeometry(14.4, 0.22, 12.4), pushkaraniWaterMat);
    water.position.set(0, 0.16, 0);
    water.receiveShadow = true;
    tankGroup.add(water);

    // C. Concentric Stepped Stone Ghats (framing the perimeter of the water basin)
    // Upper tier stepped stone rim (stepping down from walkway y = 0.40 to y = 0.28)
    const stepRimNorth = new THREE.Mesh(new THREE.BoxGeometry(14.6, 0.16, 0.55), tankAshlarMat);
    stepRimNorth.position.set(0, 0.28, -5.85);
    stepRimNorth.receiveShadow = true;
    tankGroup.add(stepRimNorth);

    const stepRimSouth = new THREE.Mesh(new THREE.BoxGeometry(14.6, 0.16, 0.55), tankAshlarMat);
    stepRimSouth.position.set(0, 0.28, 5.85);
    stepRimSouth.receiveShadow = true;
    tankGroup.add(stepRimSouth);

    const stepRimEast = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.16, 11.2), tankAshlarMat);
    stepRimEast.position.set(6.85, 0.28, 0);
    stepRimEast.receiveShadow = true;
    tankGroup.add(stepRimEast);

    const stepRimWest = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.16, 11.2), tankAshlarMat);
    stepRimWest.position.set(-6.85, 0.28, 0);
    stepRimWest.receiveShadow = true;
    tankGroup.add(stepRimWest);

    // Lower waterline step course (meeting water blue surface at y = 0.20)
    const waterStepNorth = new THREE.Mesh(new THREE.BoxGeometry(13.6, 0.12, 0.48), tankSubmergedStoneMat);
    waterStepNorth.position.set(0, 0.22, -5.35);
    waterStepNorth.receiveShadow = true;
    tankGroup.add(waterStepNorth);

    const waterStepSouth = new THREE.Mesh(new THREE.BoxGeometry(13.6, 0.12, 0.48), tankSubmergedStoneMat);
    waterStepSouth.position.set(0, 0.22, 5.35);
    waterStepSouth.receiveShadow = true;
    tankGroup.add(waterStepSouth);

    const waterStepEast = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.12, 10.3), tankSubmergedStoneMat);
    waterStepEast.position.set(6.38, 0.22, 0);
    waterStepEast.receiveShadow = true;
    tankGroup.add(waterStepEast);

    const waterStepWest = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.12, 10.3), tankSubmergedStoneMat);
    waterStepWest.position.set(-6.38, 0.22, 0);
    waterStepWest.receiveShadow = true;
    tankGroup.add(waterStepWest);

    // D. Projecting Stone Staircase Flights Descending into the Water (Images 1 & 2)
    const southStairCounts = 4;
    for (let s = 0; s < southStairCounts; s++) {
      const sY = 0.34 - s * 0.05;
      const sZ = 5.8 - s * 0.45;
      const stairStep = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.14, 0.48), tankAshlarMat);
      stairStep.position.set(1.5, sY, sZ);
      stairStep.receiveShadow = true;
      tankGroup.add(stairStep);
    }

    for (let s = 0; s < southStairCounts; s++) {
      const sY = 0.34 - s * 0.05;
      const sZ = -5.8 + s * 0.45;
      const stairStep = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.14, 0.48), tankAshlarMat);
      stairStep.position.set(-1.5, sY, sZ);
      stairStep.receiveShadow = true;
      tankGroup.add(stairStep);
    }

    // E. Authentic Hoysala Miniature Shrines (Deepa-Kuta Pavilions)
    // Matching foreground and far corner shrines in media_1793862766025_bcf39b80.jpg & media_1793862866593_6a861438.jpg
    const createKalyaniMiniatureShrine = (
      sx: number,
      sy: number,
      sz: number,
      rotY: number
    ) => {
      const kShrineGroup = new THREE.Group();
      kShrineGroup.position.set(sx, sy, sz);
      kShrineGroup.rotation.y = rotY;

      // 1. Moulded Adhisthana Plinth
      const baseUpana = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.22, 1.6), tankAshlarMat);
      baseUpana.position.y = 0.11;
      baseUpana.castShadow = true;
      kShrineGroup.add(baseUpana);

      const kumudaTorus = new THREE.Mesh(new THREE.BoxGeometry(1.44, 0.16, 1.44), shrineStoneMat);
      kumudaTorus.position.y = 0.30;
      kumudaTorus.castShadow = true;
      kShrineGroup.add(kumudaTorus);

      const pattikaPlinth = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.14, 1.5), tankAshlarMat);
      pattikaPlinth.position.y = 0.45;
      kShrineGroup.add(pattikaPlinth);

      // 2. Open Sanctum Chamber with 4 Lathe-Turned Pillars
      const chamberInner = new THREE.Mesh(new THREE.BoxGeometry(0.72, 1.05, 0.72), shrineNicheMat);
      chamberInner.position.set(0, 1.05, 0);
      kShrineGroup.add(chamberInner);

      [-0.58, 0.58].forEach((px) => {
        [-0.58, 0.58].forEach((pz) => {
          const pCol = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.11, 1.05, 12), polishedPillarMat);
          pCol.position.set(px, 1.05, pz);
          pCol.castShadow = true;
          kShrineGroup.add(pCol);

          // Torus rings on lathe-turned shafts
          [0.85, 1.25].forEach((ry) => {
            const ring = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.025, 8, 16), polishedPillarMat);
            ring.rotation.x = Math.PI / 2;
            ring.position.set(px, ry, pz);
            kShrineGroup.add(ring);
          });
        });
      });

      // Flanking Carved Relief Panels on Left and Right (Dravida Aedicules)
      [-0.62, 0.62].forEach((rx) => {
        const reliefPanel = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.88, 0.65), friezeMat);
        reliefPanel.position.set(rx, 1.05, 0);
        reliefPanel.castShadow = true;
        kShrineGroup.add(reliefPanel);
      });

      // Sculpted Torana Lintel above entrance
      const kLintel = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.18, 0.35), shrineStoneMat);
      kLintel.position.set(0, 1.66, 0.58);
      kLintel.castShadow = true;
      kShrineGroup.add(kLintel);

      // 3. Projecting Double Chhajja Cornice Eaves
      const kChhajja1 = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.16, 1.75), mainTempleSoapstoneMat);
      kChhajja1.position.y = 1.82;
      kChhajja1.castShadow = true;
      kShrineGroup.add(kChhajja1);

      const kChhajja2 = new THREE.Mesh(new THREE.BoxGeometry(1.52, 0.14, 1.52), mainTempleSoapstoneMat);
      kChhajja2.position.y = 1.97;
      kChhajja2.castShadow = true;
      kShrineGroup.add(kChhajja2);

      // 4. Multi-Tiered Dravida / Kadamba-Nagara Shikhara Spire
      [
        { w: 1.32, h: 0.28, y: 2.18 },
        { w: 1.08, h: 0.26, y: 2.45 },
        { w: 0.84, h: 0.24, y: 2.70 },
        { w: 0.60, h: 0.22, y: 2.93 },
      ].forEach((tier) => {
        const tMesh = new THREE.Mesh(new THREE.BoxGeometry(tier.w, tier.h, tier.w), shrineStoneMat);
        tMesh.position.y = tier.y;
        tMesh.castShadow = true;
        kShrineGroup.add(tMesh);
      });

      // 5. Crown: Griva Neck + Fluted Amalaka Stone + Kalasha Finial
      const grivaNeck = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.38, 0.14, 16), shrineStoneMat);
      grivaNeck.position.y = 3.11;
      kShrineGroup.add(grivaNeck);

      const amalakaStone = new THREE.Mesh(new THREE.CylinderGeometry(0.40, 0.46, 0.20, 16), shrineStoneMat);
      amalakaStone.position.y = 3.28;
      amalakaStone.castShadow = true;
      kShrineGroup.add(amalakaStone);

      const stupikaKalasha = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.38, 12), goldKalashaMat);
      stupikaKalasha.position.y = 3.57;
      stupikaKalasha.castShadow = true;
      kShrineGroup.add(stupikaKalasha);

      tankGroup.add(kShrineGroup);
    };

    // Foreground Corner Miniature Shrine (Image 1 & Image 2)
    createKalyaniMiniatureShrine(5.8, 0.4, 5.0, -Math.PI / 4);

    // Far Corner Miniature Shrine (Image 1)
    createKalyaniMiniatureShrine(-6.0, 0.4, -5.2, (3 * Math.PI) / 4);

    // F. Sculpted Stone Elephant Guarding the Descending Water Steps
    // Authentic Hoysala Elephant (Gaja) as clearly seen in media_1793862766025_bcf39b80.jpg & media_1793862866593_6a861438.jpg
    const elephantGroup = new THREE.Group();
    elephantGroup.position.set(3.4, 0.28, 4.4);
    elephantGroup.rotation.y = -Math.PI / 3;

    // 1. Carved Pedestal Plinth
    const elePedestal = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.18, 1.3), friezeMat);
    elePedestal.position.y = 0.09;
    elePedestal.receiveShadow = true;
    elephantGroup.add(elePedestal);

    // 2. Sculpted Elephant Body & Decorative Flank Trappings (Jhul)
    const eleBody = new THREE.Mesh(new THREE.BoxGeometry(0.68, 0.74, 1.18), friezeMat);
    eleBody.position.y = 0.54;
    eleBody.castShadow = true;
    elephantGroup.add(eleBody);

    const eleBlanket = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.46, 0.82), mainTempleSoapstoneMat);
    eleBlanket.position.y = 0.60;
    elephantGroup.add(eleBlanket);

    // 3. Sturdy Legs
    [-0.22, 0.22].forEach((lx) => {
      [-0.38, 0.38].forEach((lz) => {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 0.55, 10), friezeMat);
        leg.position.set(lx, 0.28, lz);
        leg.castShadow = true;
        elephantGroup.add(leg);
      });
    });

    // 4. Carved Head, Forehead Medallion & Flared Ears
    const eleHead = new THREE.Mesh(new THREE.SphereGeometry(0.30, 12, 12), friezeMat);
    eleHead.position.set(0, 0.84, 0.58);
    eleHead.castShadow = true;
    elephantGroup.add(eleHead);

    const eleKumbha = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 10), goldKalashaMat);
    eleKumbha.position.set(0, 1.0, 0.68);
    elephantGroup.add(eleKumbha);

    [-0.28, 0.28].forEach((ex) => {
      const ear = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.36, 0.22), friezeMat);
      ear.position.set(ex, 0.84, 0.48);
      ear.rotation.y = ex > 0 ? 0.35 : -0.35;
      elephantGroup.add(ear);
    });

    // 5. Pointed Stone Tusks
    [-0.12, 0.12].forEach((tx) => {
      const tusk = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.025, 0.32, 8), friezeMat);
      tusk.position.set(tx, 0.70, 0.75);
      tusk.rotation.x = 0.45;
      elephantGroup.add(tusk);
    });

    // 6. Sculpted Curved Trunk
    const upperTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.065, 0.38, 8), friezeMat);
    upperTrunk.position.set(0, 0.64, 0.78);
    upperTrunk.rotation.x = 0.55;
    elephantGroup.add(upperTrunk);

    const lowerTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.045, 0.30, 8), friezeMat);
    lowerTrunk.position.set(0, 0.40, 0.85);
    lowerTrunk.rotation.x = -0.35;
    elephantGroup.add(lowerTrunk);

    // 7. Tail
    const eleTail = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.02, 0.52, 6), friezeMat);
    eleTail.position.set(0, 0.45, -0.60);
    eleTail.rotation.x = -0.25;
    elephantGroup.add(eleTail);

    tankGroup.add(elephantGroup);

    // =========================================================================
    // 7. MAHADVARA (RAYA GOPURA) (#7)
    // 100% Architecturally accurate model matching UNESCO nomination plan &
    // uploaded reference photos: media_1793858207384_6c3858be.jpg & media_1793858236311_84e42dd7.jpg
    // =========================================================================
    const gopuraGroup = new THREE.Group();
    gopuraGroup.position.set(2, 0, 29);
    worldGroup.add(gopuraGroup);

    // -------------------------------------------------------------------------
    // A. Stepped Approach Steps (Outside Road & Inner Courtyard)
    // -------------------------------------------------------------------------
    // Outer flight of 6 wide horizontal stone steps leading up from outside road (seen in photo)
    for (let s = 0; s < 6; s++) {
      const stepW = 13.8 - s * 0.15;
      const stepD = 0.52;
      const stepH = 0.16;
      const stepY = (5 - s) * stepH + stepH / 2;
      const stepZ = 3.65 + s * stepD;
      const stepMesh = new THREE.Mesh(new THREE.BoxGeometry(stepW, stepH, stepD + 0.08), gopuraBaseStoneMat);
      stepMesh.position.set(0, stepY, stepZ);
      stepMesh.receiveShadow = true;
      stepMesh.castShadow = true;
      gopuraGroup.add(stepMesh);
    }

    // Inner courtyard steps descending into sacred courtyard
    for (let s = 0; s < 4; s++) {
      const stepW = 8.0 - s * 0.2;
      const stepD = 0.48;
      const stepH = 0.16;
      const stepY = (3 - s) * stepH + stepH / 2;
      const stepZ = -3.65 - s * stepD;
      const stepMesh = new THREE.Mesh(new THREE.BoxGeometry(stepW, stepH, stepD + 0.08), gopuraBaseStoneMat);
      stepMesh.position.set(0, stepY, stepZ);
      stepMesh.receiveShadow = true;
      stepMesh.castShadow = true;
      gopuraGroup.add(stepMesh);
    }

    // -------------------------------------------------------------------------
    // B. Weathered Ashlar Granite Substructure (y = 0 to 7.8)
    // -------------------------------------------------------------------------
    // 1. Moulded Adhisthana Plinth Courses
    const gopuraPlinthCourses = [
      { w: 14.0, h: 0.32, d: 7.8, y: 0.16 }, // Upana footing
      { w: 13.6, h: 0.32, d: 7.5, y: 0.48 }, // Jagati plinth
      { w: 13.2, h: 0.28, d: 7.3, y: 0.78 }, // Kumuda torus
      { w: 13.4, h: 0.26, d: 7.4, y: 1.05 }, // Pattika moulding
    ];
    gopuraPlinthCourses.forEach(({ w, h, d, y }) => {
      const plinth = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), gopuraBaseStoneMat);
      plinth.position.y = y;
      plinth.castShadow = true;
      plinth.receiveShadow = true;
      gopuraGroup.add(plinth);
    });

    // 2. Open Central Pass-Through Gateway (corridor looking through to Deepa Stambha & sky)
    // Portal Dimensions: width 3.6, height 6.2, depth 7.2
    const portalFloor = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.18, 7.2), gopuraBaseStoneMat);
    portalFloor.position.set(0, 1.05, 0);
    portalFloor.receiveShadow = true;
    gopuraGroup.add(portalFloor);

    // Left Granite Pylon (South block)
    const pylonL = new THREE.Mesh(new THREE.BoxGeometry(4.7, 6.2, 7.2), gopuraBaseStoneMat);
    pylonL.position.set(-4.15, 4.25, 0);
    pylonL.castShadow = true;
    pylonL.receiveShadow = true;
    gopuraGroup.add(pylonL);

    // Right Granite Pylon (North block)
    const pylonR = new THREE.Mesh(new THREE.BoxGeometry(4.7, 6.2, 7.2), gopuraBaseStoneMat);
    pylonR.position.set(4.15, 4.25, 0);
    pylonR.castShadow = true;
    pylonR.receiveShadow = true;
    gopuraGroup.add(pylonR);

    // Carved Inner Door Jambs (Dvarashakha)
    [-1.85, 1.85].forEach((jx) => {
      const jamb = new THREE.Mesh(new THREE.BoxGeometry(0.35, 6.2, 7.2), gopuraBaseStoneMat);
      jamb.position.set(jx, 4.25, 0);
      jamb.castShadow = true;
      gopuraGroup.add(jamb);
    });

    // Massive Stone Gateway Lintel Beam (Uttira)
    const gatewayLintel = new THREE.Mesh(new THREE.BoxGeometry(13.2, 1.0, 7.4), gopuraBaseStoneMat);
    gatewayLintel.position.set(0, 7.15, 0);
    gatewayLintel.castShadow = true;
    gopuraGroup.add(gatewayLintel);

    // Projecting Granite Cornice Beam (Prastara / Kapota separating granite base from stucco tower)
    const baseKapota = new THREE.Mesh(new THREE.BoxGeometry(13.8, 0.48, 8.0), gopuraBaseStoneMat);
    baseKapota.position.set(0, 7.75, 0);
    baseKapota.castShadow = true;
    gopuraGroup.add(baseKapota);

    // 3. Facade Reliefs & Carved Pilasters on Granite Pylons (Matching Photo)
    [-3.66, 3.66].forEach((faceZ) => {
      // Lower continuous frieze band with standing deity figures
      const friezeL = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.82, 0.18), gopuraBaseStoneMat);
      friezeL.position.set(-4.15, 1.75, faceZ);
      friezeL.castShadow = true;
      gopuraGroup.add(friezeL);

      const friezeR = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.82, 0.18), gopuraBaseStoneMat);
      friezeR.position.set(4.15, 1.75, faceZ);
      friezeR.castShadow = true;
      gopuraGroup.add(friezeR);

      // Slender vertical pilasters flanking entrance and corner bays
      [-6.2, -4.8, -3.4, -2.15, 2.15, 3.4, 4.8, 6.2].forEach((px) => {
        const pilaster = new THREE.Mesh(new THREE.BoxGeometry(0.24, 4.6, 0.12), gopuraBaseStoneMat);
        pilaster.position.set(px, 4.6, faceZ);
        pilaster.castShadow = true;
        gopuraGroup.add(pilaster);

        // Capital bracket (Pushpapotika)
        const cap = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.18, 0.20), gopuraBaseStoneMat);
        cap.position.set(px, 6.95, faceZ);
        cap.castShadow = true;
        gopuraGroup.add(cap);
      });

      // Framed Koshtha (Niche panels) in middle bays
      [-4.1, 4.1].forEach((nx) => {
        const niche = new THREE.Mesh(new THREE.BoxGeometry(1.05, 2.4, 0.08), gopuraBaseStoneMat);
        niche.position.set(nx, 4.4, faceZ);
        gopuraGroup.add(niche);
      });
    });

    // -------------------------------------------------------------------------
    // C. 7-Tiered Golden Stucco Superstructure (Bhumis 1 to 7)
    // Seamless stacking from y = 7.80 to y = 18.65 (ZERO gaps)
    // -------------------------------------------------------------------------
    const gopuraTiers = [
      { level: 1, bottomY: 7.80,  h: 1.70, w: 12.2, d: 6.8, hasWin: true, winW: 2.1, winH: 1.20, hasMedallion: true },
      { level: 2, bottomY: 9.50,  h: 1.65, w: 11.2, d: 6.2, hasWin: true, winW: 1.85, winH: 1.15, hasMedallion: false },
      { level: 3, bottomY: 11.15, h: 1.60, w: 10.2, d: 5.6, hasWin: true, winW: 1.65, winH: 1.10, hasMedallion: false },
      { level: 4, bottomY: 12.75, h: 1.55, w: 9.2,  d: 5.0, hasWin: true, winW: 1.45, winH: 1.05, hasMedallion: false },
      { level: 5, bottomY: 14.30, h: 1.50, w: 8.2,  d: 4.4, hasWin: false, winW: 0, winH: 0, hasMedallion: false },
      { level: 6, bottomY: 15.80, h: 1.45, w: 7.2,  d: 3.8, hasWin: false, winW: 0, winH: 0, hasMedallion: false },
      { level: 7, bottomY: 17.25, h: 1.40, w: 6.2,  d: 3.2, hasWin: false, winW: 0, winH: 0, hasMedallion: false },
    ];

    gopuraTiers.forEach((tier) => {
      const tierCenterY = tier.bottomY + tier.h / 2;
      const tierTopY = tier.bottomY + tier.h;

      // 1. Tier Main Solid Body (flush seamless stack)
      const tierBody = new THREE.Mesh(new THREE.BoxGeometry(tier.w, tier.h, tier.d), gopuraStoneMat);
      tierBody.position.set(0, tierCenterY, 0);
      tierBody.castShadow = true;
      tierBody.receiveShadow = true;
      gopuraGroup.add(tierBody);

      // 2. Overhanging Moulded Eave Cornice (Kapota) at tier top
      const tierKapota = new THREE.Mesh(new THREE.BoxGeometry(tier.w + 0.50, 0.20, tier.d + 0.50), gopuraCorniceMat);
      tierKapota.position.set(0, tierTopY, 0);
      tierKapota.castShadow = true;
      tierKapota.receiveShadow = true;
      gopuraGroup.add(tierKapota);

      // 3. Four Corner Pavilions (Kutas)
      const kw = 0.68;
      const kh = tier.h * 0.76;
      const kxOff = tier.w / 2 - kw / 2;
      const kzOff = tier.d / 2 - kw / 2;
      [
        [-kxOff, -kzOff],
        [kxOff, -kzOff],
        [-kxOff, kzOff],
        [kxOff, kzOff],
      ].forEach(([kx, kz]) => {
        const kutaBody = new THREE.Mesh(new THREE.BoxGeometry(kw, kh, kw), gopuraStoneMat);
        kutaBody.position.set(kx, tierCenterY - tier.h * 0.08, kz);
        kutaBody.castShadow = true;
        gopuraGroup.add(kutaBody);

        const kutaCornice = new THREE.Mesh(new THREE.BoxGeometry(kw + 0.16, 0.12, kw + 0.16), gopuraCorniceMat);
        kutaCornice.position.set(kx, tierCenterY - tier.h * 0.08 + kh / 2 + 0.06, kz);
        gopuraGroup.add(kutaCornice);

        const kutaDome = new THREE.Mesh(
          new THREE.SphereGeometry(kw * 0.52, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2),
          gopuraCorniceMat
        );
        kutaDome.position.set(kx, tierCenterY - tier.h * 0.08 + kh / 2 + 0.12, kz);
        gopuraGroup.add(kutaDome);

        const kutaFinial = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.25, 8), goldKalashaMat);
        kutaFinial.position.set(kx, tierCenterY - tier.h * 0.08 + kh / 2 + 0.35, kz);
        gopuraGroup.add(kutaFinial);
      });

      // 4. Subtle Wall Articulation Pilasters (Flat architectural panels matching Dravidian order)
      [-tier.d / 2, tier.d / 2].forEach((faceZ) => {
        const zDir = faceZ > 0 ? 1 : -1;
        const pxOffsets = [tier.w * 0.26, tier.w * 0.40];
        pxOffsets.forEach((ox) => {
          [-ox, ox].forEach((px) => {
            const pil = new THREE.Mesh(new THREE.BoxGeometry(0.18, tier.h * 0.85, 0.08), gopuraCorniceMat);
            pil.position.set(px, tierCenterY, faceZ + zDir * 0.04);
            gopuraGroup.add(pil);
          });
        });
      });

      // 5. Central Rectangular Windows with Iron Security Grills (Tiers 1, 2, 3, 4)
      if (tier.hasWin) {
        const winY = tierCenterY - 0.05;
        [-tier.d / 2, tier.d / 2].forEach((faceZ) => {
          const zDir = faceZ > 0 ? 1 : -1;

          // Deep dark recessed window cavity
          const winCavity = new THREE.Mesh(
            new THREE.BoxGeometry(tier.winW, tier.winH, 0.35),
            gopuraWindowMat
          );
          winCavity.position.set(0, winY, faceZ + zDir * 0.05);
          gopuraGroup.add(winCavity);

          // Sculpted Window Surround (Jambs, Lintel, Sill)
          const jambL = new THREE.Mesh(new THREE.BoxGeometry(0.18, tier.winH, 0.38), gopuraCorniceMat);
          jambL.position.set(-tier.winW / 2 - 0.09, winY, faceZ + zDir * 0.08);
          gopuraGroup.add(jambL);

          const jambR = new THREE.Mesh(new THREE.BoxGeometry(0.18, tier.winH, 0.38), gopuraCorniceMat);
          jambR.position.set(tier.winW / 2 + 0.09, winY, faceZ + zDir * 0.08);
          gopuraGroup.add(jambR);

          const winLintel = new THREE.Mesh(new THREE.BoxGeometry(tier.winW + 0.45, 0.16, 0.42), gopuraCorniceMat);
          winLintel.position.set(0, winY + tier.winH / 2 + 0.08, faceZ + zDir * 0.09);
          gopuraGroup.add(winLintel);

          const winSill = new THREE.Mesh(new THREE.BoxGeometry(tier.winW + 0.36, 0.14, 0.40), gopuraCorniceMat);
          winSill.position.set(0, winY - tier.winH / 2 - 0.07, faceZ + zDir * 0.08);
          gopuraGroup.add(winSill);

          // 4 Vertical Iron Security Grill Bars
          for (let b = -1.5; b <= 1.5; b += 1) {
            const bar = new THREE.Mesh(
              new THREE.CylinderGeometry(0.025, 0.025, tier.winH - 0.06, 8),
              gopuraGrillMat
            );
            bar.position.set(b * (tier.winW * 0.22), winY, faceZ + zDir * 0.12);
            gopuraGroup.add(bar);
          }

          // Horizontal iron tie rod
          const tie = new THREE.Mesh(
            new THREE.CylinderGeometry(0.02, 0.02, tier.winW - 0.08, 8),
            gopuraGrillMat
          );
          tie.rotation.z = Math.PI / 2;
          tie.position.set(0, winY, faceZ + zDir * 0.12);
          gopuraGroup.add(tie);
        });
      } else {
        // Tiers 5, 6, 7: Blind Aedicule Niche in center
        const nicheY = tierCenterY;
        [-tier.d / 2, tier.d / 2].forEach((faceZ) => {
          const zDir = faceZ > 0 ? 1 : -1;
          const blindNiche = new THREE.Mesh(
            new THREE.BoxGeometry(tier.w * 0.22, tier.h * 0.65, 0.15),
            gopuraWindowMat
          );
          blindNiche.position.set(0, nicheY, faceZ + zDir * 0.05);
          gopuraGroup.add(blindNiche);

          const nicheFrame = new THREE.Mesh(
            new THREE.BoxGeometry(tier.w * 0.26, tier.h * 0.72, 0.12),
            gopuraCorniceMat
          );
          nicheFrame.position.set(0, nicheY, faceZ + zDir * 0.02);
          gopuraGroup.add(nicheFrame);
        });
      }

      // 6. Tier 1 Circular Sudarshana Chakra Medallion (from media_1793858207384_6c3858be.jpg)
      if (tier.hasMedallion) {
        const medalGroup = new THREE.Group();
        // Positioned directly above Tier 1 window, fully visible in front of the wall
        medalGroup.position.set(0, 9.38, tier.d / 2 + 0.32);

        // Outer vermilion rim
        const outerRim = new THREE.Mesh(
          new THREE.CylinderGeometry(0.38, 0.38, 0.08, 32),
          gopuraMedallionRimMat
        );
        outerRim.rotation.x = Math.PI / 2;
        outerRim.castShadow = true;
        medalGroup.add(outerRim);

        // Inner glowing golden Sudarshana Chakra / Tilaka disc
        const innerChakra = new THREE.Mesh(
          new THREE.CylinderGeometry(0.25, 0.25, 0.12, 32),
          goldKalashaMat
        );
        innerChakra.rotation.x = Math.PI / 2;
        innerChakra.castShadow = true;
        medalGroup.add(innerChakra);

        // Central white bindu jewel
        const bindu = new THREE.Mesh(
          new THREE.SphereGeometry(0.08, 12, 12),
          new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2 })
        );
        bindu.position.set(0, 0, 0.07);
        medalGroup.add(bindu);

        gopuraGroup.add(medalGroup);
      }
    });

    // -------------------------------------------------------------------------
    // D. Crown: Authentic Vijayanagara Sala Shikhara (Wagon-Vault Roof)
    // 100% Solid & Continuous Connection directly atop Tier 7 (ZERO floating gaps)
    // -------------------------------------------------------------------------
    // 1. Clerestory Neck Plinth (Griva) resting flush on Tier 7 (y = 18.75)
    const grivaBase = new THREE.Mesh(new THREE.BoxGeometry(5.6, 0.35, 2.8), gopuraStoneMat);
    grivaBase.position.set(0, 18.925, 0);
    grivaBase.castShadow = true;
    grivaBase.receiveShadow = true;
    gopuraGroup.add(grivaBase);

    const grivaBody = new THREE.Mesh(new THREE.BoxGeometry(5.3, 0.40, 2.5), gopuraStoneMat);
    grivaBody.position.set(0, 19.30, 0);
    grivaBody.castShadow = true;
    grivaBody.receiveShadow = true;
    gopuraGroup.add(grivaBody);

    // Miniature pilasters around Griva neck
    [-2.1, -1.26, -0.42, 0.42, 1.26, 2.1].forEach((px) => {
      [-1.26, 1.26].forEach((pz) => {
        const pil = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.38, 0.08), gopuraCorniceMat);
        pil.position.set(px, 19.30, pz);
        pil.castShadow = true;
        gopuraGroup.add(pil);
      });
    });
    [-0.7, 0, 0.7].forEach((pz) => {
      [-2.66, 2.66].forEach((px) => {
        const pil = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.38, 0.14), gopuraCorniceMat);
        pil.position.set(px, 19.30, pz);
        pil.castShadow = true;
        gopuraGroup.add(pil);
      });
    });

    // Griva Top Cornice Moulding (Uttira)
    const grivaCornice = new THREE.Mesh(new THREE.BoxGeometry(5.75, 0.16, 2.95), gopuraCorniceMat);
    grivaCornice.position.set(0, 19.58, 0);
    grivaCornice.castShadow = true;
    grivaCornice.receiveShadow = true;
    gopuraGroup.add(grivaCornice);

    // 2. Solid Wagon-Vault Base Plinth Slab
    const vaultPlinth = new THREE.Mesh(new THREE.BoxGeometry(5.50, 0.20, 2.75), gopuraStoneMat);
    vaultPlinth.position.set(0, 19.76, 0);
    vaultPlinth.castShadow = true;
    gopuraGroup.add(vaultPlinth);

    // 3. Solid Sala Shikhara Wagon Vault (Curved Barrel Roof Extrusion along X)
    const barrelLength = 5.4;
    // Strictly Counter-Clockwise (CCW) winding order for positive outward face normals
    const vaultShape = new THREE.Shape();
    vaultShape.moveTo(1.35, 0);
    vaultShape.bezierCurveTo(1.35, 0.75, 0.75, 1.25, 0, 1.25);
    vaultShape.bezierCurveTo(-0.75, 1.25, -1.35, 0.75, -1.35, 0);
    vaultShape.lineTo(1.35, 0);

    const vaultGeom = new THREE.ExtrudeGeometry(vaultShape, { depth: barrelLength, bevelEnabled: false, steps: 1 });
    vaultGeom.translate(0, 0, -barrelLength / 2);
    vaultGeom.computeVertexNormals();
    const barrelVault = new THREE.Mesh(vaultGeom, gopuraStoneMat);
    barrelVault.rotation.y = Math.PI / 2;
    barrelVault.position.set(0, 19.86, 0);
    barrelVault.castShadow = true;
    barrelVault.receiveShadow = true;
    gopuraGroup.add(barrelVault);

    // 100% Solid internal masonry core slab beneath the barrel vault (ZERO floating gaps under kalashas)
    const vaultSolidCore = new THREE.Mesh(
      new THREE.BoxGeometry(barrelLength, 1.15, 2.65),
      gopuraStoneMat
    );
    vaultSolidCore.position.set(0, 20.43, 0);
    vaultSolidCore.castShadow = true;
    vaultSolidCore.receiveShadow = true;
    gopuraGroup.add(vaultSolidCore);

    // Kapota Eave Borders on front and rear
    [-1.38, 1.38].forEach((ez) => {
      const eave = new THREE.Mesh(new THREE.BoxGeometry(barrelLength + 0.05, 0.14, 0.18), gopuraCorniceMat);
      eave.position.set(0, 19.86, ez);
      eave.castShadow = true;
      gopuraGroup.add(eave);
    });

    // 4. Transverse Rib Mouldings across the curved vault surface (Counter-Clockwise winding)
    const ribShape = new THREE.Shape();
    ribShape.moveTo(1.36, 0);
    ribShape.bezierCurveTo(1.36, 0.76, 0.76, 1.26, 0, 1.26);
    ribShape.bezierCurveTo(-0.76, 1.26, -1.36, 0.76, -1.36, 0);
    ribShape.lineTo(-1.33, 0);
    ribShape.bezierCurveTo(-1.33, 0.73, -0.73, 1.23, 0, 1.23);
    ribShape.bezierCurveTo(0.73, 1.23, 1.33, 0.73, 1.33, 0);
    ribShape.lineTo(1.36, 0);

    const ribGeom = new THREE.ExtrudeGeometry(ribShape, { depth: 0.06, bevelEnabled: false, steps: 1 });
    ribGeom.translate(0, 0, -0.03);
    ribGeom.computeVertexNormals();

    [-2.1, -1.4, -0.7, 0.7, 1.4, 2.1].forEach((rx) => {
      const ribMesh = new THREE.Mesh(ribGeom, gopuraCorniceMat);
      ribMesh.rotation.y = Math.PI / 2;
      ribMesh.position.set(rx, 19.86, 0);
      ribMesh.castShadow = true;
      gopuraGroup.add(ribMesh);
    });

    // 5. Lateral End Gable Wall Mouldings and Horn Terminals (Karnas)
    [-1, 1].forEach((dir) => {
      const ex = dir * (barrelLength / 2);

      // Solid end gable wall plate
      const endGable = new THREE.Mesh(
        new THREE.CylinderGeometry(1.35, 1.35, 0.12, 24, 1, false, 0, Math.PI),
        gopuraStoneMat
      );
      endGable.rotation.z = Math.PI / 2;
      endGable.rotation.y = dir === 1 ? Math.PI / 2 : -Math.PI / 2;
      endGable.position.set(ex, 19.86, 0);
      endGable.castShadow = true;
      gopuraGroup.add(endGable);

      // End gable arch rim moulding
      const endRim = new THREE.Mesh(ribGeom, gopuraCorniceMat);
      endRim.rotation.y = Math.PI / 2;
      endRim.position.set(ex + dir * 0.02, 19.86, 0);
      endRim.castShadow = true;
      gopuraGroup.add(endRim);

      // Central rosette medallion
      const medallion = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 0.08, 16), gopuraCorniceMat);
      medallion.rotation.z = Math.PI / 2;
      medallion.position.set(ex + dir * 0.04, 20.35, 0);
      medallion.castShadow = true;
      gopuraGroup.add(medallion);

      // Elegant upward-sweeping Horn (Karna)
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(dir * 2.65, 20.60, 0),
        new THREE.Vector3(dir * 2.85, 21.15, 0),
        new THREE.Vector3(dir * 3.08, 21.65, 0),
        new THREE.Vector3(dir * 3.00, 22.05, 0),
      ]);
      const hornGeom = new THREE.TubeGeometry(curve, 16, 0.16, 12, false);
      const horn = new THREE.Mesh(hornGeom, gopuraCorniceMat);
      horn.castShadow = true;
      gopuraGroup.add(horn);

      // Horn tip golden finial sphere
      const hornTip = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 12), goldKalashaMat);
      hornTip.position.set(dir * 3.00, 22.05, 0);
      hornTip.castShadow = true;
      gopuraGroup.add(hornTip);
    });

    // 6. Central Nasika (Kudu) Gables on Front (East) and Rear (West)
    [-1, 1].forEach((dir) => {
      const fz = dir * 1.36;

      // Plinth bracket
      const bracket = new THREE.Mesh(new THREE.BoxGeometry(1.60, 0.15, 0.32), gopuraCorniceMat);
      bracket.position.set(0, 19.88, fz);
      bracket.castShadow = true;
      gopuraGroup.add(bracket);

      // Upright jamb body
      const body = new THREE.Mesh(new THREE.BoxGeometry(1.40, 0.50, 0.26), gopuraCorniceMat);
      body.position.set(0, 20.15, fz);
      body.castShadow = true;
      gopuraGroup.add(body);

      // Horseshoe arch hood
      const nasikaShape = new THREE.Shape();
      nasikaShape.moveTo(-0.70, 0);
      nasikaShape.absarc(0, 0, 0.70, Math.PI, 0, true);
      nasikaShape.lineTo(-0.70, 0);
      const nasikaArchGeom = new THREE.ExtrudeGeometry(nasikaShape, { depth: 0.26, bevelEnabled: false, steps: 1 });
      nasikaArchGeom.translate(0, 0, -0.13);
      const nasikaMesh = new THREE.Mesh(nasikaArchGeom, gopuraCorniceMat);
      nasikaMesh.position.set(0, 20.40, fz);
      nasikaMesh.castShadow = true;
      gopuraGroup.add(nasikaMesh);

      // Inner recessed niche
      const niche = new THREE.Mesh(new THREE.BoxGeometry(0.80, 0.60, 0.10), gopuraWindowMat);
      niche.position.set(0, 20.35, fz + dir * 0.08);
      gopuraGroup.add(niche);

      // Golden Kirtimukha crest mask
      const crest = new THREE.Mesh(new THREE.SphereGeometry(0.20, 12, 12), goldKalashaMat);
      crest.position.set(0, 21.15, fz + dir * 0.10);
      crest.castShadow = true;
      gopuraGroup.add(crest);
    });

    // 7. Horizontal Ridge Cap & Exactly 7 Golden Kalasha Urn Finials
    const ridgeCap = new THREE.Mesh(new THREE.BoxGeometry(5.42, 0.10, 0.30), gopuraCorniceMat);
    ridgeCap.position.set(0, 21.11, 0);
    ridgeCap.castShadow = true;
    gopuraGroup.add(ridgeCap);

    for (let k = -3; k <= 3; k++) {
      const kx = k * 0.70;
      const kalashaGroup = new THREE.Group();
      kalashaGroup.position.set(kx, 21.16, 0);

      // Base lotus pedestal (Padmapitha)
      const padma = new THREE.Mesh(new THREE.CylinderGeometry(0.20, 0.24, 0.08, 16), goldKalashaMat);
      padma.position.y = 0.04;
      padma.castShadow = true;
      kalashaGroup.add(padma);

      // Golden water urn (Kumbha)
      const kumbha = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), goldKalashaMat);
      kumbha.position.y = 0.20;
      kumbha.castShadow = true;
      kalashaGroup.add(kumbha);

      // Moulded neck ring
      const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.14, 0.10, 16), goldKalashaMat);
      neck.position.y = 0.36;
      neck.castShadow = true;
      kalashaGroup.add(neck);

      // Flaring mouth rim
      const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.11, 0.06, 16), goldKalashaMat);
      rim.position.y = 0.44;
      rim.castShadow = true;
      kalashaGroup.add(rim);

      // Pointed conical needle finial (Shikha)
      const needle = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.55, 16), goldKalashaMat);
      needle.position.y = 0.74;
      needle.castShadow = true;
      kalashaGroup.add(needle);

      // Spire tip (Bindu)
      const tip = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), goldKalashaMat);
      tip.position.y = 1.02;
      tip.castShadow = true;
      kalashaGroup.add(tip);

      gopuraGroup.add(kalashaGroup);
    }



    // =========================================================================
    // 8. ELEPHANT GATE (#8)
    // =========================================================================
    const eleGroup = new THREE.Group();
    eleGroup.position.set(-39, 0, 16);
    worldGroup.add(eleGroup);

    const elePortal = new THREE.Mesh(new THREE.BoxGeometry(2.5, 4.2, 5.0), wallMat);
    elePortal.position.y = 2.1;
    eleGroup.add(elePortal);

    [-1.8, 1.8].forEach((z) => {
      const elephantBody = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.2, 2.2), mainTempleSoapstoneMat);
      elephantBody.position.set(-1.6, 0.8, z);
      elephantBody.castShadow = true;
      eleGroup.add(elephantBody);

      const elephantHead = new THREE.Mesh(new THREE.SphereGeometry(0.5, 12, 12), mainTempleSoapstoneMat);
      elephantHead.position.set(-0.8, 1.1, z);
      elephantHead.castShadow = true;
      eleGroup.add(elephantHead);
    });

    // =========================================================================
    // 9. GARUDA SHRINE AND DVAJA STAMBHA (#9)
    // 100% Architecturally accurate to uploaded photographs:
    // media_1793860189266_dc1c3153.jpg (Garuda statue close-up in Anjali Mudra with wings)
    // media_1793860233446_ad42d27e.jpg (Garuda at base facing main temple + segmented pillar)
    // media_1793860260242_de30e922.png (Full height pillar, bulbous base, 11 segments & 3-tiered flag cross-bars)
    // =========================================================================
    const garudaGroup = new THREE.Group();
    garudaGroup.position.set(2, 0, 18.5);
    worldGroup.add(garudaGroup);

    // -------------------------------------------------------------------------
    // A. Stepped Granite Plinth Base & Yellow Protective Railing (NO blue box)
    // -------------------------------------------------------------------------
    const plinth1 = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.24, 3.4), friezeMat);
    plinth1.position.y = 0.12;
    plinth1.castShadow = true;
    plinth1.receiveShadow = true;
    garudaGroup.add(plinth1);

    const plinth2 = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.22, 2.5), mainTempleSoapstoneMat);
    plinth2.position.y = 0.35;
    plinth2.castShadow = true;
    plinth2.receiveShadow = true;
    garudaGroup.add(plinth2);

    // Yellow Protective Courtyard Barrier Railing (clean perimeter, zero blue box)
    [-1.65, 1.65].forEach((rx) => {
      [-1.65, 1.65].forEach((rz) => {
        const post = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1.05, 8), safetyRailMat);
        post.position.set(rx, 0.55, rz);
        post.castShadow = true;
        garudaGroup.add(post);
      });
    });

    [0.42, 0.96].forEach((ry) => {
      [-1.65, 1.65].forEach((rz) => {
        const barX = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 3.3, 8), safetyRailMat);
        barX.rotation.z = Math.PI / 2;
        barX.position.set(0, ry, rz);
        garudaGroup.add(barX);
      });
      [-1.65, 1.65].forEach((rx) => {
        const barZ = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 3.3, 8), safetyRailMat);
        barZ.rotation.x = Math.PI / 2;
        barZ.position.set(rx, ry, 0);
        garudaGroup.add(barZ);
      });
    });

    // -------------------------------------------------------------------------
    // B. Gleaming Golden Lower Stack (matching Image 3: Padma-Pitha -> Kumbha -> Tilaka Cube -> Cloth Band)
    // -------------------------------------------------------------------------
    // 1. Stepped Golden Square Sub-Base & Flared Golden Lotus Bell Foot (Padma-Pitha)
    const goldSubBase = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.16, 1.75), darkBronzeMat);
    goldSubBase.position.y = 0.54;
    goldSubBase.castShadow = true;
    garudaGroup.add(goldSubBase);

    const lotusFoot = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.74, 0.52, 24), darkBronzeMat);
    lotusFoot.position.y = 0.88;
    lotusFoot.castShadow = true;
    garudaGroup.add(lotusFoot);

    const lowerCollar = new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.055, 10, 24), darkBronzeMat);
    lowerCollar.rotation.x = Math.PI / 2;
    lowerCollar.position.y = 1.12;
    garudaGroup.add(lowerCollar);

    // 2. Prominent Wide Flattened Golden Bulbous Pot (Kumbha)
    const kumbhaPot = new THREE.Mesh(new THREE.SphereGeometry(0.78, 24, 16), darkBronzeMat);
    kumbhaPot.scale.set(1.0, 0.48, 1.0);
    kumbhaPot.position.y = 1.44;
    kumbhaPot.castShadow = true;
    garudaGroup.add(kumbhaPot);

    const kumbhaWaistRing = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.46, 0.18, 20), darkBronzeMat);
    kumbhaWaistRing.position.y = 1.82;
    garudaGroup.add(kumbhaWaistRing);

    // 3. Square Golden Pedestal Box (Harmika) with Vaishnava Tilaka (Namam) Emblem
    const namamCube = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.68, 0.72), darkBronzeMat);
    namamCube.position.y = 2.24;
    namamCube.castShadow = true;
    garudaGroup.add(namamCube);

    // U-shaped Vaishnava Namam Emblem relief on all 4 faces of square golden cube
    const namamMat = new THREE.MeshStandardMaterial({ color: 0xf7e39c, roughness: 0.25, metalness: 0.7 });
    [0, Math.PI / 2, Math.PI, -Math.PI / 2].forEach((rot) => {
      const emblem = new THREE.Group();
      emblem.position.y = 2.24;
      emblem.rotation.y = rot;

      const uBottom = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.05, 0.05), namamMat);
      uBottom.position.set(0, -0.14, 0.37);
      emblem.add(uBottom);
      [-0.10, 0.10].forEach((ux) => {
        const uArm = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.28, 0.05), namamMat);
        uArm.position.set(ux, -0.02, 0.37);
        emblem.add(uArm);
      });
      const uMid = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.22, 0.05), namamMat);
      uMid.position.set(0, -0.01, 0.37);
      emblem.add(uMid);
      garudaGroup.add(emblem);
    });

    // 4. White Ceremonial Cloth Band (Vastra) tied around shaft base (clearly visible in Image 3)
    const vastraBand = new THREE.Mesh(
      new THREE.CylinderGeometry(0.325, 0.335, 0.24, 20),
      new THREE.MeshStandardMaterial({ color: 0xf3eee4, roughness: 0.88 })
    );
    vastraBand.position.y = 2.70;
    garudaGroup.add(vastraBand);

    // -------------------------------------------------------------------------
    // C. Authentic Hoysala Garuda Statue (#9) (Facing West towards Main Temple)
    // 100% Sculpturally accurate to uploaded Reference Images 1 & 2:
    // media_1794553060235_f128e51e.jpg & media_1794553071102_000eb3ba.jpg:
    // - Moulded chloritic schist pedestal (Upapitha, Padma-vari, and inscribed tablet)
    // - Sacred red hibiscus flower offering at Garuda's feet and in folded hands
    // - Open-worked Prabhavali aureole frame with carved vertical pilasters,
    //   outer Makara foliage scrolls, horseshoe Torana arch, and Kirtimukha crest
    // - Symmetrical Samabhanga stance, planted feet with detailed carved toes and Nupura anklets
    // - Muscular calves, knees, tight pleated Hoysala silk dhoti, and central hanging Katisutra sash
    // - Heavy ornate jeweled Mekhala waistband with Simha-mukha clasp and thigh festoon loops (urumaala)
    // - Long flowing Vanamala celestial garland looping gracefully down past the knees
    // - Broad athletic chest, triple-strand diagonal Yajnopavita, and multi-tier beaded necklaces
    // - Arms bent at elbows, forearms brought together with heavy Kankana wrist bangles
    // - Hands pressed together in devout Anjali Mudra prayer holding flower blossom
    // - Serene benevolent face with Vaishnava Urdhva-Pundra (white Namam & red streak)
    // - Heavy circular Makara-Kundalas touching the shoulders
    // - Magnificent fanning eagle wings (Paksha) with 5 layered, scalloped flight feathers
    // - Tall multi-tiered Hoysala Kirita-Mukuta conical crown with jeweled tiers and Stupi finial
    // -------------------------------------------------------------------------
    const garudaStatueGroup = new THREE.Group();
    garudaStatueGroup.position.set(0, 0, -1.35);
    garudaGroup.add(garudaStatueGroup);

    // Dedicated authentic Hoysala Chloritic Schist materials
    const garudaSchistMat = new THREE.MeshStandardMaterial({
      color: 0x302b27, // Dark charcoal-brown Hoysala chloritic schist / soapstone
      roughness: 0.60,
      metalness: 0.20,
    });
    const garudaCarvedMat = new THREE.MeshStandardMaterial({
      color: 0x3d3732, // Lighter carved relief contours on stone
      roughness: 0.52,
      metalness: 0.22,
    });
    const garudaDarkSchistMat = new THREE.MeshStandardMaterial({
      color: 0x1d1917, // Deep shadowed recesses
      roughness: 0.88,
    });
    const garudaFlowerMat = new THREE.MeshStandardMaterial({
      color: 0xc92222, // Sacred vermilion hibiscus flower offering (Image 2)
      roughness: 0.55,
    });
    const garudaNamamMat = new THREE.MeshStandardMaterial({
      color: 0xf5f0eb, // White sacred Gopichandana paste (Image 1 & 2)
      roughness: 0.35,
    });

    // 1. Pedestal Architecture (Adhisthana & Padma-Pitha)
    // Lower Upapitha base block
    const garudaBasePlinth = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.14, 0.86), friezeMat);
    garudaBasePlinth.position.y = 0.07;
    garudaBasePlinth.castShadow = true;
    garudaBasePlinth.receiveShadow = true;
    garudaStatueGroup.add(garudaBasePlinth);

    // Carved lotus petal band (Padma-vari)
    const garudaLotusRim = new THREE.Mesh(new THREE.BoxGeometry(1.26, 0.04, 0.90), garudaCarvedMat);
    garudaLotusRim.position.y = 0.15;
    garudaLotusRim.castShadow = true;
    garudaStatueGroup.add(garudaLotusRim);

    // Inscribed front crest panel on pedestal front face
    const garudaFrontPlaque = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.10, 0.04), garudaSchistMat);
    garudaFrontPlaque.position.set(0, 0.07, -0.44);
    garudaFrontPlaque.castShadow = true;
    garudaStatueGroup.add(garudaFrontPlaque);

    // Intermediate moulded fillet (Kumuda)
    const garudaFillet = new THREE.Mesh(new THREE.BoxGeometry(1.12, 0.06, 0.76), garudaDarkSchistMat);
    garudaFillet.position.y = 0.19;
    garudaFillet.castShadow = true;
    garudaStatueGroup.add(garudaFillet);

    // Top standing platform (Pitha slab)
    const garudaTopPlinth = new THREE.Mesh(new THREE.BoxGeometry(1.04, 0.12, 0.68), garudaSchistMat);
    garudaTopPlinth.position.y = 0.28;
    garudaTopPlinth.castShadow = true;
    garudaTopPlinth.receiveShadow = true;
    garudaStatueGroup.add(garudaTopPlinth);

    // Sacred red hibiscus flower offering at Garuda's feet (clearly seen in Image 2)
    const garudaFootFlower = new THREE.Mesh(new THREE.SphereGeometry(0.045, 8, 8), garudaFlowerMat);
    garudaFootFlower.position.set(0, 0.35, -0.06);
    garudaFootFlower.scale.set(1.4, 0.7, 1.2);
    garudaStatueGroup.add(garudaFootFlower);

    [-0.04, 0.04].forEach((fx) => {
      const petal = new THREE.Mesh(new THREE.SphereGeometry(0.022, 6, 6), garudaFlowerMat);
      petal.position.set(fx, 0.35, -0.03);
      garudaStatueGroup.add(petal);
    });

    // 2. Open-Worked Prabhavali Aureole Framework (Carved Pilasters & Torana Arch)
    // Left & Right vertical pilasters with carved arabesque creepers (Patra-lata)
    [-0.46, 0.46].forEach((px) => {
      // Main vertical pilaster upright (open space between pilaster and body!)
      const pilaster = new THREE.Mesh(new THREE.BoxGeometry(0.13, 1.36, 0.09), garudaSchistMat);
      pilaster.position.set(px, 1.02, 0.02);
      pilaster.castShadow = true;
      garudaStatueGroup.add(pilaster);

      // Carved arabesque scrollwork relief on front face
      const reliefScroll = new THREE.Mesh(new THREE.BoxGeometry(0.10, 1.32, 0.025), garudaCarvedMat);
      reliefScroll.position.set(px, 1.02, -0.03);
      garudaStatueGroup.add(reliefScroll);

      // Moulded pillar base block
      const pBase = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.10, 0.12), garudaCarvedMat);
      pBase.position.set(px, 0.39, 0.02);
      garudaStatueGroup.add(pBase);

      // Capital bracket at top of pilaster
      const pCap = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.08, 0.12), garudaCarvedMat);
      pCap.position.set(px, 1.70, 0.02);
      garudaStatueGroup.add(pCap);

      // Lower outer S-curved foliage scroll (Makara-tail tendril flanking base)
      const outerScroll = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.58, 0.06), garudaCarvedMat);
      outerScroll.position.set(px > 0 ? px + 0.08 : px - 0.08, 0.65, 0.01);
      outerScroll.rotation.z = px > 0 ? -0.18 : 0.18;
      garudaStatueGroup.add(outerScroll);

      const scrollBulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), garudaCarvedMat);
      scrollBulb.position.set(px > 0 ? px + 0.13 : px - 0.13, 0.88, 0.01);
      garudaStatueGroup.add(scrollBulb);
    });

    // Upper Semicircular Torana Arch overhead (connecting seamlessly to pilasters at px = ±0.46)
    const garudaToranaArch = new THREE.Mesh(
      new THREE.TorusGeometry(0.46, 0.065, 12, 32, Math.PI),
      garudaSchistMat
    );
    garudaToranaArch.position.set(0, 1.70, 0.02);
    garudaToranaArch.castShadow = true;
    garudaStatueGroup.add(garudaToranaArch);

    // Carved outer foliage rim band
    const garudaToranaRim = new THREE.Mesh(
      new THREE.TorusGeometry(0.51, 0.035, 10, 32, Math.PI),
      garudaCarvedMat
    );
    garudaToranaRim.position.set(0, 1.70, 0.00);
    garudaStatueGroup.add(garudaToranaRim);

    // Inner horseshoe head-halo (Sirascakra) encircling Garuda's crown (Image 1 & 2)
    const garudaInnerHalo = new THREE.Mesh(
      new THREE.TorusGeometry(0.24, 0.028, 10, 24, Math.PI),
      garudaCarvedMat
    );
    garudaInnerHalo.position.set(0, 1.76, 0.01);
    garudaStatueGroup.add(garudaInnerHalo);

    // Apex Kirtimukha crest mask at top of arch
    const archApexCrest = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.15, 0.08), garudaCarvedMat);
    archApexCrest.position.set(0, 2.22, 0.02);
    archApexCrest.castShadow = true;
    garudaStatueGroup.add(archApexCrest);

    const archApexKalasha = new THREE.Mesh(new THREE.ConeGeometry(0.055, 0.14, 8), garudaCarvedMat);
    archApexKalasha.position.set(0, 2.34, 0.02);
    garudaStatueGroup.add(archApexKalasha);

    // Thin back connecting web behind crown for structural authenticity
    const crownBacking = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.48, 0.03), garudaDarkSchistMat);
    crownBacking.position.set(0, 1.88, 0.03);
    garudaStatueGroup.add(crownBacking);

    // 3. Feet, Anklets and Lower Legs (Samabhanga Stance)
    [-0.13, 0.13].forEach((lx) => {
      // Foot planted firmly on plinth at y = 0.34
      const foot = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.06, 0.20), garudaSchistMat);
      foot.position.set(lx, 0.37, -0.05);
      foot.castShadow = true;
      garudaStatueGroup.add(foot);

      // Carved toes
      [-0.035, -0.015, 0.005, 0.025, 0.045].forEach((tx, idx) => {
        const toe = new THREE.Mesh(
          new THREE.BoxGeometry(0.018, 0.035, 0.045 - idx * 0.004),
          garudaCarvedMat
        );
        toe.position.set(lx + tx, 0.36, -0.15 - (idx === 0 ? 0.01 : 0));
        garudaStatueGroup.add(toe);
      });

      // Beaded Nupura anklet encircling ankle
      const anklet = new THREE.Mesh(new THREE.TorusGeometry(0.068, 0.018, 8, 16), garudaCarvedMat);
      anklet.rotation.x = Math.PI / 2;
      anklet.position.set(lx, 0.44, -0.05);
      garudaStatueGroup.add(anklet);

      // Lower leg (calf & shin with muscular Hoysala taper)
      const calf = new THREE.Mesh(
        new THREE.CylinderGeometry(0.075, 0.058, 0.36, 14),
        garudaSchistMat
      );
      calf.position.set(lx, 0.62, -0.05);
      calf.castShadow = true;
      garudaStatueGroup.add(calf);

      // Kneecap (Janu)
      const kneecap = new THREE.Mesh(new THREE.SphereGeometry(0.062, 10, 10), garudaSchistMat);
      kneecap.position.set(lx, 0.81, -0.04);
      kneecap.scale.set(1.0, 1.2, 0.7);
      garudaStatueGroup.add(kneecap);

      // Muscular thigh
      const thigh = new THREE.Mesh(
        new THREE.CylinderGeometry(0.095, 0.078, 0.38, 14),
        garudaSchistMat
      );
      thigh.position.set(lx, 1.00, -0.05);
      thigh.castShadow = true;
      garudaStatueGroup.add(thigh);

      // Pleated dhoti folds over thigh
      for (let df = 0; df < 3; df++) {
        const dFold = new THREE.Mesh(
          new THREE.TorusGeometry(0.096, 0.012, 6, 14, Math.PI),
          garudaCarvedMat
        );
        dFold.rotation.x = Math.PI / 2;
        dFold.position.set(lx, 0.90 + df * 0.08, -0.05);
        garudaStatueGroup.add(dFold);
      }
    });

    // Central pleated vertical dhoti sash (Katisutra) hanging between legs
    const centerSash = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.38, 0.045), garudaCarvedMat);
    centerSash.position.set(0, 0.96, -0.08);
    centerSash.castShadow = true;
    garudaStatueGroup.add(centerSash);

    // 4. Waist, Elaborate Jeweled Mekhala Belt & Hanging Vanamala Garland
    // Mekhala waistband with Simha-mukha buckle
    const mekhalaBelt = new THREE.Mesh(
      new THREE.CylinderGeometry(0.185, 0.195, 0.11, 16),
      garudaCarvedMat
    );
    mekhalaBelt.position.set(0, 1.18, -0.05);
    mekhalaBelt.scale.set(1.15, 1.0, 0.85);
    mekhalaBelt.castShadow = true;
    garudaStatueGroup.add(mekhalaBelt);

    // Central Simha-mukha lion clasp
    const simhaClasp = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.09, 0.06), garudaCarvedMat);
    simhaClasp.position.set(0, 1.18, -0.13);
    garudaStatueGroup.add(simhaClasp);

    // Hanging U-shaped jeweled festoon loops (urumaala) draped over thighs
    [-0.10, 0.10].forEach((ux) => {
      const uLoop = new THREE.Mesh(
        new THREE.TorusGeometry(0.075, 0.014, 6, 16, Math.PI),
        garudaCarvedMat
      );
      uLoop.rotation.z = Math.PI;
      uLoop.position.set(ux, 1.14, -0.11);
      garudaStatueGroup.add(uLoop);
    });

    // Long Celestial Garland (Vanamala) looping gracefully down past knees (Image 2)
    // Left drop, bottom curve below knees, and right rise
    const vanamalaLeft = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.024, 0.58, 8), garudaCarvedMat);
    vanamalaLeft.rotation.z = 0.14;
    vanamalaLeft.position.set(-0.20, 1.08, -0.09);
    garudaStatueGroup.add(vanamalaLeft);

    const vanamalaRight = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.024, 0.58, 8), garudaCarvedMat);
    vanamalaRight.rotation.z = -0.14;
    vanamalaRight.position.set(0.20, 1.08, -0.09);
    garudaStatueGroup.add(vanamalaRight);

    const vanamalaBottom = new THREE.Mesh(
      new THREE.TorusGeometry(0.18, 0.026, 8, 20, Math.PI),
      garudaCarvedMat
    );
    vanamalaBottom.rotation.z = Math.PI;
    vanamalaBottom.position.set(0, 0.80, -0.10);
    vanamalaBottom.castShadow = true;
    garudaStatueGroup.add(vanamalaBottom);

    // 5. Torso, Sculpted Chest, Yajnopavita & Necklaces
    // Muscular torso with broad chest and narrow waist
    const torsoBody = new THREE.Mesh(
      new THREE.CylinderGeometry(0.21, 0.175, 0.36, 16),
      garudaSchistMat
    );
    torsoBody.position.set(0, 1.37, -0.05);
    torsoBody.scale.set(1.15, 1.0, 0.88);
    torsoBody.castShadow = true;
    garudaStatueGroup.add(torsoBody);

    // Sculpted pectoral contours
    [-0.09, 0.09].forEach((px) => {
      const pec = new THREE.Mesh(new THREE.SphereGeometry(0.082, 10, 10), garudaSchistMat);
      pec.position.set(px, 1.44, -0.11);
      pec.scale.set(1.1, 0.9, 0.6);
      garudaStatueGroup.add(pec);
    });

    // Diagonal Yajnopavita (Sacred Thread) from left shoulder across heart to right waist
    const yajnoThread = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.42, 6), garudaCarvedMat);
    yajnoThread.rotation.z = -0.72;
    yajnoThread.rotation.y = 0.28;
    yajnoThread.position.set(-0.04, 1.38, -0.12);
    garudaStatueGroup.add(yajnoThread);

    // Broad choker collar necklace (Graiveyaka) with beaded drop fringe
    const collarNecklace = new THREE.Mesh(
      new THREE.TorusGeometry(0.125, 0.022, 8, 16, Math.PI),
      garudaCarvedMat
    );
    collarNecklace.rotation.x = Math.PI / 2;
    collarNecklace.position.set(0, 1.54, -0.06);
    garudaStatueGroup.add(collarNecklace);

    // Longer jeweled necklace (Hara) looping over upper chest
    const chestNecklace = new THREE.Mesh(
      new THREE.TorusGeometry(0.15, 0.018, 8, 18, Math.PI),
      garudaCarvedMat
    );
    chestNecklace.rotation.x = 1.30;
    chestNecklace.position.set(0, 1.50, -0.08);
    garudaStatueGroup.add(chestNecklace);

    // 6. Arms & Hands in Anjali Mudra (Prayer Pose) with Offering Flower
    [-1, 1].forEach((dir) => {
      // Shoulder cap (deltoid)
      const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.082, 10, 10), garudaSchistMat);
      shoulder.position.set(dir * 0.25, 1.52, -0.04);
      garudaStatueGroup.add(shoulder);

      // Upper arm angled down-forward towards elbow
      const upperArm = new THREE.Mesh(
        new THREE.CylinderGeometry(0.062, 0.054, 0.26, 12),
        garudaSchistMat
      );
      upperArm.rotation.z = dir * -0.42;
      upperArm.rotation.x = 0.45;
      upperArm.position.set(dir * 0.23, 1.41, -0.10);
      upperArm.castShadow = true;
      garudaStatueGroup.add(upperArm);

      // Ornate Keyura armlet around mid-bicep
      const armlet = new THREE.Mesh(new THREE.TorusGeometry(0.065, 0.016, 6, 12), garudaCarvedMat);
      armlet.rotation.z = dir * -0.42;
      armlet.rotation.x = 0.45;
      armlet.position.set(dir * 0.23, 1.41, -0.10);
      garudaStatueGroup.add(armlet);

      // Forearm bent inward towards chest center
      const forearm = new THREE.Mesh(
        new THREE.CylinderGeometry(0.054, 0.046, 0.24, 12),
        garudaSchistMat
      );
      forearm.rotation.z = dir * 0.65;
      forearm.rotation.x = -0.55;
      forearm.position.set(dir * 0.11, 1.38, -0.17);
      forearm.castShadow = true;
      garudaStatueGroup.add(forearm);

      // Beaded wrist bracelet (Kankana)
      const wristBangle = new THREE.Mesh(new THREE.TorusGeometry(0.052, 0.014, 6, 12), garudaCarvedMat);
      wristBangle.rotation.z = dir * 0.65;
      wristBangle.rotation.x = -0.55;
      wristBangle.position.set(dir * 0.05, 1.43, -0.21);
      garudaStatueGroup.add(wristBangle);
    });

    // Joined palms and fingers pressed together in reverent Anjali Mudra
    const joinedPalms = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.12, 0.05), garudaSchistMat);
    joinedPalms.position.set(0, 1.45, -0.22);
    joinedPalms.castShadow = true;
    garudaStatueGroup.add(joinedPalms);

    const prayerFingers = new THREE.Mesh(new THREE.BoxGeometry(0.065, 0.11, 0.035), garudaCarvedMat);
    prayerFingers.position.set(0, 1.54, -0.23);
    prayerFingers.castShadow = true;
    garudaStatueGroup.add(prayerFingers);

    // Sacred flower offering held reverently between folded hands (seen in Image 2)
    const handFlower = new THREE.Mesh(new THREE.SphereGeometry(0.032, 8, 8), garudaFlowerMat);
    handFlower.position.set(0, 1.57, -0.25);
    garudaStatueGroup.add(handFlower);

    // 7. Spreading Eagle Wings (Paksha) with Multi-Tiered Scalloped Feathers (Matching Images 1 & 2)
    // Wings fan wide past the Prabhavali frame with layered coverts and primary flight quills
    [-1, 1].forEach((dir) => {
      const wingGroup = new THREE.Group();
      wingGroup.position.set(dir * 0.16, 1.44, 0.01);
      garudaStatueGroup.add(wingGroup);

      // Inner shoulder covert plates (3 overlapping rows of small feathers)
      [0.02, 0.08, 0.14].forEach((cx, cIdx) => {
        const covert = new THREE.Mesh(
          new THREE.BoxGeometry(0.12 - cIdx * 0.02, 0.18 - cIdx * 0.03, 0.035),
          garudaSchistMat
        );
        covert.rotation.z = dir * (-0.20 - cIdx * 0.15);
        covert.position.set(dir * cx, 0.04 - cIdx * 0.04, 0.01);
        wingGroup.add(covert);
      });

      // 8 sweeping layered primary and secondary flight feathers fanning outward and upward
      const featherLayers = [
        { rotZ: dir * -0.25, len: 0.32, w: 0.075, px: dir * 0.18, py: -0.12, pz: 0.01 }, // Lowest secondary
        { rotZ: dir * -0.45, len: 0.40, w: 0.080, px: dir * 0.26, py: -0.02, pz: 0.01 },
        { rotZ: dir * -0.68, len: 0.48, w: 0.082, px: dir * 0.34, py: 0.10, pz: 0.00 }, // Mid flight feather
        { rotZ: dir * -0.88, len: 0.56, w: 0.084, px: dir * 0.40, py: 0.24, pz: 0.00 }, // Sweeping wing blade
        { rotZ: dir * -1.06, len: 0.62, w: 0.080, px: dir * 0.42, py: 0.38, pz: -0.01 }, // High primary feather
        { rotZ: dir * -1.22, len: 0.58, w: 0.076, px: dir * 0.38, py: 0.50, pz: -0.02 }, // Upper wing tip
        { rotZ: dir * -1.36, len: 0.50, w: 0.070, px: dir * 0.28, py: 0.60, pz: -0.03 }, // Apex crest feather
        { rotZ: dir * -1.48, len: 0.40, w: 0.065, px: dir * 0.18, py: 0.66, pz: -0.04 }, // Inward curl feather
      ];

      featherLayers.forEach((fl) => {
        // Sculpted feather blade
        const feather = new THREE.Mesh(
          new THREE.BoxGeometry(fl.w, fl.len, 0.028),
          garudaCarvedMat
        );
        feather.rotation.z = fl.rotZ;
        feather.position.set(fl.px, fl.py, fl.pz);
        feather.castShadow = true;
        wingGroup.add(feather);

        // Raised central quill shaft along the feather blade
        const quill = new THREE.Mesh(
          new THREE.CylinderGeometry(0.008, 0.006, fl.len * 0.96, 6),
          garudaSchistMat
        );
        quill.rotation.z = fl.rotZ;
        quill.position.set(fl.px, fl.py, fl.pz - 0.016);
        wingGroup.add(quill);
      });
    });

    // 8. Head, Face, Vaishnava Tilaka & Makara-Kundala Earrings
    // Neck with ring folds (Kambu-griva)
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.092, 0.104, 0.12, 14), garudaSchistMat);
    neck.position.set(0, 1.62, -0.05);
    garudaStatueGroup.add(neck);

    // Oval head with benevolent, dignified Hoysala facial modeling
    const headFace = new THREE.Mesh(new THREE.SphereGeometry(0.125, 16, 16), garudaSchistMat);
    headFace.position.set(0, 1.74, -0.05);
    headFace.scale.set(1.0, 1.15, 0.95);
    headFace.castShadow = true;
    garudaStatueGroup.add(headFace);

    // Nose & brow with subtle aquiline eagle character
    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.032, 0.075, 8), garudaCarvedMat);
    nose.rotation.x = -1.25;
    nose.position.set(0, 1.74, -0.155);
    garudaStatueGroup.add(nose);

    // Vaishnava Urdhva-Pundra (Namam on forehead - Image 1 & 2)
    // Twin white sacred Gopichandana outer U-arms
    [-0.018, 0.018].forEach((nx) => {
      const uArm = new THREE.Mesh(new THREE.BoxGeometry(0.010, 0.055, 0.015), garudaNamamMat);
      uArm.position.set(nx, 1.82, -0.152);
      garudaStatueGroup.add(uArm);
    });
    const uBase = new THREE.Mesh(new THREE.BoxGeometry(0.038, 0.010, 0.015), garudaNamamMat);
    uBase.position.set(0, 1.79, -0.152);
    garudaStatueGroup.add(uBase);

    // Center vertical crimson vermilion streak (Sri-curna)
    const redStreak = new THREE.Mesh(new THREE.BoxGeometry(0.008, 0.060, 0.016), garudaFlowerMat);
    redStreak.position.set(0, 1.83, -0.154);
    garudaStatueGroup.add(redStreak);

    // Large circular Makara-Kundalas (earrings) resting on shoulders (Image 1 & 2)
    [-0.165, 0.165].forEach((kx) => {
      const kundala = new THREE.Mesh(new THREE.CylinderGeometry(0.054, 0.054, 0.035, 12), garudaCarvedMat);
      kundala.rotation.z = Math.PI / 2;
      kundala.position.set(kx, 1.69, -0.05);
      garudaStatueGroup.add(kundala);
    });

    // 9. Conical Hoysala Crown (Kirita-Mukuta) with Jeweled Tiers & Stupi Finial
    // Base jeweled diadem band (Pattika) encircling brow
    const crownBase = new THREE.Mesh(
      new THREE.CylinderGeometry(0.125, 0.138, 0.07, 16),
      garudaCarvedMat
    );
    crownBase.position.set(0, 1.86, -0.05);
    crownBase.castShadow = true;
    garudaStatueGroup.add(crownBase);

    // Front diadem floral crest
    const crownCrest = new THREE.Mesh(new THREE.BoxGeometry(0.075, 0.065, 0.035), garudaCarvedMat);
    crownCrest.position.set(0, 1.89, -0.12);
    garudaStatueGroup.add(crownCrest);

    // Tier 1 Octagonal carved drum
    const crownTier1 = new THREE.Mesh(
      new THREE.CylinderGeometry(0.11, 0.12, 0.09, 8),
      garudaSchistMat
    );
    crownTier1.position.set(0, 1.94, -0.05);
    crownTier1.castShadow = true;
    garudaStatueGroup.add(crownTier1);

    // Tier 2 Tapering cone with filigree ridges
    const crownTier2 = new THREE.Mesh(
      new THREE.CylinderGeometry(0.085, 0.105, 0.11, 14),
      garudaCarvedMat
    );
    crownTier2.position.set(0, 2.04, -0.05);
    crownTier2.castShadow = true;
    garudaStatueGroup.add(crownTier2);

    // Tier 3 Fluted bulbous collar (Amalaka ring)
    const crownTier3 = new THREE.Mesh(
      new THREE.TorusGeometry(0.072, 0.022, 8, 16),
      garudaSchistMat
    );
    crownTier3.rotation.x = Math.PI / 2;
    crownTier3.position.set(0, 2.11, -0.05);
    garudaStatueGroup.add(crownTier3);

    // Pointed conical Stupi finial pinnacle reaching y = 2.26
    const crownSpire = new THREE.Mesh(
      new THREE.ConeGeometry(0.048, 0.15, 12),
      garudaCarvedMat
    );
    crownSpire.position.set(0, 2.19, -0.05);
    crownSpire.castShadow = true;
    garudaStatueGroup.add(crownSpire);

    // -------------------------------------------------------------------------
    // D. 13-Segmented Burnished Gold Dvaja Stambha Shaft with Flanged Torus Rings
    // -------------------------------------------------------------------------
    const numSegments = 13;
    const shaftStartY = 2.82;
    const shaftEndY = 14.00;
    const totalShaftH = shaftEndY - shaftStartY;
    const segH = totalShaftH / numSegments;

    for (let s = 0; s < numSegments; s++) {
      const segBottom = shaftStartY + s * segH;
      const segCenter = segBottom + segH / 2;
      const tNorm = s / numSegments;
      const rBottom = 0.29 - tNorm * 0.095;
      const rTop = 0.29 - (tNorm + 1 / numSegments) * 0.095;

      const drum = new THREE.Mesh(
        new THREE.CylinderGeometry(rTop, rBottom, segH, 20),
        darkBronzeMat
      );
      drum.position.y = segCenter;
      drum.castShadow = true;
      garudaGroup.add(drum);

      const collarR = rBottom + 0.045;
      const collar = new THREE.Mesh(
        new THREE.TorusGeometry(collarR, 0.036, 10, 24),
        darkBronzeMat
      );
      collar.rotation.x = Math.PI / 2;
      collar.position.y = segBottom;
      collar.castShadow = true;
      garudaGroup.add(collar);
    }

    const topCollar = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.036, 10, 24), darkBronzeMat);
    topCollar.rotation.x = Math.PI / 2;
    topCollar.position.y = shaftEndY;
    garudaGroup.add(topCollar);

    // -------------------------------------------------------------------------
    // E. Golden Flared Crown & Projecting Temple-Side Garuda Flag Banner (No black needle)
    // -------------------------------------------------------------------------
    const bellCapital = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.19, 0.36, 20), darkBronzeMat);
    bellCapital.position.y = 14.18;
    bellCapital.castShadow = true;
    garudaGroup.add(bellCapital);

    const crownAbacus = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.10, 0.56), darkBronzeMat);
    crownAbacus.position.y = 14.40;
    garudaGroup.add(crownAbacus);

    // Compact sculpted golden Kalasha urn pinnacle at top
    const topKalasha = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 12), darkBronzeMat);
    topKalasha.position.y = 14.56;
    garudaGroup.add(topKalasha);

    const topKalashaTip = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.24, 12), darkBronzeMat);
    topKalashaTip.position.y = 14.78;
    garudaGroup.add(topKalashaTip);

    // Temple-facing perforated Golden Flag Bracket projecting West (-Z) matching top-left of Image 3
    const bannerTopBar = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, 0.72), darkBronzeMat);
    bannerTopBar.position.set(0, 14.32, -0.42);
    garudaGroup.add(bannerTopBar);

    const bannerBotBar = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, 0.62), darkBronzeMat);
    bannerBotBar.position.set(0, 13.55, -0.38);
    garudaGroup.add(bannerBotBar);

    const bannerPlate = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.74, 0.42), darkBronzeMat);
    bannerPlate.position.set(0, 13.94, -0.48);
    bannerPlate.castShadow = true;
    garudaGroup.add(bannerPlate);

    const bannerEmblem = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 0.09, 12), goldKalashaMat);
    bannerEmblem.rotation.z = Math.PI / 2;
    bannerEmblem.position.set(0, 13.94, -0.48);
    garudaGroup.add(bannerEmblem);

    // =========================================================================
    // 10. DEEPA STAMBHA (GRAVITY PILLAR) (#10)
    // Authentic South-Eastern Courtyard position (matching referral photo media_1793859702059_e0c5bfa4.jpg)
    // Free-standing in open paved courtyard with ZERO collision/overlap with temple Jagati
    // =========================================================================
    const pillarGroup = new THREE.Group();
    pillarGroup.position.set(-13, 0, 15);
    worldGroup.add(pillarGroup);

    // Multi-Tiered Stellate Base Platform (calibrated compact radius to media_1794551627037_fa2d3f60.jpg)
    const starShapeP1 = createStarShape(8, 2.2, 3.0);
    const pPlinth1 = new THREE.Mesh(
      new THREE.ExtrudeGeometry(starShapeP1, { depth: 0.35, bevelEnabled: true, bevelSize: 0.1 }),
      friezeMat
    );
    pPlinth1.rotation.x = -Math.PI / 2;
    pPlinth1.position.y = 0.35;
    pPlinth1.castShadow = true;
    pPlinth1.receiveShadow = true;
    pillarGroup.add(pPlinth1);

    const starShapeP2 = createStarShape(8, 1.7, 2.4);
    const pPlinth2 = new THREE.Mesh(
      new THREE.ExtrudeGeometry(starShapeP2, { depth: 0.35, bevelEnabled: true, bevelSize: 0.08 }),
      mainTempleSoapstoneMat
    );
    pPlinth2.rotation.x = -Math.PI / 2;
    pPlinth2.position.y = 0.70;
    pPlinth2.castShadow = true;
    pPlinth2.receiveShadow = true;
    pillarGroup.add(pPlinth2);

    // Monolithic Chloritic Granite Shaft & Base Pedestal (Color Graded to media_1794551627037_fa2d3f60.jpg)
    const pShaftBase = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.6, 1.6), gravityPillarMat);
    pShaftBase.position.y = 1.0;
    pShaftBase.castShadow = true;
    pillarGroup.add(pShaftBase);

    const pillarShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.52, 11.6, 16), gravityPillarMat);
    pillarShaft.position.y = 6.8;
    pillarShaft.castShadow = true;
    pillarGroup.add(pillarShaft);

    // Flared Bell Capital (Kalasa / Phalaka, as seen in Image 2 photo)
    const pBellCollar = new THREE.Mesh(new THREE.TorusGeometry(0.48, 0.06, 8, 16), gravityPillarMat);
    pBellCollar.rotation.x = Math.PI / 2;
    pBellCollar.position.y = 12.35;
    pillarGroup.add(pBellCollar);

    const pBell = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.38, 0.55, 16), gravityPillarMat);
    pBell.position.y = 12.65;
    pBell.castShadow = true;
    pillarGroup.add(pBell);

    // Flat square abacus capital (Phalaka slab)
    const pCap = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.40, 1.4), gravityPillarMat);
    pCap.position.y = 13.12;
    pCap.castShadow = true;
    pillarGroup.add(pCap);

    // 4 hanging stone corner bells/lanterns under the abacus capital (Image 2)
    [-0.55, 0.55].forEach((bx) => {
      [-0.55, 0.55].forEach((bz) => {
        const cornerBell = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.08, 0.22, 8), gravityPillarMat);
        cornerBell.position.set(bx, 12.82, bz);
        cornerBell.castShadow = true;
        pillarGroup.add(cornerBell);
      });
    });

    // Crowning decorative dome & stone finial at top of gravity pillar
    const pCrownDome = new THREE.Mesh(new THREE.SphereGeometry(0.38, 16, 16), gravityPillarMat);
    pCrownDome.scale.set(1.0, 0.65, 1.0);
    pCrownDome.position.y = 13.45;
    pCrownDome.castShadow = true;
    pillarGroup.add(pCrownDome);

    const pCrownFinial = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.45, 12), gravityPillarMat);
    pCrownFinial.position.y = 13.88;
    pCrownFinial.castShadow = true;
    pillarGroup.add(pCrownFinial);

    // =========================================================================
    // Shared Helper: Authentic 4-Pillar Courtyard Stone Mandapa
    // 100% Architecturally accurate to Images 1–3 (media_1794479228446_04038817.jpg):
    // stepped stone platform + coping slab + 4 entrance steps, 4 tall beveled-square
    // sandstone columns with Pushpa-Potika bracket capitals, overhanging dentil-frieze
    // Kapota cornice, recessed piered top parapet, and flat cornice cap.
    // =========================================================================
    const mandapaShaftMat = new THREE.MeshStandardMaterial({
      color: 0xb19d89, // Sunlit pale buff-ochre sandstone pillars & lintels (Image 3)
      roughness: 0.80,
      metalness: 0.10,
    });
    const mandapaTrimMat = new THREE.MeshStandardMaterial({
      color: 0x766e65, // Weathered darker grey-granite capitals, coping & eave cornice
      roughness: 0.86,
      metalness: 0.12,
    });

    const addBeveledMandapaColumn = (px: number, py: number, pz: number, parent: THREE.Group) => {
      const colGroup = new THREE.Group();
      colGroup.position.set(px, py, pz);

      const foot = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.42, 0.46), mandapaShaftMat);
      foot.position.y = 0.21;
      foot.castShadow = true;
      colGroup.add(foot);

      const shaft = new THREE.Mesh(new THREE.BoxGeometry(0.36, 2.34, 0.36), mandapaShaftMat);
      shaft.position.y = 1.59;
      shaft.castShadow = true;
      colGroup.add(shaft);

      const chamferCore = new THREE.Mesh(
        new THREE.CylinderGeometry(0.21, 0.23, 2.32, 8),
        mandapaShaftMat
      );
      chamferCore.rotation.y = Math.PI / 8;
      chamferCore.position.y = 1.59;
      colGroup.add(chamferCore);

      const neck = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.16, 0.40), mandapaTrimMat);
      neck.position.y = 2.84;
      colGroup.add(neck);

      const bracketX = new THREE.Mesh(new THREE.BoxGeometry(0.86, 0.26, 0.38), mandapaTrimMat);
      bracketX.position.y = 3.05;
      bracketX.castShadow = true;
      colGroup.add(bracketX);

      const bracketZ = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.26, 0.86), mandapaTrimMat);
      bracketZ.position.y = 3.05;
      bracketZ.castShadow = true;
      colGroup.add(bracketZ);

      parent.add(colGroup);
    };

    const addMandapaPlinthAndCrown = (
      w: number,
      d: number,
      parent: THREE.Group,
      pierXs: number[],
      pierZs: number[]
    ) => {
      // 1. Stepped Ashlar Plinth Platform (Y = 0.05 to Y = 0.72) + Overhanging Coping Deck
      const baseMasonry = new THREE.Mesh(new THREE.BoxGeometry(w, 0.50, d), mandapaShaftMat);
      baseMasonry.position.y = 0.30;
      baseMasonry.castShadow = true;
      baseMasonry.receiveShadow = true;
      parent.add(baseMasonry);

      const deckCoping = new THREE.Mesh(
        new THREE.BoxGeometry(w + 0.24, 0.18, d + 0.24),
        mandapaTrimMat
      );
      deckCoping.position.y = 0.63;
      deckCoping.castShadow = true;
      deckCoping.receiveShadow = true;
      parent.add(deckCoping);

      // 2. Ceiling Soffit, Moulded Overhanging Kapota Eave & Dentil Frieze Bosses
      const soffitDeck = new THREE.Mesh(new THREE.BoxGeometry(w - 0.2, 0.18, d - 0.2), mandapaShaftMat);
      soffitDeck.position.y = 4.24;
      soffitDeck.castShadow = true;
      parent.add(soffitDeck);

      const eaveSlab = new THREE.Mesh(
        new THREE.BoxGeometry(w + 0.38, 0.16, d + 0.38),
        mandapaTrimMat
      );
      eaveSlab.position.y = 4.35;
      eaveSlab.castShadow = true;
      parent.add(eaveSlab);

      const dentilCountX = Math.max(7, Math.round(w * 1.4));
      const dentilCountZ = Math.max(7, Math.round(d * 1.4));
      for (let i = 0; i < dentilCountX; i++) {
        const dx = (-0.44 + (i * 0.88) / Math.max(1, dentilCountX - 1)) * w;
        [-d / 2 - 0.16, d / 2 + 0.16].forEach((ez) => {
          const dBlock = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.14, 0.12), mandapaShaftMat);
          dBlock.position.set(dx, 4.28, ez);
          parent.add(dBlock);
        });
      }
      for (let i = 0; i < dentilCountZ; i++) {
        const dz = (-0.44 + (i * 0.88) / Math.max(1, dentilCountZ - 1)) * d;
        [-w / 2 - 0.16, w / 2 + 0.16].forEach((ex) => {
          const dBlock = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.14, 0.22), mandapaShaftMat);
          dBlock.position.set(ex, 4.28, dz);
          parent.add(dBlock);
        });
      }

      // 3. Recessed Piered Top Parapet Wall & Flat Cornice Cap (Y = 4.42 to 4.98)
      const parapetBody = new THREE.Mesh(
        new THREE.BoxGeometry(w - 0.18, 0.42, d - 0.18),
        mandapaShaftMat
      );
      parapetBody.position.y = 4.64;
      parapetBody.castShadow = true;
      parent.add(parapetBody);

      pierXs.forEach((rx) => {
        [-d / 2 + 0.06, d / 2 - 0.06].forEach((fz) => {
          const pier = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.42, 0.12), mandapaTrimMat);
          pier.position.set(rx, 4.64, fz);
          parent.add(pier);
        });
      });
      pierZs.forEach((rz) => {
        [-w / 2 + 0.06, w / 2 - 0.06].forEach((fx) => {
          const pier = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.42, 0.36), mandapaTrimMat);
          pier.position.set(fx, 4.64, rz);
          parent.add(pier);
        });
      });

      const parapetCap = new THREE.Mesh(
        new THREE.BoxGeometry(w + 0.06, 0.14, d + 0.06),
        mandapaTrimMat
      );
      parapetCap.position.y = 4.92;
      parapetCap.castShadow = true;
      parent.add(parapetCap);
    };

    const createAuthenticCourtyardMandapa = (
      mx: number,
      mz: number,
      w: number,
      d: number,
      rotY: number,
      hasSwingBoss: boolean
    ) => {
      const mGroup = new THREE.Group();
      mGroup.position.set(mx, 0, mz);
      mGroup.rotation.y = rotY;
      worldGroup.add(mGroup);

      addMandapaPlinthAndCrown(
        w,
        d,
        mGroup,
        [-(w / 2 - 0.22), 0, w / 2 - 0.22],
        [-(d / 2 - 0.22), 0, d / 2 - 0.22]
      );

      // 4 Granite Entrance Steps projecting cleanly on the -X access side
      for (let st = 0; st < 4; st++) {
        const sH = ((st + 1) / 4) * 0.64;
        const sX = -w / 2 - 0.82 + st * 0.24;
        const step = new THREE.Mesh(new THREE.BoxGeometry(0.28, sH, 1.95), mandapaTrimMat);
        step.position.set(sX, 0.05 + sH / 2, 0);
        step.castShadow = true;
        step.receiveShadow = true;
        mGroup.add(step);
      }

      // 4 Tall Square-Beveled Monolithic Pillars with Pushpa-Potika Bracket Capitals
      const pxOff = w / 2 - 0.52;
      const pzOff = d / 2 - 0.52;
      [-pxOff, pxOff].forEach((px) => {
        [-pzOff, pzOff].forEach((pz) => {
          addBeveledMandapaColumn(px, 0.72, pz, mGroup);
        });
      });

      // Heavy Stone Architrave Beams (Uttira) & Optional Uyyale Swing Boss
      [-pzOff, pzOff].forEach((pz) => {
        const beamX = new THREE.Mesh(new THREE.BoxGeometry(w - 0.35, 0.28, 0.40), mandapaShaftMat);
        beamX.position.set(0, 4.04, pz);
        beamX.castShadow = true;
        mGroup.add(beamX);
      });
      [-pxOff, pxOff].forEach((px) => {
        const beamZ = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.28, d - 0.35), mandapaShaftMat);
        beamZ.position.set(px, 4.04, 0);
        beamZ.castShadow = true;
        mGroup.add(beamZ);
      });

      if (hasSwingBoss) {
        const swingBoss = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.22, 0.48), mandapaTrimMat);
        swingBoss.position.set(0, 4.05, 0);
        mGroup.add(swingBoss);
      }
    };

    // =========================================================================
    // 11. VYAULE MANDAPA (SWING PAVILION) (#11)
    // =========================================================================
    createAuthenticCourtyardMandapa(-20.5, 21.0, 4.6, 4.6, 0, true);

    // =========================================================================
    // 12-17. ANCILLARY PAVILIONS, MUZRAI OFFICE, GRANARY, KALYANA MANDAPA
    // =========================================================================
    // 12. South-Eastern Pavilion (Two-storey corner stone pavilion matching right side of Image 1)
    const sePavGroup = new THREE.Group();
    sePavGroup.position.set(-9.8, 0, 26.0);
    worldGroup.add(sePavGroup);

    // 3-Tier Continuous Stepped Stone Base matching East-South Cloister
    [
      { d: 4.9, xOff: 0, zOff: -0.35, yB: 0.05, yT: 0.28 },
      { d: 4.55, xOff: 0, zOff: -0.18, yB: 0.28, yT: 0.52 },
      { d: 4.2, xOff: 0, zOff: 0.0, yB: 0.52, yT: 0.76 },
    ].forEach(({ d, zOff, yB, yT }) => {
      const step = new THREE.Mesh(new THREE.BoxGeometry(8.0, yT - yB, d), cloisterStoneMat);
      step.position.set(0, (yB + yT) / 2, zOff);
      step.receiveShadow = true;
      sePavGroup.add(step);
    });

    // Courtyard Access Steps projecting in front (-Z)
    for (let st = 0; st < 3; st++) {
      const sH = ((st + 1) / 3) * 0.72;
      const cStep = new THREE.Mesh(new THREE.BoxGeometry(2.4, sH, 0.35), mandapaTrimMat);
      cStep.position.set(-1.4, 0.05 + sH / 2, -2.95 + st * 0.28);
      cStep.castShadow = true;
      sePavGroup.add(cStep);
    }

    // Lower Veranda Gallery, Back Wall & 4 Carved Cloister Columns
    const seBackWall = new THREE.Mesh(new THREE.BoxGeometry(7.8, 2.8, 0.35), cloisterGalleryShadowMat);
    seBackWall.position.set(0, 2.15, 1.85);
    sePavGroup.add(seBackWall);

    [-3.4, -1.1, 1.1, 3.4].forEach((cx) => {
      addCloisterColumn(cx, 0.76, -1.65, 1.0, sePavGroup);
    });

    const seLowerRoof = new THREE.Mesh(new THREE.BoxGeometry(8.0, 0.28, 4.3), cloisterStoneMat);
    seLowerRoof.position.set(0, 3.64, 0);
    seLowerRoof.castShadow = true;
    sePavGroup.add(seLowerRoof);

    const seLowerEave = new THREE.Mesh(new THREE.BoxGeometry(8.1, 0.16, 0.55), cloisterEaveMat);
    seLowerEave.position.set(0, 3.52, -2.25);
    sePavGroup.add(seLowerEave);

    // Upper Second-Storey Open Stone Watch-Pavilion (visible on right skyline of Image 1)
    const seUpperFloor = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.18, 3.2), cloisterStoneMat);
    seUpperFloor.position.set(0.3, 3.86, 0.2);
    sePavGroup.add(seUpperFloor);

    const seUpperCore = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.15, 2.2), cloisterGalleryShadowMat);
    seUpperCore.position.set(0.3, 4.52, 0.2);
    sePavGroup.add(seUpperCore);

    [-1.4, 2.0].forEach((ux) => {
      [-1.1, 1.5].forEach((uz) => {
        const uPost = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1.20, 0.28), cloisterStoneMat);
        uPost.position.set(ux, 4.55, uz);
        uPost.castShadow = true;
        sePavGroup.add(uPost);
      });
    });

    const seUpperEave = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.18, 3.8), cloisterEaveMat);
    seUpperEave.position.set(0.3, 5.20, 0.2);
    seUpperEave.castShadow = true;
    sePavGroup.add(seUpperEave);

    const seUpperCap = new THREE.Mesh(new THREE.BoxGeometry(3.9, 0.18, 3.3), cloisterStoneMat);
    seUpperCap.position.set(0.3, 5.36, 0.2);
    sePavGroup.add(seUpperCap);

    // Small sculpted foreground miniature shrine on SE terrace edge (visible in Image 1)
    createHoysalaMiniatureShrine(-2.8, 0.76, -1.1, Math.PI, 0.85, sePavGroup);

    // 13. North Pavilion (#13)
    createAuthenticCourtyardMandapa(25.0, 2.0, 4.8, 4.8, Math.PI / 2, false);

    // 14. Muzrai Office (Taller flat-roofed stone historic mandapa matching center of Image 1; ZERO red cone roof)
    const muzraiGroup = new THREE.Group();
    muzraiGroup.position.set(-28, 0, 26.0);
    worldGroup.add(muzraiGroup);

    // Continuous 3-Tier Stepped Ashlar Base aligning with East-South Cloister wings
    [
      { d: 4.9, zOff: -0.35, yB: 0.05, yT: 0.28 },
      { d: 4.55, zOff: -0.18, yB: 0.28, yT: 0.52 },
      { d: 4.2, zOff: 0.0, yB: 0.52, yT: 0.76 },
    ].forEach(({ d, zOff, yB, yT }) => {
      const mStep = new THREE.Mesh(new THREE.BoxGeometry(10.4, yT - yB, d), cloisterStoneMat);
      mStep.position.set(0, (yB + yT) / 2, zOff);
      mStep.receiveShadow = true;
      muzraiGroup.add(mStep);
    });

    // Recessed Shadowed Hall & Wing Side Walls along East Rampart Wall
    const mBackChamber = new THREE.Mesh(new THREE.BoxGeometry(10.2, 3.45, 0.50), cloisterGalleryShadowMat);
    mBackChamber.position.set(0, 2.48, 1.82);
    muzraiGroup.add(mBackChamber);

    [-4.3, 4.3].forEach((wx) => {
      const mSideWing = new THREE.Mesh(new THREE.BoxGeometry(1.8, 3.45, 3.8), cloisterStoneMat);
      mSideWing.position.set(wx, 2.48, 0.15);
      mSideWing.castShadow = true;
      muzraiGroup.add(mSideWing);
    });

    // 4 Taller Carved Granite Columns supporting the Elevated Flat Stone Roof (Y = 0.76 to 4.22)
    [-4.1, -1.4, 1.4, 4.1].forEach((mx) => {
      addCloisterColumn(mx, 0.76, -1.65, 1.32, muzraiGroup);
    });

    // Heavy Stone Architrave, Overhanging Kapota Eave & Elevated Flat Parapet Roof (Y = 4.22 to 4.82)
    const mBeam = new THREE.Mesh(new THREE.BoxGeometry(10.4, 0.28, 0.50), cloisterStoneMat);
    mBeam.position.set(0, 4.22, -1.65);
    mBeam.castShadow = true;
    muzraiGroup.add(mBeam);

    const mEave = new THREE.Mesh(new THREE.BoxGeometry(10.8, 0.20, 4.85), cloisterEaveMat);
    mEave.position.set(0, 4.44, -0.15);
    mEave.castShadow = true;
    muzraiGroup.add(mEave);

    const mParapet = new THREE.Mesh(new THREE.BoxGeometry(10.3, 0.28, 4.40), cloisterStoneMat);
    mParapet.position.set(0, 4.66, -0.05);
    mParapet.castShadow = true;
    muzraiGroup.add(mParapet);

    // 15. Granary (upgraded to Image 1 stepped plinth, beveled colonnade & piered Kapota crown)
    const granaryGroup = new THREE.Group();
    granaryGroup.position.set(33.8, 0, -26.8);
    worldGroup.add(granaryGroup);

    addMandapaPlinthAndCrown(16.0, 6.0, granaryGroup, [-7.6, -3.8, 0, 3.8, 7.6], [-2.7, 0, 2.7]);

    // Enclosed ventilated stone storage chamber set behind front veranda colonnade
    const granaryHall = new THREE.Mesh(new THREE.BoxGeometry(14.8, 3.45, 3.9), mandapaShaftMat);
    granaryHall.position.set(0, 2.44, -0.78);
    granaryHall.castShadow = true;
    granaryHall.receiveShadow = true;
    granaryGroup.add(granaryHall);

    const granaryDoorway = new THREE.Mesh(new THREE.BoxGeometry(1.55, 2.35, 0.20), shrineNicheMat);
    granaryDoorway.position.set(0, 1.90, 1.15);
    granaryGroup.add(granaryDoorway);

    // Front veranda longitudinal Uttira lintel beam & 7 beveled granite columns
    const granaryBeam = new THREE.Mesh(new THREE.BoxGeometry(14.8, 0.28, 0.40), mandapaShaftMat);
    granaryBeam.position.set(0, 4.04, 2.35);
    granaryBeam.castShadow = true;
    granaryGroup.add(granaryBeam);

    for (let c = 0; c < 7; c++) {
      addBeveledMandapaColumn(-6.75 + c * 2.25, 0.72, 2.35, granaryGroup);
    }

    // 4 Front Granite Steps descending toward courtyard (+Z)
    for (let st = 0; st < 4; st++) {
      const sH = ((st + 1) / 4) * 0.64;
      const sZ = 3.82 - st * 0.24;
      const step = new THREE.Mesh(new THREE.BoxGeometry(2.6, sH, 0.28), mandapaTrimMat);
      step.position.set(0, 0.05 + sH / 2, sZ);
      step.castShadow = true;
      step.receiveShadow = true;
      granaryGroup.add(step);
    }

    // 16. Kalyana Mandapa (upgraded to Image 1 stepped plinth, 16 beveled pillars & piered Kapota crown)
    const kalyanaGroup = new THREE.Group();
    kalyanaGroup.position.set(-30.5, 0, -19);
    worldGroup.add(kalyanaGroup);

    addMandapaPlinthAndCrown(11.5, 13.0, kalyanaGroup, [-5.4, -1.8, 1.8, 5.4], [-6.1, -2.0, 2.0, 6.1]);

    // Central raised stepped ceremonial Vedi platform
    const vediBase = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.26, 3.8), mandapaTrimMat);
    vediBase.position.set(0, 0.85, 0);
    vediBase.receiveShadow = true;
    kalyanaGroup.add(vediBase);

    const vediTop = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.18, 3.2), mandapaShaftMat);
    vediTop.position.set(0, 1.07, 0);
    kalyanaGroup.add(vediTop);

    // 16 Tall Beveled-Square Columns with Bracket Capitals (4 x 4 hypostyle layout)
    [-4.4, -1.5, 1.5, 4.4].forEach((x) => {
      [-5.1, -1.7, 1.7, 5.1].forEach((z) => {
        addBeveledMandapaColumn(x, 0.72, z, kalyanaGroup);
      });
    });

    // Perimeter Architrave Lintels (Uttira)
    [-5.1, 5.1].forEach((pz) => {
      const bX = new THREE.Mesh(new THREE.BoxGeometry(10.8, 0.28, 0.40), mandapaShaftMat);
      bX.position.set(0, 4.04, pz);
      bX.castShadow = true;
      kalyanaGroup.add(bX);
    });
    [-4.4, 4.4].forEach((px) => {
      const bZ = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.28, 12.2), mandapaShaftMat);
      bZ.position.set(px, 4.04, 0);
      bZ.castShadow = true;
      kalyanaGroup.add(bZ);
    });

    // 4 Granite Entrance Steps on East (+Z) side facing open courtyard
    for (let st = 0; st < 4; st++) {
      const sH = ((st + 1) / 4) * 0.64;
      const sZ = 7.32 - st * 0.24;
      const step = new THREE.Mesh(new THREE.BoxGeometry(2.8, sH, 0.28), mandapaTrimMat);
      step.position.set(0, 0.05 + sH / 2, sZ);
      step.castShadow = true;
      step.receiveShadow = true;
      kalyanaGroup.add(step);
    }

    // =========================================================================
    // 17. EAST PAVILION & EAST RAMPART INNER ARCHITECTURE (#17)
    // 100% Architecturally accurate to uploaded Reference Image 1 (Panoramic Courtyard Photo)
    // and Image 2 (Top Drone View):
    // - Authentic Hoysala East Pavilion / Small Stone Shrine:
    //     * 3-tier moulded stone Adhisthana plinth (Upana, Jagati, Pattika)
    //     * Triple stone entrance steps flanked by moulded balustrades
    //     * Solid ashlar soapstone sanctum with corner pilasters and recessed niches
    //     * West-facing entrance portal with moulded dvarashakha stone frame,
    //       carved Lalatatilaka/Gajalakshmi lintel relief, and dark teak wood double door leaves
    //     * Wide sweeping curved stone Kapota eave (chhajja) with rolled drip edge and corner bracket corbels
    //     * Multi-tier stepped ashlar roof parapet with 4 corner stone finials and central ridge Kalasha
    // - North Temple Counter / Administration Office:
    //     * Directly abutting the North flank of Raya Gopura along the East Rampart wall
    //     * Weathered ashlar granite walls, raised stone plinth with 3 entrance steps
    //     * Central doorway with stone frame and recessed dark interior
    //     * Left & right pierced stone Jali diamond-lattice window screens
    //     * Moulded horizontal stone cornice eave and flat ashlar roof terrace
    //     * Strictly NO blue objects (zero modern blue boards, booths, or poles)
    // - Continuous Stepped Stone Seating Plinth / Terrace (Kakshasana):
    //     * Running along the inner face of the East Rampart wall between Raya Gopura and Kalyani
    //     * Lower foot-rest step course and upper polished seating ledge with rounded stone bullnose
    //     * L-shaped forward return projecting towards the courtyard creating a sheltered seating bay
    //     * Subtle authentic seated pilgrims in traditional attire (cream, saffron, crimson - strictly NO blue)
    // =========================================================================

    // A. 17. East Pavilion (Authentic Miniature Stone Shrine)
    const eastPavGroup = new THREE.Group();
    eastPavGroup.position.set(22.0, 0, 26.2);
    worldGroup.add(eastPavGroup);

    // 1. Adhisthana Moulded Stone Plinth Base
    const eastPlinthBase = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.22, 4.0), tankAshlarMat);
    eastPlinthBase.position.set(0, 0.11, 0);
    eastPlinthBase.castShadow = true;
    eastPlinthBase.receiveShadow = true;
    eastPavGroup.add(eastPlinthBase);

    const eastPlinthJagati = new THREE.Mesh(new THREE.BoxGeometry(4.35, 0.22, 3.75), kappePlinthMat);
    eastPlinthJagati.position.set(0, 0.33, 0);
    eastPlinthJagati.castShadow = true;
    eastPlinthJagati.receiveShadow = true;
    eastPavGroup.add(eastPlinthJagati);

    const eastPlinthPattika = new THREE.Mesh(new THREE.BoxGeometry(4.15, 0.20, 3.55), tankAshlarMat);
    eastPlinthPattika.position.set(0, 0.54, 0);
    eastPlinthPattika.castShadow = true;
    eastPlinthPattika.receiveShadow = true;
    eastPavGroup.add(eastPlinthPattika);

    // 2. Front Approach Steps (3 stone steps descending towards courtyard -Z)
    for (let st = 0; st < 3; st++) {
      const sW = 1.90 - st * 0.08;
      const sH = 0.18;
      const sD = 0.32;
      const sY = (2 - st) * sH + sH / 2;
      const sZ = -1.78 - st * sD;
      const stepMesh = new THREE.Mesh(new THREE.BoxGeometry(sW, sH, sD + 0.04), tankAshlarMat);
      stepMesh.position.set(0, sY, sZ);
      stepMesh.castShadow = true;
      stepMesh.receiveShadow = true;
      eastPavGroup.add(stepMesh);
    }

    // Stepped stone balustrades flanking the entrance steps
    [-1.05, 1.05].forEach((bx) => {
      const balustrade = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.65, 1.05), kappeStoneMat);
      balustrade.position.set(bx, 0.40, -2.15);
      balustrade.castShadow = true;
      eastPavGroup.add(balustrade);

      const balCoping = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 1.08, 10), kappeStoneMat);
      balCoping.rotation.x = Math.PI / 2;
      balCoping.position.set(bx, 0.73, -2.15);
      balCoping.castShadow = true;
      eastPavGroup.add(balCoping);
    });

    // 3. Solid Ashlar Soapstone Sanctum Walls (y = 0.64 to 2.94, height 2.30m)
    // Back wall (+Z, facing East Rampart wall)
    const eastBackWall = new THREE.Mesh(new THREE.BoxGeometry(3.90, 2.30, 0.45), kappeStoneMat);
    eastBackWall.position.set(0, 1.79, 1.55);
    eastBackWall.castShadow = true;
    eastBackWall.receiveShadow = true;
    eastPavGroup.add(eastBackWall);

    // Side walls (-X and +X)
    [-1.75, 1.75].forEach((sx) => {
      const sideWall = new THREE.Mesh(new THREE.BoxGeometry(0.45, 2.30, 3.10), kappeStoneMat);
      sideWall.position.set(sx, 1.79, 0.10);
      sideWall.castShadow = true;
      sideWall.receiveShadow = true;
      eastPavGroup.add(sideWall);

      // Recessed horizontal decorative frieze bands along side exterior
      const friezeTrim = new THREE.Mesh(new THREE.BoxGeometry(0.50, 0.15, 3.12), mainRoofEaveMat);
      friezeTrim.position.set(sx, 1.45, 0.10);
      eastPavGroup.add(friezeTrim);
    });

    // 4 Corner Pilasters (Kuta-stambhas with moulded base, octagonal shaft & bracket capital)
    [-1.80, 1.80].forEach((px) => {
      [-1.60, 1.60].forEach((pz) => {
        const pilasterBase = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.45, 0.38), kappePlinthMat);
        pilasterBase.position.set(px, 0.86, pz);
        pilasterBase.castShadow = true;
        eastPavGroup.add(pilasterBase);

        const pilasterShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 1.55, 8), kappePillarMat);
        pilasterShaft.position.set(px, 1.86, pz);
        pilasterShaft.castShadow = true;
        eastPavGroup.add(pilasterShaft);

        const pilasterCapital = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.24, 0.42), kappeStoneMat);
        pilasterCapital.position.set(px, 2.75, pz);
        pilasterCapital.castShadow = true;
        eastPavGroup.add(pilasterCapital);
      });
    });

    // 4. Front Facade & Entrance Portal (Facing Courtyard, -Z)
    // Left & Right flanking facade walls
    [-1.25, 1.25].forEach((fx) => {
      const frontWing = new THREE.Mesh(new THREE.BoxGeometry(1.25, 2.30, 0.45), kappeStoneMat);
      frontWing.position.set(fx, 1.79, -1.45);
      frontWing.castShadow = true;
      frontWing.receiveShadow = true;
      eastPavGroup.add(frontWing);

      // Engaged decorative pilasters flanking the doorway
      const portalPilaster = new THREE.Mesh(new THREE.BoxGeometry(0.22, 2.15, 0.18), kappePillarMat);
      portalPilaster.position.set(fx > 0 ? 0.65 : -0.65, 1.72, -1.70);
      portalPilaster.castShadow = true;
      eastPavGroup.add(portalPilaster);
    });

    // Moulded Dvarashakha Doorframe & Dark Recessed Interior Chamber
    const eastDoorInterior = new THREE.Mesh(new THREE.BoxGeometry(1.40, 2.05, 0.60), cloisterGalleryShadowMat);
    eastDoorInterior.position.set(0, 1.67, -1.15);
    eastPavGroup.add(eastDoorInterior);

    // Weathered Teak Double-Door Leaves
    const eastDoorLeaf = new THREE.Mesh(new THREE.BoxGeometry(1.25, 2.00, 0.10), kappeDoorMat);
    eastDoorLeaf.position.set(0, 1.65, -1.40);
    eastDoorLeaf.castShadow = true;
    eastPavGroup.add(eastDoorLeaf);

    // Door Jambs & Carved Gajalakshmi Lalatatilaka Lintel
    const eastDoorFrame = new THREE.Mesh(new THREE.BoxGeometry(1.55, 0.16, 0.35), kappeStoneMat);
    eastDoorFrame.position.set(0, 2.75, -1.60);
    eastDoorFrame.castShadow = true;
    eastPavGroup.add(eastDoorFrame);

    const eastGajalakshmiBlock = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.28, 0.24), kappePlinthMat);
    eastGajalakshmiBlock.position.set(0, 2.92, -1.68);
    eastGajalakshmiBlock.castShadow = true;
    eastPavGroup.add(eastGajalakshmiBlock);

    // 5. Overhanging Curved Hoysala Kapota Eave (Chhajja)
    // Wide sweeping stone eave overhanging by ~0.65m on all 4 sides
    const eastKapotaEave = new THREE.Mesh(new THREE.BoxGeometry(5.10, 0.26, 4.50), kappeEaveMat);
    eastKapotaEave.position.set(0, 3.07, 0.05);
    eastKapotaEave.castShadow = true;
    eastPavGroup.add(eastKapotaEave);

    const eastKapotaDrip = new THREE.Mesh(new THREE.BoxGeometry(4.80, 0.18, 4.20), kappeStoneMat);
    eastKapotaDrip.position.set(0, 3.22, 0.05);
    eastKapotaDrip.castShadow = true;
    eastPavGroup.add(eastKapotaDrip);

    // Under-eave carved corner bracket corbels
    [-2.2, 2.2].forEach((kx) => {
      [-1.9, 1.9].forEach((kz) => {
        const corbel = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.22, 0.28), mainRoofEaveMat);
        corbel.position.set(kx * 0.95, 2.92, kz * 0.95 + 0.05);
        eastPavGroup.add(corbel);
      });
    });

    // 6. Stepped Ashlar Roof Parapet & Kalasha Finials
    // Tier 1 Cornice Course
    const eastRoofTier1 = new THREE.Mesh(new THREE.BoxGeometry(3.90, 0.30, 3.30), kappeStoneMat);
    eastRoofTier1.position.set(0, 3.42, 0.05);
    eastRoofTier1.castShadow = true;
    eastRoofTier1.receiveShadow = true;
    eastPavGroup.add(eastRoofTier1);

    // Tier 2 Clerestory Griva Course
    const eastRoofTier2 = new THREE.Mesh(new THREE.BoxGeometry(3.30, 0.26, 2.70), kappeStoneMat);
    eastRoofTier2.position.set(0, 3.70, 0.05);
    eastRoofTier2.castShadow = true;
    eastRoofTier2.receiveShadow = true;
    eastPavGroup.add(eastRoofTier2);

    // Tier 3 Capping Roof Slab
    const eastRoofCrown = new THREE.Mesh(new THREE.BoxGeometry(2.70, 0.18, 2.10), kappeStoneMat);
    eastRoofCrown.position.set(0, 3.92, 0.05);
    eastRoofCrown.castShadow = true;
    eastPavGroup.add(eastRoofCrown);

    // 4 Corner Kuta Kalashas
    [-1.25, 1.25].forEach((cx) => {
      [-0.95, 0.95].forEach((cz) => {
        const kutaFinial = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.15, 0.38, 8), kappePlinthMat);
        kutaFinial.position.set(cx, 4.15, cz + 0.05);
        kutaFinial.castShadow = true;
        eastPavGroup.add(kutaFinial);
      });
    });

    // Central Stupa Ridge Kalasha Finial
    const eastCenterKalasha = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.22, 0.52, 12), kappePlinthMat);
    eastCenterKalasha.position.set(0, 4.27, 0.05);
    eastCenterKalasha.castShadow = true;
    eastPavGroup.add(eastCenterKalasha);

    const eastKalashaSpire = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.32, 10), kappeStoneMat);
    eastKalashaSpire.position.set(0, 4.60, 0.05);
    eastKalashaSpire.castShadow = true;
    eastPavGroup.add(eastKalashaSpire);


    // B. Temple Administration / Counter Building (Adjoining Raya Gopura North Flank)
    // Sits flush along East Rampart Wall North between X = 9.0 and X = 14.8 at Z = 26.85
    const eastOfficeGroup = new THREE.Group();
    eastOfficeGroup.position.set(11.9, 0, 26.85);
    worldGroup.add(eastOfficeGroup);

    // 1. Raised Stone Plinth Terrace (h = 0.44m)
    const eastOfficePlinth = new THREE.Mesh(new THREE.BoxGeometry(5.80, 0.44, 2.60), tankAshlarMat);
    eastOfficePlinth.position.set(0, 0.22, 0);
    eastOfficePlinth.castShadow = true;
    eastOfficePlinth.receiveShadow = true;
    eastOfficeGroup.add(eastOfficePlinth);

    // 3 Stone Approach Steps centered in front of the doorway (descending towards -Z)
    for (let st = 0; st < 3; st++) {
      const sW = 1.80 - st * 0.10;
      const sH = 0.14;
      const sD = 0.28;
      const sY = (2 - st) * sH + sH / 2;
      const sZ = -1.30 - st * sD;
      const oStep = new THREE.Mesh(new THREE.BoxGeometry(sW, sH, sD + 0.04), tankAshlarMat);
      oStep.position.set(0, sY, sZ);
      oStep.castShadow = true;
      oStep.receiveShadow = true;
      eastOfficeGroup.add(oStep);
    }

    // 2. Weathered Granite Ashlar Walls (y = 0.44 to 3.24, height 2.80m)
    // Back wall against East Rampart wall
    const eastOfficeBack = new THREE.Mesh(new THREE.BoxGeometry(5.75, 2.80, 0.35), cloisterStoneMat);
    eastOfficeBack.position.set(0, 1.84, 1.15);
    eastOfficeBack.castShadow = true;
    eastOfficeBack.receiveShadow = true;
    eastOfficeGroup.add(eastOfficeBack);

    // Left wall (abutting Gopura North base at X = 9.0)
    const eastOfficeSouth = new THREE.Mesh(new THREE.BoxGeometry(0.35, 2.80, 2.40), cloisterStoneMat);
    eastOfficeSouth.position.set(-2.70, 1.84, 0.05);
    eastOfficeSouth.castShadow = true;
    eastOfficeGroup.add(eastOfficeSouth);

    // Right wall (meeting the open seating bench at X = 14.8)
    const eastOfficeNorth = new THREE.Mesh(new THREE.BoxGeometry(0.35, 2.80, 2.40), cloisterStoneMat);
    eastOfficeNorth.position.set(2.70, 1.84, 0.05);
    eastOfficeNorth.castShadow = true;
    eastOfficeGroup.add(eastOfficeNorth);

    // Front Facade (West-facing into courtyard at Z = 25.65)
    // Center entrance doorway with stone frame and recessed dark interior
    const eastOfficeDoorVoid = new THREE.Mesh(new THREE.BoxGeometry(1.20, 2.10, 0.50), cloisterGalleryShadowMat);
    eastOfficeDoorVoid.position.set(0, 1.55, -0.95);
    eastOfficeGroup.add(eastOfficeDoorVoid);

    const eastOfficeDoorFrame = new THREE.Mesh(new THREE.BoxGeometry(1.44, 2.25, 0.16), cloisterStoneMat);
    eastOfficeDoorFrame.position.set(0, 1.62, -1.22);
    eastOfficeDoorFrame.castShadow = true;
    eastOfficeGroup.add(eastOfficeDoorFrame);

    const eastOfficeDoorPanel = new THREE.Mesh(new THREE.BoxGeometry(1.10, 2.05, 0.08), kappeDoorMat);
    eastOfficeDoorPanel.position.set(0, 1.52, -1.18);
    eastOfficeDoorPanel.castShadow = true;
    eastOfficeGroup.add(eastOfficeDoorPanel);

    // Left & Right Pierced Stone Jali Diamond-Lattice Window Screens
    [-1.75, 1.75].forEach((wx) => {
      // Wall pier behind/around window
      const wallLower = new THREE.Mesh(new THREE.BoxGeometry(1.60, 0.85, 0.35), cloisterStoneMat);
      wallLower.position.set(wx, 0.87, -1.15);
      wallLower.castShadow = true;
      eastOfficeGroup.add(wallLower);

      const wallUpper = new THREE.Mesh(new THREE.BoxGeometry(1.60, 0.70, 0.35), cloisterStoneMat);
      wallUpper.position.set(wx, 2.65, -1.15);
      wallUpper.castShadow = true;
      eastOfficeGroup.add(wallUpper);

      // Stone Jali lattice screen panel
      const jaliPanel = new THREE.Mesh(new THREE.BoxGeometry(1.25, 1.10, 0.14), kappeJaliMat);
      jaliPanel.position.set(wx, 1.80, -1.18);
      jaliPanel.castShadow = true;
      eastOfficeGroup.add(jaliPanel);

      // Moulded stone sill and lintel trims
      const sill = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.12, 0.22), tankAshlarMat);
      sill.position.set(wx, 1.25, -1.20);
      sill.castShadow = true;
      eastOfficeGroup.add(sill);

      const lintel = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.12, 0.22), tankAshlarMat);
      lintel.position.set(wx, 2.35, -1.20);
      lintel.castShadow = true;
      eastOfficeGroup.add(lintel);
    });

    // 3. Moulded Stone Cornice Eave & Flat Ashlar Roof
    const eastOfficeCornice = new THREE.Mesh(new THREE.BoxGeometry(6.10, 0.22, 2.85), cloisterEaveMat);
    eastOfficeCornice.position.set(0, 3.25, 0);
    eastOfficeCornice.castShadow = true;
    eastOfficeGroup.add(eastOfficeCornice);

    const eastOfficeRoofSlab = new THREE.Mesh(new THREE.BoxGeometry(5.90, 0.20, 2.65), tankAshlarMat);
    eastOfficeRoofSlab.position.set(0, 3.42, 0);
    eastOfficeRoofSlab.castShadow = true;
    eastOfficeRoofSlab.receiveShadow = true;
    eastOfficeGroup.add(eastOfficeRoofSlab);


    // C. Continuous Stepped Stone Seating Plinth / Terrace (Kakshasana)
    // Runs along the East Rampart wall North, featuring a lower foot-rest course,
    // upper sitting bench with rounded bullnose stone edge, and an L-shaped forward return.
    const eastBenchGroup = new THREE.Group();
    worldGroup.add(eastBenchGroup);

    // Section 1: Between Office (X = 14.8) and East Shrine (X = 19.8), width = 5.0m
    // Lower foot-rest step (h = 0.20m, d = 0.40m)
    const bench1Step = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.20, 0.40), tankAshlarMat);
    bench1Step.position.set(17.3, 0.10, 26.25);
    bench1Step.castShadow = true;
    bench1Step.receiveShadow = true;
    eastBenchGroup.add(bench1Step);

    // Main sitting bench plinth (h = 0.46m, d = 1.45m)
    const bench1Main = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.46, 1.45), kappePlinthMat);
    bench1Main.position.set(17.3, 0.23, 27.15);
    bench1Main.castShadow = true;
    bench1Main.receiveShadow = true;
    eastBenchGroup.add(bench1Main);

    // Rounded bullnose stone coping slab along sitting edge
    const bench1Coping = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.10, 1.55), tankAshlarMat);
    bench1Coping.position.set(17.3, 0.48, 27.15);
    bench1Coping.castShadow = true;
    bench1Coping.receiveShadow = true;
    eastBenchGroup.add(bench1Coping);

    // L-Shaped Forward Return Stone Bench (at X = 15.0, projecting from Z = 26.4 to Z = 24.8)
    // Matches the stone partition seen in Image 1 where pilgrims sit on the cross-bench
    const lReturnStep = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.20, 1.60), tankAshlarMat);
    lReturnStep.position.set(14.65, 0.10, 25.60);
    lReturnStep.castShadow = true;
    lReturnStep.receiveShadow = true;
    eastBenchGroup.add(lReturnStep);

    const lReturnMain = new THREE.Mesh(new THREE.BoxGeometry(1.10, 0.46, 1.60), kappePlinthMat);
    lReturnMain.position.set(15.30, 0.23, 25.60);
    lReturnMain.castShadow = true;
    lReturnMain.receiveShadow = true;
    eastBenchGroup.add(lReturnMain);

    const lReturnCoping = new THREE.Mesh(new THREE.BoxGeometry(1.20, 0.10, 1.70), tankAshlarMat);
    lReturnCoping.position.set(15.30, 0.48, 25.60);
    lReturnCoping.castShadow = true;
    lReturnCoping.receiveShadow = true;
    eastBenchGroup.add(lReturnCoping);

    // Upright stone end-bolster / armrest terminal on the return
    const bolsterEnd = new THREE.Mesh(new THREE.BoxGeometry(1.10, 0.35, 0.28), kappeStoneMat);
    bolsterEnd.position.set(15.30, 0.65, 24.80);
    bolsterEnd.castShadow = true;
    eastBenchGroup.add(bolsterEnd);

    // Section 2: Between East Shrine (X = 24.2) and Kalyani / Cloister (X = 28.4), width = 4.2m
    const bench2Step = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.20, 0.40), tankAshlarMat);
    bench2Step.position.set(26.3, 0.10, 26.25);
    bench2Step.castShadow = true;
    bench2Step.receiveShadow = true;
    eastBenchGroup.add(bench2Step);

    const bench2Main = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.46, 1.45), kappePlinthMat);
    bench2Main.position.set(26.3, 0.23, 27.15);
    bench2Main.castShadow = true;
    bench2Main.receiveShadow = true;
    eastBenchGroup.add(bench2Main);

    const bench2Coping = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.10, 1.55), tankAshlarMat);
    bench2Coping.position.set(26.3, 0.48, 27.15);
    bench2Coping.castShadow = true;
    bench2Coping.receiveShadow = true;
    eastBenchGroup.add(bench2Coping);

    // Subtle authentic seated pilgrims on the bench (traditional cream, saffron, crimson attire - strictly NO blue)
    const createSeatedPilgrim = (x: number, y: number, z: number, colorHex: number) => {
      const pilgrimGroup = new THREE.Group();
      pilgrimGroup.position.set(x, y, z);

      // Folded legs / seated body base
      const bodyMat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.85 });
      const seatedLegs = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.18, 0.38), bodyMat);
      seatedLegs.position.y = 0.09;
      seatedLegs.castShadow = true;
      pilgrimGroup.add(seatedLegs);

      // Torso in traditional garment
      const torso = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.42, 0.26), bodyMat);
      torso.position.y = 0.35;
      torso.castShadow = true;
      pilgrimGroup.add(torso);

      // Head
      const headMat = new THREE.MeshStandardMaterial({ color: 0x8a6245, roughness: 0.8 });
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 10), headMat);
      head.position.y = 0.65;
      head.castShadow = true;
      pilgrimGroup.add(head);

      eastBenchGroup.add(pilgrimGroup);
    };

    // Place subtle seated figures matching Image 1:
    createSeatedPilgrim(15.3, 0.53, 25.3, 0xb83838); // Pilgrim in traditional crimson on return bench
    createSeatedPilgrim(17.8, 0.53, 26.8, 0xd48b32); // Pilgrim in warm saffron along main wall bench
    createSeatedPilgrim(18.5, 0.53, 26.8, 0xdfd9ce); // Pilgrim in traditional cream/ivory along main wall bench



    // =========================================================================
    // INTERACTIVE BEACONS & RAYCASTING COLLIDERS
    // =========================================================================
    const clickables: THREE.Object3D[] = [];
    const complexBeacons: THREE.Group[] = [];
    const archBeacons: THREE.Group[] = [];

    const createBeacon = (node: BeaconNode, colorHex: number, isArch: boolean) => {
      const beaconGroup = new THREE.Group();
      beaconGroup.position.copy(node.position);

      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.48, 16, 16),
        new THREE.MeshBasicMaterial({ color: colorHex })
      );
      beaconGroup.add(sphere);

      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.65, 0.85, 24),
        new THREE.MeshBasicMaterial({ color: colorHex, side: THREE.DoubleSide, transparent: true, opacity: 0.7 })
      );
      ring.rotation.x = Math.PI / 2;
      beaconGroup.add(ring);

      const pin = new THREE.Mesh(new THREE.ConeGeometry(0.35, 0.9, 12), new THREE.MeshBasicMaterial({ color: colorHex }));
      pin.position.y = 0.9;
      pin.rotation.x = Math.PI;
      beaconGroup.add(pin);

      const hitBox = new THREE.Mesh(
        new THREE.SphereGeometry(1.6, 8, 8),
        new THREE.MeshBasicMaterial({ visible: false })
      );
      hitBox.userData = { node };
      beaconGroup.add(hitBox);
      clickables.push(hitBox);

      scene.add(beaconGroup);
      if (isArch) {
        beaconGroup.visible = activeLayer === "architecture";
        archBeacons.push(beaconGroup);
      } else {
        beaconGroup.visible = activeLayer === "complex";
        complexBeacons.push(beaconGroup);
      }
    };

    complexNodes.forEach((node) => createBeacon(node, 0xd4af37, false));
    architectureNodes.forEach((node) => createBeacon(node, 0x38bdf8, true));

    complexBeaconsRef.current = complexBeacons;
    architectureBeaconsRef.current = archBeacons;
    clickableObjectsRef.current = clickables;

    // Raycasting for Mouse Interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(clickableObjectsRef.current, false);

      if (intersects.length > 0) {
        const hitNode = intersects[0].object.userData.node as BeaconNode;
        setHoveredNode(hitNode);
        setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
        container.style.cursor = "pointer";
      } else {
        setHoveredNode(null);
        setTooltipPos(null);
        container.style.cursor = "grab";
      }
    };

    const handleClick = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(clickableObjectsRef.current, false);

      if (intersects.length > 0) {
        const hitNode = intersects[0].object.userData.node as BeaconNode;
        if (hitNode.type === "complex") {
          const matched = UNESCO_COMPLEX_STRUCTURES.find((s) => s.id === hitNode.id);
          if (matched) {
            onSelectAttraction(matched);
            focusOnNode(hitNode);
          }
        } else if (hitNode.type === "architecture") {
          const matched = TEMPLE_ARCHITECTURAL_FEATURES.find((f) => f.id === hitNode.id);
          if (matched && onSelectArchitectureFeature) {
            onSelectArchitectureFeature(matched);
            focusOnNode(hitNode);
          }
        }
      }
    };

    container.addEventListener("mousemove", handlePointerMove);
    container.addEventListener("click", handleClick);

    // Dynamic ResizeObserver guarantees 100% full-screen responsive adaptation
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect;
        if (w > 0 && h > 0 && cameraRef.current && rendererRef.current) {
          cameraRef.current.aspect = w / h;
          cameraRef.current.updateProjectionMatrix();
          rendererRef.current.setSize(w, h, false);
        }
      }
    });
    resizeObserver.observe(container);

    // Animation & Render Loop
    let clock = new THREE.Clock();
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();

      // Gentle aquatic wave motion for Vasudeva Sarovara
      if (waterTexture) {
        waterTexture.offset.x = (elapsedTime * 0.035) % 1;
        waterTexture.offset.y = (elapsedTime * 0.025) % 1;
      }

      // Smooth camera lerp transition
      if (cameraTargetRef.current.animating) {
        camera.position.lerp(cameraTargetRef.current.pos, 0.05);
        controls.target.lerp(cameraTargetRef.current.look, 0.05);
        if (
          camera.position.distanceTo(cameraTargetRef.current.pos) < 0.25 &&
          controls.target.distanceTo(cameraTargetRef.current.look) < 0.25
        ) {
          cameraTargetRef.current.animating = false;
        }
      }

      // Auto Orbit Rotation
      if (isAutoRotating && !cameraTargetRef.current.animating) {
        controls.autoRotate = true;
        controls.autoRotateSpeed = 0.85;
      } else {
        controls.autoRotate = false;
      }

      // Animate Beacon Rings & Spheres
      const pulseScale = 1 + Math.sin(elapsedTime * 3) * 0.18;
      const ringScale = 1 + (elapsedTime % 1.2) * 0.8;
      const ringOpacity = Math.max(0, 1 - (elapsedTime % 1.2));

      [...complexBeaconsRef.current, ...architectureBeaconsRef.current].forEach((bg) => {
        if (!bg.visible) return;
        const sphere = bg.children[0];
        const ring = bg.children[1] as THREE.Mesh;
        const pin = bg.children[2];

        if (sphere) sphere.scale.set(pulseScale, pulseScale, pulseScale);
        if (ring) {
          ring.scale.set(ringScale, ringScale, ringScale);
          (ring.material as THREE.MeshBasicMaterial).opacity = ringOpacity;
        }
        if (pin) pin.position.y = 0.9 + Math.sin(elapsedTime * 2.5) * 0.15;
      });

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      container.removeEventListener("mousemove", handlePointerMove);
      container.removeEventListener("click", handleClick);
      resizeObserver.disconnect();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [
    topViewPos,
    topViewLook,
    isDark,
    isAutoRotating,
    activeLayer,
    complexNodes,
    architectureNodes,
    onSelectAttraction,
    onSelectArchitectureFeature,
    focusOnNode,
  ]);

  // Lighting Mode Swapping
  const handleLightingChange = (mode: LightingPreset) => {
    setLighting(mode);
    if (!dirLightRef.current || !hemiLightRef.current || !sceneRef.current) return;

    if (mode === "droneDaylight") {
      dirLightRef.current.intensity = 2.1;
      dirLightRef.current.color.setHex(0xfff5e4);
      hemiLightRef.current.intensity = 0.85;
      sceneRef.current.background = new THREE.Color(isDark ? 0x120d0b : 0xe8eef5);
    } else if (mode === "goldenHour") {
      dirLightRef.current.intensity = 2.5;
      dirLightRef.current.color.setHex(0xffa742);
      hemiLightRef.current.intensity = 0.95;
      sceneRef.current.background = new THREE.Color(isDark ? 0x22130e : 0xf7e1c8);
    } else if (mode === "dusk") {
      dirLightRef.current.intensity = 0.6;
      dirLightRef.current.color.setHex(0x5a78a6);
      hemiLightRef.current.intensity = 0.35;
      sceneRef.current.background = new THREE.Color(0x0e111a);
    }
  };

  const handleZoom = (factor: number) => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.lerp(controlsRef.current.target, 1 - factor);
  };

  const activeNodesList = activeLayer === "complex" ? complexNodes : architectureNodes;

  return (
    <div className="relative w-full h-full select-none overflow-hidden bg-heritage-ivory dark:bg-heritage-carved-basalt">
      {/* 3D WebGL Canvas Container: 100% Full Viewport */}
      <div ref={mountRef} className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Floating Hover Tooltip */}
      {hoveredNode && tooltipPos && (
        <div
          className="absolute z-30 pointer-events-none transform -translate-x-1/2 -translate-y-full mb-3 px-3 py-1.5 rounded-lg shadow-xl backdrop-blur-md bg-heritage-deep-stone/95 text-heritage-ivory border border-heritage-gold/50 text-xs transition-all duration-75 flex flex-col items-center gap-0.5"
          style={{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }}
        >
          <span className="font-bold text-heritage-gold text-[12px] flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            {language === "kn" ? hoveredNode.nameKn : hoveredNode.nameEn}
          </span>
          {hoveredNode.categoryEn && (
            <span className="text-[10px] text-heritage-stone">
              {language === "kn" ? hoveredNode.categoryKn : hoveredNode.categoryEn}
            </span>
          )}
          <span className="text-[9px] text-emerald-400 font-mono">
            {language === "kn" ? "ಕ್ಲಿಕ್ ಮಾಡಿ ಅನ್ವೇಷಿಸಿ" : "Click to Inspect"}
          </span>
        </div>
      )}

      {/* Top Floating Control Toolbar */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-20">
        {/* Layer Selector & Camera Presets (Image 4 Top View, Image 3 Side Angle, Image 2 Front Gopura) */}
        <div className="flex flex-wrap items-center gap-1.5 pointer-events-auto">
          {onLayerChange && (
            <div className="inline-flex rounded-lg p-0.5 bg-heritage-ivory/95 dark:bg-heritage-deep-stone/95 border border-heritage-brown/15 dark:border-heritage-gold/25 shadow-sm backdrop-blur-md">
              <button
                onClick={() => onLayerChange("complex")}
                className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                  activeLayer === "complex"
                    ? "bg-heritage-gold text-heritage-brown shadow-xs"
                    : "text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>{language === "kn" ? "೧೮ ತಾಣಗಳು" : "18 Sites"}</span>
              </button>
              <button
                onClick={() => onLayerChange("architecture")}
                className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                  activeLayer === "architecture"
                    ? "bg-sky-500 text-white shadow-xs"
                    : "text-heritage-umber dark:text-heritage-stone hover:text-sky-400"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{language === "kn" ? "ವಾಸ್ತು ಅಂಗಗಳು" : "Anatomy"}</span>
              </button>
            </div>
          )}

          {/* Dedicated Camera View Angle Presets */}
          <div className="inline-flex rounded-lg p-0.5 bg-heritage-ivory/95 dark:bg-heritage-deep-stone/95 border border-heritage-brown/15 dark:border-heritage-gold/25 shadow-sm backdrop-blur-md">
            {/* Top View (Drone - Image 4) */}
            <button
              onClick={handleSetTopView}
              title={t.topViewBtn}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-bold transition-all ${
                activeCameraPreset === "top"
                  ? "bg-heritage-gold text-heritage-brown shadow-xs"
                  : "text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold"
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>{t.topViewBtn}</span>
            </button>

            {/* Side Angle (Detail - Image 3) */}
            <button
              onClick={handleSetSideAngle}
              title={t.sideAngleBtn}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-bold transition-all ${
                activeCameraPreset === "side"
                  ? "bg-amber-600 text-white shadow-xs"
                  : "text-heritage-umber dark:text-heritage-stone hover:text-amber-500"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{t.sideAngleBtn}</span>
            </button>

            {/* Front View (Elevation - Image 1) */}
            <button
              onClick={handleSetTempleFrontView}
              title={t.templeFrontBtn}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-bold transition-all ${
                activeCameraPreset === "front"
                  ? "bg-emerald-600 text-white shadow-xs"
                  : "text-heritage-umber dark:text-heritage-stone hover:text-emerald-500"
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>{t.templeFrontBtn}</span>
            </button>

            {/* Front Gopura (Image 2) */}
            <button
              onClick={handleSetGopuraView}
              title={t.frontGopuraBtn}
              className={`hidden sm:flex items-center gap-1 px-2 py-1 rounded-md text-xs font-bold transition-all ${
                activeCameraPreset === "gopura"
                  ? "bg-heritage-gold text-heritage-brown shadow-xs"
                  : "text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold"
              }`}
            >
              <span>{t.frontGopuraBtn}</span>
            </button>
          </div>
        </div>

        {/* Right Action Tools: Lighting, Orbit, Fullscreen */}
        <div className="flex items-center gap-1 pointer-events-auto bg-heritage-ivory/90 dark:bg-heritage-deep-stone/90 p-1 rounded-lg border border-heritage-brown/15 dark:border-heritage-gold/20 shadow-sm backdrop-blur-md">
          {/* Lighting Presets */}
          <button
            onClick={() => handleLightingChange("droneDaylight")}
            title="Daylight"
            className={`p-1.5 rounded-md transition-colors ${
              lighting === "droneDaylight" ? "text-amber-500 bg-amber-500/15" : "text-heritage-umber dark:text-heritage-stone"
            }`}
          >
            <Sun className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleLightingChange("goldenHour")}
            title="Golden Hour"
            className={`p-1.5 rounded-md transition-colors ${
              lighting === "goldenHour" ? "text-orange-500 bg-orange-500/15" : "text-heritage-umber dark:text-heritage-stone"
            }`}
          >
            <Sunset className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleLightingChange("dusk")}
            title="Dusk / Night"
            className={`p-1.5 rounded-md transition-colors ${
              lighting === "dusk" ? "text-indigo-400 bg-indigo-500/15" : "text-heritage-umber dark:text-heritage-stone"
            }`}
          >
            <Moon className="w-4 h-4" />
          </button>

          <div className="w-[1px] h-4 bg-heritage-brown/15 dark:bg-heritage-gold/20 mx-0.5" />

          {/* Auto Rotate */}
          <button
            onClick={() => setIsAutoRotating((prev) => !prev)}
            title={isAutoRotating ? "Pause Orbit" : "Auto Orbit 360°"}
            className={`p-1.5 rounded-md transition-colors ${
              isAutoRotating ? "text-heritage-gold bg-heritage-gold/15" : "text-heritage-umber dark:text-heritage-stone"
            }`}
          >
            {isAutoRotating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>

          <button
            onClick={handleSetTopView}
            title="Reset to Top View"
            className="p-1.5 rounded-md text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={onToggleFullscreen}
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen 3D Map"}
            className="p-1.5 rounded-md text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Quick Navigation Monument Chips at Bottom */}
      <div className="absolute bottom-3 left-3 right-16 sm:right-24 flex items-center gap-1.5 overflow-x-auto no-scrollbar pointer-events-auto z-20 pb-0.5">
        <button
          onClick={handleSetTopView}
          className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[11px] font-bold bg-heritage-ivory/95 dark:bg-heritage-deep-stone/95 text-heritage-brown dark:text-heritage-marble border border-heritage-gold/40 shadow-sm hover:border-heritage-gold transition-all"
        >
          <Compass className="w-3 h-3 text-heritage-gold" />
          <span>{language === "kn" ? "ಆಕಾಶ ನೋಟ" : "Overview"}</span>
        </button>

        {activeNodesList.map((node) => {
          const isSelected =
            activeLayer === "complex"
              ? selectedAttraction.id === node.id
              : selectedArchitectureFeature?.id === node.id;

          return (
            <button
              key={node.id}
              onClick={() => {
                if (node.type === "complex") {
                  const matched = UNESCO_COMPLEX_STRUCTURES.find((a) => a.id === node.id);
                  if (matched) onSelectAttraction(matched);
                } else if (node.type === "architecture" && onSelectArchitectureFeature) {
                  const matched = TEMPLE_ARCHITECTURAL_FEATURES.find((f) => f.id === node.id);
                  if (matched) onSelectArchitectureFeature(matched);
                }
                focusOnNode(node);
              }}
              className={`flex-shrink-0 px-2.5 py-1.5 rounded-full text-[11px] font-medium transition-all shadow-sm ${
                isSelected
                  ? activeLayer === "complex"
                    ? "bg-heritage-gold text-heritage-brown font-bold shadow-gold-glow scale-105"
                    : "bg-sky-500 text-white font-bold shadow-md scale-105"
                  : "bg-heritage-ivory/90 dark:bg-heritage-deep-stone/90 text-heritage-umber dark:text-heritage-stone border border-heritage-brown/15 dark:border-heritage-gold/20 hover:text-heritage-gold"
              }`}
            >
              {language === "kn" ? node.nameKn.split(" ")[0] : node.nameEn.split(" ")[0]}
            </button>
          );
        })}
      </div>

      {/* Floating Zoom Controls */}
      <div className="absolute bottom-12 right-3 flex flex-col gap-1 pointer-events-auto z-20">
        <button
          onClick={() => handleZoom(0.8)}
          title="Zoom In"
          className="p-2 rounded-md bg-heritage-ivory/90 dark:bg-heritage-deep-stone/90 text-heritage-brown dark:text-heritage-stone hover:text-heritage-gold border border-heritage-brown/15 dark:border-heritage-gold/20 shadow-sm"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleZoom(1.25)}
          title="Zoom Out"
          className="p-2 rounded-md bg-heritage-ivory/90 dark:bg-heritage-deep-stone/90 text-heritage-brown dark:text-heritage-stone hover:text-heritage-gold border border-heritage-brown/15 dark:border-heritage-gold/20 shadow-sm"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Helpful Hint Overlay */}
      <div className="absolute top-16 left-3 pointer-events-none z-10 hidden sm:flex items-center gap-1.5 text-[10px] text-heritage-umber/80 dark:text-heritage-stone/75 bg-heritage-ivory/80 dark:bg-heritage-deep-stone/80 px-2.5 py-0.5 rounded-full backdrop-blur-xs">
        <Info className="w-3 h-3 text-heritage-gold flex-shrink-0" />
        <span>
          {language === "kn"
            ? activeCameraPreset === "front"
              ? "ಮುಂಭಾಗದ ನೋಟ: ಮಕರತೋರಣ, ದ್ವಾರಪಾಲಕರು, ಮದನಿಕಾ ಶಿಲಾಬಾಲಿಕೆಯರು ಮತ್ತು ಮೆಟ್ಟಿಲುಗಳ ಕಿರುದೇವಾಲಯಗಳು"
              : activeCameraPreset === "side"
              ? "ಪಾರ್ಶ್ವ ನೋಟ: ನಕ್ಷತ್ರ ಜಗತಿ, ಜಾಲಂಧ್ರ ಮತ್ತು ಕಕ್ಷಾಸನ ವಿವರಗಳು"
              : "ನೈಜ ಆಕಾಶ ನೋಟ • ೩೬೦° ತಿರುಗಿಸಲು ಎಳೆಯಿರಿ"
            : activeCameraPreset === "front"
            ? "Front View: Makaratorana, Dvarapalas, Madanika brackets & staircase shrines"
            : activeCameraPreset === "side"
            ? "Side Angle: Stellate Jagati, Jali lattice & Kakshasana details"
            : "Top View: Full 18-site precinct • Drag to orbit 360°"}
        </span>
      </div>
    </div>
  );
};
