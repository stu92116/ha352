const metrics = {
  temperature: ["水溫", "mdi:thermometer-water"],
  inlet_temperature: ["進水溫度", "mdi:thermometer"],
  recent: ["最近一次製水", "mdi:cup-water"],
  ratio: ["純廢比", "mdi:water-percent"],
  work: ["運轉", "mdi:water-sync"],
  heating: ["加熱", "mdi:fire"],
  lock: ["童鎖", "mdi:lock-outline"],
  uv: ["UV 殺菌", "mdi:shield-sun-outline"],
  holiday: ["假日模式", "mdi:palm-tree"],
};

const stateLabels = new Map([
  ["on", "開啟"], ["off", "關閉"], ["待机", "待機"], ["制水中", "製水中"],
  ["加热中", "加熱中"], ["未加热", "未加熱"], ["自动", "自動"],
]);
const missingStates = new Set(["unknown", "unavailable", "", "none"]);
const formatNumber = new Intl.NumberFormat("zh-TW", { maximumFractionDigits: 2 });

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]
  ));
}

const style = `
  :host { display:block; color-scheme:normal; }
  * { box-sizing:border-box; }
  .shell {
    --text:#152c38; --muted:#425f6c; --accent:#096777; --line:#d7e1e6;
    --panel:#fff; --wash:#edf5f6; --warn:#90431c; --focus:#2388a1;
    margin:12px auto; max-width:1340px; color:var(--text); padding:clamp(16px, 3.5vw, 48px);
    border-radius:28px; background:#f2f7f9;
    font-family:var(--primary-font-family, system-ui, sans-serif);
  }
  .shell.atelier {
    --text:#f7f1e4; --muted:#bebfb2; --accent:#e8c989; --line:#3b4c42;
    --panel:#182921; --wash:#14221b; --warn:#ffb58a; --focus:#f4d490;
    margin:12px auto; border-radius:28px; background:#0e1b15;
  }
  header { display:flex; justify-content:space-between; align-items:center; gap:14px; margin:0 0 24px; }
  h1,h2,p,figure { margin:0; }
  h1 { font-size:clamp(28px, 4vw, 45px); line-height:1.12; letter-spacing:-.045em; }
  h2 { font-size:17px; font-weight:700; }
  .model { color:var(--muted); font-size:13px; margin-top:8px; }
  .status { display:flex; align-items:center; gap:8px; color:var(--muted); border:1px solid var(--line); border-radius:99px; padding:8px 12px; font-size:12px; white-space:nowrap; }
  .status::before { content:""; width:7px; height:7px; flex:none; border-radius:100%; background:#7a888e; }
  .status.live::before { background:#43a889; }
  .status.alert { color:var(--warn); }
  .status.alert::before { background:currentColor; }
  .layout { display:grid; grid-template-columns:minmax(0,1.15fr) minmax(0,1fr); gap:16px; align-items:stretch; }
  .layout.full { grid-template-columns:minmax(0,1fr); }
  .surface { background:var(--panel); border:1px solid var(--line); border-radius:22px; padding:clamp(16px,2.5vw,25px); min-width:0; }
  .hero {
    background:radial-gradient(ellipse at 79% 35%,#d8f3f3 0%,#ecf7f8 51%,#f9fbfc 88%);
    min-height:320px; position:relative; isolation:isolate; display:flex; flex-direction:column;
    justify-content:space-between; gap:22px; box-shadow:0 14px 38px #18364512;
  }
  .ateliersample {
    color:#fff8e9; min-height:340px; overflow:hidden;
    background:#233a30; border-color:#49614c;
    --muted:#e4dfcc; --accent:#ffdd9f; --line:#e7f0d840; --focus:#ffdd9f;
  }
  .kitchen { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; object-position:62% 59%; z-index:-2; }
  .ateliersample::after { content:""; position:absolute; z-index:-1; inset:0; background:linear-gradient(101deg,#0d2015f5 0%,#132b20e8 35%,#20362bb3 63%,#12201669 100%); }
  .herohead { display:flex; align-items:center; gap:9px; color:var(--accent); font-size:14px; font-weight:700; }
  .herohead ha-icon { --mdc-icon-size:21px; }
  .mainmetric { display:flex; align-items:center; gap:clamp(13px,2vw,26px); }
  .readout {
    display:flex; flex-direction:column; justify-content:center; align-items:center; flex:0 0 auto;
    width:clamp(133px,16vw,196px); aspect-ratio:1; border-radius:100%;
    background:radial-gradient(circle at 36% 24%,#ffffff 0%,#e9f9fa 71%);
    border:1px solid #aacfd1; box-shadow:0 0 0 8px #95c9c727,0 10px 34px #1356601c;
  }
  .ateliersample .readout { border-radius:20px; aspect-ratio:auto; min-height:143px; align-items:flex-start; padding:14px 22px; background:#112f26c6; border-color:#d7b4759e; box-shadow:0 12px 42px #040c075c; }
  .readout strong { font-size:clamp(47px,7vw,79px); font-weight:680; letter-spacing:-.08em; line-height:1; }
  .readout small, .subunit { color:var(--muted); font-size:12px; }
  .comparison { display:grid; gap:15px; }
  .comparison strong { font-size:clamp(20px,3vw,35px); line-height:1.15; }
  .comparison span, .cardlabel { font-size:12px; color:var(--muted); }
  .comparison .readline { display:block; text-align:left; }
  .detail { border-top:1px solid var(--line); padding-top:12px; display:flex; justify-content:space-between; gap:8px; color:var(--muted); font-size:12px; }
  .side { display:grid; grid-template-rows:auto 1fr; gap:16px; min-width:0; }
  .filter-list { margin-top:15px; display:grid; gap:13px; }
  .filter { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:11px; width:100%; }
  .filter > ha-icon { display:grid; place-items:center; --mdc-icon-size:18px; width:35px; height:35px; color:var(--accent); background:var(--wash); border-radius:10px; }
  .filter-body { min-width:0; text-align:left; }
  .filter-num { font-size:15px; font-weight:700; font-variant-numeric:tabular-nums; }
  .bar { display:block; margin-top:6px; width:100%; height:6px; background:var(--wash); border-radius:99px; overflow:hidden; }
  .fill { display:block; height:100%; background:var(--accent); border-radius:99px; }
  .low .fill { background:#d78d5e; }
  .low .filter-num, .warning { color:var(--warn); }
  .warning { margin-top:10px; font-size:12px; }
  .stat-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:13px; }
  .stat { min-height:65px; text-align:left; background:var(--wash); border-radius:12px; padding:9px 11px; display:flex; flex-direction:column; justify-content:center; align-items:flex-start; gap:5px; min-width:0; }
  .stat strong { font-size:18px; font-weight:700; white-space:nowrap; }
  .stat .cardlabel { display:flex; align-items:center; gap:5px; }
  .stat ha-icon { --mdc-icon-size:15px; color:var(--accent); }
  strong { font-variant-numeric:tabular-nums; }
  button { border:0; color:inherit; background:transparent; font:inherit; padding:0; }
  button[data-entity], button[data-range] { cursor:pointer; }
  button:focus-visible { outline:2px solid var(--focus); outline-offset:4px; }
  button[data-entity]:hover { filter:brightness(.94); }
  .operations, .history { margin-top:16px; }
  .chips { display:flex; gap:9px; flex-wrap:wrap; margin-top:13px; }
  .chip { min-height:40px; padding:6px 10px; border:1px solid var(--line); border-radius:11px; display:flex; align-items:center; gap:7px; font-size:13px; }
  .chip ha-icon { --mdc-icon-size:16px; color:var(--accent); }
  .chip span { color:var(--muted); font-size:12px; }
  .history-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; }
  .range { display:flex; border:1px solid var(--line); border-radius:10px; padding:3px; gap:2px; }
  .range button { min-width:52px; min-height:32px; padding:0 6px; color:var(--muted); font-size:12px; }
  .range button[aria-pressed="true"] { color:var(--text); background:var(--wash); border-radius:7px; }
  canvas { display:block; width:100%; height:156px; margin-top:6px; }
  .legend { display:flex; gap:18px; font-size:12px; color:var(--muted); margin-top:5px; }
  .legend i { margin-right:6px; display:inline-block; width:9px; height:9px; border-radius:50%; background:#dfbc78; }
  .legend span:first-child i { background:#7cbda7; }
  .empty { color:var(--muted); margin-top:16px; font-size:13px; }
  [hidden] { display:none !important; }
  @media(max-width:760px) {
    .layout { grid-template-columns:1fr; gap:12px; }
    .side { grid-template-rows:auto; gap:12px; }
    .hero,.ateliersample { min-height:255px; }
    .shell,.shell.atelier { margin:5px; border-radius:20px; }
    header { margin-bottom:16px; }
    .operations,.history { margin-top:12px; }
  }
  @media(max-width:360px) { .status { padding:6px 8px; } .chip { flex:1 1 auto; } }
`;

