import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface Props {
  parkingLat: number;
  parkingLon: number;
  userLat?: number | null;
  userLon?: number | null;
  institutionName: string;
}

export const MapView: React.FC<Props> = ({ parkingLat, parkingLon, userLat, userLon, institutionName }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    if (!leafletMap.current) {
      leafletMap.current = L.map(mapRef.current).setView([parkingLat, parkingLon], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(leafletMap.current);
    }

    const map = leafletMap.current;
    
    // Clear existing layers
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) {
        map.removeLayer(layer);
      }
    });

    const parkingIcon = L.divIcon({
      html: '<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold border-2 border-white shadow-lg shadow-black/50">P</div>',
      className: '',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });

    L.marker([parkingLat, parkingLon], { icon: parkingIcon })
      .bindPopup(`<b>${institutionName}</b><br/>Parking Area`)
      .addTo(map);

    if (userLat && userLon) {
      const userIcon = L.divIcon({
        html: '<div class="w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow"></div>',
        className: '',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      L.marker([userLat, userLon], { icon: userIcon })
        .bindPopup('Your Location')
        .addTo(map);

      // Draw line
      L.polyline([[userLat, userLon], [parkingLat, parkingLon]], { color: 'blue', dashArray: '5, 5' }).addTo(map);

      // Fit bounds
      const bounds = L.latLngBounds([userLat, userLon], [parkingLat, parkingLon]);
      map.fitBounds(bounds, { padding: [50, 50] });
    } else {
      map.setView([parkingLat, parkingLon], 16);
    }

    return () => {
      // Cleanup if needed on unmount
    };
  }, [parkingLat, parkingLon, userLat, userLon, institutionName]);

  return <div ref={mapRef} className="w-full h-[250px] md:h-[350px] rounded-lg shadow-md z-0" />;
};
