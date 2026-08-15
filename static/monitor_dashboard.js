const REFRESH_INTERVAL_MS = 30000;

let map = null;
let markersLayer = null;
let latestData = [];

let uniqueSpeciesData = [];
let uniqueSpeciesIndex = 0;

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch ${url}`);
    return await response.json();
}

function formatTime(timestamp) {
    if (!timestamp || timestamp === "N/A") return "--";

    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
}

async function loadSummary() {
    try {
        const data = await fetchJson("/summary?filter=all&station=all");

        totalDetections.textContent = data.total_detections ?? "--";
        uniqueSpecies.textContent = data.unique_species ?? "--";
        latestSpecies.textContent = data.latest_species ?? "--";
        latestTime.textContent = formatTime(data.latest_timestamp);

    } catch (error) {
        console.error("Summary error:", error);
    }
}

function initializeMap() {
    if (map) return;

    map = L.map("map", {
        zoomControl: false,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        tap: false,
        attributionControl: true
    }).setView([39.68, -75.75], 8);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "Leaflet"
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);
}

async function loadMap() {
    try {
        initializeMap();

        const data = await fetchJson("/locations?filter=all&station=all");
        markersLayer.clearLayers();

        const bounds = [];

        data.slice(0, 500).forEach(item => {
            if (!item.lat || !item.lon) return;

            L.marker([item.lat, item.lon])
                .bindPopup(`<strong>${item.species || "Unknown species"}</strong><br>Station ${item.station_id || "--"}`)
                .addTo(markersLayer);

            bounds.push([item.lat, item.lon]);
        });

        if (bounds.length > 0) {
            map.fitBounds(bounds, {
                padding: [40, 40],
                maxZoom: 14
            });
        }

        setTimeout(() => map.invalidateSize(), 200);

    } catch (error) {
        console.error("Map error:", error);
    }
}



async function loadRecentDetections() {
    try {
        const response = await fetchJson("/latest?filter=all&station=all");
        const data = response.rows || [];

        recentDetections.innerHTML = "";

        if (data.length === 0) {
            recentDetections.innerHTML = "<p>No recent detections available.</p>";
            return;
        }

        const recentPanel = document.querySelector(".recent-panel");
        const panelTitle = recentPanel.querySelector("h2");

        const availableHeight =
            recentPanel.clientHeight -
            panelTitle.offsetHeight -
            28;

        const cardHeight = 58;
        const maxCards = Math.floor(availableHeight / cardHeight);

        data.slice(0, maxCards).forEach(item => {
            const div = document.createElement("div");
            div.className = "recent-item";

            div.innerHTML = `
                <img 
                    src="${item.png_url || ''}" 
                    alt="${item.species || 'Bird'}"
                    class="recent-bird-img"
                    onerror="this.style.display='none'"
                >
                <div>
                    <strong>${item.species || "Unknown species"}</strong>
                    <p>Station ${item.station_id || "--"} • ${formatTime(item.timestamp)}</p>
                </div>
            `;

            recentDetections.appendChild(div);
        });

    } catch (error) {
        console.error("Recent detections error:", error);
    }
}

async function loadUniqueSpeciesSpotlight() {
    try {
        const response = await fetchJson("/unique-species-list");

        uniqueSpeciesData = response.rows || [];

        updateUniqueSpeciesSpotlight();

    } catch (error) {
        console.error("Unique species spotlight error:", error);
    }
}

function updateUniqueSpeciesSpotlight() {

    if (!uniqueSpeciesData || uniqueSpeciesData.length === 0) return;

    const item = uniqueSpeciesData[
        uniqueSpeciesIndex % uniqueSpeciesData.length
    ];

    console.log("Spotlight item:", item);
    console.log("Spotlight image:", item.png_url);

    spotlightSpecies.textContent =
        item.species || "Unknown species";

    spotlightStation.textContent =
        `${item.count} detections`;

    spotlightImage.src = item.png_url || "";

    spotlightImage.style.display =
        item.png_url ? "block" : "none";

    uniqueSpeciesIndex++;
}
async function loadSpeciesTimeline() {
    try {
        const response = await fetchJson("/species-timeline?filter=all&station=all");
        const data = response.rows || [];

        speciesTimeline.innerHTML = "";

        if (data.length === 0) {
            speciesTimeline.innerHTML = "<p>No species timeline available.</p>";
            return;
        }

        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

        const table = document.createElement("div");
        table.className = "timeline-table";

        const header = document.createElement("div");
        header.className = "timeline-row timeline-header";

        header.innerHTML =
            `<div class="species-name">Species</div>` +
            months.map(month => `<div class="month-label">${month}</div>`).join("");

        table.appendChild(header);

        data.slice(0, 10).forEach(speciesRow => {
            const row = document.createElement("div");
            row.className = "timeline-row";

            let cells = `<div class="species-name">${speciesRow.species}</div>`;

            for (let m = 0; m < 12; m++) {
                const quarterValues = speciesRow.values.slice(m * 4, m * 4 + 4);

                cells += `
                    <div class="timeline-month-box">
                        ${quarterValues.map(q => `
                            <div class="quarter-bar-wrap">
                                <div 
                                    class="quarter-bar"
                                    style="height:${q.percent || 0}%"
                                    title="${q.count || 0} detections"
                                ></div>
                            </div>
                        `).join("")}
                    </div>
                `;
            }

            row.innerHTML = cells;
            table.appendChild(row);
        });

        speciesTimeline.appendChild(table);

    } catch (error) {
        console.error("Species timeline error:", error);
    }
}
async function loadTopSpeciesList() {
    try {
        const response = await fetchJson("/top-species?filter=all&station=all");
        const data = response.rows || [];

        topSpeciesList.innerHTML = "";

        if (data.length === 0) {
            topSpeciesList.innerHTML = "<p>No top species available.</p>";
            return;
        }

        const maxCount = Math.max(...data.map(d => d.count));

        const wrapper = document.createElement("div");
        wrapper.className = "top-species-modern";

        data.slice(0, 5).forEach(item => {
            const widthPercent = (item.count / maxCount) * 100;

            const row = document.createElement("div");
            row.className = "top-species-modern-row";

            row.innerHTML = `
                <img 
                    src="${item.png_url || ''}" 
                    class="top-species-modern-img"
                    onerror="this.style.display='none'"
                >

                <div class="top-species-modern-content">
                    <div class="top-species-modern-name">
                        ${item.species}
                    </div>

                    <div class="top-species-modern-bar-bg">
                        <div 
                            class="top-species-modern-bar"
                            style="width:${widthPercent}%"
                        ></div>
                    </div>
                </div>
            `;

            wrapper.appendChild(row);
        });

        topSpeciesList.appendChild(wrapper);

    } catch (error) {
        console.error("Top species error:", error);
    }
}

let bestHoursChart = null;

async function loadBestHours() {
    try {
        const response = await fetchJson("/best-hours");

        const hours = response.hours || [];

        bestHoursList.innerHTML = "";

        if (hours.length === 0) {
            bestHoursList.innerHTML = "<p>No data available.</p>";
            return;
        }

        bestHoursList.innerHTML = hours
            .map(hour => `
                <div class="best-hour-pill">${hour}</div>
            `)
            .join("");

        const ctx = document.getElementById("bestHoursChart");

        if (bestHoursChart) {
            bestHoursChart.destroy();
        }

        bestHoursChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: response.chart_labels,
                datasets: [{
                    data: response.chart_counts,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: "#cbd5e1",
                            font: {
                                size: 9
                            }
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

    } catch (error) {
        console.error("Best hours error:", error);
    }
}
async function loadActivityForecast() {
    try {
        const response = await fetchJson("/activity-forecast");

        if (!response.ok) {
            forecastStatus.textContent = "Unavailable";
            return;
        }

        forecastStatus.textContent = `${response.activity} Expected`;

    } catch (error) {
        console.error("Activity forecast error:", error);
    }
}
async function loadMonitorDashboard() {
    await loadSummary();
    await loadMap();
    await loadRecentDetections();
    await loadSpeciesTimeline();
    await loadTopSpeciesList();
    await loadBestHours();
    await loadActivityForecast();
    await loadUniqueSpeciesSpotlight();
}

document.addEventListener("DOMContentLoaded", async () => {
    await loadMonitorDashboard();

    setInterval(loadMonitorDashboard, REFRESH_INTERVAL_MS);

    setInterval(() => {
        updateUniqueSpeciesSpotlight();
    }, 10000);
});
