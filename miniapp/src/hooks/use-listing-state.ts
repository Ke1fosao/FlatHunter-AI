"use client";

import { useCallback, useState } from "react";

import {
  ApiError,
  setListingState,
  type ListingFeedItem,
} from "@/lib/api";

export type ListingStateAction = "favorite" | "hide" | "compare";

export function useListingState() {
  const [pendingId, setPendingId] = useState("");
  const [error, setError] = useState("");

  const updateListingState = useCallback(
    async (
      listing: ListingFeedItem,
      action: ListingStateAction,
      value: boolean,
      onUpdated: (listing: ListingFeedItem) => void,
    ) => {
      setPendingId(listing.id);
      setError("");
      try {
        const updated = await setListingState(listing.id, action, value);
        onUpdated(updated);
        return updated;
      } catch (reason) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Не вдалося зберегти дію.",
        );
        return null;
      } finally {
        setPendingId("");
      }
    },
    [],
  );

  return {
    pendingId,
    error,
    clearError: () => {
      setError("");
    },
    updateListingState,
  };
}
