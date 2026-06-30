// ─── HeartBits Speech AI: Voice Slur Detection ─────────────────
// Uses Web Speech API to detect speech difficulties.
// User repeats a reference sentence; AI compares accuracy.

var HBSpeech = (function () {
  var recognition = null;
  var supported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  // Reference sentences
  var SENTENCES = {
    vi: "Trời hôm nay rất trong xanh",
    en: "The weather is clear today"
  };

  // Simple word-matching similarity (Sørensen-Dice style)
  function similarity(a, b) {
    a = a.toLowerCase().trim();
    b = b.toLowerCase().trim();
    if (a === b) return 1;
    var wordsA = a.split(/\s+/);
    var wordsB = b.split(/\s+/);
    var matches = 0;
    wordsA.forEach(function (w) {
      if (wordsB.indexOf(w) !== -1) matches++;
    });
    return (2 * matches) / (wordsA.length + wordsB.length);
  }

  function start(callback) {
    if (!supported) {
      if (callback) callback({ error: 'not_supported' });
      return;
    }

    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();

    var lang = localStorage.getItem('lang') || 'vi';
    recognition.lang = lang === 'en' ? 'en-US' : 'vi-VN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 3;

    var reference = SENTENCES[lang] || SENTENCES.vi;

    recognition.onresult = function (event) {
      var bestMatch = 0;
      var transcript = '';

      for (var i = 0; i < event.results[0].length; i++) {
        var alt = event.results[0][i];
        var sim = similarity(alt.transcript, reference);
        // Weight: combine speech API confidence with our word-matching
        var score = (alt.confidence * 0.4) + (sim * 0.6);
        if (score > bestMatch) {
          bestMatch = score;
          transcript = alt.transcript;
        }
      }

      var isNormal = bestMatch >= 0.5;

      if (callback) callback({
        transcript: transcript,
        score: Math.round(bestMatch * 100),
        isNormal: isNormal,
        reference: reference
      });

    };

    recognition.onerror = function (event) {
      if (callback) callback({ error: event.error });
    };

    recognition.onend = function () {
      // Speech ended
    };

    recognition.start();
  }

  function stop() {
    if (recognition) {
      try { recognition.stop(); } catch (e) { }
    }
  }

  function getReference() {
    var lang = localStorage.getItem('lang') || 'vi';
    return SENTENCES[lang] || SENTENCES.vi;
  }

  return {
    supported: supported,
    start: start,
    stop: stop,
    getReference: getReference
  };
})();
