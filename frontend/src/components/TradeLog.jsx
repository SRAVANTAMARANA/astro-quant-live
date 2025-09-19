import React, {useEffect, useState} from "react";
import axios from "axios";

export default function TradeLog({symbol}){
  const [stats, setStats] = useState(null);
  useEffect(()=>{
    let mounted=true;
    async function load(){ const r = await axios.get(`/api/ict/stats?symbol=${encodeURIComponent(symbol)}`); if(mounted) setStats(r.data); }
    load();
    const t = setInterval(load, 8000);
    return ()=>{ mounted=false; clearInterval(t); }
  },[symbol]);

  if(!stats) return <div>No trade log</div>;
  return (
    <div style={{background:'#061018',padding:8,borderRadius:6}}>
      <h4>Trade Log</h4>
      <div>Total events: {stats.total}</div>
      <div>Wins: {stats.wins} Losses: {stats.losses}</div>
      <div>Unresolved: {stats.unresolved}</div>
    </div>
  )
}