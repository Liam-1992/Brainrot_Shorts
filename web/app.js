const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");

const genForm = document.getElementById("gen-form");
const statusText = document.getElementById("status-text");
const jobIdLabel = document.getElementById("job-id");
const logBox = document.getElementById("log-box");
const progressBar = document.getElementById("progress-bar");
const previewVideo = document.getElementById("preview-video");
const downloadLink = document.getElementById("download-link");
const generateBtn = document.getElementById("generate-btn");
const promptHelp = document.getElementById("prompt-help");
const durationLabel = document.getElementById("duration-label");
const durationInput = genForm.querySelector('input[name="duration_seconds"]');
const promptInput = genForm.querySelector('textarea[name="topic_prompt"]');
const generateVariationsBtn = document.getElementById("generate-variations-btn");
const variantLabBtn = document.getElementById("variant-lab-btn");

const templateSelect = document.getElementById("template-select");
const voiceSelect = document.getElementById("voice-select");
const voicePreviewBtn = document.getElementById("voice-preview-btn");
const presetSelect = document.getElementById("preset-select");

const galleryGrid = document.getElementById("gallery-grid");
const detailThumb = document.getElementById("detail-thumb");
const detailPreview = document.getElementById("detail-preview");
const detailVideo = document.getElementById("detail-video");
const detailMeta = document.getElementById("detail-meta");
const detailDownload = document.getElementById("detail-download");
const rerunBtn = document.getElementById("rerun-btn");
const previewStartInput = document.getElementById("preview-start");
const previewDurationInput = document.getElementById("preview-duration");
const previewBtn = document.getElementById("preview-btn");
const renderFinalBtn = document.getElementById("render-final-btn");
const rerenderBtn = document.getElementById("rerender-btn");
const regenVoice = document.getElementById("regen-voice");
const regenCaptions = document.getElementById("regen-captions");
const regenRender = document.getElementById("regen-render");

const beatsTableBody = document.getElementById("beats-table-body");
const addBeatBtn = document.getElementById("add-beat-btn");
const saveBeatsBtn = document.getElementById("save-beats-btn");

const hookTextEl = document.getElementById("hook-text");
const hookScoreBtn = document.getElementById("score-hook-btn");
const rewriteHookBtn = document.getElementById("rewrite-hook-btn");
const hookScoreEl = document.getElementById("hook-score");
const hookCandidates = document.getElementById("hook-candidates");

const beatChart = document.getElementById("beat-chart");
const wordChart = document.getElementById("word-chart");
const metricsSuggestions = document.getElementById("metrics-suggestions");
const optimizationList = document.getElementById("optimization-list");
const validationReport = document.getElementById("validation-report");
const captionReport = document.getElementById("caption-report");
const cancelJobBtn = document.getElementById("cancel-job-btn");
const publishPackBtn = document.getElementById("publish-pack-btn");
const publishPackLink = document.getElementById("publish-pack-link");
const viralityReportBtn = document.getElementById("virality-report-btn");
const viralityReportLink = document.getElementById("virality-report-link");

const abCompare = document.getElementById("ab-compare");

const presetForm = document.getElementById("preset-form");
const presetList = document.getElementById("preset-list");

const healthGrid = document.getElementById("health-grid");
const healthPill = document.getElementById("health-pill");
const recommendedModels = document.getElementById("recommended-models");
const recommendedLog = document.getElementById("recommended-log");

const batchForm = document.getElementById("batch-form");
const batchLog = document.getElementById("batch-log");

const abForm = document.getElementById("ab-form");
const abLog = document.getElementById("ab-log");

const downloadForm = document.getElementById("download-form");
const downloadBtn = document.getElementById("download-btn");
const downloadStatusText = document.getElementById("download-status-text");
const downloadIdLabel = document.getElementById("download-id");
const downloadPathLabel = document.getElementById("download-path");
const downloadLogBox = document.getElementById("download-log-box");
const downloadProgressBar = document.getElementById("download-progress-bar");

const variantModal = document.getElementById("variant-modal");
const variantCloseBtn = document.getElementById("variant-close");
const variantResults = document.getElementById("variant-results");

const assetTypeSelect = document.getElementById("asset-type");
const assetSearchInput = document.getElementById("asset-search");
const assetList = document.getElementById("asset-list");
const assetDetail = document.getElementById("asset-detail");

const routingForm = document.getElementById("routing-form");
const routingMode = document.getElementById("routing-mode");
const routingPolicy = document.getElementById("routing-policy");
const hookModelSelect = document.getElementById("hook-model-select");
const scriptModelSelect = document.getElementById("script-model-select");
const runBenchmarksBtn = document.getElementById("run-benchmarks-btn");
const benchmarksList = document.getElementById("benchmarks-list");

const envForm = document.getElementById("env-form");
const envStatus = document.getElementById("env-status");
const envSaveNoReload = document.getElementById("env-save-no-reload");
const envModal = document.getElementById("env-modal");
const envMissingList = document.getElementById("env-missing-list");
const envModalOpen = document.getElementById("env-modal-open");
const envModalClose = document.getElementById("env-modal-close");

const watchFolderStatus = document.getElementById("watch-folder-status");
const schedulerStatus = document.getElementById("scheduler-status");
const watchFolderScanBtn = document.getElementById("watch-folder-scan-btn");
const watchApproveToggle = document.getElementById("watch-approve-toggle");
const schedulerDryRunBtn = document.getElementById("scheduler-dry-run-btn");
const watchFolderLog = document.getElementById("watch-folder-log");
const watchPendingList = document.getElementById("watch-pending-list");
const schedulerRuns = document.getElementById("scheduler-runs");

const campaignForm = document.getElementById("campaign-form");
const campaignList = document.getElementById("campaign-list");
const campaignDetail = document.getElementById("campaign-detail");
const campaignMemory = document.getElementById("campaign-memory");
const campaignMemoryResetBtn = document.getElementById("campaign-memory-reset-btn");
const campaignJobs = document.getElementById("campaign-jobs");
const campaignRunBtn = document.getElementById("campaign-run-btn");
const campaignExportBtn = document.getElementById("campaign-export-btn");
const campaignExportProBtn = document.getElementById("campaign-export-pro-btn");
const campaignExportLink = document.getElementById("campaign-export-link");

