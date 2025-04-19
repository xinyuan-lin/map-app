// Global Variables
let acousticData = null;
let trajectoryPoints = [];
let map = null;
let currentPointIndex = -1;
let currentChannelIndex = 0;
let tooltip = document.getElementById('mapTooltip');
let trajectoryGeoJson = null; // 缓存轨迹数据

const basemapStyles = {
    osm: {
        version: 8,
        sources: {
            'osm-tiles': {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '© OpenStreetMap contributors'
            }
        },
        layers: [{
            id: 'osm-tiles',
            type: 'raster',
            source: 'osm-tiles'
        }]
    },
    terrain: {
        version: 8,
        sources: {
            'terrain-tiles': {
                type: 'raster',
                tiles: ['https://a.tile.opentopomap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '© OpenTopoMap'
            }
        },
        layers: [{
            id: 'terrain-tiles',
            type: 'raster',
            source: 'terrain-tiles'
        }]
    },
    ocean: {
        version: 8,
        sources: {
            'ocean-tiles': {
                type: 'raster',
                tiles: ['https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}'],
                tileSize: 256,
                attribution: '© Esri Ocean Basemap'
            }
        },
        layers: [{
            id: 'ocean-tiles',
            type: 'raster',
            source: 'ocean-tiles'
        }]
    }
};

function highlightTrajectoryInRange(startTime, endTime) {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const filteredCoords = trajectoryPoints
        .filter(p => {
            const pointTime = new Date(p.time);
            return pointTime >= start && pointTime <= end;
        })
        .map(p => [p.lng, p.lat]);

    const geojson = {
        type: 'FeatureCollection',
        features: [{
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: filteredCoords
            }
        }]
    };

    if (!map.getSource('highlighted-trajectory')) {
        map.addSource('highlighted-trajectory', {
            type: 'geojson',
            data: geojson
        });
        map.addLayer({
            id: 'highlighted-trajectory-line',
            type: 'line',
            source: 'highlighted-trajectory',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#00cc44',
                'line-width': 5,
                'line-opacity': 0.8
            }
        });
    } else {
        map.getSource('highlighted-trajectory').setData(geojson);
    }
}

function updateHighlightedTrajectory() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    
    if (startTime && endTime) {
        highlightTrajectoryInRange(startTime, endTime);
    }
}

function generateRangeEchogram() {
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    if (startTime && endTime) {
        highlightTrajectoryInRange(startTime, endTime);
        fetchEchogram(true);
    } else {
        alert('Please select both start and end times');
    }
}

function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: basemapStyles['osm'],
        center: [-40, -60],
        zoom: 3
    });

    map.addControl(new maplibregl.NavigationControl());

    map.on('load', function () {
        if (trajectoryPoints.length > 0) {
            addTrajectoryToMap();
        }
    });
}

document.addEventListener('DOMContentLoaded', async function () {
    initMap();

    try {
        await loadAcousticData();
        document.getElementById('loading').classList.add('hidden');
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('loading').textContent = 'Error loading data. Please refresh the page.';
    }

    setupEventListeners();
});

async function loadAcousticData() {
    try {
        const response = await fetch('/api/acoustic-data');
        if (!response.ok) {
            throw new Error(`Server responded with error: ${response.status}`);
        }

        const text = await response.text();
        acousticData = JSON.parse(text);
        console.log('Loaded acoustic data:', acousticData.latitude.length, 'points');

        acousticData.latitude = acousticData.latitude.map(val => val === null ? -60 : val);
        acousticData.longitude = acousticData.longitude.map(val => val === null ? -40 : val);

        extractTrajectoryPoints();
        if (map) {
            addTrajectoryToMap();
        }
    } catch (error) {
        console.error('Error loading acoustic data:', error);
        throw error;
    }
}

function extractTrajectoryPoints() {
    if (!acousticData) return;

    trajectoryPoints = [];
    const { latitude, longitude, time } = acousticData;

    for (let i = 0; i < latitude.length; i++) {
        if (latitude[i] === null || longitude[i] === null) continue;

        trajectoryPoints.push({
            lat: latitude[i],
            lng: longitude[i],
            time: new Date(time[i] || '2017-07-24T00:00:00'),
            index: i
        });
    }

    trajectoryGeoJson = {
        type: 'FeatureCollection',
        features: [{
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: trajectoryPoints.map(p => [p.lng, p.lat])
            }
        }]
    };
}

function addTrajectoryToMap() {
    console.log('🛰️ RE-ADDING TRAJECTORY', trajectoryPoints.length);
    if (!map || !trajectoryPoints.length || !trajectoryGeoJson) return;

    if (!map.getSource('trajectory')) {
        map.addSource('trajectory', {
            type: 'geojson',
            data: trajectoryGeoJson
        });

        map.addLayer({
            id: 'trajectory-line',
            type: 'line',
            source: 'trajectory',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: { 'line-color': '#0080ff', 'line-width': 3, 'line-opacity': 0.8 }
        });
    }

    const pointFeatures = trajectoryPoints.map(p => ({
        type: 'Feature',
        properties: { index: p.index, time: p.time.toISOString() },
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] }
    }));

    const pointsGeoJson = { type: 'FeatureCollection', features: pointFeatures };

    if (!map.getSource('trajectory-points')) {
        map.addSource('trajectory-points', { type: 'geojson', data: pointsGeoJson });
        map.addLayer({
            id: 'trajectory-points',
            type: 'circle',
            source: 'trajectory-points',
            paint: {
                'circle-radius': 4,
                'circle-color': '#ff4400',
                'circle-stroke-width': 1,
                'circle-stroke-color': '#ffffff'
            }
        });

        map.on('click', 'trajectory-points', handlePointClick);
        map.on('mouseenter', 'trajectory-points', function (e) {
            map.getCanvas().style.cursor = 'pointer';
            const coordinates = e.features[0].geometry.coordinates.slice();
            const time = new Date(e.features[0].properties.time).toLocaleString();
            tooltip.innerHTML = `<strong>Time:</strong> ${time}`;
            tooltip.style.left = e.point.x + 'px';
            tooltip.style.top = e.point.y + 'px';
            tooltip.style.opacity = 1;
        });
        map.on('mouseleave', 'trajectory-points', function () {
            map.getCanvas().style.cursor = '';
            tooltip.style.opacity = 0;
        });
    }
}

