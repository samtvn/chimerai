export const mockKpis = {
  purchaseValue: 48_320,
  marketValue: 71_450,
  totalBottles: 312,
  activeAlerts: 3,
  topWine: {
    name: "Lynch-Bages 2018",
    bottlesSold: 14,
  },
};

export const mockRegionBalance = [
  { region: "Burgundy", pct: 34 },
  { region: "Rhône", pct: 28 },
  { region: "Other", pct: 16 },
  { region: "Champagne", pct: 10 },
  { region: "Bordeaux", pct: 12 },
];

export const mockAlerts = [
  { id: 1, message: "Lynch-Bages 2018 — stock at 0, restock recommended", severity: "error" },
  { id: 2, message: "Bordeaux representation below 15% — cellar imbalanced", severity: "warning" },
  { id: 3, message: "Hermitage 2019 approaching peak drinking window (2026)", severity: "info" },
];

export const mockRecentActivity = [
  { id: 1, wine: "Lynch-Bages 2018", action: "sold", quantity: 1, timestamp: "2026-05-17 20:14" },
  { id: 2, wine: "Hermitage 2019", action: "sold", quantity: 2, timestamp: "2026-05-17 19:32" },
  { id: 3, wine: "Côtes du Rhône 2022", action: "restocked", quantity: 12, timestamp: "2026-05-17 14:05" },
  { id: 4, wine: "Bollinger Spéciale NV", action: "added", quantity: 6, timestamp: "2026-05-16 11:20" },
  { id: 5, wine: "Pontet-Canet 2019", action: "sold", quantity: 1, timestamp: "2026-05-16 09:47" },
];