let pollTimer = null;
let downloadTimer = null;
let recommendedTimer = null;
let selectedGalleryJob = null;
let currentBeats = [];
let currentHook = "";
let currentTitle = "";
let variantSelection = null;
let currentProjectStyle = "brainrot_facts";
let currentAssets = [];
let selectedAsset = null;
let selectedCampaignId = null;

cancelJobBtn.disabled = true;

function switchTab(tab) {
  tabs.forEach((btn) => btn.classList.toggle("active", btn === tab));
  panels.forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tab.dataset.tab}`);
  });
  if (tab.dataset.tab === "settings") {
    loadConfig();
    loadHealth();
    loadRecommendedModels();
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab));
});

function setStatus(text, progress) {
  statusText.textContent = text;
  if (typeof progress === "number") {
    progressBar.style.width = `${progress}%`;
  }
}

function appendLogs(logs) {
  logBox.textContent = logs.join("\n");
  logBox.scrollTop = logBox.scrollHeight;
}

function appendDownloadLogs(logs) {
  downloadLogBox.textContent = logs.join("\n");
  downloadLogBox.scrollTop = downloadLogBox.scrollHeight;
}

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    if (isJson && payload) {
      if (typeof payload === "string") {
        message = payload;
      } else if (payload.detail) {
        message = Array.isArray(payload.detail)
          ? payload.detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
          : String(payload.detail);
      }
    } else if (typeof payload === "string" && payload.trim()) {
      message = payload.trim();
    }
    const err = new Error(message);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }
  return payload;
}

function updatePromptState() {
  const value = String(promptInput.value || "");
  const ok = value.trim().length >= 3;
  generateBtn.disabled = !ok;
  if (!ok) {
    promptHelp.textContent = "Prompt must be at least 3 characters.";
  } else {
    promptHelp.textContent = "";
  }
}

async function pollStatus(jobId) {
  try {
    const data = await fetchJSON(`/status/${jobId}`);
    setStatus(`${data.status} (${data.progress}%)`, data.progress);
    jobIdLabel.textContent = `Job: ${jobId}`;
    appendLogs(data.logs || []);

    if (data.output_video_url) {
      previewVideo.src = data.output_video_url;
      downloadLink.href = data.output_video_url;
      downloadLink.classList.add("ready");
    } else if (data.preview_video_url) {
      previewVideo.src = data.preview_video_url;
    }

    if (data.preview_video_url) {
      detailPreview.src = data.preview_video_url;
    }

    if (data.status === "done" || data.status === "error") {
      clearInterval(pollTimer);
      pollTimer = null;
      generateBtn.disabled = false;
      cancelJobBtn.disabled = true;
      loadGallery();
    } else {
      cancelJobBtn.disabled = false;
    }
  } catch (err) {
    setStatus("error", 0);
    generateBtn.disabled = false;
  }
}

async function pollDownload(downloadId) {
  try {
    const data = await fetchJSON(`/models/status/${downloadId}`);
    downloadStatusText.textContent = `${data.status} (${data.progress}%)`;
    downloadProgressBar.style.width = `${data.progress}%`;
    downloadIdLabel.textContent = `Download: ${downloadId}`;
    if (data.output_dir) {
      downloadPathLabel.textContent = `Saved to: ${data.output_dir}`;
    }
    appendDownloadLogs(data.logs || []);

    if (data.status === "done" || data.status === "error") {
      clearInterval(downloadTimer);
      downloadTimer = null;
      downloadBtn.disabled = false;
    }
  } catch (err) {
    downloadStatusText.textContent = "error";
    downloadProgressBar.style.width = "0%";
    downloadBtn.disabled = false;
  }
}

async function loadTemplates() {
  try {
    const templates = await fetchJSON("/templates");
    templateSelect.innerHTML = templates
      .map((t) => `<option value="${t.name}">${t.name}</option>`)
      .join("");
  } catch (err) {
    templateSelect.innerHTML = "<option value=\"brainrot_facts\">brainrot_facts</option>";
  }
}

async function loadPresets() {
  try {
    const data = await fetchJSON("/presets");
    presetSelect.innerHTML = "<option value=\"\">None</option>";
    presetList.innerHTML = "";
    data.presets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.name;
      option.textContent = preset.name;
      presetSelect.appendChild(option);

      const card = document.createElement("div");
      card.className = "preset-card";
      card.innerHTML = `
        <strong>${preset.name}</strong>
        <span>${preset.style} - ${preset.duration_seconds}s</span>
        <button data-name="${preset.name}">Delete</button>
      `;
      card.querySelector("button").addEventListener("click", async () => {
        await fetch(`/presets/${preset.name}`, { method: "DELETE" });
        loadPresets();
      });
      presetList.appendChild(card);
    });
  } catch (err) {
    presetList.textContent = "No presets found.";
  }
}

function buildGalleryCard(project) {
  const card = document.createElement("div");
  card.className = "gallery-card";
  const thumb = project.thumb_styled_path || project.thumb_path;
  let thumbFile = "";
  if (thumb) {
    const parts = thumb.split(/[/\\]/);
    thumbFile = parts[parts.length - 1];
  }
  const thumbUrl = thumbFile ? `/outputs/${project.job_id}/${thumbFile}` : "";
  const variant = project.variant_name ? ` (${project.variant_name})` : "";
  card.innerHTML = `
    <div class="thumb" style="background-image:url('${thumbUrl}')"></div>
    <div class="meta">
      <strong>${project.title || project.prompt}${variant}</strong>
      <span>${project.style} - ${project.created_at}</span>
    </div>
  `;
  card.addEventListener("click", () => showProject(project));
  return card;
}

async function loadGallery() {
  try {
    const data = await fetchJSON("/projects");
    galleryGrid.innerHTML = "";
    const groups = {};
    data.projects.forEach((project) => {
      const key = project.group_id || project.job_id;
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(project);
    });
    Object.entries(groups).forEach(([groupId, projects]) => {
      const block = document.createElement("div");
      block.className = "group-block";
      if (projects[0].group_id) {
        const header = document.createElement("div");
        header.className = "group-header";
        header.textContent = `Group: ${groupId}`;
        block.appendChild(header);
      }
      const grid = document.createElement("div");
      grid.className = "gallery-grid";
      projects.forEach((project) => grid.appendChild(buildGalleryCard(project)));
      block.appendChild(grid);
      galleryGrid.appendChild(block);
    });
  } catch (err) {
    galleryGrid.textContent = "No projects found.";
  }
}

function showProject(project) {
  selectedGalleryJob = project.job_id;
  currentProjectStyle = project.style || "brainrot_facts";
  detailThumb.src = project.thumb_styled_path
    ? `/outputs/${project.job_id}/thumb_styled.jpg`
    : project.thumb_path
    ? `/outputs/${project.job_id}/thumb.jpg`
    : "";
  detailPreview.src = `/outputs/${project.job_id}/preview.mp4`;
  detailVideo.src = project.final_path ? `/outputs/${project.job_id}/final.mp4` : "";
  detailMeta.textContent = `${project.style} - ${project.created_at} - ${project.voice}`;
  detailDownload.href = project.final_path ? `/outputs/${project.job_id}/final.mp4` : "#";
  publishPackLink.href = "#";
  publishPackLink.classList.remove("ready");
  viralityReportLink.href = "#";
  viralityReportLink.classList.remove("ready");
  loadBeats(project.job_id);
  loadMetrics(project.job_id);
  loadOptimization(project.job_id);
  loadValidation(project.job_id);
  loadCaptionReport(project.job_id);
  loadGroupCompare(project.group_id, project.job_id);
}

async function loadBeats(jobId) {
  try {
    const data = await fetchJSON(`/projects/${jobId}/beats`);
    currentBeats = data.beats || [];
    currentHook = data.hook || "";
    currentTitle = data.title || "";
    hookTextEl.textContent = currentHook || "(No hook found)";
    renderBeatsTable();
  } catch (err) {
    currentBeats = [];
    renderBeatsTable();
  }
}

function renderBeatsTable() {
  beatsTableBody.innerHTML = "";
  currentBeats.forEach((beat, index) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><input type="number" step="0.1" value="${beat.t}" /></td>
      <td><input type="text" value="${beat.text}" /></td>
      <td>
        <button type="button" data-action="up">Up</button>
        <button type="button" data-action="down">Down</button>
        <button type="button" data-action="remove">Remove</button>
      </td>
    `;
    const timeInput = row.querySelector("input[type='number']");
    const textInput = row.querySelector("input[type='text']");
    const buttons = row.querySelectorAll("button");

    timeInput.addEventListener("input", () => {
      currentBeats[index].t = Number(timeInput.value);
    });
    textInput.addEventListener("input", () => {
      currentBeats[index].text = textInput.value;
      currentBeats[index].on_screen = textInput.value;
      if (index === 0) {
        currentHook = textInput.value;
        hookTextEl.textContent = currentHook;
      }
    });
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.action === "remove") {
          currentBeats.splice(index, 1);
        } else if (btn.dataset.action === "up" && index > 0) {
          const temp = currentBeats[index - 1];
          currentBeats[index - 1] = currentBeats[index];
          currentBeats[index] = temp;
        } else if (btn.dataset.action === "down" && index < currentBeats.length - 1) {
          const temp = currentBeats[index + 1];
          currentBeats[index + 1] = currentBeats[index];
          currentBeats[index] = temp;
        }
        renderBeatsTable();
      });
    });
    beatsTableBody.appendChild(row);
  });
}

