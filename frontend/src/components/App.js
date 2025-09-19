import React from "react";
import ChartPanel from "./components/ChartPanel";
import ICTPanel from "./components/ICTPanel";
import TradeLog from "./components/TradeLog";

export default function App() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: 12, background: "#071019", minHeight: "100vh", color: "#cfeeea" }}>
      <h1 style={{ color: "#5fd3c9" }}>AstroQuant — ICT Trading Model</h1>

      <div style={{ display: "flex", gap: 12, flex: 1 }}>
        <div style={{ flex: 2, background: "#0b1b25", borderRadius: 8, padding: 8, display: "flex" }}>
          <ChartPanel id="ict" symbol="AAPL" mode="ict" />
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          <ICTPanel symbol="AAPL" />
          <TradeLog symbol="AAPL" />
        </div>
      </div>
    </div>
  );
}
