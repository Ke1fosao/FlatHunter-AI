import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createImportantPlace, previewImportantPlaceGeocode, deleteImportantPlace } = vi.hoisted(
  () => ({
    createImportantPlace: vi.fn(),
    previewImportantPlaceGeocode: vi.fn(),
    deleteImportantPlace: vi.fn()
  })
);

vi.mock("@/lib/map-api", () => ({
  createImportantPlace,
  previewImportantPlaceGeocode,
  deleteImportantPlace
}));

import { ImportantPlacePanel } from "@/components/important-place-panel";

const createdPlace = {
  id: "place-1",
  name: "Офіс",
  address: "Львів, вул. Наукова 7",
  latitude: "49.812300",
  longitude: "24.012300",
  geocoding_provider: "demo",
  geocoding_confidence: "0.960",
  max_distance_km: "5.00",
  max_walk_minutes: null,
  max_drive_minutes: null,
  max_transit_minutes: null,
  importance: 4,
  created_at: "2026-07-16T12:00:00Z"
};

describe("ImportantPlacePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("validates that a point has a name", () => {
    render(
      <ImportantPlacePanel
        profileId="profile-1"
        places={[]}
        draftPoint={{ latitude: 49.8, longitude: 24.0 }}
        onCreated={vi.fn()}
        onDeleted={vi.fn()}
        onClearDraft={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Додати точку" }));

    expect(screen.getByRole("status")).toHaveTextContent("Додайте коротку назву точки");
    expect(createImportantPlace).not.toHaveBeenCalled();
  });

  it("previews and creates an address-based important place", async () => {
    previewImportantPlaceGeocode.mockResolvedValue({
      latitude: 49.8123,
      longitude: 24.0123,
      display_name: "Львів, вул. Наукова 7, UA",
      provider: "demo",
      confidence: 0.96,
      country_code: "UA"
    });
    createImportantPlace.mockResolvedValue(createdPlace);
    const onCreated = vi.fn();

    render(
      <ImportantPlacePanel
        profileId="profile-1"
        places={[]}
        draftPoint={null}
        onCreated={onCreated}
        onDeleted={vi.fn()}
        onClearDraft={vi.fn()}
      />
    );

    fireEvent.change(screen.getByLabelText("Назва"), { target: { value: "Офіс" } });
    fireEvent.change(screen.getByLabelText("Адреса"), {
      target: { value: "вул. Наукова 7" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Перевірити адресу" }));

    await waitFor(() => {
      expect(screen.getByText("Львів, вул. Наукова 7, UA")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Додати точку" }));

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(createdPlace);
    });
    expect(createImportantPlace).toHaveBeenCalledWith(
      "profile-1",
      expect.objectContaining({ name: "Офіс", address: "вул. Наукова 7" })
    );
  });
});