async function saveBeats() {
  if (!selectedGalleryJob) return;
  const payload = {
    beats: currentBeats,
    hook: currentHook || null,
    title: currentTitle || null,
  };
  await fetchJSON(`/projects/${selectedGalleryJob}/beats`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function triggerRender(previewMode) {
  if (!selectedGalleryJob) return;
  const payload = {
    regenerate_voice: regenVoice.checked,
    regenerate_captions: regenCaptions.checked,
    regenerate_render: regenRender.checked,
    preview_mode: previewMode,
    preview_start: Number(previewStartInput.value || 0),
    preview_duration: Number(previewDurationInput.value || 10),
  };
  await fetchJSON(`/projects/${selectedGalleryJob}/render_from_beats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  pollTimer = setInterval(() => pollStatus(selectedGalleryJob), 2000);
}

async function loadMetrics(jobId) {
  try {
    const data = await fetchJSON(`/projects/${jobId}/metrics`);
    drawChart(beatChart, data.beat_density, "#ffb300");
    drawChart(wordChart, data.words_per_second, "#12d6a3");
    metricsSuggestions.innerHTML = "";
    data.suggestions.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      metricsSuggestions.appendChild(li);
    });
  } catch (err) {
    metricsSuggestions.innerHTML = "<li>No metrics yet.</li>";
  }
}

async function loadOptimization(jobId) {
  try {
    const data = await fetchJSON(`/projects/${jobId}/optimization`);
    optimizationList.innerHTML = "";
    if (!data.attempts || !data.attempts.length) {
      optimizationList.textContent = "No optimization attempts yet.";
      return;
    }
    data.attempts.forEach((attempt) => {
      const row = document.createElement("div");
      row.textContent = `Attempt ${attempt.attempt}: score ${attempt.hook_score} (${attempt.selected ? "selected" : "unused"})`;
      optimizationList.appendChild(row);
    });
  } catch (err) {
    optimizationList.textContent = "No optimization data.";
  }
}

async function loadValidation(jobId) {
  try {
    const data = await fetchJSON(`/projects/${jobId}/validation`);
    validationReport.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    validationReport.textContent = "No validation yet.";
  }
}

async function loadCaptionReport(jobId) {
  try {
    const data = await fetchJSON(`/projects/${jobId}/caption_report`);
    captionReport.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    captionReport.textContent = "No caption report yet.";
  }
}

function drawChart(canvas, data, color) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  if (!data || !data.length) return;
  const maxVal = Math.max(...data, 1);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.forEach((val, idx) => {
    const x = (idx / (data.length - 1 || 1)) * (width - 10) + 5;
    const y = height - (val / maxVal) * (height - 10) - 5;
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

async function loadGroupCompare(groupId, jobId) {
  abCompare.innerHTML = "";
  if (!groupId) return;
  try {
    const data = await fetchJSON("/projects");
    const groupProjects = data.projects.filter((p) => p.group_id === groupId);
    groupProjects.forEach((project) => {
      const card = document.createElement("div");
      card.className = "compare-card";
      card.innerHTML = `
        <strong>${project.variant_name || project.job_id}</strong>
        <video controls playsinline src="/outputs/${project.job_id}/final.mp4"></video>
        <span class="muted">${project.style}</span>
      `;
      abCompare.appendChild(card);
    });
  } catch (err) {
    abCompare.textContent = "No comparison available.";
  }
}

async function loadHealth() {
  try {
    const data = await fetchJSON("/health");
    healthGrid.innerHTML = `
      <div class="health-item">FFmpeg: ${data.ffmpeg_ok}</div>
      <div class="health-item">FFprobe: ${data.ffprobe_ok}</div>
      <div class="health-item">Piper: ${data.piper_ok}</div>
      <div class="health-item">LLM model: ${data.llm_model_ok}</div>
      <div class="health-item">Whisper model: ${data.whisper_model_ok}</div>
      <div class="health-item">GPU: ${data.gpu_available}</div>
    `;
    healthPill.textContent = data.ffmpeg_ok && data.piper_ok ? "Dependencies OK" : "Missing tools";
    voiceSelect.innerHTML = "";
    if (data.available_voices && data.available_voices.length) {
      data.available_voices.forEach((voice) => {
        const opt = document.createElement("option");
        opt.value = voice;
        opt.textContent = voice;
        voiceSelect.appendChild(opt);
      });
    } else {
      const opt = document.createElement("option");
      opt.value = "en_US";
      opt.textContent = "en_US";
      voiceSelect.appendChild(opt);
    }
  } catch (err) {
    healthPill.textContent = "Health check failed";
  }
}

async function loadConfig() {
  try {
    const data = await fetchJSON("/config");
    const values = data.values || {};
    const defaults = data.defaults || {};
    Object.entries(values).forEach(([key, value]) => {
      const input = envForm.querySelector(`[name="${key}"]`);
      if (!input) return;
      if (input.type === "checkbox") {
        input.checked = ["true", "1", "yes", "on"].includes(String(value).toLowerCase());
      } else {
        input.value = value || "";
        if (!value && defaults[key]) {
          input.placeholder = defaults[key];
        }
      }
    });
    envStatus.textContent = `Loaded from ${data.env_path || ".env"}`;
    if (data.missing && data.missing.length) {
      envMissingList.innerHTML = "";
      data.missing.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        envMissingList.appendChild(li);
      });
      envModal.classList.add("active");
    }
  } catch (err) {
    envStatus.textContent = "Failed to load config.";
  }
}

async function loadRecommendedModels() {
  if (!recommendedModels) return;
  recommendedModels.innerHTML = "Loading...";
  try {
    const data = await fetchJSON("/models/recommended");
    recommendedModels.innerHTML = "";
    data.models.forEach((model) => {
      const card = document.createElement("div");
      card.className = "preset-card";
      card.innerHTML = `
        <div>
          <strong>${model.name}</strong>
          <div class="muted">${model.description}</div>
          <div class="muted">Kind: ${model.kind}</div>
          <div class="muted">Installed: ${model.installed ? "yes" : "no"}</div>
        </div>
        <div class="row actions">
          <button type="button" data-action="download">${model.installed ? "Reinstall" : "Download & Apply"}</button>
          <button type="button" data-action="fill">Fill URLs</button>
        </div>
      `;
      card.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (btn.dataset.action === "download") {
            await downloadRecommendedModel(model.model_id);
          } else {
            fillDownloadForm(model);
          }
        });
      });
      recommendedModels.appendChild(card);
    });
  } catch (err) {
    recommendedModels.textContent = "Failed to load recommended models.";
  }
}

async function downloadRecommendedModel(modelId) {
  recommendedLog.textContent = `Downloading ${modelId}...`;
  try {
    const data = await fetchJSON("/models/recommended/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId }),
    });
    if (!data.download_id) {
      recommendedLog.textContent = "Failed to start download.";
      return;
    }
    if (recommendedTimer) {
      clearInterval(recommendedTimer);
      recommendedTimer = null;
    }
    recommendedTimer = setInterval(async () => {
      const status = await fetchJSON(`/models/status/${data.download_id}`);
      const msg = `${status.status} (${status.progress}%)`;
      recommendedLog.textContent = status.logs && status.logs.length ? status.logs.join("\n") : msg;
      if (status.status === "done" || status.status === "error") {
        clearInterval(recommendedTimer);
        recommendedTimer = null;
        await loadConfig();
        await loadHealth();
        await loadRecommendedModels();
      }
    }, 2000);
  } catch (err) {
    recommendedLog.textContent = `Download failed: ${err.message || err}`;
  }
}

function fillDownloadForm(model) {
  if (!downloadForm) return;
  const nameInput = downloadForm.querySelector('input[name="name"]');
  const kindSelect = downloadForm.querySelector('select[name="kind"]');
  const urlsInput = downloadForm.querySelector('textarea[name="urls"]');
  if (nameInput) nameInput.value = model.name || model.model_id;
  if (kindSelect) kindSelect.value = model.kind || "custom";
  if (urlsInput) urlsInput.value = (model.urls || []).join("\n");
  recommendedLog.textContent = `Filled downloader with ${model.name}`;
}

async function saveEnv(reloadAfter) {
  const values = {};
  const inputs = envForm.querySelectorAll("input, select, textarea");
  inputs.forEach((input) => {
    if (!input.name) return;
    if (input.type === "checkbox") {
      values[input.name] = input.checked ? "true" : "false";
    } else {
      values[input.name] = String(input.value || "").trim();
    }
  });
  envStatus.textContent = "Saving...";
  try {
    await fetchJSON("/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    envStatus.textContent = "Saved. Reload to apply new paths.";
    if (reloadAfter) {
      window.location.reload();
    }
  } catch (err) {
    envStatus.textContent = "Failed to save config.";
  }
}

async function loadRoutingStatus() {
  try {
    const data = await fetchJSON("/routing/status");
    routingMode.value = data.config.routing_mode || "manual";
    routingPolicy.value = data.config.policy || "balanced";
    hookModelSelect.innerHTML = "";
    scriptModelSelect.innerHTML = "";
    const llmModels = data.registry.llm || [];
    llmModels.forEach((model) => {
      const opt = document.createElement("option");
      opt.value = model.path;
      opt.textContent = model.name || model.path;
      hookModelSelect.appendChild(opt.cloneNode(true));
      scriptModelSelect.appendChild(opt);
    });
    if (data.config.hook_model) hookModelSelect.value = data.config.hook_model;
    if (data.config.script_model) scriptModelSelect.value = data.config.script_model;
    if (!hookModelSelect.value && data.selected.hook) hookModelSelect.value = data.selected.hook;
    if (!scriptModelSelect.value && data.selected.script) scriptModelSelect.value = data.selected.script;
  } catch (err) {
    benchmarksList.textContent = "Routing status unavailable.";
  }
}

async function loadBenchmarks() {
  try {
    const data = await fetchJSON("/benchmarks");
    benchmarksList.textContent = JSON.stringify(data.benchmarks || [], null, 2);
  } catch (err) {
    benchmarksList.textContent = "No benchmark data.";
  }
}

routingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    routing_mode: routingMode.value,
    policy: routingPolicy.value,
    hook_model: hookModelSelect.value || null,
    script_model: scriptModelSelect.value || null,
  };
  await fetchJSON("/routing/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  loadRoutingStatus();
});

runBenchmarksBtn.addEventListener("click", async () => {
  benchmarksList.textContent = "Running benchmarks...";
  await fetchJSON("/benchmarks/run", { method: "POST" });
  loadBenchmarks();
});

async function loadWatchFolderStatus() {
  try {
    const data = await fetchJSON("/watch_folder/status");
    watchFolderStatus.textContent = `Watch folder: ${data.enabled ? "enabled" : "disabled"} | ${data.path || "not set"} | last scan: ${data.last_scan || "n/a"}`;
  } catch (err) {
    watchFolderStatus.textContent = "Watch folder status unavailable.";
  }
}

async function loadSchedulerStatus() {
  try {
    const data = await fetchJSON("/scheduler/status");
    schedulerStatus.textContent = `Scheduler: last tick ${data.last_tick || "n/a"} | schedules ${data.schedule_count}`;
  } catch (err) {
    schedulerStatus.textContent = "Scheduler status unavailable.";
  }
}

async function loadSchedulerRuns() {
  try {
    const data = await fetchJSON("/scheduler/runs");
    schedulerRuns.innerHTML = "";
    (data.runs || []).forEach((run) => {
      const card = document.createElement("div");
      card.className = "preset-card";
      card.textContent = `${run.run_id} | jobs: ${(run.job_ids || []).length}`;
      schedulerRuns.appendChild(card);
    });
  } catch (err) {
    schedulerRuns.textContent = "No scheduler runs yet.";
  }
}

async function loadWatchPending() {
  try {
    const data = await fetchJSON("/watch_folder/pending");
    watchPendingList.innerHTML = "";
    (data.pending || []).forEach((batch) => {
      const card = document.createElement("div");
      card.className = "preset-card";
      const preview = (batch.prompts || []).slice(0, 3).join(" | ");
      card.innerHTML = `
        <strong>${batch.source_file}</strong>
        <span>${(batch.prompts || []).length} prompts</span>
        <span class="muted">${preview}</span>
        <div class="row actions">
          <button type="button" data-action="approve">Approve</button>
          <button type="button" data-action="delete">Delete</button>
        </div>
      `;
      card.querySelector('[data-action="approve"]').addEventListener("click", async () => {
        await fetchJSON(`/watch_folder/pending/${batch.batch_id}/approve`, { method: "POST" });
        loadWatchPending();
      });
      card.querySelector('[data-action="delete"]').addEventListener("click", async () => {
        await fetchJSON(`/watch_folder/pending/${batch.batch_id}`, { method: "DELETE" });
        loadWatchPending();
      });
      watchPendingList.appendChild(card);
    });
  } catch (err) {
    watchPendingList.textContent = "No pending batches.";
  }
}

watchFolderScanBtn.addEventListener("click", async () => {
  watchFolderLog.textContent = "Scanning...";
  try {
    const data = await fetchJSON("/watch_folder/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approve_mode: watchApproveToggle.checked }),
    });
    watchFolderLog.textContent = JSON.stringify(data, null, 2);
    loadWatchFolderStatus();
    loadSchedulerStatus();
    loadWatchPending();
  } catch (err) {
    watchFolderLog.textContent = "Scan failed.";
  }
});

schedulerDryRunBtn.addEventListener("click", async () => {
  watchFolderLog.textContent = "Dry run...";
  try {
    const data = await fetchJSON("/scheduler/dry_run", { method: "POST" });
    watchFolderLog.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    watchFolderLog.textContent = "Dry run failed.";
  }
});

genForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  updatePromptState();
  if (generateBtn.disabled) {
    setStatus("Prompt too short.", 0);
    return;
  }
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  const formData = new FormData(genForm);
  const payload = Object.fromEntries(formData.entries());
  payload.duration_seconds = Number(payload.duration_seconds || 35);
  payload.speech_speed = Number(payload.speech_speed || 1.08);
  payload.zoom_punch_strength = Number(payload.zoom_punch_strength || 0.3);
  payload.shake_strength = Number(payload.shake_strength || 0.2);
  payload.drift_strength = Number(payload.drift_strength || 0.3);
  payload.loop_smoothing_seconds = Number(payload.loop_smoothing_seconds || 0.35);
  payload.min_hook_score = Number(payload.min_hook_score || 70);
  payload.max_words_per_second = Number(payload.max_words_per_second || 4.0);
  payload.max_retries = Number(payload.max_retries || 2);
  payload.optimization_max_attempts = Number(payload.optimization_max_attempts || 5);
  payload.max_words_per_second_estimate = Number(payload.max_words_per_second_estimate || 4.0);
  payload.min_beats_per_10s = Number(payload.min_beats_per_10s || 4.0);
  payload.max_beats_per_10s = Number(payload.max_beats_per_10s || 7.0);
  payload.hook_pool_size = Number(payload.hook_pool_size || 10);
  payload.hook_pick = Number(payload.hook_pick || 3);
  payload.script_candidate_count = Number(payload.script_candidate_count || 3);
  payload.max_chars_per_line = Number(payload.max_chars_per_line || 18);
  payload.min_caption_duration = Number(payload.min_caption_duration || 0.55);
  payload.music_ducking_strength = Number(payload.music_ducking_strength || 0.6);
  payload.impact_rate = Number(payload.impact_rate || 0.2);
  payload.seed = payload.seed ? Number(payload.seed) : null;
  payload.unhinged = payload.unhinged === "on";
  payload.quality_gate_enabled = payload.quality_gate_enabled === "on";
  payload.optimization_enabled = payload.optimization_enabled === "on";
  payload.hook_first_enabled = payload.hook_first_enabled === "on";
  payload.candidate_selection_enabled = payload.candidate_selection_enabled === "on";
  payload.caption_autofix_enabled = payload.caption_autofix_enabled === "on";

  payload.render_mode = payload.render_mode === "preview" ? "preview" : "final";
  if (!payload.bg_category) payload.bg_category = null;
  if (!payload.template_name) payload.template_name = null;
  if (!payload.preset_name) payload.preset_name = null;

  if (variantSelection) {
    payload.topic_prompt += ` Preferred hook: ${variantSelection.hook}. Preferred title: ${variantSelection.title}.`;
  }

  setStatus("queued", 0);
  appendLogs([]);
  previewVideo.removeAttribute("src");
  previewVideo.load();
  downloadLink.href = "#";
  downloadLink.classList.remove("ready");
  generateBtn.disabled = true;

  try {
    const data = await fetchJSON("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    jobIdLabel.textContent = `Job: ${data.job_id}`;
    pollTimer = setInterval(() => pollStatus(data.job_id), 2000);
    pollStatus(data.job_id);
  } catch (err) {
    const message = err && err.message ? err.message : "Request failed";
    setStatus(`error: ${message}`, 0);
    appendLogs([message]);
    generateBtn.disabled = false;
  }
});

if (durationInput) {
  durationInput.addEventListener("input", (event) => {
    durationLabel.textContent = `${event.target.value}s`;
  });
  durationLabel.textContent = `${durationInput.value}s`;
}

if (promptInput) {
  promptInput.addEventListener("input", updatePromptState);
  updatePromptState();
}

voicePreviewBtn.addEventListener("click", async () => {
  const voice = voiceSelect.value;
  try {
    const data = await fetchJSON("/voices/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice, text: "Quick voice preview for Shorts Studio." }),
    });
    const audio = new Audio(data.url);
    audio.play();
  } catch (err) {
    healthPill.textContent = "Voice preview failed";
  }
});

generateVariationsBtn.addEventListener("click", async () => {
  const formData = new FormData(genForm);
  const payload = {
    topic_prompt: String(formData.get("topic_prompt") || ""),
    preset_name: formData.get("preset_name") || null,
    count: 5,
  };
  if (!payload.topic_prompt) {
    setStatus("Add a prompt first.", 0);
    return;
  }
  try {
    const data = await fetchJSON("/generate_variations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    appendLogs([`Generated variations: ${data.job_ids.join(", ")}`]);
    loadGallery();
  } catch (err) {
    appendLogs(["Variation request failed."]);
  }
});

variantLabBtn.addEventListener("click", async () => {
  variantModal.classList.add("active");
  variantResults.innerHTML = "Loading...";
  try {
    const formData = new FormData(genForm);
    const payload = {
      topic_prompt: String(formData.get("topic_prompt") || ""),
      style: String(formData.get("style") || "brainrot_facts"),
      num_hooks: 10,
      num_titles: 10,
      pick: 3,
    };
    const data = await fetchJSON("/generate_variants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    variantResults.innerHTML = "";
    data.picks.forEach((pick, idx) => {
      const card = document.createElement("div");
      card.className = "panel subtle";
      card.innerHTML = `
        <strong>Pick ${idx + 1}</strong>
        <p>Hook: ${pick.hook.text}</p>
        <p>Title: ${pick.title.text}</p>
        <button type="button">Use this combo</button>
      `;
      card.querySelector("button").addEventListener("click", () => {
        variantSelection = { hook: pick.hook.text, title: pick.title.text };
        variantModal.classList.remove("active");
      });
      variantResults.appendChild(card);
    });
  } catch (err) {
    variantResults.textContent = "Variant lab failed.";
  }
});

variantCloseBtn.addEventListener("click", () => {
  variantModal.classList.remove("active");
});

previewBtn.addEventListener("click", async () => {
  await saveBeats();
  await triggerRender(true);
});

renderFinalBtn.addEventListener("click", async () => {
  await saveBeats();
  await triggerRender(false);
});

rerenderBtn.addEventListener("click", async () => {
  await saveBeats();
  await triggerRender(false);
});

addBeatBtn.addEventListener("click", () => {
  const last = currentBeats[currentBeats.length - 1];
  const nextTime = last ? Number(last.t) + 2.0 : 0.0;
  currentBeats.push({ t: nextTime, text: "New beat", on_screen: "New beat" });
  renderBeatsTable();
});

saveBeatsBtn.addEventListener("click", async () => {
  await saveBeats();
});

hookScoreBtn.addEventListener("click", async () => {
  if (!currentHook) return;
  const data = await fetchJSON("/score_hook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hook_text: currentHook }),
  });
  hookScoreEl.textContent = `Score: ${data.score}`;
});

rewriteHookBtn.addEventListener("click", async () => {
  if (!currentHook) return;
  const data = await fetchJSON("/rewrite_hook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hook_text: currentHook, style: currentProjectStyle }),
  });
  hookCandidates.innerHTML = "";
  data.candidates.forEach((candidate) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = candidate;
    btn.addEventListener("click", async () => {
      currentHook = candidate;
      hookTextEl.textContent = candidate;
      if (currentBeats.length) {
        currentBeats[0].text = candidate;
        currentBeats[0].on_screen = candidate;
      }
      await saveBeats();
    });
    hookCandidates.appendChild(btn);
  });
});

rerunBtn.addEventListener("click", async () => {
  if (!selectedGalleryJob) return;
  const steps = Array.from(document.querySelectorAll(".rerun-step"))
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => checkbox.value);
  if (!steps.length) return;
  await fetchJSON(`/rerun/${selectedGalleryJob}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ steps }),
  });
});

