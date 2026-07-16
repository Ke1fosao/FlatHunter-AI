"use client";

import { useEffect, useRef, useState } from "react";
import type { LayerGroup, Map as LeafletMapInstance } from "leaflet";

import type { ImportantPlace, MapPointFeature } from "@/lib/map-types";

type MapClickPoint = { latitude: number; longitude: number };

type LeafletMapProps = {
  features: MapPointFeature[];
  places: ImportantPlace[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onMapClick: (point: MapClickPoint) => void;
};

function listingTooltip(feature: MapPointFeature): HTMLDivElement {
  const wrapper = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = feature.properties.title;
  wrapper.append(title, document.createElement("br"));
  const format = new Intl.NumberFormat("uk-UA");
  const minimum = feature.properties.price_min_uah;
  const maximum = feature.properties.price_max_uah;
  wrapper.append(
    minimum === maximum
      ? `${format.format(minimum)} грн`
      : `${format.format(minimum)}–${format.format(maximum)} грн`
  );
  const score = feature.properties.match?.score;
  if (score !== undefined) {
    wrapper.append(document.createElement("br"), `Match ${String(score)}%`);
  }
  if (feature.properties.member_count > 1) {
    wrapper.append(
      document.createElement("br"),
      `${String(feature.properties.member_count)} джерела`
    );
  }
  return wrapper;
}

function placeTooltip(place: ImportantPlace): HTMLDivElement {
  const wrapper = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = `◆ ${place.name}`;
  wrapper.append(title, document.createElement("br"), place.address);
  return wrapper;
}

export function LeafletMap({ features, places, selectedId, onSelect, onMapClick }: LeafletMapProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMapInstance | null>(null);
  const listingLayerRef = useRef<LayerGroup | null>(null);
  const placeLayerRef = useRef<LayerGroup | null>(null);
  const fittedRef = useRef(false);
  const selectRef = useRef(onSelect);
  const mapClickRef = useRef(onMapClick);

  selectRef.current = onSelect;
  mapClickRef.current = onMapClick;

  useEffect(() => {
    if (container === null) return;
    let cancelled = false;
    async function mountMap(target: HTMLDivElement) {
      const L = await import("leaflet");
      if (cancelled) return;
      const map = L.map(target, {
        center: [49.0, 31.0],
        zoom: 6,
        zoomControl: true,
        attributionControl: true,
        preferCanvas: true
      });
      L.tileLayer(
        process.env.NEXT_PUBLIC_MAP_TILES_URL ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          attribution: process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ?? "© OpenStreetMap contributors",
          maxZoom: 19
        }
      ).addTo(map);
      listingLayerRef.current = L.layerGroup().addTo(map);
      placeLayerRef.current = L.layerGroup().addTo(map);
      map.on("click", (event) => {
        mapClickRef.current({ latitude: event.latlng.lat, longitude: event.latlng.lng });
      });
      mapRef.current = map;
    }
    void mountMap(container);
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
      listingLayerRef.current = null;
      placeLayerRef.current = null;
      fittedRef.current = false;
    };
  }, [container]);

  useEffect(() => {
    let cancelled = false;
    async function renderLayers() {
      const map = mapRef.current;
      const listingLayer = listingLayerRef.current;
      const placeLayer = placeLayerRef.current;
      if (!map || !listingLayer || !placeLayer) {
        window.setTimeout(() => {
          if (!cancelled) void renderLayers();
        }, 80);
        return;
      }
      const L = await import("leaflet");
      if (cancelled) return;
      listingLayer.clearLayers();
      placeLayer.clearLayers();
      const bounds: [number, number][] = [];
      features.forEach((feature) => {
        const [longitude, latitude] = feature.geometry.coordinates;
        bounds.push([latitude, longitude]);
        const score = feature.properties.match?.score;
        const marker = L.circleMarker([latitude, longitude], {
          radius: feature.id === selectedId ? 12 : 9,
          weight: feature.id === selectedId ? 4 : 2,
          color: feature.properties.user_state.is_favorite ? "#f3b61f" : "#2b6f4d",
          fillColor: score !== undefined && score >= 80 ? "#3bb273" : "#f4f7f3",
          fillOpacity: 0.96
        });
        marker.bindTooltip(listingTooltip(feature), { direction: "top", opacity: 0.96 });
        marker.on("click", () => {
          selectRef.current(feature.id);
        });
        marker.addTo(listingLayer);
      });
      places.forEach((place) => {
        if (place.latitude === null || place.longitude === null) return;
        const latitude = Number(place.latitude);
        const longitude = Number(place.longitude);
        bounds.push([latitude, longitude]);
        L.circleMarker([latitude, longitude], {
          radius: 8 + place.importance,
          weight: 3,
          color: "#6c4dd8",
          fillColor: "#d9d0ff",
          fillOpacity: 1
        })
          .bindTooltip(placeTooltip(place), {
            direction: "top",
            opacity: 0.96
          })
          .addTo(placeLayer);
      });
      if (!fittedRef.current && bounds.length > 0) {
        map.fitBounds(bounds, { padding: [32, 32], maxZoom: 14 });
        fittedRef.current = true;
      }
    }
    void renderLayers();
    return () => {
      cancelled = true;
    };
  }, [features, places, selectedId]);

  return <div ref={setContainer} className="leaflet-map" aria-label="Карта квартир і важливих місць" />;
}
