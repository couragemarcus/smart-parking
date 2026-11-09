import React from 'react';
import type { ParkingSpace } from '../types';

interface Props {
  spaces: ParkingSpace[];
  assignedSpaceId?: number | null;
  showLabels?: boolean;
  onSpaceClick?: (space: ParkingSpace) => void;
}

const getSpaceColorClass = (state: string, isAssigned: boolean) => {
  if (state === 'RESERVED' && isAssigned) return 'parking-reserved-self';
  switch (state) {
    case 'AVAILABLE': return 'parking-available';
    case 'RESERVED': return 'parking-reserved-other';
    case 'OCCUPIED': return 'parking-occupied';
    case 'OUT_OF_SERVICE': return 'parking-oos';
    default: return 'parking-available';
  }
};

export const ParkingLayout: React.FC<Props> = ({
  spaces,
  assignedSpaceId,
  showLabels = false,
  onSpaceClick,
}) => {
  const sortedSpaces = [...spaces].sort((a, b) => a.position - b.position);
  
  const renderSpace = (space: ParkingSpace) => {
    const isAssigned = space.id === assignedSpaceId;
    const shouldShowLabel = showLabels || isAssigned;
    const colorClass = getSpaceColorClass(space.state, isAssigned);
    const status = space.state === 'OCCUPIED'
      ? 'Occupied'
      : space.state === 'OUT_OF_SERVICE'
        ? 'Unavailable'
        : space.state === 'RESERVED' && isAssigned
          ? 'Reserved for you'
          : space.state === 'RESERVED'
            ? 'Unavailable'
            : 'Available';

    return (
      <div
        key={space.id}
        onClick={() => onSpaceClick?.(space)}
        role="img"
        aria-label={`Space ${space.name}, ${status}`}
        className={`parking-bay ${colorClass} ${onSpaceClick ? 'cursor-pointer' : 'cursor-default'}`}
      >
        <span className="parking-bay-label">{shouldShowLabel ? space.name : 'Bay'}</span>
        <span className="parking-bay-status">{status}</span>
      </div>
    );
  };

      return (
    <div className="parking-layout-shell" aria-label="Parking entrance, road, and L1 to L4 parking row">
      <div className="parking-schematic">
        <div className="parking-approach">
          <span className="parking-entrance">Entrance</span>
          <span className="parking-turn" aria-hidden="true">↱</span>
          <div className="parking-road"><span>Access road</span></div>
        </div>
        <div className="parking-gap" aria-hidden="true" />
        <div className="parking-row">
          {sortedSpaces.map(renderSpace)}
        </div>
      </div>
      <div className="parking-legend">
        <span><i className="legend-swatch available" />Available</span>
        <span><i className="legend-swatch reserved" />Reserved for you</span>
        <span><i className="legend-swatch occupied" />Occupied</span>
        <span><i className="legend-swatch unavailable" />Unavailable</span>
      </div>
    </div>
  );
};