cancelJobBtn.addEventListener("click", async () => {
  if (!selectedGalleryJob) return;
  await fetchJSON(`/cancel/${selectedGalleryJob}`, { method: "POST" });
  cancelJobBtn.disabled = true;
});

publishPackBtn.addEventListener("click", async () => {
  if (!selectedGalleryJob) return;
  const data = await fetchJSON(`/projects/${selectedGalleryJob}/export_publish_pack`, {
    method: "POST",
  });
  publishPackLink.href = data.path;
  publishPackLink.classList.add("ready");
});

viralityReportBtn.addEventListener("click", async () => {
  if (!selectedGalleryJob) return;
  const data = await fetchJSON(`/projects/${selectedGalleryJob}/export_virality_report`, {
    method: "POST",
  });
  viralityReportLink.href = data.path;
  viralityReportLink.classList.add("ready");
});

presetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(presetForm);
  const payload = Object.fromEntries(formData.entries());
  payload.duration_seconds = Number(payload.duration_seconds || 35);
  payload.speech_speed = Number(payload.speech_speed || 1.08);
  payload.zoom_punch_strength = Number(payload.zoom_punch_strength || 0.3);
  payload.shake_strength = Number(payload.shake_strength || 0.2);
  payload.drift_strength = Number(payload.drift_strength || 0.3);
  payload.loop_smoothing_seconds = Number(payload.loop_smoothing_seconds || 0.35);
  payload.quality_gate_enabled = payload.quality_gate_enabled === "on";
  payload.min_hook_score = Number(payload.min_hook_score || 70);
  payload.max_words_per_second = Number(payload.max_words_per_second || 4.0);
  payload.max_retries = Number(payload.max_retries || 2);
  payload.optimization_enabled = payload.optimization_enabled === "on";
  payload.optimization_max_attempts = Number(payload.optimization_max_attempts || 5);
  payload.max_words_per_second_estimate = Number(payload.max_words_per_second_estimate || 4.0);
  payload.min_beats_per_10s = Number(payload.min_beats_per_10s || 4.0);
  payload.max_beats_per_10s = Number(payload.max_beats_per_10s || 7.0);
  payload.hook_pool_size = Number(payload.hook_pool_size || 10);
  payload.hook_pick = Number(payload.hook_pick || 3);
  payload.script_candidate_count = Number(payload.script_candidate_count || 3);
  payload.max_chars_per_line = Number(payload.max_chars_per_line || 18);
  payload.min_caption_duration = Number(payload.min_caption_duration || 0.55);
  payload.music_ducking_strength = Number(payload.music_ducking_strength || 0.6);
  payload.impact_rate = Number(payload.impact_rate || 0.2);
  payload.hook_first_enabled = payload.hook_first_enabled === "on";
  payload.candidate_selection_enabled = payload.candidate_selection_enabled === "on";
  payload.caption_autofix_enabled = payload.caption_autofix_enabled === "on";
  try {
    await fetchJSON("/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    presetForm.reset();
    loadPresets();
  } catch (err) {
    presetList.textContent = "Failed to save preset.";
  }
});

batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(batchForm);
  const prompts = String(formData.get("prompts") || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!prompts.length) {
    batchLog.textContent = "Add prompts first.";
    return;
  }
  const payload = {
    prompts,
    preset_name: formData.get("preset_name") || null,
  };
  try {
    const data = await fetchJSON("/batch_generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    batchLog.textContent = `Batch ${data.batch_id}: ${data.job_ids.join(", ")}`;
  } catch (err) {
    batchLog.textContent = "Batch request failed.";
  }
});

abForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(abForm);
  const payload = {
    topic_prompt: formData.get("topic_prompt"),
    preset_name: formData.get("preset_name") || null,
    variants: [
      {
        name: "A",
        overrides: {
          caption_style: formData.get("a_caption_style"),
          voice: formData.get("a_voice"),
        },
      },
      {
        name: "B",
        overrides: {
          caption_style: formData.get("b_caption_style"),
          voice: formData.get("b_voice"),
        },
      },
    ],
  };
  try {
    const data = await fetchJSON("/ab_generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    abLog.textContent = `AB jobs: ${data.job_ids.join(", ")}`;
    loadGallery();
  } catch (err) {
    abLog.textContent = "AB test failed.";
  }
});

downloadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (downloadTimer) {
    clearInterval(downloadTimer);
    downloadTimer = null;
  }

  const formData = new FormData(downloadForm);
  const urlsRaw = formData.get("urls") || "";
  const urls = String(urlsRaw)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!urls.length) {
    downloadStatusText.textContent = "error: add at least one URL";
    downloadBtn.disabled = false;
    return;
  }

  const payload = {
    name: formData.get("name") || null,
    kind: formData.get("kind") || "custom",
    urls,
    overwrite: formData.get("overwrite") === "on",
  };

  downloadStatusText.textContent = "queued";
  downloadProgressBar.style.width = "0%";
  downloadIdLabel.textContent = "";
  downloadPathLabel.textContent = "";
  appendDownloadLogs([]);
  downloadBtn.disabled = true;

  try {
    const data = await fetchJSON("/models/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    downloadIdLabel.textContent = `Download: ${data.download_id}`;
    downloadTimer = setInterval(() => pollDownload(data.download_id), 2000);
    pollDownload(data.download_id);
  } catch (err) {
    downloadStatusText.textContent = "error";
    downloadBtn.disabled = false;
  }
});

