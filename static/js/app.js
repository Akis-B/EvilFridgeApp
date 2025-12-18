const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const previewContainer = document.getElementById('previewContainer');
const previewImage = document.getElementById('previewImage');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const errorDiv = document.getElementById('error');
const welcomeScreen = document.getElementById('welcomeScreen');
const appShell = document.getElementById('appShell');
const playBtn = document.getElementById('playBtn');
const scene = document.querySelector('.scene');
const wheelWrap = document.getElementById('wheelWrap');
const wheel = document.getElementById('wheel');
const spinBtn = document.getElementById('spinBtn');
const wheelText = document.getElementById('wheelText');
const outcomeBadge = document.getElementById('outcomeBadge');
const wheelLoading = document.getElementById('wheelLoading');
const itemsDetected = document.getElementById('itemsDetected');

let selectedFile = null;
let lastItems = [];
let lastNonFridgeItems = [];
let spinning = false;
let firstSpinDone = false;
let tickTimer = null;
let audioCtx = null;
let loadingTimer = null;

// Wheel rotation logic - using exact logic from example
let currentRotation = 0;
let lastResult = "None"; // Variable to store the result

const segments = [
    { id: 'environmental_destruction', name: "Environmental Destruction", rotate: 0 },
    { id: 'weapon_manufacturing', name: "Mischief Engineering", rotate: 240 },
    { id: 'general_chaos', name: "General Chaos", rotate: 120 }
];

// Function to get the current result
function getResult() {
    console.log("Current Wheel Result:", lastResult);
    return lastResult;
}

// Loading animation for recipe text
function startLoadingAnimation() {
    let dots = 1;
    wheelText.textContent = 'Loading.';
    loadingTimer = setInterval(() => {
        dots = (dots % 3) + 1;
        wheelText.textContent = 'Loading' + '.'.repeat(dots);
    }, 500);
}

function stopLoadingAnimation() {
    if (loadingTimer) {
        clearInterval(loadingTimer);
        loadingTimer = null;
    }
}

playBtn.addEventListener('click', () => {
    document.body.classList.add('alert');
    scene.classList.add('alert');
    setTimeout(() => {
        document.body.classList.remove('alert');
        scene.classList.remove('alert');
    }, 450);
    welcomeScreen.classList.add('dismiss');
    appShell.classList.add('show');
    playClick();
});

function setEvilPersistent() {
    document.body.classList.add('alert');
    scene.classList.add('alert');
}

function flashFridge() {
    document.body.classList.add('alert');
    scene.classList.add('alert');
    setTimeout(() => {
        document.body.classList.remove('alert');
        scene.classList.remove('alert');
    }, 600);
    // keep evil state after a spin
    setEvilPersistent();
}

uploadArea.addEventListener('click', () => {
    fileInput.click();
    playClick();
});

fileInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
    playClick();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
    playClick();
});

function handleFile(file) {
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showError('Please upload an image file');
        return;
    }

    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        previewContainer.style.display = 'block';
    };
    reader.readAsDataURL(file);

    analyzeBtn.disabled = false;
    results.classList.remove('show');
    errorDiv.classList.remove('show');
}

analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    loading.classList.add('show');
    results.classList.remove('show');
    errorDiv.classList.remove('show');
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append('image', selectedFile);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            displayResults(data.items || data.fridge_items, data.non_fridge_items || []);
        } else {
            showError(data.error || 'An error occurred');
        }
    } catch (error) {
        showError('Failed to connect to server: ' + error.message);
    } finally {
        loading.classList.remove('show');
        analyzeBtn.disabled = false;
    }
});

