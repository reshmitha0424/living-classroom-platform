let currentFilter = "all";
let currentStation = "all";
let bestHoursChart = null;

let uniqueSpeciesData = [];
let uniqueSpeciesIndex = 0;

function setFilter(filter) {
  currentFilter = filter;

  refresh();
  loadSummary();
  loadTopSpecies();
  loadSpeciesTimeline();
  loadMap();
}

function setStation(station) {
  currentStation = station;

  refresh();
  loadSummary();
  loadTopSpecies();
  loadSpeciesTimeline();
  loadMap();
}

async function refresh() {
  try {
    const res = await fetch(`/latest?filter=${currentFilter}&station=${currentStation}`);
    const data = await res.json();

    if (data.ok) {
      const cardsHtml = data.rows.map(x => `
        <div class="dcard">
          ${x.png_url ? `<img src="${x.png_url}">` : ""}
          <div>
            <div class="dtitle" onclick="openSpeciesModal('${x.species}')">${x.species}</div>
            <div class="dmeta">Station ${x.station_id}</div>
            <div class="dmeta">${formatTime(x.timestamp)}</div>
          </div>
        </div>
      `).join("");

      document.getElementById("cards").innerHTML = cardsHtml;
      document.getElementById("updated").textContent =
        `Last updated: ${new Date().toLocaleTimeString()}`;
    }
  } catch (e) {
    document.getElementById("cards").innerHTML =
      `<div class="dcard">Network error</div>`;
  }
}

async function openSpeciesModal(species) {
  const res = await fetch(`/species-detail?species=${encodeURIComponent(species)}&filter=${currentFilter}&station=${currentStation}`);
  const data = await res.json();

  if (!data.ok) return;

  document.getElementById("speciesModalContent").innerHTML = `
    <div class="modal-content-row">
      <img src="${data.png_url}" class="modal-bird-img">

      <div>
        <h2>${data.species}</h2>
        <p class="scientific-name">${data.scientific_name || ""}</p>
        <p><b>Total detections:</b> ${data.total_detections}</p>
    
        <p><b>Last detected:</b> ${formatTime(data.last_detected)}</p>

        ${data.soundscape_url ? `
          <div class="audio-box">
            <p class="audio-title">Do you hear me?</p>
            <audio controls>
              <source src="${data.soundscape_url}" type="audio/mpeg">
              Your browser does not support audio playback.
            </audio>
          </div>
        ` : `
          <p class="no-audio">No audio available for this species.</p>
        `}
      </div>
    </div>
  `;

  document.getElementById("speciesModal").style.display = "flex";
}

function closeSpeciesModal() {
  document.getElementById("speciesModal").style.display = "none";
}

async function loadSummary() {
  const res = await fetch(`/summary?filter=${currentFilter}&station=${currentStation}`);
  const data = await res.json();

  if (data.ok) {
    document.getElementById("totalDetections").textContent = data.total_detections;
    document.getElementById("uniqueSpecies").textContent = data.unique_species;
    document.getElementById("topSpecies").textContent = data.latest_species ?? "-";
    document.getElementById("topSpecies").onclick = () => {
      if (data.latest_species && data.latest_species !== "N/A") {
        openSpeciesModal(data.latest_species);
      }
    };
    document.getElementById("latestTimestamp").textContent = formatTime(data.latest_timestamp);
  }
}

async function loadTopSpecies() {
  const res = await fetch(`/top-species?filter=${currentFilter}&station=${currentStation}`);
  const data = await res.json();

  if (!data.ok) return;

  const maxCount = Math.max(...data.rows.map(d => d.count));

  const html = data.rows.map(x => {

    const widthPercent = (x.count / maxCount) * 100;

    return `
      <div class="top-species-modern-row">

        <img 
          src="${x.png_url || ''}" 
          class="top-species-modern-img"
          onerror="this.style.display='none'"
        >

        <div class="top-species-modern-content">

          <div class="top-species-modern-name" onclick="openSpeciesModal('${x.species}')">
            ${x.species}
          </div>

          <div class="top-species-modern-bar-bg">
            <div 
              class="top-species-modern-bar"
              style="width:${widthPercent}%"
            ></div>
          </div>

        </div>
      </div>
    `;
  }).join("");

  document.getElementById("topSpeciesList").innerHTML = html;
}

