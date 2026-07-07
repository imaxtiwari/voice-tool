const SIDECAR_URL = "http://localhost:8433";

async function checkSidecar() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const r = await fetch(`${SIDECAR_URL}/health`, {
      signal: controller.signal
    });
    clearTimeout(timeout);
    return r.ok;
  } catch (err) {
    return false;  // always return bool, never throw
  }
}

async function requestRewrite(text, deAiLevel, voiceLevel, mode) {
  const r = await fetch(`${SIDECAR_URL}/rewrite`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      text,
      de_ai_level: deAiLevel,
      voice_level: voiceLevel,
      mode
    })
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.message || `Sidecar error: ${r.status}`);
  }
  return r.json();
}
