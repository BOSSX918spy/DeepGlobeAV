const map = L.map('map',{zoomControl:false}).setView([30.7333,76.7794],16);

L.tileLayer(
'https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key=Zj8Fhh26WHZlW8frkOOk',
{maxZoom:19}
).addTo(map);

let routeLayer=null;
let maskLayer=null;
let movingTimer=null;

function log(t){
document.getElementById("log").innerText=t;
}

async function runInference(){
const c = map.getCenter();
const lat=c.lat;
const lon=c.lng;

log("Hailo running...");

const res = await fetch(
`http://127.0.0.1:8000/segment-live?lat=${lat}&lon=${lon}`
);

const data = await res.json();

if(maskLayer) map.removeLayer(maskLayer);

maskLayer=L.imageOverlay(
`http://127.0.0.1:8000/${data.mask}`,
map.getBounds(),
{opacity:0.45}
).addTo(map);

log("AI terrain overlay active");
}

/* AUTO RUN WHEN MAP STOPS MOVING */
map.on("moveend",()=>{
if(movingTimer) clearTimeout(movingTimer);
movingTimer=setTimeout(()=>{
runInference();
},700); // delay after movement
});

/* ROUTE FUNCTION */
async function computeRoute(){
const sx=startX.value;
const sy=startY.value;
const gx=goalX.value;
const gy=goalY.value;

log("Computing route...");

const res=await fetch(`http://127.0.0.1:8000/route?start_x=${sx}&start_y=${sy}&goal_x=${gx}&goal_y=${gy}`);
const data=await res.json();

if(!data.route){ log("No route"); return;}

if(routeLayer) map.removeLayer(routeLayer);

const latlngs=data.route.map(p=>map.containerPointToLatLng([p[0],p[1]]));

routeLayer=L.polyline(latlngs,{
color:'#00ffa6',
weight:4
}).addTo(map);

log("Route ready");
}