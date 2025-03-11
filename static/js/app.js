// Global Variables
let acousticData = null;
let trajectoryPoints = [];
let map = null;
let currentPointIndex = -1;
let currentChannelIndex = 0;
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
        
        // Add hover effect
        map.on('mouseenter', 'trajectory-points', function(e) {
            map.getCanvas().style.cursor = 'pointer';
            
            const coordinates = e.features[0].geometry.coordinates.slice();
            const time = new Date(e.features[0].properties.time).toLocaleString();
            
            tooltip.innerHTML = `<strong>Time:</strong> ${time}`;
            tooltip.style.left = e.point.x + 'px';
            tooltip.style.top = e.point.y + 'px';
            tooltip.style.opacity = 1;
        });
        
        map.on('mouseleave', 'trajectory-points', function() {
            map.getCanvas().style.cursor = '';
            tooltip.style.opacity = 0;
        });
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
        const timeStr = new Date(feature.properties.time).toLocaleString();
        
        currentPointIndex = pointIndex;

        // Update point info display
        document.getElementById('pointInfo').classList.remove('hidden');
        document.getElementById('pointCoords').textContent = `${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}`;
        document.getElementById('pointTime').textContent = timeStr;
        
        // Show time selector
        document.getElementById('timeSelector').classList.remove('hidden');
        
        // Set default time values based on selected point
        const pointTime = new Date(feature.properties.time);
        
        // Set default start time to 30 minutes before point time
        const startTime = new Date(pointTime);
        startTime.setMinutes(startTime.getMinutes() - 30);
        
        // Set default end time to 30 minutes after point time
        const endTime = new Date(pointTime);
        endTime.setMinutes(endTime.getMinutes() + 30);
        
        // Format for datetime-local input (YYYY-MM-DDThh:mm)
        document.getElementById('startTime').value = formatDateTimeLocal(startTime);
        document.getElementById('endTime').value = formatDateTimeLocal(endTime);
        
        // Fetch and display echogram for single point
        fetchEchogram();
    }
}

// Format date for datetime-local input
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Fetch and Display Echogram
async function fetchEchogram(isTimeRange = false) {
    if (currentPointIndex < 0) return;
    
    const echogramDiv = document.getElementById('echogram');
    echogramDiv.innerHTML = '<div class="loading">Loading echogram...</div>';
    
    try {
        // Get current settings
        const channelIndex = parseInt(document.getElementById('channelSelector').value);
        const vmin = document.getElementById('vminSlider').value;
        const vmax = document.getElementById('vmaxSlider').value;
        
        // Construct URL with parameters
        let url = `/api/echogram?pointIndex=${currentPointIndex}&channelIndex=${channelIndex}&vmin=${vmin}&vmax=${vmax}`;
        
        // Add time range parameters if requested
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
        
        // Create iframe to display the echogram
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.width = '100%';
        iframe.height = '100%';
        iframe.style.border = 'none';
        iframe.onload = function() {
            // Remove loading indicator when iframe loads
            const loadingEl = echogramDiv.querySelector('.loading');
            if (loadingEl) loadingEl.remove();
        };
        
        // Clear and add iframe
        echogramDiv.innerHTML = '';
        echogramDiv.appendChild(iframe);
        
    } catch (error) {
        console.error('Error fetching echogram:', error);
        echogramDiv.innerHTML = '<p class="error">Failed to load echogram. Please try again.</p>';
    }
}

// Generate echogram for time range
function generateRangeEchogram() {
    fetchEchogram(true);
}

// Event Listeners
function setupEventListeners() {
    // Slider event listeners with debounce to reduce server load
    let debounceTimer;
    const debounceDelay = 300; // ms
    
    document.getElementById('vminSlider').addEventListener('input', function(e) {
        document.getElementById('vminValue').textContent = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(updateEchogram, debounceDelay);
    });
    
    document.getElementById('vmaxSlider').addEventListener('input', function(e) {
        document.getElementById('vmaxValue').textContent = e.target.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(updateEchogram, debounceDelay);
    });
    
    document.getElementById('channelSelector').addEventListener('change', updateEchogram);
    
    // Time range echogram generation
    document.getElementById('generateRangeEchogram').addEventListener('click', generateRangeEchogram);
}

// Update Echogram when parameters change
function updateEchogram() {
    if (currentPointIndex >= 0) {
        fetchEchogram();
    }
}