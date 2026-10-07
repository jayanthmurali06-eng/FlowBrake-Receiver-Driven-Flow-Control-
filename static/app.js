let running=false,timer=null;
const $=id=>document.getElementById(id);
const sendRate=$("sendRate"),drainRate=$("drainRate"),bufferCap=$("bufferCap"),adaptive=$("adaptive");
const fileInput=$("fileInput"),chooseFile=$("chooseFile"),uploadBtn=$("uploadBtn"),dropZone=$("dropZone");
let selectedFile=null;

sendRate.oninput=()=>$("sendVal").textContent=sendRate.value;
drainRate.oninput=()=>$("drainVal").textContent=drainRate.value;
bufferCap.oninput=()=>$("bufferVal").textContent=bufferCap.value;

$("toggle").onclick=()=>{
  if(!currentFileSize()) return;
  running=!running;
  $("toggle").textContent=running?"Pause":"Resume";
  $("runState").textContent=running?"RUNNING":"PAUSED";
};
$("reset").onclick=resetSimulation;

document.querySelectorAll(".preset button").forEach(b=>b.onclick=async()=>{
  sendRate.value=b.dataset.s; drainRate.value=b.dataset.d;
  $("sendVal").textContent=b.dataset.s; $("drainVal").textContent=b.dataset.d;
  await resetSimulation();
});

function currentFileSize(){
  const text=$("fileSize").dataset.bytes;
  return Number(text||0);
}
function formatBytes(bytes){
  if(!bytes)return "0 B";
  const units=["B","KB","MB","GB"];
  const i=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length-1);
  return (bytes/Math.pow(1024,i)).toFixed(i?1:0)+" "+units[i];
}
function setWaitingUI(){
  $("runState").textContent="WAITING FOR FILE";
  $("tick").textContent="NO DATA";
  $("heroWindow").textContent="—";
  $("used").textContent="—"; $("capacity").textContent="—";
  $("window").textContent="—"; $("brake").textContent="WAITING";
  $("brakeCard").textContent="WAITING"; $("senderRateCard").textContent="—";
  $("receiverWindowCard").textContent="WINDOW —"; $("dropped").textContent="—";
  $("util").textContent="Upload a file to begin";
  $("bar").style.width="0%";
  $("brakeText").textContent="Upload a real file to start the receiver-driven experiment.";
  $("events").innerHTML='<div class="event"><span class="time">—</span><span class="state">WAITING</span><span class="desc">No file uploaded yet.</span><span class="win">WINDOW —</span></div>';
  draw([],100);
}

async function resetSimulation(){
  if(!currentFileSize()){setWaitingUI();return;}
  running=true;
  $("toggle").textContent="Pause"; $("runState").textContent="RUNNING";
  const res=await fetch("/api/reset",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({buffer_capacity:+bufferCap.value,drain_rate:+drainRate.value,base_send_rate:+sendRate.value,adaptive:adaptive.checked})});
  render(await res.json());
}

async function step(){
  if(!running || !currentFileSize()) return;
  const r=await fetch("/api/step",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({incoming_rate:+sendRate.value,drain_rate:+drainRate.value,adaptive:adaptive.checked})});
  const state=await r.json();
  render(state);
  if(state.file && state.file.complete){
    running=false;
    $("toggle").textContent="Completed";
    $("runState").textContent="TRANSFER COMPLETE";
  }
}

function render(s){
  if(!s.has_file){setWaitingUI();return;}
  $("used").textContent=s.buffer_used;
  $("capacity").textContent=s.buffer_capacity;
  $("window").textContent=s.advertised_window;
  $("heroWindow").textContent=s.advertised_window;
  $("dropped").textContent=s.dropped_total;
  $("tick").textContent="TICK "+s.tick;
  $("util").textContent=s.history.length?s.history.at(-1).utilization+"% utilized":"0% utilized";
  $("bar").style.width=(s.buffer_used/s.buffer_capacity*100)+"%";
  $("brake").textContent=s.brake_level;
  $("brakeCard").textContent=s.brake_level;
  $("senderRateCard").textContent=s.sender_rate+" packets/tick";
  $("receiverWindowCard").textContent="WINDOW "+s.advertised_window+" packets";
  $("brakeText").textContent={NORMAL:"Receiver has sufficient space.",MODERATE:"Buffer pressure is rising; allowance is moderated.",HIGH:"Receiver is busy; stronger braking is active.",CRITICAL:"Buffer is nearly full; transmission is heavily restricted."}[s.brake_level]||"Transfer is complete.";
  draw(s.history,s.buffer_capacity); renderEvents(s.history); renderFile(s.file||{});
}

