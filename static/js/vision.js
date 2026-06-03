// ─── HeartBits AI Vision: Face Drooping Detection ───────────────
// Uses MediaPipe Face Mesh to measure facial asymmetry in real-time.
// Sustained asymmetry only raises a manual confirmation prompt in the UI.

var HBVision = (function () {
  var faceMesh = null;
  var camera = null;
  var running = false;
  var alertCounter = 0;       // Consecutive frames with high asymmetry
  var ALERT_THRESHOLD = 15;   // % asymmetry to flag
  var ALERT_DURATION = 30;    // ~3 seconds at 10fps

  var _statusCallback = null;

  // ─── Tremor Detection (rolling buffer) ──────────────────────────
  var tremorBuffer = [];
  var TREMOR_BUFFER_SIZE = 20;

  function calcTremorIndex(buf) {
    if (buf.length < TREMOR_BUFFER_SIZE) return 0;
    var vals = [];
    for (var i = 0; i < buf.length; i++) {
      vals.push(buf[i].left);
      vals.push(buf[i].right);
    }
    var sum = 0;
    for (var i = 0; i < vals.length; i++) sum += vals[i];
    var mean = sum / vals.length;
    var sqSum = 0;
    for (var i = 0; i < vals.length; i++) {
      var d = vals[i] - mean;
      sqSum += d * d;
    }
    var stddev = Math.sqrt(sqSum / vals.length);
    return Math.min(100, Math.round(stddev * 10000));
  }

  // ─── Response Delay Tracking ────────────────────────────────────
  var asymmetryStartTime = null;
  var lastResponseDelay = 0;

  // ─── Frame Counter ──────────────────────────────────────────────
  var frameCounter = 0;

  function init(videoEl, canvasEl, statusCallback) {
    _statusCallback = statusCallback;
    var ctx = canvasEl.getContext('2d');

    faceMesh = new FaceMesh({
      locateFile: function (file) {
        return 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/' + file;
      }
    });

    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });

    var lastProcessedTime = 0;
    var processInterval = 100; // Process every 100ms (~10 FPS)

    faceMesh.onResults(function (results) {
      ctx.save();
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
      ctx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);

      if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
        var lm = results.multiFaceLandmarks[0];
        frameCounter++;

        // ─── Neon wireframe: tesselation (subtle purple) ──────────
        drawConnectors(ctx, lm, FACEMESH_TESSELATION, {
          color: 'rgba(139,92,246,0.35)', lineWidth: 0.5
        });

        // ─── Neon wireframe: key contours (brighter purple) ───────
        drawConnectors(ctx, lm, FACEMESH_FACE_OVAL, {
          color: 'rgba(139,92,246,0.8)', lineWidth: 1.5
        });
        drawConnectors(ctx, lm, FACEMESH_LIPS, {
          color: 'rgba(139,92,246,0.8)', lineWidth: 1.5
        });

        // Key landmarks: mouth corners (61 left, 291 right), forehead (10), chin (152)
        var leftMouth = lm[61];
        var rightMouth = lm[291];
        var faceH = Math.abs(lm[10].y - lm[152].y);
        var yDiff = Math.abs(leftMouth.y - rightMouth.y);
        var score = Math.min(100, Math.round((yDiff / faceH) * 500));

        // ─── Tremor buffer update ─────────────────────────────────
        tremorBuffer.push({ left: lm[61].y, right: lm[291].y });
        if (tremorBuffer.length > TREMOR_BUFFER_SIZE) tremorBuffer.shift();
        var tremorIndex = calcTremorIndex(tremorBuffer);

        // Draw mouth landmarks
        var color = score > ALERT_THRESHOLD ? '#EF4444' : '#10B981';
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(leftMouth.x * canvasEl.width, leftMouth.y * canvasEl.height, 5, 0, 2 * Math.PI);
        ctx.arc(rightMouth.x * canvasEl.width, rightMouth.y * canvasEl.height, 5, 0, 2 * Math.PI);
        ctx.fill();

        // Check sustained asymmetry
        if (score > ALERT_THRESHOLD) {
          alertCounter++;
          // ─── Response delay: mark start of asymmetry ────────────
          if (asymmetryStartTime === null) {
            asymmetryStartTime = Date.now();
          }
        } else {
          alertCounter = Math.max(0, alertCounter - 2); // Decay
          // ─── Response delay: record recovery time ───────────────
          if (asymmetryStartTime !== null) {
            lastResponseDelay = Date.now() - asymmetryStartTime;
            asymmetryStartTime = null;
          }
        }

        var isAlert = alertCounter >= (ALERT_DURATION / 3); // Adjusted for throttling

        // ─── Enhanced callback with telemetry ─────────────────────
        if (_statusCallback) {
          _statusCallback(score, isAlert, {
            tremorIndex: tremorIndex,
            responseDelay: lastResponseDelay,
            frameCount: frameCounter
          });
        }

      } else {
        if (_statusCallback) {
          _statusCallback(0, false, {
            tremorIndex: 0,
            responseDelay: lastResponseDelay,
            frameCount: frameCounter
          });
        }
      }
      ctx.restore();
    });

    camera = new Camera(videoEl, {
      onFrame: async function () {
        if (!running) return;
        var now = Date.now();
        if (now - lastProcessedTime >= processInterval) {
          lastProcessedTime = now;
          await faceMesh.send({ image: videoEl });
        }
      },
      width: 480,
      height: 360
    });

    // PRO-TIP: Send a dummy canvas to the model immediately to trigger WASM loading & compilation
    try {
      var dummyCanvas = document.createElement('canvas');
      dummyCanvas.width = 10; dummyCanvas.height = 10;
      faceMesh.send({ image: dummyCanvas });
    } catch (e) { }
  }

  function start(videoEl, canvasEl) {
    if (!faceMesh) return;
    running = true;
    alertCounter = 0;
    canvasEl.width = canvasEl.clientWidth;
    canvasEl.height = canvasEl.clientHeight;
    camera.start();
  }

  function stop() {
    running = false;
    alertCounter = 0;
    if (camera) camera.stop();
  }

  function setCallback(cb) {
    _statusCallback = cb;
  }

  function resetTelemetry() {
    tremorBuffer = [];
    asymmetryStartTime = null;
    lastResponseDelay = 0;
    frameCounter = 0;
  }

  return {
    init: init,
    start: start,
    stop: stop,
    setCallback: setCallback,
    resetTelemetry: resetTelemetry
  };
})();
