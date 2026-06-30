// ─── NovaMed AI Vision: Face Drooping Detection ───────────────
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

  // ─── Calibration State ──────────────────────────────────────────
  var calibrationState = 'idle'; // 'idle', 'neutral', 'smile'
  var calibrationFrames = 30;
  var calibrationData = [];
  var calibrationWidths = [];
  
  var neutralBaseline = 0;
  var smileBaseline = 0;
  var neutralMouthWidth = 0;

  function loadFaceProfile() {
    try {
      var profile = JSON.parse(localStorage.getItem('SAVN_FaceProfile'));
      if (profile) {
        neutralBaseline = profile.neutral || 0;
        smileBaseline = profile.smile || 0;
        neutralMouthWidth = profile.width || 0;
      }
    } catch(e) {}
  }

  function saveFaceProfile() {
    try {
      localStorage.setItem('SAVN_FaceProfile', JSON.stringify({
        neutral: neutralBaseline,
        smile: smileBaseline,
        width: neutralMouthWidth
      }));
    } catch(e) {}
  }

  function startCalibration(state) {
    if (state === 'neutral' || state === 'smile') {
      calibrationState = state;
      calibrationData = [];
      calibrationWidths = [];
    } else {
      calibrationState = 'idle';
    }
  }

  function init(videoEl, canvasEl, statusCallback) {
    loadFaceProfile();
    _statusCallback = statusCallback;
    var ctx = canvasEl.getContext('2d');

    faceMesh = new FaceMesh({
      locateFile: function (file) {
        return 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/' + file;
      }
    });

    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: false,
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

        // Key landmark for scale: forehead (10), chin (152)
        var faceH = Math.abs(lm[10].y - lm[152].y);

        // ─── Head Pose Compensation (Roll) ──────────────────────────
        var eyeOuterLeft = lm[33];
        var eyeOuterRight = lm[263];
        var theta = Math.atan2(eyeOuterLeft.y - eyeOuterRight.y, eyeOuterLeft.x - eyeOuterRight.x);
        var sinNegTheta = Math.sin(-theta);
        var cosNegTheta = Math.cos(-theta);

        // ─── Multi-Region Asymmetry Detection ───────────────────────
        var regions = [
          { name: 'mouth', leftIdx: 61, rightIdx: 291 },
          { name: 'eye_lower', leftIdx: 145, rightIdx: 374 },
          { name: 'eyebrow', leftIdx: 70, rightIdx: 300 },
          { name: 'cheek', leftIdx: 50, rightIdx: 280 }
        ];

        var maxScore = 0;
        var regionScores = [];

        for (var i = 0; i < regions.length; i++) {
          var leftPt = lm[regions[i].leftIdx];
          var rightPt = lm[regions[i].rightIdx];

          // Rotate points back by -theta around their midpoint to neutralize tilt
          var midX = (leftPt.x + rightPt.x) / 2;
          var midY = (leftPt.y + rightPt.y) / 2;

          var leftCorrectedY = (leftPt.x - midX) * sinNegTheta + (leftPt.y - midY) * cosNegTheta + midY;
          var rightCorrectedY = (rightPt.x - midX) * sinNegTheta + (rightPt.y - midY) * cosNegTheta + midY;

          var yDiff = Math.abs(leftCorrectedY - rightCorrectedY);
          var rScore = Math.min(100, Math.round((yDiff / faceH) * 500));
          
          regionScores.push({
            name: regions[i].name,
            score: rScore,
            leftPt: leftPt,
            rightPt: rightPt
          });

          if (rScore > maxScore) {
            maxScore = rScore;
          }
        }

        var score = maxScore;

        // Measure current mouth width for expression detection
        var leftMouth = lm[61];
        var rightMouth = lm[291];
        var mouthWidth = Math.sqrt(Math.pow(leftMouth.x - rightMouth.x, 2) + Math.pow(leftMouth.y - rightMouth.y, 2));

        // ─── Calibration Logic ────────────────────────────────────
        if (calibrationState === 'neutral') {
          calibrationData.push(score);
          calibrationWidths.push(mouthWidth);
          if (calibrationData.length >= calibrationFrames) {
            var sumScore = 0;
            var sumWidth = 0;
            for (var i = 0; i < calibrationData.length; i++) {
              sumScore += calibrationData[i];
              sumWidth += calibrationWidths[i];
            }
            neutralBaseline = Math.round(sumScore / calibrationFrames);
            neutralMouthWidth = sumWidth / calibrationFrames;
            calibrationState = 'idle';
            saveFaceProfile();
          }
        } else if (calibrationState === 'smile') {
          calibrationData.push(score);
          if (calibrationData.length >= calibrationFrames) {
            var sumScore = 0;
            for (var i = 0; i < calibrationData.length; i++) {
              sumScore += calibrationData[i];
            }
            smileBaseline = Math.round(sumScore / calibrationFrames);
            calibrationState = 'idle';
            saveFaceProfile();
          }
        }

        var isCalibrating = (calibrationState !== 'idle');
        var isSmiling = neutralMouthWidth > 0 && mouthWidth > neutralMouthWidth * 1.08;
        var currentBaseline = isSmiling ? smileBaseline : neutralBaseline;
        var finalScore = isCalibrating ? 0 : Math.max(0, score - currentBaseline);

        // ─── Tremor buffer update ─────────────────────────────────
        tremorBuffer.push({ left: lm[61].y, right: lm[291].y });
        if (tremorBuffer.length > TREMOR_BUFFER_SIZE) tremorBuffer.shift();
        var tremorIndex = calcTremorIndex(tremorBuffer);

        // Draw landmarks for all tracked regions
        for (var i = 0; i < regionScores.length; i++) {
          var rs = regionScores[i];
          var regionFinal = isCalibrating ? 0 : Math.max(0, rs.score - currentBaseline);
          var color = regionFinal > ALERT_THRESHOLD ? '#EF4444' : '#10B981';
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(rs.leftPt.x * canvasEl.width, rs.leftPt.y * canvasEl.height, 4, 0, 2 * Math.PI);
          ctx.arc(rs.rightPt.x * canvasEl.width, rs.rightPt.y * canvasEl.height, 4, 0, 2 * Math.PI);
          ctx.fill();
        }

        // Check sustained asymmetry
        if (finalScore > ALERT_THRESHOLD) {
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
          _statusCallback(finalScore, isAlert, {
            tremorIndex: tremorIndex,
            responseDelay: lastResponseDelay,
            frameCount: frameCounter,
            isCalibrating: isCalibrating,
            calibrationState: calibrationState,
            calibrationProgress: isCalibrating ? Math.round((calibrationData.length / calibrationFrames) * 100) : 100
          });
        }

      } else {
        if (_statusCallback) {
          _statusCallback(0, false, {
            tremorIndex: 0,
            responseDelay: lastResponseDelay,
            frameCount: frameCounter,
            isCalibrating: isCalibrating,
            calibrationState: calibrationState,
            calibrationProgress: isCalibrating ? Math.round((calibrationData.length / calibrationFrames) * 100) : 100
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
    startCalibration('neutral');
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
    resetTelemetry: resetTelemetry,
    startCalibration: startCalibration
  };
})();
