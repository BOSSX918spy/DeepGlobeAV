function log(t){
    document.getElementById("log").innerText = t;
}

/* ======================
   PREPARE CITY
====================== */
async function prepareCity(){

    const city = document.getElementById("city").value;

    if(!city){
        log("Enter city name first");
        return;
    }

    log("Downloading tiles for " + city + "...");

    const res = await fetch("http://"+location.hostname+":5000/city", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({city: city})
    });

    const data = await res.json();

    if(data.error){
        log("Error: " + data.error);
        return;
    }

    log("Tiles ready: " + data.prepared_tiles);

    document.getElementById("city_name").innerText = data.city;
    document.getElementById("tiles_prepared").innerText = data.prepared_tiles;
}

/* ======================
   RUN DETECTION
====================== */
async function runDetection(){

    log("Starting Hailo segmentation...");

    await fetch("http://"+location.hostname+":5000/run", {
        method: "POST"
    });
}

/* ======================
   STOP
====================== */
async function stopDetection(){
    await fetch("http://"+location.hostname+":5000/stop", {
        method: "POST"
    });
    log("Stopped");
}

/* ======================
   LIVE STATS
====================== */
async function updateStats(){

    const res = await fetch("http://"+location.hostname+":5000/stats");
    const data = await res.json();

    document.getElementById("status").innerText = data.status;
    document.getElementById("tiles_processed").innerText = data.tiles_processed;
    document.getElementById("fps").innerText = data.fps;
    document.getElementById("latency").innerText = data.latency;
}

setInterval(updateStats, 1000);