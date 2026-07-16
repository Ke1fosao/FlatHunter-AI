"use client";

import { useMemo, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  createImportantPlace,
  deleteImportantPlace,
  previewImportantPlaceGeocode
} from "@/lib/map-api";
import type { GeocodingPreview, ImportantPlace } from "@/lib/map-types";

type DraftPoint = { latitude: number; longitude: number } | null;

type ImportantPlacePanelProps = {
  profileId: string;
  places: ImportantPlace[];
  draftPoint: DraftPoint;
  onCreated: (place: ImportantPlace) => void;
  onDeleted: (placeId: string) => void;
  onClearDraft: () => void;
};

export function ImportantPlacePanel({
  profileId,
  places,
  draftPoint,
  onCreated,
  onDeleted,
  onClearDraft
}: ImportantPlacePanelProps) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [distance, setDistance] = useState("5");
  const [importance, setImportance] = useState("3");
  const [preview, setPreview] = useState<GeocodingPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const coordinatesLabel = useMemo(() => {
    if (!draftPoint) return "";
    return `${draftPoint.latitude.toFixed(5)}, ${draftPoint.longitude.toFixed(5)}`;
  }, [draftPoint]);

  async function previewAddress() {
    if (!address.trim()) {
      setMessage("Введіть адресу для перевірки.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      setPreview(await previewImportantPlaceGeocode(profileId, address.trim()));
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося знайти адресу.");
    } finally {
      setBusy(false);
    }
  }

  async function createPlace() {
    if (!name.trim()) {
      setMessage("Додайте коротку назву точки.");
      return;
    }
    const maxDistance = Number(distance);
    if (!Number.isFinite(maxDistance) || maxDistance <= 0 || maxDistance > 100) {
      setMessage("Радіус має бути від 0.1 до 100 км.");
      return;
    }
    if (!draftPoint && !address.trim()) {
      setMessage("Введіть адресу або натисніть потрібне місце на карті.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const place = await createImportantPlace(profileId, {
        name: name.trim(),
        address: draftPoint ? address.trim() || "Точка з карти" : address.trim(),
        latitude: draftPoint?.latitude,
        longitude: draftPoint?.longitude,
        max_distance_km: maxDistance,
        importance: Number(importance)
      });
      onCreated(place);
      setName("");
      setAddress("");
      setPreview(null);
      onClearDraft();
      setMessage("Важливу точку додано.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Не вдалося додати точку.");
    } finally {
      setBusy(false);
    }
  }

  async function removePlace(place: ImportantPlace) {
    if (!window.confirm(`Видалити важливу точку «${place.name}»?`)) return;
    onDeleted(place.id);
    try {
      await deleteImportantPlace(profileId, place.id);
    } catch (error) {
      onCreated(place);
      setMessage(error instanceof ApiError ? error.message : "Не вдалося видалити точку.");
    }
  }

  return (
    <section className="important-panel" aria-label="Важливі точки">
      <div className="important-panel__head">
        <div>
          <span>ВАЖЛИВІ ТОЧКИ</span>
          <h3>Робота, навчання, родина</h3>
        </div>
        <strong>{places.length}</strong>
      </div>

      <div className="important-panel__form">
        <label>
          Назва
          <input value={name} onChange={(event) => { setName(event.target.value); }} placeholder="Наприклад, Офіс" />
        </label>
        <label>
          Адреса
          <input value={address} onChange={(event) => { setAddress(event.target.value); setPreview(null); }} placeholder="Львів, вул. Наукова 7" />
        </label>
        <div className="important-panel__row">
          <label>
            Радіус, км
            <input type="number" min="0.1" max="100" step="0.1" value={distance} onChange={(event) => { setDistance(event.target.value); }} />
          </label>
          <label>
            Важливість
            <select value={importance} onChange={(event) => { setImportance(event.target.value); }}>
              <option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option>
            </select>
          </label>
        </div>
        {draftPoint && (
          <div className="important-panel__draft">
            <span>Точка з карти</span><strong>{coordinatesLabel}</strong>
            <button type="button" onClick={onClearDraft}>Скасувати</button>
          </div>
        )}
        {preview && (
          <div className="important-panel__preview">
            <span>{preview.provider.toUpperCase()} · {Math.round(preview.confidence * 100)}%</span>
            <strong>{preview.display_name}</strong>
            <small>{preview.latitude.toFixed(5)}, {preview.longitude.toFixed(5)}</small>
          </div>
        )}
        <div className="important-panel__actions">
          <button type="button" className="secondary" disabled={busy || !address.trim()} onClick={() => { void previewAddress(); }}>Перевірити адресу</button>
          <button type="button" disabled={busy} onClick={() => { void createPlace(); }}>{busy ? "Зберігаю…" : "Додати точку"}</button>
        </div>
        {message && <p className="important-panel__message" role="status">{message}</p>}
      </div>

      <div className="important-panel__list">
        {places.length === 0 && <p>Додайте точку за адресою або натисніть на карту.</p>}
        {places.map((place) => (
          <article key={place.id}>
            <div><strong>◆ {place.name}</strong><span>{place.address}</span><small>{place.max_distance_km ? `до ${place.max_distance_km} км` : "без ліміту"} · важливість {place.importance}/5</small></div>
            <button type="button" aria-label={`Видалити ${place.name}`} onClick={() => { void removePlace(place); }}>×</button>
          </article>
        ))}
      </div>
    </section>
  );
}
