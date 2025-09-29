const base = '';
const $ = (id) => document.getElementById(id);

function show(id, obj){
  $(id).textContent = JSON.stringify(obj, null, 2);
}

function copyText(id){
  const t = $(id).textContent;
  navigator.clipboard.writeText(t).then(()=>alert('Copied to clipboard'))
}

function demoHeader(){
  return {'x-demo-fallback': ($('demo-mode').value === 'fallback') ? '1' : '0'}
}

async function post(path, body){
  const headers = Object.assign({'Content-Type':'application/json'}, demoHeader());
  const res = await fetch(base + path, {method:'POST', headers, body: JSON.stringify(body)});
  return res.json();
}

async function get(path){
  const headers = demoHeader();
  const res = await fetch(base + path, {headers});
  return res.json();
}

function setBigCrypto(obj){
  if(obj && obj.price){
    $('big-crypto').textContent = `$${Number(obj.price).toLocaleString(undefined,{maximumFractionDigits:2})}`
  } else {
    $('big-crypto').textContent = '—'
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  $('btn-file').addEventListener('click', async ()=>{
    try{ const v = await post('/mcp/file', {name:$('file-name').value, max_chars: Number($('file-chars').value)}); show('out-file', v);}catch(e){show('out-file', {error: String(e)})}
  });

  $('btn-weather').addEventListener('click', async ()=>{
    try{ const v = await post('/mcp/weather', {city:$('weather-city').value, days: Number($('weather-days').value)}); show('out-weather', v);}catch(e){show('out-weather', {error: String(e)})}
  });

  $('btn-crypto').addEventListener('click', async ()=>{
    try{ const v = await post('/mcp/crypto', {symbol:$('crypto-symbol').value, vs:$('crypto-vs').value}); show('out-crypto', v); setBigCrypto(v);}catch(e){show('out-crypto', {error: String(e)})}
  });

  $('btn-health').addEventListener('click', async ()=>{
    try{ const v = await get('/mcp/health'); show('out-health', v);}catch(e){show('out-health', {error: String(e)})}
  });

  // copy buttons
  document.querySelectorAll('.copy').forEach(b=>{b.addEventListener('click', ()=> copyText(b.dataset.target))})

  // tool catalog
  $('btn-catalog').addEventListener('click', async ()=>{
    try{ const v = await get('/mcp/tools'); show('out-catalog', v);}catch(e){show('out-catalog', {error: String(e)})}
  });

  // initial catalog load
  $('btn-catalog').click();
});
