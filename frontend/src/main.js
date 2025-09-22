import { createIctChart, toLwCandles, overlaySignals } from './ict.js';
import { fetchCandles, fetchSignals } from './api.js';
import { addIctControls } from './components/IctPanel/IctControls.js';
import { renderSignalTable } from './components/Shared/SignalTable.js';
import { loadNarrative } from './components/IctPanel/IctNarrator.js';

const root = document.getElementById('chart');
const { chart, series } = createIctChart(root);

async function load(symbol){
  const data = await fetchCandles(symbol,'1min',200);
  const lw = toLwCandles(data.candles);
  series.setData(lw);

  const sig = await fetchSignals(symbol,'1min',200,false);
  overlaySignals(series, sig.signals);
  renderSignalTable(document.getElementById("signal-table"), sig.signals);
  await loadNarrative(symbol);
}

document.getElementById('reload').onclick = () => {
  load(document.getElementById('sym').value);
};
document.getElementById('alert').onclick = async () => {
  const s = document.getElementById('sym').value;
  await load(s);
  await fetchSignals(s,'1min',200,true);
};

addIctControls(document.getElementById("controls"), () => {
  load(document.getElementById('sym').value);
});

load("BTC/USD");
