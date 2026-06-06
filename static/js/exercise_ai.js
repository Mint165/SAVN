// ─── HeartBits AI Exercise Trainer: Pose Estimation ─────────────────
// Uses MediaPipe Pose to analyze senior rehabilitation exercises.
// Tracks arm angles and guides the user through correct movements.

var HBExerciseAI = (function () {
  'use strict';

  var pose = null;
  var camera = null;
  var running = false;
  
  var _onStatusUpdate = null;
  var _onCompleted = null;
  
  var repsCount = 0;
  var targetReps = 10;
  var isArmRaised = false;
  var frameCount = 0;

  // Initialize MediaPipe Pose
  function init(videoEl, canvasEl, onStatusUpdate, onCompleted) {
    _onStatusUpdate = onStatusUpdate;
    _onCompleted = onCompleted;
    
    var ctx = canvasEl.getContext('2d');

    pose = new Pose({
      locateFile: function (file) {
        return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + file;
      }
    });

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });

    var lastProcessedTime = 0;
    var processInterval = 100; // 10 FPS for performance

    pose.onResults(function (results) {
      if (!running) return;
      ctx.save();
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
      
      // Mirror the video input
      ctx.translate(canvasEl.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);
      ctx.translate(canvasEl.width, 0);
      ctx.scale(-1, 1);

      if (results.poseLandmarks) {
        frameCount++;
        var lm = results.poseLandmarks;
        
        // Draw key joints and connectors manually with beautiful neon aesthetics
        _drawSkeleton(ctx, lm, canvasEl);

        var leftShoulder = lm[11];
        var rightShoulder = lm[12];
        var leftElbow = lm[13];
        var rightElbow = lm[14];
        var leftHip = lm[23];
        var rightHip = lm[24];

        // Calculate arm angles
        var leftArmAngle = _calcAngle(leftHip, leftShoulder, leftElbow);
        var rightArmAngle = _calcAngle(rightHip, rightShoulder, rightElbow);

        // Assess posture symmetry
        var shoulderSymmetry = Math.abs(leftShoulder.y - rightShoulder.y);
        var asymmetryWarning = shoulderSymmetry > 0.08;

        // Feedback logic
        var feedback = "";

        if (leftArmAngle > 140 && rightArmAngle > 140) {
          if (asymmetryWarning) {
            feedback = "keep_shoulders_level";
          } else {
            feedback = "perfect_hold";
          }
          
          if (!isArmRaised) {
            isArmRaised = true;
          }
        } else if (leftArmAngle < 60 && rightArmAngle < 60) {
          feedback = "raise_both_arms";
          if (isArmRaised) {
            repsCount++;
            isArmRaised = false;
            
            if (_onStatusUpdate) {
              _onStatusUpdate({
                reps: repsCount,
                leftAngle: Math.round(leftArmAngle),
                rightAngle: Math.round(rightArmAngle),
                feedback: feedback,
                completed: repsCount >= targetReps
              });
            }

            if (repsCount >= targetReps) {
              stop();
              if (_onCompleted) _onCompleted();
              return;
            }
          }
        } else {
          feedback = "raise_arms_higher";
        }

        if (_onStatusUpdate) {
          _onStatusUpdate({
            reps: repsCount,
            leftAngle: Math.round(leftArmAngle),
            rightAngle: Math.round(rightArmAngle),
            feedback: feedback,
            completed: repsCount >= targetReps
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
          await pose.send({ image: videoEl });
        }
      },
      width: 480,
      height: 360
    });
  }

  function _calcAngle(A, B, C) {
    if (!A || !B || !C) return 0;
    var ab = { x: A.x - B.x, y: A.y - B.y };
    var cb = { x: C.x - B.x, y: C.y - B.y };
    
    var dotProduct = ab.x * cb.x + ab.y * cb.y;
    var lenAB = Math.sqrt(ab.x * ab.x + ab.y * ab.y);
    var lenCB = Math.sqrt(cb.x * cb.x + cb.y * cb.y);
    
    if (lenAB === 0 || lenCB === 0) return 0;
    var cosTheta = dotProduct / (lenAB * lenCB);
    var angleRad = Math.acos(Math.max(-1, Math.min(1, cosTheta)));
    return (angleRad * 180) / Math.PI;
  }

  function _drawSkeleton(ctx, lm, canvas) {
    var width = canvas.width;
    var height = canvas.height;

    var connections = [
      [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
      [11, 23], [12, 24], [23, 24]
    ];

    ctx.strokeStyle = 'rgba(139,92,246,0.6)';
    ctx.lineWidth = 3;
    for (var i = 0; i < connections.length; i++) {
      var p1 = lm[connections[i][0]];
      var p2 = lm[connections[i][1]];
      if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
        ctx.beginPath();
        ctx.moveTo((1 - p1.x) * width, p1.y * height);
        ctx.lineTo((1 - p2.x) * width, p2.y * height);
        ctx.stroke();
      }
    }

    ctx.fillStyle = '#10B981';
    var keyJoints = [11, 12, 13, 14, 15, 16, 23, 24];
    for (var j = 0; j < keyJoints.length; j++) {
      var pt = lm[keyJoints[j]];
      if (pt && pt.visibility > 0.5) {
        ctx.beginPath();
        ctx.arc((1 - pt.x) * width, pt.y * height, 6, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
  }

  function start(videoEl, canvasEl) {
    if (!pose) return;
    running = true;
    repsCount = 0;
    isArmRaised = false;
    canvasEl.width = canvasEl.clientWidth;
    canvasEl.height = canvasEl.clientHeight;
    camera.start();
  }

  function stop() {
    running = false;
    if (camera) camera.stop();
  }

  return {
    init: init,
    start: start,
    stop: stop
  };
})();
