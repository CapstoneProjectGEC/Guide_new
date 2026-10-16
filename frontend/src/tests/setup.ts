import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock HTMLCanvasElement.getContext for AudioVisualizer
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  clearRect: vi.fn(),
  beginPath: vi.fn(),
  roundRect: vi.fn(),
  fill: vi.fn(),
  createLinearGradient: vi.fn().mockReturnValue({
    addColorStop: vi.fn(),
  }),
}) as any;

// Mock window.Audio and URL.createObjectURL
global.Audio = class {
  src: string = "";
  paused: boolean = true;
  currentTime: number = 0;
  onended: (() => void) | null = null;
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
} as any;

global.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/mock-audio-blob");
global.URL.revokeObjectURL = vi.fn();

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
