// ─── HeartBits AI Vision: Face Drooping Detection ───────────────
// Uses MediaPipe Face Mesh to measure facial asymmetry in real-time.
// If asymmetry exceeds threshold for 3 consecutive seconds → triggerEmergency()

var HBVision = (function(){
  var faceMesh = null;
  var camera = null;
  var running = false;
  var alertCounter = 0;       // Consecutive frames with high asymmetry
  var ALERT_THRESHOLD = 15;   // % asymmetry to flag
  var ALERT_DURATION = 30;    // ~3 seconds at 10fps

  function init(videoEl, canvasEl, statusCallback){
    var ctx = canvasEl.getContext('2d');

    faceMesh = new FaceMesh({locateFile: function(file){
      return 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/' + file;
    }});

    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    });

    faceMesh.onResults(function(results){
      ctx.save();
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
      ctx.drawImage(results.image, 0, 0, canvasEl.width, canvasEl.height);

      if(results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0){
        var lm = results.multiFaceLandmarks[0];

        // Draw face mesh
        drawConnectors(ctx, lm, FACEMESH_TESSELATION, {color: '#10B98140', lineWidth: 1});

        // Key landmarks: mouth corners (61 left, 291 right), forehead (10), chin (152)
        var leftMouth = lm[61];
        var rightMouth = lm[291];
        var faceH = Math.abs(lm[10].y - lm[152].y);
        var yDiff = Math.abs(leftMouth.y - rightMouth.y);
        var score = Math.min(100, Math.round((yDiff / faceH) * 500));

        // Draw mouth landmarks
        var color = score > ALERT_THRESHOLD ? '#EF4444' : '#10B981';
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(leftMouth.x * canvasEl.width, leftMouth.y * canvasEl.height, 5, 0, 2*Math.PI);
        ctx.arc(rightMouth.x * canvasEl.width, rightMouth.y * canvasEl.height, 5, 0, 2*Math.PI);
        ctx.fill();

        // Check sustained asymmetry
        if(score > ALERT_THRESHOLD){
          alertCounter++;
        } else {
          alertCounter = Math.max(0, alertCounter - 2); // Decay
        }

        var isAlert = alertCounter >= ALERT_DURATION;
        if(statusCallback) statusCallback(score, isAlert);

        if(isAlert && typeof window.triggerEmergency === 'function'){
          window.triggerEmergency('face');
          alertCounter = 0; // Reset to prevent re-fire
        }
      }
      ctx.restore();
    });

    camera = new Camera(videoEl, {
      onFrame: async function(){
        if(running) await faceMesh.send({image: videoEl});
      },
      width: 480,
      height: 360
    });
  }

  function start(videoEl, canvasEl){
    if(!faceMesh) return;
    running = true;
    alertCounter = 0;
    canvasEl.width = canvasEl.clientWidth;
    canvasEl.height = canvasEl.clientHeight;
    camera.start();
  }

  function stop(){
    running = false;
    alertCounter = 0;
    if(camera) camera.stop();
  }

  return { init: init, start: start, stop: stop };
})();
