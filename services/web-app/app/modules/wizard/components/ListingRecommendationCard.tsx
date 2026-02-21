import React, { useState } from "react";
import { MapPin, TreePine, ChevronDown } from "lucide-react";
import { cn } from "~/lib/utils";

interface ListingRecommendation {
  id: string;
  project_name: string;
  country: string;
  project_type: string;
  price_eur: number;
  reason: string;
  details?: string;
}

interface ListingRecommendationCardProps {
  listing: ListingRecommendation;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function ListingRecommendationCard({ listing, isSelected, onSelect }: ListingRecommendationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      onClick={() => onSelect(listing.id)}
      className={cn(
        "w-full text-left rounded-xl border p-4 transition-all duration-200 cursor-pointer",
        isSelected ? "border-ember bg-ember/5 shadow-sm" : "border-mist bg-white hover:border-sage/40",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h4 className="font-serif text-base font-semibold text-slate truncate">{listing.project_name}</h4>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-slate/60">
            <span className="flex items-center gap-1">
              <MapPin size={12} /> {listing.country}
            </span>
            <span className="flex items-center gap-1">
              <TreePine size={12} /> {listing.project_type}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate/70 leading-relaxed">{listing.reason}</p>
        </div>
        <div className="text-right shrink-0">
          <span className="font-mono text-lg font-semibold text-canopy">€{listing.price_eur.toFixed(2)}</span>
          <span className="block text-[10px] text-slate/50 font-mono">/ tCO₂e</span>
        </div>
      </div>

      {listing.details && (
        <div className="mt-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="flex items-center gap-1 text-xs font-medium text-canopy hover:text-sage transition-colors cursor-pointer"
          >
            Tell me more
            <ChevronDown size={12} className={cn("transition-transform", expanded && "rotate-180")} />
          </button>
          {expanded && (
            <p className="mt-2 text-xs text-slate/60 leading-relaxed">{listing.details}</p>
          )}
        </div>
      )}
    </button>
  );
}