async function loadAssets() {
  const type = assetTypeSelect.value;
  const query = assetSearchInput.value.trim();
  const url = query
    ? `/assets/list?type=${encodeURIComponent(type)}&q=${encodeURIComponent(query)}`
    : `/assets/list?type=${encodeURIComponent(type)}`;
  try {
    const data = await fetchJSON(url);
    currentAssets = data.items || [];
    renderAssetList();
  } catch (err) {
    assetList.textContent = "No assets found.";
  }
}

function renderAssetList() {
  assetList.innerHTML = "";
  currentAssets.forEach((asset) => {
    const card = document.createElement("div");
    card.className = "asset-card";
    card.textContent = `${asset.name} (${asset.tags.join(", ") || "no tags"})`;
    card.addEventListener("click", () => showAssetDetail(asset));
    assetList.appendChild(card);
  });
}

async function showAssetDetail(asset) {
  selectedAsset = asset;
  const data = await fetchJSON(`/assets/metadata?path=${encodeURIComponent(asset.path)}`);
  const previewUrl = `/assets/preview?path=${encodeURIComponent(asset.path)}`;
  const isVideo = asset.type === "bg_clips";
  const isAudio = asset.type === "music" || asset.type === "sfx";
  const duration = data.duration_seconds ? `${data.duration_seconds.toFixed(2)}s` : "n/a";
  assetDetail.innerHTML = `
    <p><strong>${data.name}</strong></p>
    <p class="muted">${data.path}</p>
    <p class="muted">Size: ${(data.size_bytes / 1024 / 1024).toFixed(2)} MB | Duration: ${duration}</p>
    ${isVideo ? `<video controls playsinline src="${previewUrl}"></video>` : ""}
    ${isAudio ? `<audio controls src="${previewUrl}"></audio>` : ""}
    ${asset.type === "fonts" ? `<p style="font-family: '${data.name.replace(".ttf","")}', sans-serif;">Sample font preview</p>` : ""}
    <div>
      <label>Tags (comma separated)</label>
      <input type="text" id="asset-tags-input" value="${(data.tags || []).join(", ")}" />
      <button type="button" id="save-tags-btn">Save tags</button>
    </div>
    <div id="hotspot-panel"></div>
  `;
  document.getElementById("save-tags-btn").addEventListener("click", async () => {
    const tagInput = document.getElementById("asset-tags-input").value;
    const tags = tagInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    await fetchJSON("/assets/tags", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: data.path, type: asset.type, tags }),
    });
    loadAssets();
  });

  if (asset.type === "bg_clips") {
    const panel = document.getElementById("hotspot-panel");
    panel.innerHTML = `
      <h3>Hotspots</h3>
      <div class="hotspot-list" id="hotspot-list"></div>
      <div class="row">
        <label>Start <input type="number" step="0.1" id="hotspot-start" /></label>
        <label>End <input type="number" step="0.1" id="hotspot-end" /></label>
        <label>Label <input type="text" id="hotspot-label" /></label>
      </div>
      <button type="button" id="add-hotspot-btn">Add hotspot</button>
    `;
    selectedAsset.hotspots = data.hotspots || [];
    renderHotspots(selectedAsset.hotspots);
    document.getElementById("add-hotspot-btn").addEventListener("click", async () => {
      const start = Number(document.getElementById("hotspot-start").value || 0);
      const end = Number(document.getElementById("hotspot-end").value || 0);
      const label = document.getElementById("hotspot-label").value || "";
      const hotspots = (selectedAsset.hotspots || []).concat([{ start, end, label }]);
      await fetchJSON("/assets/hotspots", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: data.path, hotspots }),
      });
      selectedAsset.hotspots = hotspots;
      renderHotspots(hotspots);
    });
  }
}