async function loadSpeciesTimeline() {
  const res = await fetch(`/species-timeline?filter=${currentFilter}&station=${currentStation}`);
  const data = await res.json();

  if (!data.ok) return;

  let html = `
    <div class="timeline-row" style="font-weight:bold;">
      <div>Species</div>

      <div>Jan</div>
      <div>Feb</div>
      <div>Mar</div>
      <div>Apr</div>
      <div>May</div>
      <div>Jun</div>
      <div>Jul</div>
      <div>Aug</div>
      <div>Sep</div>
      <div>Oct</div>
      <div>Nov</div>
      <div>Dec</div>
    </div>
  `;

  data.rows.forEach(row => {

    html += `<div class="timeline-row"><div>${row.species}</div>`;

    for (let m = 0; m < 12; m++) {

      const monthValues = row.values.slice(m * 4, m * 4 + 4);

      html += `<div class="month-box">`;

      monthValues.forEach(v => {

        html += `
          <div 
            class="mini-bar"
            style="height:${v.percent || 0}%"
            title="${v.count || 0} detections"
          ></div>
        `;
      });

      html += `</div>`;
    }

    html += `</div>`;
  });

  document.getElementById("speciesTimeline").innerHTML = html;
}

async function loadBestHours() {

  try {

    const res = await fetch("/best-hours");
    const data = await res.json();

    const hours = data.hours || [];

    document.getElementById("bestHoursList").innerHTML =
      hours.map(hour => `
        <div class="best-hour-pill">
          ${hour}
        </div>
      `).join("");

    const ctx = document.getElementById("bestHoursChart");

    if (bestHoursChart) {
      bestHoursChart.destroy();
    }

    bestHoursChart = new Chart(ctx, {
      type: "bar",

      data: {
        labels: data.chart_labels,

        datasets: [{
          data: data.chart_counts,
          borderWidth: 0,
          backgroundColor: "#63d471"
        }]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        plugins: {
          legend: { display: false }
        },

        scales: {

          x: {
            ticks: {
              color: "#cbd5e1",
              font: { size: 9 }
            },

            grid: {
              display: false
            }
          },

          y: {
            display: false
          }
        }
      }
    });

  } catch (e) {
    console.log(e);
  }
}

async function loadActivityForecast() {

  try {

    const res = await fetch("/activity-forecast");
    const data = await res.json();

    document.getElementById("forecastStatus").textContent =
      data.ok
        ? `${data.activity} Expected`
        : "Unavailable";

  } catch (e) {
    console.log(e);
  }
}

async function loadUniqueSpeciesSpotlight() {

  try {

    const res = await fetch("/unique-species-list");
    const data = await res.json();

    uniqueSpeciesData = data.rows || [];

    updateUniqueSpeciesSpotlight();

  } catch (e) {
    console.log(e);
  }
}

function updateUniqueSpeciesSpotlight() {

  if (!uniqueSpeciesData.length) return;

  const item =
    uniqueSpeciesData[
      uniqueSpeciesIndex % uniqueSpeciesData.length
    ];

  document.getElementById("spotlightSpecies").textContent =
    item.species || "Unknown species";

  document.getElementById("spotlightSpecies").onclick = () => {
    openSpeciesModal(item.species);
  };  

  document.getElementById("spotlightStation").textContent =
    `${item.count} detections`;


  const img = document.getElementById("spotlightImage");

  img.src = item.png_url || "";

  img.style.display =
    item.png_url ? "block" : "none";

  uniqueSpeciesIndex++;
}

function formatTime(ts) {
  if (!ts || ts === "N/A") return "N/A";

  const date = new Date(ts);

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

let map = L.map("map").setView([39.8, -75.8], 12);
let markersLayer = L.layerGroup().addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
}).addTo(map);

async function loadMap() {
  const res = await fetch(`/locations?station=${currentStation}&filter=${currentFilter}`);
  const data = await res.json();

  markersLayer.clearLayers();

  data.forEach(d => {
    if (d.lat && d.lon) {
      L.marker([d.lat, d.lon])
        .addTo(markersLayer)
        .bindPopup(`Station ${d.station_id}<br>${d.species}`);
    }
  });
}

async function loadDashboard() {

  await refresh();

  await loadSummary();

  await loadTopSpecies();

  await loadSpeciesTimeline();

  await loadBestHours();

  await loadActivityForecast();

  await loadUniqueSpeciesSpotlight();

  await loadMap();
}

loadDashboard();

setInterval(() => {

  refresh();

  loadSummary();

  loadActivityForecast();

}, 30000);

setInterval(() => {

  updateUniqueSpeciesSpotlight();

}, 10000);