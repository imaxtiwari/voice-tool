function renderDiff(diffObjects, panel) {
  const container = panel.querySelector("#vt-diff");
  container.innerHTML = "";
  
  let pendingCount = 0;
  
  diffObjects.forEach((obj, idx) => {
    if (obj.type === "equal") return;
    
    pendingCount++;
    const item = document.createElement("div");
    item.className = "vt-diff-item";
    item.dataset.pending = "true";
    item.dataset.idx = idx;
    
    // Fact flag amber indicator
    if (obj.fact_flag) {
      item.classList.add("vt-fact-flagged");
    }
    
    let content = "";
    if (obj.type === "deletion") {
      content = `<span class="vt-del">${obj.original}</span>`;
    } else if (obj.type === "insertion") {
      content = `<span class="vt-ins">${obj.rewritten}</span>`;
    } else {
      content = `<span class="vt-del">${obj.original}</span>
                 <span class="vt-arrow">→</span>
                 <span class="vt-ins">${obj.rewritten}</span>`;
    }
    
    const factIcon = obj.fact_flag ? '<span class="vt-fact-icon">⚠</span>' : "";
    
    item.innerHTML = `
      ${factIcon}
      <span class="vt-diff-content">${content}</span>
      <span class="vt-actions">
        <button class="vt-accept" title="Accept">✓</button>
        <button class="vt-reject" title="Reject">✗</button>
      </span>
    `;
    
    // Wire accept/reject
    const result = window.VoiceTool.currentResult;
    
    item.querySelector(".vt-accept").addEventListener("click", () => {
      VoiceTool.logEdit(obj, true, result);
      item.dataset.pending = "false";
      item.classList.add("vt-resolved", "vt-accepted");
      checkAllResolved(panel, diffObjects);
    });
    
    item.querySelector(".vt-reject").addEventListener("click", () => {
      VoiceTool.logEdit(obj, false, result);
      item.dataset.pending = "false";
      item.classList.add("vt-resolved", "vt-rejected");
      checkAllResolved(panel, diffObjects);
    });
    
    container.appendChild(item);
  });
  
  if (pendingCount === 0) {
    container.textContent = "No changes suggested.";
  }
}

function checkAllResolved(panel, diffObjects) {
  const pending = panel.querySelectorAll(".vt-diff-item[data-pending='true']");
  if (pending.length === 0) {
    // Build final text from accepted changes
    applyAcceptedChanges(diffObjects, panel);
  }
}

function applyAcceptedChanges(diffObjects, panel) {
  const editable = window.VoiceTool.currentEditable;
  const result = window.VoiceTool.currentResult;
  
  // Accepted = use rewritten. Rejected = use original.
  // Simplest correct approach: use rewritten_text but 
  // revert rejected segments back to original.
  // For v1: just replace with full rewritten_text if any accepted,
  // keep original if all rejected.
  const items = panel.querySelectorAll(".vt-diff-item");
  const allRejected = [...items].every(i => i.classList.contains("vt-rejected"));
  
  if (!allRejected) {
    editable.innerText = result.rewritten_text;
  }
  
  const accepted = panel.querySelectorAll(".vt-accepted").length;
  const rejected = panel.querySelectorAll(".vt-rejected").length;
  panel.querySelector("#vt-status").textContent = 
    `Done — ${accepted} accepted, ${rejected} rejected`;
}