function renderHotspots(hotspots) {
  const list = document.getElementById("hotspot-list");
  if (!list) return;
  list.innerHTML = "";
  hotspots.forEach((spot, idx) => {
    const row = document.createElement("div");
    row.className = "hotspot-item";
    row.innerHTML = `
      <span>${spot.start}s - ${spot.end}s (${spot.label || "hotspot"})</span>
      <button type="button">Delete</button>
    `;
    row.querySelector("button").addEventListener("click", async () => {
      const updated = hotspots.filter((_, i) => i !== idx);
      await fetchJSON("/assets/hotspots", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: selectedAsset.path, hotspots: updated }),
      });
      selectedAsset.hotspots = updated;
      renderHotspots(updated);
    });
    list.appendChild(row);
  });
}

assetTypeSelect.addEventListener("change", loadAssets);
assetSearchInput.addEventListener("input", loadAssets);

async function loadCampaigns() {
  try {
    const data = await fetchJSON("/campaigns");
    campaignList.innerHTML = "";
    data.campaigns.forEach((campaign) => {
      const card = document.createElement("div");
      card.className = "preset-card";
      card.innerHTML = `
        <strong>${campaign.name}</strong>
        <span>${campaign.status}</span>
        <button type="button">Open</button>
      `;
      card.querySelector("button").addEventListener("click", () => {
        showCampaign(campaign.campaign_id);
      });
      campaignList.appendChild(card);
    });
  } catch (err) {
    campaignList.textContent = "No campaigns found.";
  }
}

