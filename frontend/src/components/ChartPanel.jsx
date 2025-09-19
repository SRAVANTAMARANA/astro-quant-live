import React, { useEffect, useRef, useState } from 'react'
import { createChart } from 'lightweight-charts'
import axios from 'axios'

export default function ChartPanel({ id, symbol, mode, scale=1, live=true }){
  const ref = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const [signalsVisible, setSignalsVisible] = useState(false)

  useEffect(()=>{
    function onToggle(){
      setSignalsVisible(v=>!v)
    }
    window.addEventListener(`toggleSignals${id.replace('c','')}`, onToggle)
    return ()=>window.removeEventListener(`toggleSignals${id.replace('c','')}`, onToggle)
  },[id])

  useEffect(()=>{
    const container = ref.current
    container.innerHTML = ''
    const chart = createChart(container, {
      layout: { background: { color: '#071019'}, textColor: '#cfeeea'},
      width: container.clientWidth,
      height: container.clientHeight,
      rightPriceScale: { visible: true },
      timeScale: { timeVisible: true, secondsVisible: true }
    })
    chartRef.current = chart
    const line = chart.addLineSeries({ color: mode === 'gann' ? '#ffa14b' : '#5fd3c9', lineWidth: 2 * scale })
    seriesRef.current = line

    const ro = new ResizeObserver(()=>chart.applyOptions({ width: container.clientWidth, height: container.clientHeight }))
    ro.observe(container)

    fetchHistory()

    // websocket fallback
    let ws = null
    try{
      const wsUrl = (location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + location.host + '/ws/realtime'
      ws = new WebSocket(wsUrl)
      ws.onmessage = (e)=>{
        const d = JSON.parse(e.data)
        if(d.symbol === symbol && seriesRef.current) {
          seriesRef.current.update({ time: toChartTime(d.time), value: d.close })
        }
      }
    }catch(e){ console.warn('WS failed, will poll') }

    let pollId = null
    if(!ws) pollId = setInterval(()=>fetchRealtime(), 2000)

    const onRefresh = ()=>fetchHistory()
    window.addEventListener('refreshAll', onRefresh)
    window.addEventListener('resetZoom', ()=>chart.timeScale().fitContent())

    return ()=>{
      ro.disconnect && ro.disconnect()
      chart.remove()
      ws && ws.close()
      pollId && clearInterval(pollId)
      window.removeEventListener('refreshAll', onRefresh)
    }
    // eslint-disable-next-line
  }, [symbol, mode])

  useEffect(()=>{
    if(seriesRef.current) seriesRef.current.applyOptions({ lineWidth: 2 * scale })
  },[scale])

  async function fetchHistory(){
    try{
      const res = await axios.get(`/api/history?symbol=${encodeURIComponent(symbol)}&limit=300`)
      const data = res.data || []
      const mapped = data.map(d => ({ time: toChartTime(d.time), value: d.close }))
      seriesRef.current.setData(mapped)
      // also fetch ICT overlays if this is ICT mode
      if(mode === 'ict'){
        try{
          const r = await axios.get(`/api/ict/signals?symbol=${encodeURIComponent(symbol)}`)
          const overlays = r.data.result.overlays || {}
          const msb = overlays.msb || []
          const markers = msb.map(m => ({ time: toChartTime(new Date().toISOString()), position:'aboveBar', color:'#ffde59', shape:'arrowUp', text: m.type }))
          line.setMarkers(markers)
        }catch(e){}
      }
    }catch(err){
      console.error('history fetch failed', err)
    }
  }

  async function fetchRealtime(){
    try{
      const res = await axios.get(`/api/realtime?symbol=${encodeURIComponent(symbol)}`)
      const d = res.data
      if(d && seriesRef.current) seriesRef.current.update({ time: toChartTime(d.time), value: d.close })
    }catch(e){}
  }

  return (
    <div style={{display:'flex',flex:1,minHeight:0}}>
      <div ref={ref} style={{flex:1,minHeight:0}}/>
      <div className="left-col" style={{display: signalsVisible ? 'flex' : 'none'}}>
        <div className="panel">
          <h4 style={{margin:'0 0 6px 0'}}>Signals — {mode}</h4>
          <div style={{fontSize:13,color:'#9aaab3'}}>Hidden panel: ICT/Gann/Math/Momentum signals (backend provides these)</div>
          <div style={{marginTop:8}}>
            <button className="btn small" onClick={()=>alert('Fetch signals for '+symbol)}>Refresh Signals</button>
          </div>
          <div style={{marginTop:8}}>
            <pre style={{whiteSpace:'pre-wrap',color:'#cfeeea',fontSize:12}}>
              {`Example:\nBuy: 2025-09-19T12:34:00Z\nSell: 2025-09-19T12:45:00Z\nConfidence: 0.84`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

function toChartTime(t){
  const d = new Date(t)
  return Math.floor(d.getTime() / 1000)
}