function renderEvents(h){
  const el=$("events");
  if(!h.length){el.innerHTML='<div class="event"><span class="time">—</span><span class="state">READY</span><span class="desc">File uploaded. Waiting for transfer ticks.</span><span class="win">WINDOW —</span></div>';return}
  el.innerHTML=h.slice(-12).reverse().map(p=>`<div class="event"><span class="time">T+${p.tick}</span><span class="state">${p.brake_level}</span><span class="desc">sent ${p.accepted} packets · received ${p.drained} · limited ${p.dropped}</span><span class="win">W ${p.receiver_window}</span></div>`).join("");
}

function draw(h,cap){
  const c=$("chart"),ctx=c.getContext("2d"),dpr=window.devicePixelRatio||1,rect=c.getBoundingClientRect();
  c.width=rect.width*dpr;c.height=310*dpr;ctx.scale(dpr,dpr);const w=rect.width,ht=310,pad=28;ctx.clearRect(0,0,w,ht);
  ctx.strokeStyle="#202833";ctx.lineWidth=1;for(let i=0;i<=4;i++){const y=pad+(ht-pad*1.5)*i/4;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(w-pad,y);ctx.stroke()}
  if(!h.length)return;const x=i=>pad+(w-pad*2)*(i/Math.max(1,h.length-1)),y=v=>ht-pad-(ht-pad*1.5)*(v/cap);
  ctx.strokeStyle="#e2eaf3";ctx.lineWidth=2;ctx.beginPath();h.forEach((p,i)=>i?ctx.lineTo(x(i),y(p.buffer_used)):ctx.moveTo(x(i),y(p.buffer_used)));ctx.stroke();
  ctx.strokeStyle="#687588";ctx.lineWidth=1.5;ctx.beginPath();h.forEach((p,i)=>i?ctx.lineTo(x(i),y(p.receiver_window)):ctx.moveTo(x(i),y(p.receiver_window)));ctx.stroke();
}

function renderFile(f){
  const size=Number(f.size||0), transferred=Number(f.transferred||0), progress=size?Math.min(100,transferred/size*100):0;
  $("fileName").textContent=f.name||"—";
  $("fileSize").textContent=size?formatBytes(size):"—";
  $("fileSize").dataset.bytes=size;
  $("fileTransferred").textContent=size?formatBytes(Math.min(transferred,size)):"0 B";
  $("fileProgress").style.width=progress.toFixed(1)+"%";
  $("filePercent").textContent=progress.toFixed(1)+"%";
  $("packetInfo").textContent=f.total_packets?`${f.packets_received} / ${f.total_packets} packets received · ${f.packet_size} B/packet`:"—";
  if(f.complete){
    $("uploadStatus").textContent="TRANSFERRED COMPLETELY";
    $("downloadBtn").hidden=false;
  } else {
    $("uploadStatus").textContent="TRANSFERRING";
    $("downloadBtn").hidden=true;
  }
}

function chooseSelectedFile(file){
  if(!file)return; selectedFile=file;
  $("selectedFile").textContent=file.name+" · "+formatBytes(file.size);
  $("uploadBtn").disabled=false; $("uploadStatus").textContent="FILE READY";
}
chooseFile.onclick=()=>fileInput.click();
fileInput.onchange=()=>chooseSelectedFile(fileInput.files[0]);
dropZone.ondragover=e=>{e.preventDefault();dropZone.classList.add("dragover")};
dropZone.ondragleave=()=>dropZone.classList.remove("dragover");
dropZone.ondrop=e=>{e.preventDefault();dropZone.classList.remove("dragover");chooseSelectedFile(e.dataTransfer.files[0])};

uploadBtn.onclick=async()=>{
  if(!selectedFile)return;
  uploadBtn.disabled=true; $("uploadStatus").textContent="UPLOADING";
  const form=new FormData();form.append("file",selectedFile);
  try{
    const res=await fetch("/api/upload",{method:"POST",body:form});
    const data=await res.json(); if(!res.ok)throw new Error(data.error||"Upload failed");
    $("downloadBtn").href=data.download_url; $("uploadStatus").textContent="FILE LOADED";
    render(data.state);
    running=true; $("toggle").textContent="Pause"; $("runState").textContent="RUNNING";
    uploadBtn.disabled=false;
  }catch(err){$("uploadStatus").textContent="ERROR";alert(err.message);uploadBtn.disabled=false;}
};

async function boot(){
  const r=await fetch("/api/state");
  const s=await r.json();
  if(s.has_file) render(s); else setWaitingUI();
  if(timer)clearInterval(timer); timer=setInterval(step,700);
}
boot();
window.onresize=()=>fetch("/api/state").then(r=>r.json()).then(render);