function switchBasemapStyle(styleKey) {
    if (!basemapStyles[styleKey]) return;

    const currentCenter = map.getCenter();
    const currentZoom = map.getZoom();

    map.setStyle(basemapStyles[styleKey]);

    const waitForStyleLoad = setInterval(() => {
        if (map.isStyleLoaded()) {
            clearInterval(waitForStyleLoad);
            map.setCenter(currentCenter);
            map.setZoom(currentZoom);
            addTrajectoryToMap();
            
            // Re-highlight trajectory after style change if there's a time range selected
            const startTime = document.getElementById('startTime').value;
            const endTime = document.getElementById('endTime').value;
            if (startTime && endTime) {
                highlightTrajectoryInRange(startTime, endTime);
            }
            
            console.log('✅ Style loaded, trajectory redrawn');
        }
    }, 100);
}

function handlePointClick(e) {
    if (e.features.length > 0) {
        const feature = e.features[0];
        const pointIndex = feature.properties.index;
        const coords = feature.geometry.coordinates;
        const timeStr = new Date(feature.properties.time).toLocaleString();

        currentPointIndex = pointIndex;

        document.getElementById('pointInfo').classList.remove('hidden');
        document.getElementById('pointCoords').textContent = `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}`;
        document.getElementById('pointTime').textContent = timeStr;

        document.getElementById('timeSelector').classList.remove('hidden');

        const pointTime = new Date(feature.properties.time);
        const startTime = new Date(pointTime);
        const endTime = new Date(pointTime);
        startTime.setMinutes(startTime.getMinutes() - 30);
        endTime.setMinutes(endTime.getMinutes() + 30);

        document.getElementById('startTime').value = formatDateTimeLocal(startTime);
        document.getElementById('endTime').value = formatDateTimeLocal(endTime);

        // Highlight the trajectory for the initial time range
        updateHighlightedTrajectory();
        
        fetchEchogram();
    }
}

function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

async function fetchEchogram(isTimeRange = false) {
    if (currentPointIndex < 0) return;

    const echogramDiv = document.getElementById('echogram');
    echogramDiv.innerHTML = '<div class="loading">Loading echogram...</div>';

    try {
        const channelIndex = parseInt(document.getElementById('channelSelector').value);
        const vmin = document.getElementById('vminSlider').value;
        const vmax = document.getElementById('vmaxSlider').value;

        let url = `/api/echogram?pointIndex=${currentPointIndex}&channelIndex=${channelIndex}&vmin=${vmin}&vmax=${vmax}`;

        if (isTimeRange) {
            const startTime = document.getElementById('startTime').value;
            const endTime = document.getElementById('endTime').value;
            if (startTime && endTime) {
                url += `&startTime=${encodeURIComponent(startTime)}&endTime=${encodeURIComponent(endTime)}`;
            } else {
                alert('Please select both start and end times');
                return;
            }
        }

        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.width = '100%';
        iframe.height = '100%';
        iframe.style.border = 'none';
        iframe.onload = function () {
            const loadingEl = echogramDiv.querySelector('.loading');
            if (loadingEl) loadingEl.remove();
        };

        echogramDiv.innerHTML = '';
        echogramDiv.appendChild(iframe);

    } catch (error) {
        console.error('Error fetching echogram:', error);
        echogramDiv.innerHTML = '<p class="error">Failed to load echogram. Please try again.</p>';
    }
}

function setupEventListeners() {
    let debounceTimer;
    const debounceDelay = 300;

    document.getElementById('vminSlider').addEventListener('input', function (e) {
        document.getElementById('vminValue').textContent = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(updateEchogram, debounceDelay);
    });

    document.getElementById('vmaxSlider').addEventListener('input', function (e) {
        document.getElementById('vmaxValue').textContent = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(updateEchogram, debounceDelay);
    });

    document.getElementById('basemapSelector').addEventListener('change', function (e) {
        const selectedStyle = e.target.value;
        switchBasemapStyle(selectedStyle);
    });

    document.getElementById('channelSelector').addEventListener('change', updateEchogram);
    document.getElementById('generateRangeEchogram').addEventListener('click', generateRangeEchogram);
    
    // Add event listeners for time selectors to update highlighted trajectory
    document.getElementById('startTime').addEventListener('change', updateHighlightedTrajectory);
    document.getElementById('endTime').addEventListener('change', updateHighlightedTrajectory);
}

function updateEchogram() {
    if (currentPointIndex >= 0) {
        fetchEchogram();
    }
}