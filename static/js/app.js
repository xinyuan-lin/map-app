// Global Variables
let acousticData = null;
let trajectoryPoints = [];
let map = null;
let currentPointIndex = -1;
let tooltip = document.getElementById('mapTooltip');

// Initialize the application
document.addEventListener('DOMContentLoaded', async function() {
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

// Initialize Maplibre Map
function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: {
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
                source: 'osm-tiles',
                minzoom: 0,
                maxzoom: 19
            }]
        },
        center: [-40, -60], // Default center, will update after loading data
        zoom: 3
    });

    map.addControl(new maplibregl.NavigationControl());
    
    map.on('load', function() {
        if (trajectoryPoints.length > 0) {
            addTrajectoryToMap();
        }
    });
}

// Load Acoustic Data
async function loadAcousticData() {
    try {
        const response = await fetch('/api/acoustic-data');
        if (!response.ok) {
            throw new Error(`Server responded with error: ${response.status}`);
        }
        
        const text = await response.text();
        try {
            acousticData = JSON.parse(text);
            console.log('Loaded acoustic data:', acousticData.latitude.length, 'points');

            acousticData.latitude = acousticData.latitude.map(val => val === null ? -60 : val);
            acousticData.longitude = acousticData.longitude.map(val => val === null ? -40 : val);

            extractTrajectoryPoints();
            if (map) {
                addTrajectoryToMap();
            }
        } catch (error) {
            console.error('Error parsing JSON:', error);
            console.error('Received response:', text.substring(0, 500) + '...');
            throw error;
        }
    } catch (error) {
        console.error('Error loading acoustic data:', error);
        throw error;
    }
}

// Extract Trajectory Points
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

    if (trajectoryPoints.length > 0 && map) {
        const bounds = new maplibregl.LngLatBounds();
        trajectoryPoints.forEach(point => {
            bounds.extend([point.lng, point.lat]);
        });
        
        map.fitBounds(bounds, { padding: 50 });
    }
}

// Add Trajectory to Map
function addTrajectoryToMap() {
    if (!map || !trajectoryPoints.length) return;

    if (!map.getSource('trajectory')) {
        map.addSource('trajectory', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: [{
                    type: 'Feature',
                    geometry: { type: 'LineString', coordinates: trajectoryPoints.map(p => [p.lng, p.lat]) }
                }]
            }
        });

        map.addLayer({
            id: 'trajectory-line',
            type: 'line',
            source: 'trajectory',
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: { 'line-color': '#0080ff', 'line-width': 3, 'line-opacity': 0.8 }
        });
    } else {
        map.getSource('trajectory').setData({
            type: 'FeatureCollection',
            features: [{
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: trajectoryPoints.map(p => [p.lng, p.lat]) }
            }]
        });
    }

    if (!map.getSource('trajectory-points')) {
        map.addSource('trajectory-points', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: trajectoryPoints.map(p => ({
                    type: 'Feature',
                    properties: { index: p.index, time: p.time.toISOString() },
                    geometry: { type: 'Point', coordinates: [p.lng, p.lat] }
                }))
            }
        });

        map.addLayer({
            id: 'trajectory-points',
            type: 'circle',
            source: 'trajectory-points',
            paint: { 'circle-radius': 4, 'circle-color': '#ff4400', 'circle-stroke-width': 1, 'circle-stroke-color': '#ffffff' }
        });

        map.on('click', 'trajectory-points', handlePointClick);
    } else {
        map.getSource('trajectory-points').setData({
            type: 'FeatureCollection',
            features: trajectoryPoints.map(p => ({
                type: 'Feature',
                properties: { index: p.index, time: p.time.toISOString() },
                geometry: { type: 'Point', coordinates: [p.lng, p.lat] }
            }))
        });
    }
}

// Handle Click Event on Trajectory Points
function handlePointClick(e) {
    if (e.features.length > 0) {
        const feature = e.features[0];
        const pointIndex = feature.properties.index;
        const coords = feature.geometry.coordinates;
        
        currentPointIndex = pointIndex;

        fetchEchogram(pointIndex, coords);
    }
}

// // Fetch and Display Echogram
// async function fetchEchogram(pointIndex, coords) {
//     try {
//         const response = await fetch(`/api/echogram?pointIndex=${pointIndex}&channelIndex=0`);
//         if (!response.ok) {
//             throw new Error(`Server responded with error: ${response.status}`);
//         }
        
//         const echogramHtml = await response.text();
        
//         // Display in a popup
//         new maplibregl.Popup()
//             .setLngLat(coords)
//             .setHTML(echogramHtml)
//             .addTo(map);

//     } catch (error) {
//         console.error('Error fetching echogram:', error);
//         alert('Failed to load echogram. Please try again.');
//     }
// }

async function fetchEchogram(pointIndex, coords) {
    try {
        const response = await fetch(`/api/echogram?pointIndex=${pointIndex}&channelIndex=0`);
        if (!response.ok) {
            throw new Error(`Server responded with error: ${response.status}`);
        }

        // Create an iframe to load the echogram HTML file
        const iframe = `<iframe src="/api/echogram?pointIndex=${pointIndex}&channelIndex=0" width="600px" height="400px"></iframe>`;

        // Display echogram in a popup
        new maplibregl.Popup()
            .setLngLat(coords)
            .setHTML(iframe)
            .addTo(map);

    } catch (error) {
        console.error('Error fetching echogram:', error);
        alert('Failed to load echogram. Please try again.');
    }
}



// Event Listeners
function setupEventListeners() {
    document.getElementById('vminSlider').addEventListener('input', updateEchogram);
    document.getElementById('vmaxSlider').addEventListener('input', updateEchogram);
    document.getElementById('channelSelector').addEventListener('change', updateEchogram);
}

// Update Echogram when parameters change
function updateEchogram() {
    if (currentPointIndex >= 0) {
        fetchEchogram(currentPointIndex);
    }
}
