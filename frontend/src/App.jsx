import React, { useState } from 'react'
import ChartPanel from './components/ChartPanel'
import ICTPanel from './components/ICTPanel'
import TradeLog from './components/TradeLog'

const SYMBOL = 'AAPL' // default

export default function App(){
  const [scale, setScale] = useState(1)
  const [live, setLive] = useState(true)

  return (
    <div className="app">
      <div className="header">
        <div className="title">AstroQuant — Live Demo Dashboard (4 charts)</div>
        <div style={{flex:1}}/>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <button className="btn small" onClick={()=>setLive(l=>!l)}>{live? 'Stop Live':'Start Live'}</button>
          <label style={{color:'#9aaab3'}}>Scale</label>
          <select value={scale} onChange={(e)=>setScale(Number(e.target.value))} className="btn small">
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
        </div>
      </div>

      <div className="container">
        <div className="card">
          <div className="card-header">
            <div>Chart 1 — ICT Models</div>
            <div className="controls">
              <button className="btn small" onClick={()=>window.dispatchEvent(new CustomEvent('refreshAll'))}>Refresh Data</button>
              <button className="btn small signals-btn" onClick={()=>window.dispatchEvent(new CustomEvent('toggleSignals1'))}>Signals</button>
            </div>
          </div>
          <div className="chart-wrap" style={{flexDirection:'column'}}>
            <ChartPanel id="c1" symbol={SYMBOL} mode="ict" scale={scale} live={live}/>
            <div style={{marginTop:8}}>
              <ICTPanel symbol={SYMBOL} />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>Chart 2 — Gann / Conversions</div>
            <div className="controls">
              <button className="btn small" onClick={()=>window.dispatchEvent(new CustomEvent('resetZoom'))}>Reset Zoom</button>
              <button className="btn small signals-btn" onClick={()=>window.dispatchEvent(new CustomEvent('toggleSignals2'))}>Signals</button>
            </div>
          </div>
          <div className="chart-wrap">
            <ChartPanel id="c2" symbol={SYMBOL} mode="gann" scale={scale} live={live}/>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>Chart 3 — Math / Algo</div>
            <div className="controls">
              <button className="btn small" onClick={()=>window.dispatchEvent(new CustomEvent('exportPNG'))}>Export PNG</button>
              <button className="btn small signals-btn" onClick={()=>window.dispatchEvent(new CustomEvent('toggleSignals3'))}>Signals</button>
            </div>
          </div>
          <div className="chart-wrap">
            <ChartPanel id="c3" symbol={SYMBOL} mode="math" scale={scale} live={live}/>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>Chart 4 — Momentum / Algo</div>
            <div className="controls">
              <button className="btn small" onClick={()=>window.dispatchEvent(new CustomEvent('minmax'))}>Min / Max / Close</button>
              <button className="btn small signals-btn" onClick={()=>window.dispatchEvent(new CustomEvent('toggleSignals4'))}>Signals</button>
            </div>
          </div>
          <div className="chart-wrap">
            <ChartPanel id="c4" symbol={SYMBOL} mode="momentum" scale={scale} live={live}/>
          </div>
        </div>
      </div>
    </div>
  )
}