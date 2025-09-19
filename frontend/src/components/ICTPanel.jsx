import React, { useEffect, useState } from "react";
import axios from "axios";

export default function ICTPanel({ symbol }) {
  const [signals, setSignals] = useState(null);
  const [narrative, setNarrative] = useState([]);
  const [stats, setStats] = useState(null);

  async function fetchAll(){
    try{
      const s = await axios.get(`/api/ict/signals?symbol=${encodeURIComponent(symbol)}`);
      setSignals(s.data.result);
    }catch(e){ setSignals(null); }

    try{
      const n = await axios.get(`/api/ict/narrative?symbol=${encodeURIComponent(symbol)}`);
      setNarrative(n.data.narrative || []);
    }catch(e){ setNarrative([]); }

    try{
      const st = await axios.get(`/api/ict/stats?symbol=${encodeURIComponent(symbol)}`);
      setStats(st.data);
    }catch(e){ setStats(null); }
  }

  useEffect(()=>{
    fetchAll();
    const t = setInterval(fetchAll, 8000);
    return ()=>clearInterval(t);
  }, [symbol]);

  async function ack(event_id, outcome){
    try{
      await axios.post(`/api/ict/ack`, { event_id, outcome });
      fetchAll();
    }catch(e){ alert("ack failed: "+e) }
  }

  return (
    <div style={{display:'flex',gap:12}}>
      <div style={{flex:1}}>
        <h4>ICT Candidates</h4>
        {!signals && <div>No signals loaded</div>}
        {signals && signals.candidates && signals.candidates.length===0 && <div>No candidates</div>}
        {signals && signals.candidates && signals.candidates.map((c, idx)=>(
          <div key={idx} style={{padding:8,marginBottom:8,background:'#061018',borderRadius:6}}>
            <div><b>{c.side.toUpperCase()}</b> entry:{c.entry} stop:{c.stop} tgt:{c.target} RR:{c.rr}</div>
            <div style={{marginTop:6}}>
              <button onClick={()=>ack(c.id||0,'win')} className="btn small">Mark Win</button>
              <button onClick={()=>ack(c.id||0,'loss')} className="btn small" style={{marginLeft:6}}>Mark Loss</button>
            </div>
          </div>
        ))}
      </div>

      <div style={{width:320}}>
        <h4>Narrative</h4>
        <div style={{background:'#061018',padding:8,borderRadius:6}}>
          {narrative.map((l,i)=> <div key={i} style={{marginBottom:6}}>- {l}</div>)}
        </div>

        <h4 style={{marginTop:12}}>Stats (24h)</h4>
        <div style={{background:'#061018',padding:8,borderRadius:6}}>
          {stats ? (
            <div>
              <div>Total events: {stats.total}</div>
              <div>Wins: {stats.wins} Losses: {stats.losses} Unresolved: {stats.unresolved}</div>
            </div>
          ) : <div>No stats</div>}
        </div>
      </div>
    </div>
