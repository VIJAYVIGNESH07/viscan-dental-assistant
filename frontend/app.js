(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const sessionId = (window.crypto && typeof window.crypto.randomUUID === "function")
    ? window.crypto.randomUUID() : `viscan-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const state = { busy: false, messages: [], recognition: null, listening: false };

  function addHistory(text, role) {
    state.messages.push({ text: String(text || ""), role });
    state.messages = state.messages.slice(-12);
    const list = $("historyList");
    list.replaceChildren();
    if (!state.messages.length) {
      const empty = document.createElement("div"); empty.className = "history-empty";
      empty.textContent = "Your recent messages will appear here."; list.append(empty); return;
    }
    state.messages.filter((item) => item.role === "user").slice(-8).reverse().forEach((item) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "history-item";
      button.textContent = item.text; button.title = item.text;
      button.addEventListener("click", () => { $("messageInput").value = item.text; $("messageInput").focus(); });
      list.append(button);
    });
  }

  // function scrollToBottom() {
  //   requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }));
  // }
     
  
// function scrollToBottom() {
//   requestAnimationFrame(() => {
//     const messages = document.getElementById("messages");
//     if (messages) {
//       messages.scrollTop = messages.scrollHeight;
//     }
//   });
// }

function scrollToBottom() {
    requestAnimationFrame(() => {
        const chatStage = document.querySelector(".chat-stage");

        if (chatStage) {
            chatStage.scrollTo({
                top: chatStage.scrollHeight,
                behavior: "smooth"
            });
        }
    });
}


  function makeMessage(role, text, data) {
    $("welcomePanel").hidden = true;
    const wrapper = document.createElement("article"); wrapper.className = `message ${role}`;
    const avatar = document.createElement("div"); avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "You" : "✳";
    const content = document.createElement("div"); content.className = "message-content";
    const label = document.createElement("div"); label.className = "message-label"; label.textContent = role === "user" ? "YOU" : "VISCAN ASSISTANT";
    const bubble = document.createElement("div"); bubble.className = "bubble"; bubble.textContent = text || "";
    content.append(label, bubble);
    if (role === "assistant" && data) {
      if (data.report && typeof data.report === "object") content.append(renderReportCard(data));
      if (data.status === "draft" || Array.isArray(data.findings)) content.append(renderDraftCard(data));
      if (Array.isArray(data.candidates) && data.candidates.length) content.append(renderCandidates(data.candidates));
      if (Array.isArray(data.evidence) && data.evidence.length) content.append(renderEvidence(data.evidence));
    }
    wrapper.append(avatar, content); $("messages").append(wrapper); scrollToBottom();
    return wrapper;
  }

  function renderReportCard(data) {
    const report = data.report || {};
    const card = document.createElement("section"); card.className = "report-card";
    const head = document.createElement("div"); head.className = "card-head";
    const title = document.createElement("strong"); title.textContent = "Retrieved report";
    const tag = document.createElement("span"); tag.className = "card-tag"; tag.textContent = report.report_type || "Dental report";
    head.append(title, tag);
    const body = document.createElement("div"); body.className = "card-body";
    const meta = document.createElement("div"); meta.className = "report-meta";
    const patientName = data.patient && data.patient.name;
    [["Patient", patientName], ["Report ID", report.report_id], ["Date", report.report_date]].forEach(([key, value]) => {
      if (value) { const span = document.createElement("span"); span.textContent = `${key}: ${value}`; meta.append(span); }
    });
    const text = document.createElement("div"); text.className = "report-text"; text.textContent = report.report_text || "No report text is available in this record.";
    body.append(meta, text);
    if (Array.isArray(report.findings) && report.findings.length) {
      const list = document.createElement("ul"); list.className = "findings-list";
      report.findings.forEach((finding) => {
        const li = document.createElement("li"); li.textContent = typeof finding === "string" ? finding : (finding.text || JSON.stringify(finding)); list.append(li);
      }); body.append(list);
    }
    card.append(head, body); return card;
  }

  function renderDraftCard(data) {
    const card = document.createElement("section"); card.className = "draft-card";
    const head = document.createElement("div"); head.className = "card-head";
    const title = document.createElement("strong"); title.textContent = "Structured draft report";
    const tag = document.createElement("span"); tag.className = "card-tag"; tag.textContent = "Editable";
    head.append(title, tag);
    const body = document.createElement("div"); body.className = "card-body";
    const label = document.createElement("label"); label.className = "draft-label"; label.textContent = "Draft text — edit before use";
    const editor = document.createElement("textarea"); editor.className = "draft-editor"; editor.value = data.draft_report || ""; editor.rows = 4;
    const actions = document.createElement("div"); actions.className = "card-actions";
    const copy = document.createElement("button"); copy.type = "button"; copy.className = "small-button"; copy.textContent = "Copy draft";
    copy.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(editor.value); copy.textContent = "Copied"; }
      catch { editor.focus(); editor.select(); copy.textContent = "Select and copy"; }
    });
    const jsonButton = document.createElement("button"); jsonButton.type = "button"; jsonButton.className = "small-button"; jsonButton.textContent = "View structured JSON";
    const json = document.createElement("pre"); json.hidden = true; json.style.cssText = "white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px;line-height:1.6;color:#506174;background:#f6f9fb;padding:10px;border-radius:8px;margin-top:10px;";
    const safeData = { status: data.status, findings: data.findings || [], uncertainties: data.uncertainties || [], requires_clinician_review: data.requires_clinician_review, source_transcript: data.source_transcript };
    json.textContent = JSON.stringify(safeData, null, 2);
    jsonButton.addEventListener("click", () => { json.hidden = !json.hidden; jsonButton.textContent = json.hidden ? "View structured JSON" : "Hide structured JSON"; });
    const warning = document.createElement("div"); warning.className = "review-warning"; warning.textContent = "Clinician review required. This is an editable draft, not a finalized report or diagnosis.";
    actions.append(copy, jsonButton); body.append(label, editor, actions, json, warning);
    if (Array.isArray(data.uncertainties) && data.uncertainties.length) {
      const list = document.createElement("ul"); list.className = "uncertainty-list";
      data.uncertainties.forEach((item) => { const li = document.createElement("li"); li.textContent = item; list.append(li); }); body.append(list);
    }
    card.append(head, body); return card;
  }

  function renderCandidates(candidates) {
    const wrap = document.createElement("div"); wrap.className = "candidate-list";
    candidates.forEach((patient) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "candidate-button";
      button.textContent = `${patient.name}${patient.patient_id ? ` · ${patient.patient_id}` : ""}`;
      button.addEventListener("click", () => sendMessage(`Open the latest report for ${patient.name}`)); wrap.append(button);
    });
    return wrap;
  }

  function renderEvidence(evidence) {
    const card = document.createElement("div"); card.className = "evidence-card";
    const body = document.createElement("div"); body.className = "card-body";
    evidence.forEach((item) => {
      const line = document.createElement("div"); line.className = "evidence-line";
      const mark = document.createElement("span"); mark.textContent = "↳";
      const text = document.createElement("span");
      text.textContent = item.report_id ? `Source: synthetic report ${item.report_id}` : (item.source === "user_provided_transcript" ? "Source: transcript supplied in this message" : `Source: ${item.source || "not specified"}`);
      line.append(mark, text); body.append(line);
    });
    card.append(body); return card;
  }

  function showTyping() {
    const node = makeMessage("assistant", ""); node.dataset.typing = "true";
    const bubble = node.querySelector(".bubble"); bubble.classList.add("typing");
    bubble.innerHTML = "<i></i><i></i><i></i>";
    return node;
  }

  async function postChat(query) {
    const response = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId })
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data && (data.detail || data.message);
      throw new Error(detail || `The server returned HTTP ${response.status}.`);
    }
    if (!data || typeof data !== "object") throw new Error("The server returned an invalid response.");
    return data;
  }

  async function sendMessage(rawText) {
    const text = String(rawText || "").trim();
    if (!text || state.busy) return;
    state.busy = true; $("sendBtn").disabled = true;
    $("messageInput").value = ""; autoResizeInput();
    addHistory(text, "user"); makeMessage("user", text);
    const typing = showTyping();
    try {
      const data = await postChat(text);
      typing.remove();
      const responseText = data.message || (data.status === "draft" ? "Draft created. Clinician review is required." : "The request completed without a message.");
      makeMessage("assistant", responseText, data);
      if (data.status === "error") state.messages.push({ text: responseText, role: "assistant" });
      addHistory(responseText, "assistant");
    } catch (error) {
      typing.remove(); makeMessage("assistant", `I couldn't reach the assistant service. ${error.message} Check that the FastAPI server is running, then try again.`);
    } finally {
      state.busy = false; $("sendBtn").disabled = false; $("messageInput").focus();
    }
  }

  function autoResizeInput() {
    const input = $("messageInput"); input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  async function checkHealth() {
    const badge = $("apiStatus");
    try {
      const response = await fetch("/api/health"); if (!response.ok) throw new Error("offline");
      const data = await response.json(); badge.classList.remove("offline"); badge.classList.add("ready");
      badge.title = data.groq_key_configured ? `LLM enabled · ${data.groq_model}` : "Fallback mode: configure GROQ_API_KEY in .env for dynamic LLM interpretation.";
      badge.lastChild && (badge.lastChild.textContent = ""); badge.textContent = data.mode === "groq" ? "AI service ready" : "Fallback mode";
      const dot = document.createElement("span"); dot.className = "status-dot"; badge.prepend(dot);
    } catch { badge.classList.remove("ready"); badge.classList.add("offline"); badge.textContent = "API offline"; }
  }

  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const button = $("micBtn"), status = $("micStatus");
    if (!SpeechRecognition) {
      button.title = "Speech recognition is not supported in this browser. You can type or paste a transcript.";
      button.addEventListener("click", () => { status.textContent = "Speech recognition unavailable; type or paste the transcript instead."; });
      return;
    }
    const recognition = new SpeechRecognition(); recognition.lang = "en-IN"; recognition.interimResults = true; recognition.continuous = false;
    state.recognition = recognition;
    recognition.onstart = () => { state.listening = true; button.classList.add("listening"); status.textContent = "Listening… review the text before sending."; };
    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript;
      if (transcript) { $("messageInput").value = transcript.trim(); autoResizeInput(); }
    };
    recognition.onerror = (event) => { status.textContent = event.error === "not-allowed" ? "Microphone permission denied." : "Speech recognition stopped; type your message if needed."; };
    recognition.onend = () => { state.listening = false; button.classList.remove("listening"); if (status.textContent === "Listening… review the text before sending.") status.textContent = "Transcript ready — review before sending."; };
    button.addEventListener("click", () => {
      if (state.listening) { recognition.stop(); return; }
      status.textContent = "Requesting microphone…";
      try { recognition.start(); } catch { status.textContent = "Could not start microphone. Type or paste your transcript instead."; }
    });
  }

  $("chatForm").addEventListener("submit", (event) => { event.preventDefault(); sendMessage($("messageInput").value); });
  $("messageInput").addEventListener("input", autoResizeInput);
  $("messageInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("chatForm").requestSubmit(); }
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => sendMessage(button.dataset.prompt)));
  $("newChatBtn").addEventListener("click", () => window.location.reload());
  setupSpeechRecognition(); checkHealth();
})();
