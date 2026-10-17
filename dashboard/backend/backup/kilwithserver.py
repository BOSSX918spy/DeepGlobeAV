import time
import threading
from pathlib import Path
from queue import Queue, Empty
from PIL import Image
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import signal
from core.segmentation.hailo_segment import HailoSegmentor

# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

TILE_CACHE = ROOT / "services/tile_cache"

# =========================================================
# APP
# =========================================================

app = FastAPI()

app.mount(
    "/services",
    StaticFiles(directory=str(ROOT / "services")),
    name="services"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# GLOBALS
# =========================================================

tile_queue = Queue()

running = False
segmentor = None

processed_tiles = set()
queued_tiles = set()

stats = {
    "status": "idle",
    "tiles": 0,
    "processed": 0,
    "fps": 0,
}

# =========================================================
# HELPERS
# =========================================================


def load_tiles(city):

    path = TILE_CACHE / city / "tiles"

    print("📂 LOADING:", path)

    if not path.exists():

        print("❌ TILE PATH NOT FOUND")

        return []

    files = (
        list(path.rglob("*.png")) +
        list(path.rglob("*.jpg")) +
        list(path.rglob("*.jpeg"))
    )

    print("📦 FOUND:", len(files))

    return [str(f) for f in files]

# =========================================================
# REQUEST MODEL
# =========================================================

class Req(BaseModel):
    city: str

# =========================================================
# WORKER
# =========================================================
def worker(city):

    global running

    print("🚀 Worker started")

    start_time = time.time()

    stats["status"] = "running"

    while running or not tile_queue.empty():

        try:

            tile = tile_queue.get(timeout=2)

        except Empty:
            continue

        if tile in processed_tiles:
            continue

        print("🧠 Processing:", tile)

        try:

            segmentor.segment_tile(tile)

            print("✅ Segmented")

            processed_tiles.add(tile)

            stats["processed"] = len(processed_tiles)

            elapsed = time.time() - start_time

            if elapsed > 0:

                stats["fps"] = round(
                    stats["processed"] / elapsed,
                    2
                )

        except Exception as e:

            print("❌ ERROR:", e)

    stats["status"] = "done"

    running = False

    print("🏁 Worker finished")
@app.get("/image_size/{region}")
def image_size(region: str):

    tile_dir = TILE_CACHE / region / "tiles"

    files = (
        list(tile_dir.glob("*.png")) +
        list(tile_dir.glob("*.jpg"))
    )

    if not files:
        return {
            "width": 32768,
            "height": 32768
        }

    img = Image.open(files[0])

    tile_w, tile_h = img.size

    max_x = 0
    max_y = 0

    for f in files:

        parts = f.stem.split("_")

        nums = []

        for p in parts:
            if p.isdigit():
                nums.append(int(p))

        if len(nums) < 2:
            continue

        x = nums[-2]
        y = nums[-1]

        max_x = max(max_x, x)
        max_y = max(max_y, y)

    return {
        "width": max_x + tile_w,
        "height": max_y + tile_h
    }

# =========================================================
# RUN
# =========================================================
@app.post("/run")
def run(req: Req):

    global running
    global segmentor
    global processed_tiles
    global queued_tiles

    city = req.city.strip()

    print("🚀 STARTING:", city)

    tiles = load_tiles(city)

    print("📦 TILES FOUND:", len(tiles))

    if not tiles:
        return {"error": "no tiles"}
        
    if segmentor is None:

     print("🚀 INITIALIZING HAILO")

     segmentor = HailoSegmentor()

     print("✅ HAILO READY")
		

    ####################################################
    # RESET
    ####################################################

    processed_tiles.clear()
    queued_tiles.clear()

    ####################################################
    # CLEAR QUEUE
    ####################################################

    while True:

        try:
            tile_queue.get_nowait()

        except Empty:
            break

    ####################################################
    # IMPORTANT
    ####################################################

    running = True

    ####################################################
    # STATS
    ####################################################

    stats["processed"] = 0
    stats["fps"] = 0
    stats["tiles"] = len(tiles)
    stats["status"] = "running"

    ####################################################
    # FILL QUEUE
    ####################################################

    for t in tiles:

        if t not in queued_tiles:

            queued_tiles.add(t)

            tile_queue.put(t)

    print("📦 FINAL QUEUE:", tile_queue.qsize())

    ####################################################
    # THREAD
    ####################################################

    thread = threading.Thread(
        target=worker,
        args=(city,),
        daemon=True
    )

    thread.start()

    print("🚀 THREAD STARTED")

    return {
        "status": "started"
    }
# =========================================================
# REGIONS
# =========================================================
@app.get("/regions")
def regions():

    regions = []

    for p in TILE_CACHE.iterdir():

        if not p.is_dir():
            continue

        pyramid = p / "pyramid"
        tiles = p / "tiles"

        if pyramid.exists() and tiles.exists():

            regions.append(p.name)

    regions.sort()

    print("🌍 REGIONS:", regions)

    return regions
# =========================================================
# STATS
# =========================================================

@app.get("/stats")
def get_stats():

    return stats
# =========================================================
# SHUTDOWN
# =========================================================

@app.post("/shutdown")
def shutdown():

    os.kill(
        os.getpid(),
        signal.SIGINT
    )

    return {
        "status":"shutdown"
    }
# =========================================================
# KILL BROWSER
# =========================================================
@app.post("/kill_browser")
def kill_browser():

    try:

        print("🔥 KILLING CHROMIUM")

        os.system("pkill -9 chromium")

        os.system("pkill -9 chromium-browser")

        os.system("pkill -9 chrome")

    except Exception as e:

        print("BROWSER KILL ERROR:", e)

    return {
        "status":"browser_closed"
    }
# =========================================================
# UI
# =========================================================
@app.get("/", response_class=HTMLResponse)
def home():

    return """

<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<title>DeepGlobeAV+</title>

<link rel="stylesheet"
href="https://unpkg.com/leaflet/dist/leaflet.css"/>

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
rel="stylesheet">

<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
    font-family:'Inter',sans-serif;
}

html,body{
    width:100%;
    height:100%;
    overflow:hidden;

    background:
    linear-gradient(
        180deg,
        #eef1f5 0%,
        #dde3ea 100%
    );
}

#container{
    width:100vw;
    height:100vh;

    display:flex;

    gap:18px;

    padding:16px;
}

/* LEFT PANEL */

#leftPanel{

    width:25%;
    min-width:360px;

    height:100%;

    border-radius:32px;

    background:rgba(255,255,255,0.32);

    backdrop-filter:blur(30px);

    border:1px solid rgba(255,255,255,0.4);

    box-shadow:
        0 10px 30px rgba(0,0,0,0.08);

    padding:18px;

    display:flex;
    flex-direction:column;
}

#mainLogo{
    width:100%;
    border-radius:18px;
    margin-bottom:18px;
}

/* SELECT */

select{

    width:100%;

    padding:18px;

    border:none;

    border-radius:18px;

    background:white;

    font-size:15px;

    outline:none;

    margin-bottom:14px;
}

/* BUTTONS */

.buttonRow{
    display:flex;
    gap:10px;

    margin-bottom:18px;
}

button{

    flex:1;

    padding:16px;

    border:none;

    border-radius:18px;

    background:white;

    font-weight:600;

    cursor:pointer;

    transition:0.2s;

    box-shadow:
        0 4px 10px rgba(0,0,0,0.05);
}

button:hover{
    transform:translateY(-2px);
}

/* CARDS */

.card{

    padding:20px;

    border-radius:24px;

    background:rgba(255,255,255,0.24);

    border:1px solid rgba(255,255,255,0.35);

    margin-bottom:14px;
}

.cardTitle{

    font-size:11px;

    color:#888;

    margin-bottom:8px;

    letter-spacing:1px;
}

.cardValue{

    font-size:24px;

    font-weight:700;

    color:#111;
}

/* FOOTER */

#footer{

    margin-top:auto;

    text-align:center;
}
#bottomIcons{

    display:flex;

    justify-content:center;

    gap:18px;

    margin-bottom:18px;
}

.footerIcon{

    width:54px;
    height:54px;

    border:none;

    border-radius:16px;

    background:rgba(255,255,255,0.7);

    font-size:24px;

    cursor:pointer;

    transition:0.2s;

    display:flex;

    align-items:center;

    justify-content:center;

    box-shadow:
        0 4px 10px rgba(0,0,0,0.1);
}

.footerIcon:hover{

    transform:translateY(-2px);
}

.dialogOverlay{

    display:none;

    position:fixed;

    top:0;
    left:0;

    width:100%;
    height:100%;

    background:rgba(0,0,0,0.55);

    z-index:999999;

    justify-content:center;

    align-items:center;
}

.dialogBox{

    width:420px;

    padding:30px;

    border-radius:26px;

    background:white;

    text-align:center;

    box-shadow:
        0 10px 40px rgba(0,0,0,0.35);
}

.dialogBox h2{

    margin-bottom:18px;
}

.dialogBox p{

    margin-bottom:22px;

    line-height:1.7;

    color:#444;
}

.dialogBox input{

    width:100%;

    padding:14px;

    border-radius:14px;

    border:1px solid #ccc;

    margin-bottom:18px;

    outline:none;
}

#cuLogo{
    width:180px;
    margin-bottom:16px;
}

#footerText{

    font-size:15px;

    color:#222;

    line-height:1.8;
}

/* RIGHT PANEL */

#rightPanel{

    flex:1;

    position:relative;

    height:100%;
}

#map{

    width:100%;
    height:100%;

    border-radius:34px;

    overflow:hidden;

    background:black;

    box-shadow:
        0 12px 30px rgba(0,0,0,0.15);
}

.leaflet-container{
    background:black;
}

/* TOPBAR */

#topbar{

    position:absolute;

    top:16px;
    left:16px;
    right:16px;

    z-index:9999;

    height:64px;

    border-radius:24px;

    background:rgba(255,255,255,0.18);

    backdrop-filter:blur(24px);

    border:1px solid rgba(255,255,255,0.28);

    display:flex;

    align-items:center;

    justify-content:space-between;

    padding:0 20px;
}

#topbarTitle{

    color:white;

    font-size:20px;

    font-weight:700;
}

#topbarButtons{
    display:flex;
    gap:10px;
}

.topPill{

    padding:10px 16px;

    border-radius:999px;

    background:rgba(255,255,255,0.18);

    color:white;

    font-size:12px;
}

</style>

</head>

<body>

<div id="container">

    <div id="leftPanel">

        <img
        id="mainLogo"
        src="/services/logoh.jpeg">

        <select id="city"></select>

            
        

        <div class="buttonRow">

            <button onclick="runSegmentation()">
                RUN
            </button>

            <button onclick="stopSegmentation()">
                STOP
            </button>

        </div>

        <div class="card">

            <div class="cardTitle">
                STATUS
            </div>

            <div class="cardValue"
            id="status">

                idle

            </div>

        </div>

        <div class="card">

            <div class="cardTitle">
                FPS
            </div>

            <div class="cardValue"
            id="fps">

                0

            </div>

        </div>

        <div class="card">

            <div class="cardTitle">
                PROCESSED
            </div>

            <div class="cardValue"
            id="processed">

                0/0

            </div>

        </div>

        <<div id="footer">

    <!-- ICONS -->
    <div id="bottomIcons">

        <!-- HELP -->
        <button
        class="footerIcon"
        onclick="openHelpDialog()">

            ?

        </button>

        <!-- CAMERA -->
        <button
        class="footerIcon">

            📷

        </button>

        <!-- EXIT -->
        <button
        class="footerIcon"
        onclick="openExitDialog()">

            ⎋

        </button>

    </div>

    <img
    id="cuLogo"
    src="/services/culogo.png">

    <div id="footerText">

        Developed At Department of Electronics &
        Communication Engineering

    </div>

</div>

    </div>

    <div id="rightPanel">

        <div id="topbar">

            <div id="topbarTitle">
                Disaster Intelligence Viewer
            </div>

            <div id="topbarButtons">

                <div class="topPill">
                    Satellite
                </div>

              <div class="topPill">
    Segmentation
</div>

            <button
id="roadsBtn"
onclick="toggleRoads()"
style="
padding:10px 16px;
border:none;
border-radius:999px;
background:rgba(255,255,255,0.18);
color:white;
font-size:12px;
cursor:pointer;
">

    Roads

</button>

            </div>

        </div>

        <div id="map"></div>

    </div>

</div>
<!-- HELP DIALOG -->
<div id="helpDialog"
class="dialogOverlay">

    <div class="dialogBox">

        <h2>Help</h2>

        <p>

            Placeholder help text.
            Add your instructions later.

        </p>

        <button onclick="closeHelpDialog()">

            Close

        </button>

    </div>

</div>

<!-- EXIT DIALOG -->
<div id="exitDialog"
class="dialogOverlay">

    <div class="dialogBox">

        <h2>Service Authentication</h2>

        <input
        type="password"
        id="serviceCode"
        placeholder="Enter Service Code">

        <button onclick="verifyExitCode()">

            Exit Application

        </button>

        <br><br>

        <button onclick="closeExitDialog()">

            Cancel

        </button>

    </div>

</div>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

<script>

/////////////////////////////////////////////////////////
// GLOBALS
/////////////////////////////////////////////////////////

let map = null;
let roadsLayer = null;
let roadsVisible = true;
let satelliteLayer = null;

let IMAGE_WIDTH = 32768;
let IMAGE_HEIGHT = 32768;
/////////////////////////////////////////////////////////
// HELP DIALOG
/////////////////////////////////////////////////////////

function openHelpDialog(){

    document
    .getElementById("helpDialog")
    .style.display = "flex";
}

function closeHelpDialog(){

    document
    .getElementById("helpDialog")
    .style.display = "none";
}

/////////////////////////////////////////////////////////
// EXIT DIALOG
/////////////////////////////////////////////////////////

function openExitDialog(){

    document
    .getElementById("exitDialog")
    .style.display = "flex";
}

function closeExitDialog(){

    document
    .getElementById("exitDialog")
    .style.display = "none";
}

/////////////////////////////////////////////////////////
// VERIFY EXIT
/////////////////////////////////////////////////////////

async function verifyExitCode(){

    const code =
    document
    .getElementById("serviceCode")
    .value;

    if(code !== "9182"){

        alert("Invalid Service Code");

        return;
    }

    /////////////////////////////////////////////////////////
    // KILL CHROMIUM FIRST
    /////////////////////////////////////////////////////////

    await fetch('/kill_browser', {
        method:'POST'
    });

    /////////////////////////////////////////////////////////
    // SHUTDOWN UVICORN AFTER
    /////////////////////////////////////////////////////////

    setTimeout(async () => {

        await fetch('/shutdown', {
            method:'POST'
        });

    }, 1000);
}
/////////////////////////////////////////////////////////
// RUN
/////////////////////////////////////////////////////////

async function runSegmentation(){

    const city =
    document.getElementById("city").value;

    await fetch('/run',{

        method:'POST',

        headers:{
            'Content-Type':'application/json'
        },

        body:JSON.stringify({
            city:city
        })

    });
}

/////////////////////////////////////////////////////////
// STOP
/////////////////////////////////////////////////////////

async function stopSegmentation(){

    await fetch('/stop',{
        method:'POST'
    });
}

/////////////////////////////////////////////////////////
// STATS
/////////////////////////////////////////////////////////

async function updateStats(){

    const r =
    await fetch('/stats');

    const s =
    await r.json();

    document.getElementById("status").innerText =
        s.status;

    document.getElementById("fps").innerText =
        s.fps;

    document.getElementById("processed").innerText =
        s.processed + "/" + s.tiles;
}

setInterval(updateStats,500);

/////////////////////////////////////////////////////////
// LOAD REGIONS
/////////////////////////////////////////////////////////

async function loadRegions(){

    const r =
    await fetch('/regions');

    const regions =
    await r.json();

    const select =
    document.getElementById("city");

    select.innerHTML = "";

    regions.forEach(region => {

        const option =
        document.createElement("option");

        option.value = region;

        option.textContent = region;

        select.appendChild(option);

    });
}

/////////////////////////////////////////////////////////
// LOAD ROADS
/////////////////////////////////////////////////////////

async function loadRoads(region){

    try{

        const response = await fetch(

            `/services/roads/${encodeURIComponent(region)}/roads_pixels.geojson`

        );

        const data = await response.json();

        console.log(
            "FEATURE COUNT:",
            data.features.length
        );

        ///////////////////////////////////////////////////
        // ONLY ROAD LINES
        ///////////////////////////////////////////////////

        const lineFeatures =
        data.features.filter(f => {

            if(!f.geometry)
                return false;

            return (

                f.geometry.type === "LineString" ||

                f.geometry.type === "MultiLineString"

            );

        });

        console.log(
            "LINE FEATURES:",
            lineFeatures.length
        );

        ///////////////////////////////////////////////////
        // CREATE LAYER
        ///////////////////////////////////////////////////

        roadsLayer = L.geoJSON({

            type:"FeatureCollection",

            features:lineFeatures

        },{

            renderer:L.canvas(),

            ///////////////////////////////////////////////////
            // PIXEL SPACE
            ///////////////////////////////////////////////////

            coordsToLatLng:function(coords){

    /////////////////////////////////////////////////////
    // OFFSET TUNING
    /////////////////////////////////////////////////////

    const OFFSET_X = 1000;
const OFFSET_Y = -19050;

    const point =
    map.unproject(
        [
            coords[0] + OFFSET_X,
            coords[1] + OFFSET_Y
        ],
        4
    );

    return point;
},

            ///////////////////////////////////////////////////
            // STYLE
            ///////////////////////////////////////////////////

            style:function(){

                return {

                    color:"#00ff00",

                    weight:2,

                    opacity:1
                };
            }

        });

        ///////////////////////////////////////////////////
        // ADD
        ///////////////////////////////////////////////////

        roadsLayer.addTo(map);

        roadsVisible = true;

        console.log("✅ ROADS RENDERED");

    }catch(error){

        console.log(
            "❌ ROADS ERROR:",
            error
        );
    }
}

/////////////////////////////////////////////////////////
// TOGGLE
/////////////////////////////////////////////////////////

function toggleRoads(){

    if(!roadsLayer){

        console.log("❌ roadsLayer NULL");

        return;
    }

    if(roadsVisible){

        map.removeLayer(roadsLayer);

        roadsVisible = false;

        console.log("🚫 ROADS HIDDEN");

    }else{

        roadsLayer.addTo(map);

        roadsVisible = true;

        console.log("✅ ROADS SHOWN");
    }
}

/////////////////////////////////////////////////////////
// LOAD MAP
/////////////////////////////////////////////////////////

async function loadMap(region){

    region = region.trim();

    /////////////////////////////////////////////////////
    // REMOVE OLD MAP
    /////////////////////////////////////////////////////

    if(map){

        map.remove();
    }

    roadsLayer = null;

    /////////////////////////////////////////////////////
    // IMAGE SIZE
    /////////////////////////////////////////////////////

    const response =
    await fetch(`/image_size/${region}`);

    const size =
    await response.json();

    IMAGE_WIDTH = size.width;
    IMAGE_HEIGHT = size.height;

    console.log(
        "IMAGE:",
        IMAGE_WIDTH,
        IMAGE_HEIGHT
    );

    /////////////////////////////////////////////////////
    // CREATE MAP
    /////////////////////////////////////////////////////

    map = L.map('map',{

    crs: L.CRS.Simple,

    minZoom: 0,
    maxZoom: 4,

    zoomControl: true,

    attributionControl: false
});

    /////////////////////////////////////////////////////
    // BOUNDS
    /////////////////////////////////////////////////////

    const southWest =
map.unproject([0, IMAGE_HEIGHT], 4);

const northEast =
map.unproject([IMAGE_WIDTH, 0], 4);

const bounds =
new L.LatLngBounds(
    southWest,
    northEast
);

 /////////////////////////////////////////////////////
// SATELLITE TILES
/////////////////////////////////////////////////////
satelliteLayer = L.tileLayer(

    `/services/tile_cache/${encodeURIComponent(region)}/pyramid/{z}/{x}/{y}.png`,

    {
        tileSize: 512,

        minZoom: 0,
        maxZoom: 4,
        maxNativeZoom: 4,

        noWrap: true,

        continuousWorld: false,
		keepBuffer: 0,
        bounds: bounds
    }
);
satelliteLayer.addTo(map);
map.setView(
    bounds.getCenter(),
    map.getBoundsZoom(bounds)
);

    /////////////////////////////////////////////////
// FIT EXACTLY
/////////////////////////////////////////////////
map.setMaxBounds(bounds);

map.options.maxBoundsViscosity = 1.0;

const zoom =
map.getBoundsZoom(bounds);

map.setView(
    bounds.getCenter(),
    zoom + 0.2
);

/////////////////////////////////////////////////
// FORCE CAMERA INSIDE
/////////////////////////////////////////////////



/////////////////////////////////////////////////
// PREVENT EMPTY SPACE
/////////////////////////////////////////////////



/////////////////////////////////////////////////
// NO BOUNCE
/////////////////////////////////////////////////



    /////////////////////////////////////////////////////
    // HARD LIMITS
    /////////////////////////////////////////////////////

    

    /////////////////////////////////////////////////////
    // LOAD ROADS
    /////////////////////////////////////////////////////

    await loadRoads(region);

    /////////////////////////////////////////////////////
    // REFRESH
    /////////////////////////////////////////////////////

    setTimeout(() => {

        map.invalidateSize();

    },200);
}

/////////////////////////////////////////////////////////
// INIT
/////////////////////////////////////////////////////////

async function init(){

    await loadRegions();

    const firstRegion =
    document.getElementById("city").value;

    await loadMap(firstRegion);
}

init();

/////////////////////////////////////////////////////////
// REGION CHANGEmap.setMaxBounds(bounds);

map.options.maxBoundsViscosity = 1.0;

const zoom =
map.getBoundsZoom(bounds);

map.setView(
    bounds.getCenter(),
    zoom + 0.2
);
/////////////////////////////////////////////////////////

document
.getElementById("city")
.addEventListener("change", async e => {

    await loadMap(e.target.value);

});

</script>
</body>

</html>

"""
