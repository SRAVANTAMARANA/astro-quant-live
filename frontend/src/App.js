import React, { useEffect, useRef, useState } from "react";
import { createChart } from "lightweight-charts";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://your-backend-url"; // set in Render env

export default function App(){
  const chartRef = useRef(null);
  const containerRef = useRef();
  const [symbol, setSymbol] = useState("AAPL");
  const [tf, setTf] = useState("1D");
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;
    chartRef.current = createChart(containerRef.current, { width: 900, height: 400, layout: { backgroundColor: '#fff' }});
    const candleSeries = chartRef.current.addCandlestickSeries();
    // dummy data (replace with real data API)
    candleSeries.setData([
      { time: '2023-09-11', open: 150, high: 155, low: 148, close: 153 },
      { time: '2023-09-12', open: 153, high: 157, low: 152, close: 156 },
      { time: '2023-09-13', open: 156, high: 158, low: 150, close: 151 },
      { time: '2023-09-14', open: 151, high: 154, low: 149, close: 153 },
      { time: '2023-09-15', open: 153, high: 160, low: 152, close: 159 }
    ]);
    const handleResize = () => {
      chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  async function sendSignal() {
    const payload = { model: "ICT", symbol, timeframe: tf, direction: "LONG", price: null };
    const resp = await fetch(`${BACKEND.replace(/\/$/, "")}/signal`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    alert("Signal posted: " + JSON.stringify(data.stats || data));
    fetchStats();
  }

  async function fetchStats(){
    try{
      const resp = await fetch(`${BACKEND.replace(/\/$/, "")}/stats`);
      const j = await resp.json();
      setStats(j.stats);
    }catch(e){ console.warn(e); }
  }

  useEffect(()=>{ fetchStats(); }, []);

  return (
    <div style={{padding:20}}>
      <h2>ICT Trading Model — Demo Chart</h2>
      <div style={{maxWidth:900}}>
        <div ref={containerRef} style={{border:"1px solid #ddd", marginBottom:10}} />
        <div style={{display:"flex", gap:10, marginTop:10, alignItems:"center"}}>
          <input value={symbol} onChange={(e)=>setSymbol(e.target.value.toUpperCase())}/>
          <select value={tf} onChange={e=>setTf(e.target.value)}>
            <option>1D</option><option>1H</option><option>15m</option>
          </select>
          <button onClick={sendSignal}>Send Signal to Backend</button>
          <button onClick={fetchStats}>Refresh Stats</button>
        </div>

        <div style={{marginTop:20}}>
          <h4>Backend Stats (recent)</h4>
          <pre style={{background:"#f5f5f5", padding:10}}>
            {stats ? JSON.stringify(stats, null, 2) : "No stats loaded"}
          </pre>
        </div>
      </div>
    </div>
  );
}
