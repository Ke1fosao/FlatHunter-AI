import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ setClusterState: vi.fn() }));

vi.mock("@/lib/cluster-api", () => ({
  setClusterState: mocks.setClusterState,
}));

import { ClusterNoteEditor } from "@/components/cluster-note-editor";

describe("ClusterNoteEditor", () => {
  beforeEach(() => {
    mocks.setClusterState.mockReset().mockResolvedValue({
      user_state: { note: "Уточнити генератор" },
    });
  });

  it("persists notes through cluster state PATCH", async () => {
    const onSaved = vi.fn();
    render(
      <ClusterNoteEditor
        clusterId="cluster-1"
        initialNote=""
        onSaved={onSaved}
      />,
    );

    fireEvent.change(screen.getByLabelText("Ваша нотатка"), {
      target: { value: "Уточнити генератор" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Зберегти нотатку" }));

    await waitFor(() => {
      expect(mocks.setClusterState).toHaveBeenCalledWith("cluster-1", {
        note: "Уточнити генератор",
      });
      expect(onSaved).toHaveBeenCalledWith("Уточнити генератор");
    });
    expect(screen.getByText("Нотатку збережено")).toBeInTheDocument();
  });

  it("shows backend failures without losing typed text", async () => {
    mocks.setClusterState.mockRejectedValue(new Error("Backend unavailable"));
    render(
      <ClusterNoteEditor clusterId="cluster-1" initialNote="Старий текст" />,
    );

    fireEvent.change(screen.getByLabelText("Ваша нотатка"), {
      target: { value: "Новий текст" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Зберегти нотатку" }));

    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
    expect(screen.getByLabelText("Ваша нотатка")).toHaveValue("Новий текст");
  });
});
