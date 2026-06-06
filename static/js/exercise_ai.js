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
  var currentExerciseId = 4;
  var holdStartTime = null;
  var activeSide = null;
  var leftReps = 0;
  var rightReps = 0;

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

        var leftWrist = lm[15];
        var rightWrist = lm[16];
        var leftKnee = lm[25];
        var rightKnee = lm[26];
        var leftAnkle = lm[27];
        var rightAnkle = lm[28];
        var nose = lm[0];

        var feedback = "";
        var now = Date.now();
        
        switch (currentExerciseId) {
          case 1: // Thở sâu (Deep Breathing)
            var shoulderHeight = (leftShoulder.y + rightShoulder.y) / 2;
            if (!isArmRaised && shoulderHeight < 0.45) {
              if (!holdStartTime) holdStartTime = now;
              var holdTime1 = 2 - Math.floor((now - holdStartTime) / 1000);
              if (holdTime1 <= 0) {
                isArmRaised = true;
                holdStartTime = null;
                feedback = "exhale";
              } else {
                feedback = "hold_breath_2s";
              }
            } else if (isArmRaised && shoulderHeight > 0.48) {
              repsCount++;
              isArmRaised = false;
              holdStartTime = null;
              feedback = "inhale";
            } else {
              if (shoulderHeight >= 0.45 && shoulderHeight <= 0.48) holdStartTime = null;
              feedback = isArmRaised ? "breathe_normally" : "inhale";
            }
            break;

          case 2: // Đi bộ tại chỗ (Walking in Place)
            targetReps = 40; // 20 left + 20 right
            var leftKneeUp = leftKnee.y < leftHip.y + 0.1;
            var rightKneeUp = rightKnee.y < rightHip.y + 0.1;
            
            if (leftKneeUp && activeSide !== 'left') {
              leftReps++;
              activeSide = 'left';
              repsCount = leftReps + rightReps;
              feedback = "knee_up_right";
            } else if (rightKneeUp && activeSide !== 'right') {
              rightReps++;
              activeSide = 'right';
              repsCount = leftReps + rightReps;
              feedback = "knee_up_left";
            } else {
              feedback = "keep_walking";
            }
            break;

          case 3: // Giãn cơ cổ (Neck Stretching)
            var shoulderCenterX = (leftShoulder.x + rightShoulder.x) / 2;
            var headTilt = nose.x - shoulderCenterX; 
            
            if (Math.abs(headTilt) > 0.08) {
              if (!holdStartTime) holdStartTime = now;
              var holdTime3 = 5 - Math.floor((now - holdStartTime) / 1000);
              
              if (holdTime3 <= 0) {
                var side3 = headTilt > 0 ? 'left' : 'right';
                if (activeSide !== side3) {
                  repsCount++;
                  activeSide = side3;
                  holdStartTime = null;
                  feedback = "switch_side";
                }
              } else {
                feedback = "hold_time_" + holdTime3;
              }
            } else {
              holdStartTime = null;
              feedback = "tilt_head";
            }
            break;

          case 4: // Tập tay và vai (Arm Raises)
            var leftArmAngle = _calcAngle(leftHip, leftShoulder, leftElbow);
            var rightArmAngle = _calcAngle(rightHip, rightShoulder, rightElbow);
            
            var isForward = (leftWrist.z < leftShoulder.z - 0.2) && (rightWrist.z < rightShoulder.z - 0.2);
            var isUpward = (leftWrist.y < leftShoulder.y - 0.2) && (rightWrist.y < rightShoulder.y - 0.2);

            if (isForward) {
               feedback = "perfect_forward";
               if (!isArmRaised) isArmRaised = true;
            } else if (isUpward) {
               feedback = "perfect_upward";
               if (!isArmRaised) isArmRaised = true;
            } else if (leftArmAngle < 60 && rightArmAngle < 60) {
               feedback = "raise_arms_forward_or_up";
               if (isArmRaised) {
                 repsCount++;
                 isArmRaised = false;
               }
            } else {
               feedback = "keep_arms_straight";
            }
            break;

          case 5: // Tập thăng bằng (Balance)
            var ankleDiff = leftAnkle.y - rightAnkle.y;
            if (Math.abs(ankleDiff) > 0.05) {
              if (!holdStartTime) holdStartTime = now;
              var holdTime5 = 5 - Math.floor((now - holdStartTime) / 1000);
              
              if (holdTime5 <= 0) {
                var side5 = ankleDiff > 0 ? 'right' : 'left'; 
                if (activeSide !== side5) {
                  repsCount++;
                  activeSide = side5;
                  holdStartTime = null;
                  feedback = "switch_leg";
                }
              } else {
                feedback = "hold_time_" + holdTime5;
              }
            } else {
              holdStartTime = null;
              feedback = "lift_one_leg";
            }
            break;

          case 6: // Yoga ghế nhẹ (Chair Yoga)
            var shoulderToHip = Math.abs(leftShoulder.y - leftHip.y);
            if (!isArmRaised && shoulderToHip < 0.2) {
              if (!holdStartTime) holdStartTime = now;
              var holdTime6 = 3 - Math.floor((now - holdStartTime) / 1000);
              if (holdTime6 <= 0) {
                isArmRaised = true;
                holdStartTime = null;
                feedback = "sit_straight";
              } else {
                feedback = "hold_time_" + holdTime6;
              }
            } else if (isArmRaised && shoulderToHip > 0.3) {
              repsCount++;
              isArmRaised = false;
              feedback = "bend_forward";
            } else {
              if (shoulderToHip >= 0.2 && shoulderToHip <= 0.3) holdStartTime = null;
              feedback = isArmRaised ? "sit_straight" : "bend_forward";
            }
            break;
            
          default:
            feedback = "keep_moving";
        }

        if (_onStatusUpdate) {
          _onStatusUpdate({
            reps: repsCount,
            targetReps: targetReps,
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

  function start(videoEl, canvasEl, exId) {
    if (!pose) return;
    currentExerciseId = exId || 4;
    running = true;
    repsCount = 0;
    isArmRaised = false;
    holdStartTime = null;
    activeSide = null;
    leftReps = 0;
    rightReps = 0;
    if (currentExerciseId === 2) targetReps = 40;
    else targetReps = 10;
    
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