function displayResults(items, nonFridgeItems) {
    lastItems = items;
    lastNonFridgeItems = nonFridgeItems || [];
    wheelText.textContent = '';
    outcomeBadge.textContent = 'Awaiting spin...';
    firstSpinDone = false;
    spinBtn.textContent = 'Spin';

    // Display detected items
    let itemsHTML = '<div style="margin-bottom: 20px;">';
    if (items && items.length > 0) {
        itemsHTML += '<div style="background: rgba(47, 223, 134, 0.1); border: 1px solid rgba(47, 223, 134, 0.3); border-radius: 12px; padding: 12px; margin-bottom: 10px;">';
        itemsHTML += '<strong style="color: #2fdf86;">Items in Fridge:</strong> ';
        itemsHTML += items.join(', ');
        itemsHTML += '</div>';
    }
    itemsHTML += '</div>';
    itemsDetected.innerHTML = itemsHTML;

    if (!items.length) {
        wheelWrap.classList.remove('show');
        showError('No items detected in the image.');
    } else {
        errorDiv.classList.remove('show');
        wheelWrap.classList.add('show');
        results.classList.add('show');
        setEvilPersistent();
    }
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}

function spinWheel() {
    if (!lastItems.length) {
        showError('Please analyze a fridge image first.');
        return;
    }
    if (spinning) return;
    spinning = true;
    spinBtn.disabled = true;
    errorDiv.classList.remove('show');
    wheelText.textContent = '';
    flashFridge();
    startTicks();

    // === EXACT LOGIC FROM EXAMPLE CODE ===
    // 1. Determine winner
    const winnerIndex = Math.floor(Math.random() * 3);
    const winner = segments[winnerIndex];
    lastResult = winner.name; // Store result

    // 2. Calculate smooth rotation
    const extraSpins = 5 * 360;
    const segmentAngle = 120;
    const targetAngle = winner.rotate + (segmentAngle / 2);

    // Add to current rotation to keep spinning forward
    currentRotation += extraSpins + (360 - (currentRotation % 360)) + (360 - targetAngle);

    // 3. Execute animation
    wheel.style.transform = `rotate(${currentRotation}deg)`;

    wheelLoading.classList.add('show');
    outcomeBadge.textContent = "Consulting the evil fridge...";

    // Hide loading text when wheel starts decelerating
    setTimeout(() => {
        wheelLoading.classList.remove('show');
    }, 3000);

    // 4. Handle completion
    setTimeout(async () => {
        stopTicks();
        outcomeBadge.textContent = "RESULT: " + lastResult;

        // Output result to console automatically
        getResult();

        await handleOutcome(winner);
    }, 4000); // Matches CSS duration
}

async function handleOutcome(choice) {
    // Show the result
    outcomeBadge.textContent = `RESULT: ${choice.name}`;
    firstSpinDone = true;
    spinBtn.textContent = 'Spin Again';

    // Start loading animation in recipe text box
    startLoadingAnimation();

    try {
        const response = await fetch('/chaos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                items: lastItems,
                non_fridge_items: lastNonFridgeItems,
                category: choice.id
            })
        });
        const data = await response.json();
        stopLoadingAnimation();
        if (response.ok && data.result) {
            wheelText.textContent = data.result;
        } else {
            showError(data.error || 'Failed to get a result.');
        }
    } catch (err) {
        stopLoadingAnimation();
        showError('Failed to get a result: ' + err.message);
    } finally {
        spinning = false;
        wheelLoading.classList.remove('show');
        spinBtn.disabled = false;
        if (firstSpinDone) {
            spinBtn.style.display = 'block';
        }
    }
}

spinBtn.addEventListener('click', spinWheel);

function ensureAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playTone(freq = 440, duration = 0.08, type = 'sine', volume = 0.08) {
    ensureAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
}

function playClick() {
    playTone(320, 0.05, 'square', 0.05);
}

function playTick() {
    playTone(900, 0.03, 'sine', 0.04);
}

function startTicks() {
    stopTicks();
    tickTimer = setInterval(playTick, 140);
}

function stopTicks() {
    if (tickTimer) {
        clearInterval(tickTimer);
        tickTimer = null;
    }
}