class Ha352PurifierCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${style}</style><div id="content"></div>`;
    this.content = this.shadowRoot.getElementById("content");
    this.range = 24;
    this.history = {};
    this.historyError = false;
    this.historyKey = "";
    this.observer = new ResizeObserver(() => this.drawHistory());
    this.content.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (button?.dataset.entity) {
        this.dispatchEvent(new CustomEvent("hass-more-info", {
          bubbles: true, composed: true, detail: { entityId: button.dataset.entity },
        }));
      }
      if (button?.dataset.range && Number(button.dataset.range) !== this.range) {
        this.range = Number(button.dataset.range);
        this.refreshHistory();
      }
    });
  }

  connectedCallback() {
    this.observer.observe(this);
    this.render();
    this.refreshHistory();
  }

  disconnectedCallback() {
    this.observer.disconnect();
    this.historyKey = "";
  }

  setConfig(config) {
    if (!config.entities?.outlet || !config.entities?.inlet) {
      throw new Error("請設定進水和出水 TDS 實體。");
    }
    this.config = config;
    this.render();
    this.refreshHistory();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
    this.refreshHistory();
  }

  getCardSize() { return 8; }

  sample(key) {
    const entry = this._hass?.states[this.config.entities[key]];
    if (!entry || missingStates.has(entry.state) || entry.state === "65535") {
      return { value: null, text: "—", unit: "" };
    }
    const number = Number(entry.state);
    const value = Number.isFinite(number) ? number : null;
    return {
      value,
      text: value === null ? (stateLabels.get(entry.state) ?? entry.state) : formatNumber.format(value),
      unit: entry.attributes.unit_of_measurement ?? "",
      at: entry.last_reported ?? entry.last_updated,
    };
  }

  entityButton(key, className, html, label) {
    const id = this.config.entities[key];
    if (!id) return `<div class="${className}">${html}</div>`;
    return `<button type="button" class="${className}" data-entity="${escapeHtml(id)}" aria-label="${escapeHtml(label)}">${html}</button>`;
  }

  filter(key, name, sample) {
    const clamp = sample.value === null ? 0 : Math.max(0, Math.min(100, sample.value));
    const low = sample.value !== null && sample.value <= 15;
    return this.entityButton(key, `filter${low ? " low" : ""}`, `
      <ha-icon icon="mdi:filter-variant" aria-hidden="true"></ha-icon>
      <span class="filter-body"><span class="cardlabel">${name}</span>
        <span class="bar" aria-hidden="true"><span class="fill" style="width:${clamp}%"></span></span></span>
      <span class="filter-num">${escapeHtml(sample.text)}${sample.value === null ? "" : "%"}</span>`,
    name + " 詳情");
  }

  render() {
    if (!this.config || !this._hass) return;
    const sample = Object.fromEntries(Object.keys(this.config.entities).map((key) => [key, this.sample(key)]));
    const [outlet, inlet] = [sample.outlet, sample.inlet];
    const signature = JSON.stringify([this.config, sample]);
    if (signature === this.signature) return;
    this.signature = signature;
    const focus = this.shadowRoot.activeElement?.dataset;
    const atelier = this.config.style === "atelier";
    const error = sample.error?.value;
    const connected = inlet.value !== null || outlet.value !== null;
    const status = error ? `故障代碼 ${sample.error.text}` : connected ? "已接收讀值" : "暫無讀值";
    const reduction = inlet.value > 0 && outlet.value !== null && outlet.value <= inlet.value
      ? `${formatNumber.format(100 * (inlet.value - outlet.value) / inlet.value)}%` : "—";
    const changed = outlet.at ? new Intl.DateTimeFormat("zh-TW", {
      timeZone: this._hass.config?.time_zone,
      month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(new Date(outlet.at)) : "—";
    const photo = atelier && typeof this.config.photo === "string" && this.config.photo.startsWith("/local/")
      ? `<img class="kitchen" src="${escapeHtml(this.config.photo)}" alt="">` : "";
    const filters = ["filter_1", "filter_2"].filter((key) => sample[key]);
    const needsService = filters
      .filter((key) => sample[key].value !== null && sample[key].value <= 15)
      .map((key) => `濾芯 ${key.at(-1)}`);
    const stats = ["temperature", "inlet_temperature", "recent", "ratio"].filter((key) => sample[key]);
    const operation = ["work", "heating", "lock", "uv", "holiday"].filter((key) => sample[key]);
    this.content.innerHTML = `
      <main class="shell ${atelier ? "atelier" : ""}">
        <header><div><h1>${escapeHtml(this.config.title || "廚房淨水")}</h1>
          <p class="model">${escapeHtml(this.config.model || "352 A418H")}</p></div>
          <span class="status ${error ? "alert" : connected ? "live" : ""}">${escapeHtml(status)}</span>
        </header>
        <div class="layout${filters.length || stats.length ? "" : " full"}">
          <section class="surface hero ${atelier ? "ateliersample" : ""}" aria-label="水質">
            ${photo}<div class="herohead"><ha-icon icon="mdi:water-check-outline" aria-hidden="true"></ha-icon>出水 TDS</div>
            <div class="mainmetric">
              ${this.entityButton("outlet", "readout", `<strong>${escapeHtml(outlet.text)}</strong><small>${escapeHtml(outlet.unit || "ppm")}</small>`, "出水 TDS 詳情")}
              <div class="comparison">
                ${this.entityButton("inlet", "readline", `<span>進水 TDS</span><br><strong>${escapeHtml(inlet.text)}</strong> <small class="subunit">${escapeHtml(inlet.unit || "ppm")}</small>`, "進水 TDS 詳情")}
                <div><span>TDS 降幅</span><br><strong>${reduction}</strong></div>
              </div>
            </div>
            <div class="detail"><span>總溶解固體（TDS）</span><span>${changed === "—" ? changed : "更新 " + changed}</span></div>
          </section>
          ${filters.length || stats.length ? `<div class="side">
            ${filters.length ? `<section class="surface"><h2>濾芯壽命</h2>
              <div class="filter-list">${filters.map((key) => this.filter(key, `濾芯 ${key.at(-1)}`, sample[key])).join("")}</div>
              ${needsService.length ? `<p class="warning">${needsService.join("、")}接近更換</p>` : ""}
            </section>` : ""}
            ${stats.length ? `<section class="surface"><h2>製水資訊</h2><div class="stat-grid">
              ${stats.map((key) => this.entityButton(key, "stat", `
                <span class="cardlabel"><ha-icon icon="${metrics[key][1]}" aria-hidden="true"></ha-icon>${metrics[key][0]}</span>
                <strong>${escapeHtml(sample[key].text)} <small class="subunit">${escapeHtml(sample[key].unit)}</small></strong>`,
              metrics[key][0] + "詳情")).join("")}
            </div></section>` : ""}
          </div>` : ""}
        </div>
        ${atelier ? `
          <section class="surface history">
            <div class="history-heading"><h2>TDS 趨勢</h2><div class="range" aria-label="歷史範圍">
              <button type="button" data-range="24">24 小時</button><button type="button" data-range="168">7 天</button>
            </div></div>
            <canvas role="img" aria-label="進水與出水 TDS 趨勢"></canvas>
            <div class="legend"><span><i></i>進水 TDS</span><span><i></i>出水 TDS</span></div>
            <p class="empty" role="status" hidden></p>
          </section>` : ""}
        ${operation.length ? `<section class="surface operations"><h2>裝置狀態</h2><div class="chips">
          ${operation.map((key) => this.entityButton(key, "chip", `
            <ha-icon icon="${metrics[key][1]}" aria-hidden="true"></ha-icon>${metrics[key][0]}<span>${escapeHtml(sample[key].text)}</span>`,
          metrics[key][0] + "詳情")).join("")}
        </div></section>` : ""}
      </main>`;
    if (focus?.entity || focus?.range) {
      const selector = focus.entity ? `[data-entity="${CSS.escape(focus.entity)}"]` : `[data-range="${focus.range}"]`;
      this.content.querySelector(selector)?.focus({ preventScroll: true });
    }
    this.drawHistory();
  }

  async refreshHistory() {
    if (!this.isConnected || this.config?.style !== "atelier" || !this._hass) return;
    const entities = [this.config.entities.inlet, this.config.entities.outlet];
    const now = Date.now();
    const key = JSON.stringify([entities, this.range, Math.floor(now / 300000)]);
    if (this.historyKey === key) return;
    const start = now - this.range * 3600000;
    this.historyKey = key;
    this.history = {};
    this.historyError = false;
    this.drawHistory();
    try {
      const result = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: new Date(start).toISOString(),
        end_time: new Date(now).toISOString(),
        entity_ids: entities,
        minimal_response: true,
        no_attributes: true,
      });
      if (this.historyKey !== key) return;
      this.history = { start, now, series: entities.map((id) => (result[id] || []).map((item) => {
        const value = Number(item.s ?? item.state);
        const epoch = item.lu ?? item.last_updated ?? item.last_changed;
        const time = typeof epoch === "number" ? epoch * 1000 : Date.parse(epoch);
        return { time, value: value >= 0 && value < 65535 && !missingStates.has(item.s ?? item.state) ? value : null };
      }).filter((point) => Number.isFinite(point.time))) };
    } catch {
      if (this.historyKey !== key) return;
      this.historyError = true;
    }
    this.drawHistory();
  }

  drawHistory() {
    const canvas = this.content.querySelector("canvas");
    if (!canvas) return;
    for (const button of this.content.querySelectorAll("[data-range]")) {
      button.setAttribute("aria-pressed", String(Number(button.dataset.range) === this.range));
    }
    const empty = this.content.querySelector(".empty");
    const legend = this.content.querySelector(".legend");
    const { start, now, series } = this.history;
    const data = series?.flatMap((line) => line.filter((point) => point.value !== null));
    canvas.hidden = legend.hidden = !data?.length;
    empty.hidden = !canvas.hidden;
    if (canvas.hidden) {
      empty.textContent = this.historyError ? "暫時無法讀取歷史紀錄" : series ? "這段期間沒有 TDS 紀錄" : "正在載入歷史紀錄";
      return;
    }
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;
    const ctx = canvas.getContext("2d");
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * scale);
    canvas.height = Math.floor(height * scale);
    ctx.scale(scale, scale);
    const max = Math.max(1, ...data.map((point) => point.value));
    const limit = Math.ceil(max / 4) * 4;
    const left = 34, top = 12, bottom = height - 24, right = width - 8;
    const x = (time) => left + (Math.max(start, Math.min(time, now)) - start) * (right - left) / (now - start);
    const y = (value) => bottom - value * (bottom - top) / limit;
    ctx.font = "11px system-ui";
    ctx.fillStyle = "#bebfb2";
    ctx.textAlign = "right";
    for (let index = 0; index <= 4; index++) {
      const value = limit * index / 4;
      ctx.strokeStyle = "#3b4c42";
      ctx.beginPath();
      ctx.moveTo(left, y(value));
      ctx.lineTo(right, y(value));
      ctx.stroke();
      ctx.fillText(String(value), left - 7, y(value) + 4);
    }
    const timeFormatter = new Intl.DateTimeFormat("zh-TW", this.range === 24
      ? { hour: "2-digit", minute: "2-digit", hour12: false } : { month: "numeric", day: "numeric" });
    ctx.textAlign = "left";
    ctx.fillText(timeFormatter.format(new Date(start)), left, height - 4);
    ctx.textAlign = "right";
    ctx.fillText("現在", right, height - 4);
    series.forEach((points, index) => {
      ctx.strokeStyle = ["#7cbda7", "#dfbc78"][index];
      ctx.lineWidth = 2;
      ctx.beginPath();
      let previous = null;
      for (const point of points) {
        if (previous) ctx.lineTo(x(point.time), y(previous.value));
        if (point.value !== null) {
          if (previous) ctx.lineTo(x(point.time), y(point.value));
          else ctx.moveTo(x(point.time), y(point.value));
        }
        previous = point.value === null ? null : point;
      }
      if (previous) ctx.lineTo(right, y(previous.value));
      ctx.stroke();
    });
  }
}

if (!customElements.get("ha352-purifier-card")) {
  customElements.define("ha352-purifier-card", Ha352PurifierCard);
}
