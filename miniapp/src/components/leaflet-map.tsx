"use client";

import { useEffect, useRef } from "react";
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

export function LeafletMap({ features, places, selectedId, onSelect, onMapClick }: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMapInstance | null>(null);
  const listingLayerRef = useRef<LayerGroup | null>(null);
  const placeLayerRef = useRef<LayerGroup | null>(null);
  const fittedRef = useRef(false);
  const selectRef = useRef(onSelect);
  const mapClickRef = useRef(onMapClick);

  selectRef.current = onSelect;
  mapClickRef.current = onMapClick;

  useEffect(() => {
    let cancelled = false;
    async function mountMap() {
      if (!containerRef.current || mapRef.current) return;
      const L = await import("leaflet");
      if (cancelled || !containerRef.current) return;
      const map = L.map(containerRef.current, {
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
    void mountMap();
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
      listingLayerRef.current = null;
      placeLayerRef.current = null;
      fittedRef.current = false;
    };
  }, []);

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
        marker.bindTooltip(
          `<strong>${feature.properties.title}</strong><br>${new Intl.NumberFormat("uk-UA").format(feature.properties.price_uah)} грн${score === undefined ? "" : `<br>Match ${String(score)}%`}`,
          { direction: "top", opacity: 0.96 }
        );
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
          .bindTooltip(`<strong>◆ ${place.name}</strong><br>${place.address}`, {
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

  return <div ref={containerRef} className="leaflet-map" aria-label="Карта квартир і важливих місць" />;
}