async function showCampaign(campaignId) {
  selectedCampaignId = campaignId;
  campaignExportLink.href = "#";
  campaignExportLink.classList.remove("ready");
  try {
    const data = await fetchJSON(`/campaigns/${campaignId}`);
    campaignDetail.textContent = JSON.stringify(data.metadata || {}, null, 2);
    const memory = await fetchJSON(`/campaigns/${campaignId}/memory`);
    campaignMemory.textContent = JSON.stringify(memory || {}, null, 2);
    campaignJobs.innerHTML = "";
    (data.jobs || []).forEach((job) => {
      const card = document.createElement("div");
      card.className = "preset-card";
      card.innerHTML = `
        <strong>Part ${job.series_number}</strong>
        <span>${job.job_id}</span>
        <a class="download ready" href="/outputs/${job.job_id}/final.mp4" download>MP4</a>
      `;
      campaignJobs.appendChild(card);
    });
  } catch (err) {
    campaignDetail.textContent = "Failed to load campaign.";
  }
}

campaignForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(campaignForm);
  const payload = Object.fromEntries(formData.entries());
  try {
    const data = await fetchJSON("/campaigns/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    selectedCampaignId = data.campaign_id;
    loadCampaigns();
  } catch (err) {
    campaignDetail.textContent = "Campaign creation failed.";
  }
});

campaignRunBtn.addEventListener("click", async () => {
  if (!selectedCampaignId) return;
  await fetchJSON(`/campaigns/${selectedCampaignId}/run`, { method: "POST" });
  loadCampaigns();
});

campaignExportBtn.addEventListener("click", async () => {
  if (!selectedCampaignId) return;
  const data = await fetchJSON(`/campaigns/${selectedCampaignId}/export`, { method: "POST" });
  campaignExportLink.href = data.path;
  campaignExportLink.classList.add("ready");
});

campaignExportProBtn.addEventListener("click", async () => {
  if (!selectedCampaignId) return;
  const data = await fetchJSON(`/campaigns/${selectedCampaignId}/export_pro`, { method: "POST" });
  campaignExportLink.href = data.path;
  campaignExportLink.classList.add("ready");
});

campaignMemoryResetBtn.addEventListener("click", async () => {
  if (!selectedCampaignId) return;
  const data = await fetchJSON(`/campaigns/${selectedCampaignId}/memory/reset`, { method: "POST" });
  campaignMemory.textContent = JSON.stringify(data.memory || {}, null, 2);
});

envForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await saveEnv(true);
});

envSaveNoReload.addEventListener("click", async () => {
  await saveEnv(false);
});

envModalOpen.addEventListener("click", () => {
  envModal.classList.remove("active");
  const settingsTab = document.querySelector(".tab[data-tab='settings']");
  if (settingsTab) {
    switchTab(settingsTab);
  }
});

envModalClose.addEventListener("click", () => {
  envModal.classList.remove("active");
});

loadTemplates();
loadPresets();
loadGallery();
loadHealth();
loadConfig();
loadRecommendedModels();
loadAssets();
loadRoutingStatus();
loadBenchmarks();
loadWatchFolderStatus();
loadSchedulerStatus();
loadSchedulerRuns();
loadWatchPending();
loadCampaigns();
