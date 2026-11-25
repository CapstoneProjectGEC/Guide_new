import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TourismMap } from "../features/map/TourismMap";

// Mock Three.js 3D WebGL Canvas for headless JSDOM environment
vi.mock("../features/map/BelurPrecinct3D", () => ({
  BelurPrecinct3D: () => <div data-testid="belur-precinct-3d">3D Precinct WebGL Canvas</div>,
}));

describe("TourismMap 3D Component", () => {
  it("renders when isOpen is true with 3D and UNESCO badges", () => {
    const onClose = vi.fn();
    const onAsk = vi.fn();

    render(
      <TourismMap
        isOpen={true}
        onClose={onClose}
        language="en"
        onAskAboutAttraction={onAsk}
      />
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("3D REAL")).toBeInTheDocument();
    expect(screen.getByText("UNESCO / INTACH")).toBeInTheDocument();
    expect(screen.getByText("Monuments & Map")).toBeInTheDocument();
    expect(screen.getByTestId("belur-precinct-3d")).toBeInTheDocument();
  });

  it("does not render when isOpen is false", () => {
    render(
      <TourismMap
        isOpen={false}
        onClose={vi.fn()}
        language="en"
        onAskAboutAttraction={vi.fn()}
      />
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders UNESCO complex sites including all 18 key architectural monuments", () => {
    render(
      <TourismMap
        isOpen={true}
        onClose={vi.fn()}
        language="en"
        onAskAboutAttraction={vi.fn()}
      />
    );

    // Verify key UNESCO monuments across the precinct
    expect(screen.getAllByText("Chennakeshava Main Temple")[0]).toBeInTheDocument();
    expect(screen.getByText("Kappe Chennigaraya Temple")).toBeInTheDocument();
    expect(screen.getByText("Vira Narayana Temple")).toBeInTheDocument();
    expect(screen.getByText("Saumyanayaki Temple")).toBeInTheDocument();
    expect(screen.getByText("Ranganayaki / Andal Temple")).toBeInTheDocument();
    expect(screen.getByText("Vasudeva Sarovara")).toBeInTheDocument();
    expect(screen.getByText("Mahadvara (Raya Gopura)")).toBeInTheDocument();
    expect(screen.getByText("Elephant Gate")).toBeInTheDocument();
    expect(screen.getByText("Garuda Shrine and Dvaja Stambha")).toBeInTheDocument();
    expect(screen.getByText("Deepa Stambha (Gravity Pillar)")).toBeInTheDocument();
    expect(screen.getByText("Vyaule Mandapa")).toBeInTheDocument();
    expect(screen.getByText("Granary")).toBeInTheDocument();
    expect(screen.getByText("Kalyana Mandapa")).toBeInTheDocument();
    expect(screen.getByText("Rampart Wall")).toBeInTheDocument();
  });

  it("switches to the Temple Architecture exploration layer and displays all 6 zones", () => {
    render(
      <TourismMap
        isOpen={true}
        onClose={vi.fn()}
        language="en"
        onAskAboutAttraction={vi.fn()}
      />
    );

    // Click the "Temple Architecture (6 Zones)" tab
    const archTab = screen.getByText("Temple Architecture (6 Zones)");
    fireEvent.click(archTab);

    // Verify all 6 architectural anatomy zones appear
    expect(screen.getAllByText(/Garbhagriha/)[0]).toBeInTheDocument();
    expect(screen.getByText(/Antarala/)).toBeInTheDocument();
    expect(screen.getByText(/Navaranga/)).toBeInTheDocument();
    expect(screen.getByText(/Dvara Mandapa/)).toBeInTheDocument();
    expect(screen.getByText(/Kakshasana/)).toBeInTheDocument();
    expect(screen.getByText(/Jagati/)).toBeInTheDocument();

    // Verify Kannada architectural names are presented in parentheses
    expect(screen.getAllByText(/ಗರ್ಭಗುಡಿ/)[0]).toBeInTheDocument();
    expect(screen.getByText(/ಅಂತರಾಳ/)).toBeInTheDocument();
    expect(screen.getByText(/ನವರಂಗ ಮಂಟಪ/)).toBeInTheDocument();
  });

  it("clicking 'Ask Guide' on complex site fires formulated prompt and closes map", () => {
    const onClose = vi.fn();
    const onAsk = vi.fn();

    render(
      <TourismMap
        isOpen={true}
        onClose={onClose}
        language="en"
        onAskAboutAttraction={onAsk}
      />
    );

    const askBtn = screen.getByText("Ask Guide About This Place");
    fireEvent.click(askBtn);

    expect(onAsk).toHaveBeenCalledWith(
      "Tell me about the Chennakeshava Main Temple at Belur."
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("clicking 'Ask Guide' on architectural zone fires formulated prompt and closes map", () => {
    const onClose = vi.fn();
    const onAsk = vi.fn();

    render(
      <TourismMap
        isOpen={true}
        onClose={onClose}
        language="en"
        onAskAboutAttraction={onAsk}
      />
    );

    // Switch to Architecture layer
    fireEvent.click(screen.getByText("Temple Architecture (6 Zones)"));

    const askBtn = screen.getByText("Ask Guide About Garbhagriha");
    fireEvent.click(askBtn);

    expect(onAsk).toHaveBeenCalledWith(
      "Explain the Garbhagriha architectural feature in the Belur Chennakeshava Temple."
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("localizes strings and monuments accurately in Kannada mode", () => {
    render(
      <TourismMap
        isOpen={true}
        onClose={vi.fn()}
        language="kn"
        onAskAboutAttraction={vi.fn()}
      />
    );

    expect(screen.getByText("ತಾಣಗಳು & ನಕ್ಷೆ")).toBeInTheDocument();
    expect(screen.getAllByText("ಚೆನ್ನಕೇಶವ ಮುಖ್ಯ ದೇವಾಲಯ")[0]).toBeInTheDocument();
    expect(screen.getByText("ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ದೇವಾಲಯ")).toBeInTheDocument();
    expect(screen.getByText("ವಾಸುದೇವ ಸರೋವರ (ಕಲ್ಯಾಣಿ)")).toBeInTheDocument();
    expect(screen.getByText("ಈ ತಾಣದ ಬಗ್ಗೆ ಮಾರ್ಗದರ್ಶಿಯನ್ನು ಕೇಳಿ")).toBeInTheDocument();
  });

  it("filters structures via search input", () => {
    render(
      <TourismMap
        isOpen={true}
        onClose={vi.fn()}
        language="en"
        onAskAboutAttraction={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText("Search 18 sites or architectural zones...");
    fireEvent.change(searchInput, { target: { value: "Granary" } });

    expect(screen.getByText("Granary")).toBeInTheDocument();
    expect(screen.queryByText("Vasudeva Sarovara")).not.toBeInTheDocument();
  });

  it("handles fullscreen expand and restore toggle", () => {
    render(
      <TourismMap
        isOpen={true}
        onClose={vi.fn()}
        language="en"
        onAskAboutAttraction={vi.fn()}
      />
    );

    // Default state is fullscreen for immersive border-to-border 3D experience
    const exitBtn = screen.getByLabelText("Exit Fullscreen");
    fireEvent.click(exitBtn);
    expect(screen.getByLabelText("Fullscreen 3D Map")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Fullscreen 3D Map"));
    expect(screen.getByLabelText("Exit Fullscreen")).toBeInTheDocument();
  });
});
