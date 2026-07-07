const observer = new MutationObserver(() => {
  const composeWindows = document.querySelectorAll('[role="dialog"]');
  composeWindows.forEach(win => {
    if (win.dataset.voiceToolInjected) return;
    const editable = win.querySelector('[contenteditable="true"]');
    if (!editable) return;
    win.dataset.voiceToolInjected = "true";
    injectPanel(win, editable);
  });
});

observer.observe(document.body, { childList: true, subtree: true });

async function injectPanel(win, editable) {
  console.log("voice tool injecting panel...");
  const online = await checkSidecar();
  if (window.VoiceTool && window.VoiceTool.createPanel) {
    window.VoiceTool.createPanel(win, editable, online);
    console.log("voice tool injected successfully");
  } else {
    console.warn("window.VoiceTool.createPanel is not defined yet.");
  }
}
