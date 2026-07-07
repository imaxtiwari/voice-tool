window.VoiceTool = window.VoiceTool || {};

window.VoiceTool.createPanel = function(win, editable, sidecarOnline) {
  // Create panel element
  const panel = document.createElement("div");
  panel.className = "vt-panel";
  
  // Panel states: idle, loading, diff, error, offline
  // All CSS classes prefixed with vt- to avoid Gmail collision
  
  panel.innerHTML = `
    <div class="vt-header">
      <div class="vt-mode-toggle">
        <button class="vt-mode-btn vt-active" data-mode="my_voice">
          My Voice
        </button>
        <button class="vt-mode-btn" data-mode="ceo_archetype">
          CEO
        </button>
      </div>
      <span class="vt-label">voice tool</span>
    </div>
    
    <div class="vt-controls">
      <div class="vt-slider-row">
        <label class="vt-slider-label">De-AI</label>
        <input type="range" class="vt-slider" id="vt-deai" 
               min="0" max="100" value="60">
        <span class="vt-slider-val">60</span>
      </div>
      <div class="vt-slider-row">
        <label class="vt-slider-label">Voice</label>
        <input type="range" class="vt-slider" id="vt-voice" 
               min="0" max="100" value="60">
        <span class="vt-slider-val">60</span>
      </div>
    </div>
    
    <button class="vt-rewrite-btn" id="vt-rewrite">
      Rewrite
    </button>
    
    <div class="vt-diff-view" id="vt-diff" style="display:none"></div>
    
    <div class="vt-bulk-actions" id="vt-bulk" style="display:none">
      <button class="vt-accept-all">Accept All</button>
      <button class="vt-reject-all">Reject All</button>
    </div>
    
    <div class="vt-status" id="vt-status"></div>
  `;
  
  // Insert panel above the compose toolbar
  const toolbar = win.querySelector('[role="toolbar"]') 
                  || editable.parentElement;
  toolbar.parentElement.insertBefore(panel, toolbar);
  
  // Wire slider value display
  panel.querySelectorAll(".vt-slider").forEach(slider => {
    slider.addEventListener("input", e => {
      e.target.nextElementSibling.textContent = e.target.value;
    });
  });
  
  // Wire mode toggle
  let activeMode = "my_voice";
  panel.querySelectorAll(".vt-mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      panel.querySelectorAll(".vt-mode-btn")
           .forEach(b => b.classList.remove("vt-active"));
      btn.classList.add("vt-active");
      activeMode = btn.dataset.mode;
    });
  });
  
  // Handle offline state
  if (!sidecarOnline) {
    setState("offline");
  }
  
  // Wire Rewrite button
  panel.querySelector("#vt-rewrite")
    .addEventListener("click", async () => {
      const text = editable.innerText.trim();
      if (!text) return;
      
      setState("loading");
      
      try {
        const online = await checkSidecar();
        if (!online) { setState("offline"); return; }
        
        const deAiLevel = parseInt(
          panel.querySelector("#vt-deai").value
        );
        const voiceLevel = parseInt(
          panel.querySelector("#vt-voice").value
        );
        
        const result = await requestRewrite(
          text, deAiLevel, voiceLevel, activeMode
        );
        
        // Add level parameters so edit logger has them
        result.de_ai_level = deAiLevel;
        result.voice_level = voiceLevel;
        result.mode = activeMode;
        
        window.VoiceTool.currentResult = result;
        window.VoiceTool.currentEditable = editable;
        
        renderDiff(result.diff, panel);
        setState("diff");
        
      } catch(err) {
        setState("error", err.message);
      }
    });
  
  // Wire Accept All / Reject All
  panel.querySelector(".vt-accept-all").addEventListener("click", () => {
    panel.querySelectorAll(".vt-diff-item[data-pending='true']")
         .forEach(item => item.querySelector(".vt-accept").click());
  });
  
  panel.querySelector(".vt-reject-all").addEventListener("click", () => {
    panel.querySelectorAll(".vt-diff-item[data-pending='true']")
         .forEach(item => item.querySelector(".vt-reject").click());
  });
  
  function setState(state, message = "") {
    const btn = panel.querySelector("#vt-rewrite");
    const diff = panel.querySelector("#vt-diff");
    const bulk = panel.querySelector("#vt-bulk");
    const status = panel.querySelector("#vt-status");
    
    const states = {
      idle:    () => { btn.disabled=false; btn.textContent="Rewrite";
                       diff.style.display="none"; bulk.style.display="none";
                       status.textContent=""; },
      loading: () => { btn.disabled=true; btn.textContent="Rewriting...";
                       status.textContent=""; },
      diff:    () => { btn.disabled=false; btn.textContent="Rewrite";
                       diff.style.display="block"; bulk.style.display="flex"; },
      error:   () => { btn.disabled=false; status.textContent=message;
                       status.className="vt-status vt-error"; },
      offline: () => { btn.disabled=true; btn.textContent="Rewrite";
                       status.textContent="voice engine offline — start the sidecar";
                       status.className="vt-status vt-offline"; }
    };
    (states[state] || states.idle)();
  }
};
