const map = L.map('map').setView([30.5161,76.6598],15);

L.tileLayer(
'https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key=Zj8Fhh26WHZlW8frkOOk',
{maxZoom:19}
).addTo(map);

let graphLayer=null;

function log(t){
document.getElementById("log").innerText=t;
}

/* BUILD INTELLIGENCE AREA */
async function buildArea(){

const center = map.getCenter();
const lat=center.lat;
const lon=center.lng;

log("Processing area with Hailo...");

await fetch(`/build-area?lat=${lat}&lon=${lon}&radius=2`);

log("AI intelligence ready");

/* load graph overlay */
loadGraph();
}

/* LOAD GRAPH OVERLAY */
async function loadGraph(){

const res = await fetch("/services/graphs/city_graph.json");
const graph = await res.json();

if(graphLayer){
map.removeLayer(graphLayer);
}

const lines=[];

graph.edges.forEach(edge=>{
const pts=edge.map(p=>map.containerPointToLatLng([p[0],p[1]]));
lines.push(pts);
});

graphLayer = L.layerGroup(
lines.map(l=>L.polyline(l,{color:'#00ffa6',weight:2}))
).addTo(map);

log("Road intelligence loaded");
}