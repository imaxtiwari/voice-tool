window.VoiceTool = window.VoiceTool || {};

window.VoiceTool.logEdit = function(diffObj, accepted, result) {
  // Fire and forget — never block UI on this
  fetch("http://localhost:8433/log-edit", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      original_seg: diffObj.original,
      proposed_seg: diffObj.rewritten,
      accepted: accepted,
      de_ai_level: result.de_ai_level || 0,
      voice_level: result.voice_level || 0,
      mode: result.mode || "my_voice",
      model_used: result.model_used || "unknown"
    })
  }).catch(() => {});  // silently discard all errors
};
