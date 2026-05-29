const artifacts = [
  ["hotel", "호텔 예약 화면", "hotel-booking-screenshot.png", "IMG", "체크인 시간, 늦은 도착, 예약번호 확인", "예약 요약 영역", "체크인 15:00. 22:00 이후 도착 시 숙소 연락 필요.", ["checkin", "checkout", "lateArrival", "bookingNumber"]],
  ["host", "호스트 체크인 안내", "host-message-capture.png", "IMG", "출입 코드, 도착 지연 연락 조건 확인", "셀프 체크인 안내 영역", "출입 코드는 마스킹됨. 22:00 이후 도착 시 호스트에게 연락.", ["doorCode"]],
  ["voucher", "후지산 투어 바우처", "fuji-tour-voucher.pdf", "PDF", "모바일 바우처, 집합 시간, 장소 확인", "바우처 제시 조건 영역", "모바일 바우처 가능. 출발 15분 전까지 도착.", ["mobileVoucher", "meetTime", "meetPlace"]],
  ["rental", "렌터카 예약 약관", "rental-car-terms.pdf", "PDF", "연료 정책, 보증금 조건 확인", "연료 정책 표", "가득 채워 반납. 보증금 JPY 50,000 보류 가능.", ["fuelPolicy", "deposit"]],
  ["receipt", "호텔 도시세 영수증", "hotel-city-tax-receipt.jpg", "JPG", "도시세, 추가 결제 이유 확인", "금액 표시 영역", "체크인 시 도시세 JPY 1,200 결제.", ["cityTax"]]
].map(([id, name, file, ext, meta, locator, snippet, facts]) => ({ id, name, file, ext, meta, locator, snippet, facts }));

const seedFacts = {
  checkin: makeFact("checkin", "hotel", "숙소 체크인", "체크인", "15:00", 0.96, "호텔 예약 화면 · 예약 요약 영역"),
  checkout: makeFact("checkout", "hotel", "숙소 체크인", "체크아웃", "11:00", 0.91, "호텔 예약 화면 · 예약 요약 영역"),
  lateArrival: makeFact("lateArrival", "hotel", "숙소 체크인", "늦은 도착", "22:00 이후 숙소 연락 필요", 0.88, "호텔 예약 화면 · 늦은 도착 안내"),
  bookingNumber: makeFact("bookingNumber", "hotel", "숙소 체크인", "예약번호", "****1234", 0.84, "호텔 예약 화면 · 예약번호 영역", true),
  doorCode: makeFact("doorCode", "host", "숙소 체크인", "출입 코드", "수동 확인 필요", 0.64, "호스트 체크인 안내 · 셀프 체크인 안내", true),
  mobileVoucher: makeFact("mobileVoucher", "voucher", "후지산 투어", "바우처 제시", "모바일 바우처 가능", 0.93, "후지산 투어 바우처 · 2쪽 바우처 조건"),
  meetTime: makeFact("meetTime", "voucher", "후지산 투어", "집합 시간", "08:45", 0.89, "후지산 투어 바우처 · 1쪽 집합 안내"),
  meetPlace: makeFact("meetPlace", "voucher", "후지산 투어", "집합 장소", "Shinjuku Center Building 1F", 0.78, "후지산 투어 바우처 · 1쪽 집합 장소"),
  fuelPolicy: makeFact("fuelPolicy", "rental", "렌터카 수령", "연료 정책", "가득 채워 반납", 0.87, "렌터카 예약 약관 · 4쪽 연료 정책 표"),
  deposit: makeFact("deposit", "rental", "렌터카 수령", "보증금", "JPY 50,000 보류 가능", 0.81, "렌터카 예약 약관 · 3쪽 보증금 안내"),
  cityTax: makeFact("cityTax", "receipt", "숙소 체크인", "도시세", "JPY 1,200", 0.86, "호텔 도시세 영수증 · 금액 표시 영역")
};

const schedules = [
  ["숙소 체크인", "5월 12일 · 신주쿠"],
  ["후지산 투어", "5월 13일 · 도쿄 출발"],
  ["렌터카 수령", "5월 14일 · 가와구치코"]
];

let facts = clone(seedFacts);
let selectedArtifact = "hotel";

const $ = (selector) => document.querySelector(selector);
const approvedFacts = () => Object.values(facts).filter((fact) => fact.status === "approved");
const byArtifact = (id) => artifacts.find((artifact) => artifact.id === id);

function makeFact(id, artifactId, schedule, label, value, confidence, citation, sensitive = false) {
  return { id, artifactId, schedule, label, value, confidence, citation, sensitive, status: "pending" };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function showToast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("show");
  window.setTimeout(() => $("#toast").classList.remove("show"), 1700);
}

function switchView(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === name));
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
}

function renderArtifacts() {
  $("#artifactList").innerHTML = artifacts.map((artifact) => `
    <button class="artifact-item ${artifact.id === selectedArtifact ? "active" : ""}" data-artifact="${artifact.id}">
      <span class="file-badge">${artifact.ext}</span>
      <span class="artifact-text">
        <strong>${artifact.name}</strong>
        <span>${artifact.meta}</span>
        <small>${artifact.file}</small>
      </span>
    </button>
  `).join("");
}

function renderDocument() {
  const artifact = byArtifact(selectedArtifact);
  $("#docTitle").textContent = artifact.name;
  $("#docMeta").textContent = artifact.meta;
  $("#sourceName").textContent = artifact.name;
  $("#sourceFile").textContent = artifact.file;
  $("#sourceLocator").textContent = artifact.locator;
  $("#sourceSnippet").textContent = artifact.snippet;
}

function renderFacts() {
  const artifact = byArtifact(selectedArtifact);
  $("#factList").innerHTML = artifact.facts.map((id) => {
    const fact = facts[id];
    const confidenceLabel = fact.confidence >= 0.9 ? "근거 선명" : fact.confidence >= 0.78 ? "원문 확인 권장" : "직접 확인 필요";
    const statusLabel = fact.status === "approved" ? "저장됨" : fact.status === "rejected" ? "무시됨" : "확인 필요";
    const sensitive = fact.sensitive ? `<span class="pill warn">민감 정보</span>` : "";
    return `
      <article class="fact-card ${fact.status}">
        <div class="fact-head">
          <div>
            <h3>${fact.label} ${sensitive}</h3>
            <div class="fact-value">${fact.value}</div>
          </div>
          <div class="confidence">
            <span>${confidenceLabel} · ${statusLabel}</span>
            <div class="bar"><span style="width:${Math.round(fact.confidence * 100)}%"></span></div>
          </div>
        </div>
        <div class="citation"><span>원문 근거</span><code>${fact.citation}</code></div>
        <div class="fact-actions">
          <button class="success" data-action="approve" data-fact="${fact.id}">저장</button>
          <button data-action="edit" data-fact="${fact.id}">수정</button>
          <button class="danger" data-action="reject" data-fact="${fact.id}">무시</button>
        </div>
      </article>
    `;
  }).join("");
}

function renderHome() {
  const saved = new Set(approvedFacts().map((fact) => fact.id));
  const moments = [
    ["숙소 앞에서", "체크인할 때", "hotel", ["checkin", "lateArrival", "bookingNumber"], ["체크인 시간", "늦은 도착 조건", "예약번호"], "호텔에 늦게 도착하면 어떻게 돼?"],
    ["투어 출발 전", "집합 장소로 가기 전", "voucher", ["mobileVoucher", "meetTime", "meetPlace"], ["모바일 바우처", "집합 시간", "집합 장소"], "투어는 모바일 바우처만 보여줘도 돼?"],
    ["렌터카 반납 전", "카운터에 가기 전", "rental", ["fuelPolicy", "deposit"], ["연료 정책", "보증금 조건"], "렌터카 반납할 때 기름 채워야 해?"],
    ["여행 후 정리", "경비를 맞출 때", "receipt", ["cityTax"], ["도시세 영수증", "추가 결제 이유"], "이 호텔에서 왜 추가 결제했지?"]
  ];

  $("#momentGrid").innerHTML = moments.map(([title, subtitle, artifact, ids, items, question]) => {
    const count = ids.filter((id) => saved.has(id)).length;
    const done = count === ids.length;
    const label = done ? "저장됨" : count ? `${count}/${ids.length} 저장됨` : "확인 필요";
    return `
      <article class="moment-card ${done ? "done" : ""}">
        <div class="moment-head">
          <div><h2>${title}</h2><small>${subtitle}</small></div>
          <span class="pill ${done ? "good" : "warn"}">${label}</span>
        </div>
        <ul class="moment-list">
          ${items.map((item, index) => `<li><span class="check">${saved.has(ids[index]) ? "✓" : "!"}</span><span>${item}</span></li>`).join("")}
        </ul>
        <div class="moment-actions">
          <button data-open-review="${artifact}">원문 근거 확인</button>
          <button data-question="${question}">자료에 질문</button>
        </div>
      </article>
    `;
  }).join("");
}

function renderBoard() {
  const saved = approvedFacts();
  $("#boardGrid").innerHTML = schedules.map(([name, date]) => {
    const items = saved.filter((fact) => fact.schedule === name);
    const body = items.length
      ? items.map((fact) => `<div class="mini-fact"><strong>${fact.label}</strong><span>${fact.value}</span></div>`).join("")
      : `<div class="empty-state">원문을 확인하고 저장하면 이 상황에 표시됩니다.</div>`;
    return `<article class="schedule-card"><strong>${name}</strong><span>${date}</span><div>${body}</div><button data-question="${name}에 대해 확인해야 할 게 뭐야?">자료에 질문</button></article>`;
  }).join("");
}

function renderIssues() {
  const saved = new Set(approvedFacts().map((fact) => fact.id));
  const checks = [
    ["호텔 체크인 핵심 정보", saved.has("checkin") && saved.has("lateArrival"), "체크인 시간과 늦은 도착 조건"],
    ["액티비티 바우처 조건", saved.has("mobileVoucher") && saved.has("meetTime"), "모바일 바우처와 집합 시간"],
    ["집합 장소", saved.has("meetPlace"), "장소명은 확인해도 정확한 입구는 직접 확인"],
    ["렌터카 반납 조건", saved.has("fuelPolicy"), "연료 정책과 보증금 조건"]
  ];

  $("#issueList").innerHTML = checks.map(([title, ok, text], index) => {
    const state = ok ? "good" : index === 2 ? "bad" : "warn";
    return `<div class="issue ${state}"><div><strong>${title}</strong><p>${ok ? `${text}을 근거와 함께 확인했습니다.` : `${text}의 근거 확인이 필요합니다.`}</p></div><span class="pill ${ok ? "good" : "warn"}">${ok ? "저장됨" : "확인 필요"}</span></div>`;
  }).join("");

  $("#issueCount").textContent = `확인 필요 ${checks.filter(([, ok]) => !ok).length}`;
}

function renderAnswer() {
  const query = $("#questionInput").value.trim().toLowerCase();
  let answer = ["업로드된 자료에서 확인하지 못했습니다.", "이 질문에 답할 수 있는 원문 근거를 찾지 못했습니다.", "근거 부족", "현재 자료 목록"];

  if (query.includes("늦") || query.includes("체크인")) {
    answer = ["22:00 이후 도착하면 숙소에 사전 연락이 필요합니다.", "체크인 시작 시간은 15:00이고, late arrival 조건은 호텔 예약 자료에서 확인됩니다.", "원문 근거", "호텔 예약 화면 · 늦은 도착 안내"];
  } else if (query.includes("바우처") || query.includes("투어") || query.includes("모바일")) {
    answer = ["모바일 바우처 제시가 가능합니다.", "출발 15분 전까지 집합 장소에 도착해야 합니다. 장소 좌표는 수동 확인 대상으로 남깁니다.", "원문 근거", "후지산 투어 바우처 · 2쪽 바우처 조건"];
  } else if (query.includes("렌터") || query.includes("기름") || query.includes("연료")) {
    answer = ["반납 시 연료를 가득 채우는 조건입니다.", "렌터카 약관의 연료 정책 표에서 가득 채워 반납 조건이 확인됩니다.", "원문 근거", "렌터카 예약 약관 · 4쪽 연료 정책 표"];
  }

  $("#answerBox").innerHTML = `<h3>${answer[0]}</h3><p>${answer[1]}</p><div class="citation"><span>${answer[2]}</span><code>${answer[3]}</code></div>`;
}

function updateCounters() {
  const count = approvedFacts().length;
  $("#savedCount").textContent = `저장됨 ${count}`;
  $("#exportedFacts").textContent = `${count}개`;
}

function renderAll() {
  renderArtifacts();
  renderDocument();
  renderFacts();
  renderHome();
  renderBoard();
  renderIssues();
  updateCounters();
}

document.body.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  if (button.dataset.view) switchView(button.dataset.view);
  if (button.dataset.openView) switchView(button.dataset.openView);
  if (button.id === "reviewStart") switchView("review");

  if (button.dataset.artifact) {
    selectedArtifact = button.dataset.artifact;
    renderAll();
    switchView("review");
  }

  if (button.dataset.openReview) {
    selectedArtifact = button.dataset.openReview;
    renderAll();
    switchView("review");
  }

  if (button.dataset.question) {
    $("#questionInput").value = button.dataset.question;
    renderAnswer();
    switchView("qa");
  }

  if (button.dataset.action) {
    const fact = facts[button.dataset.fact];
    if (button.dataset.action === "approve") fact.status = "approved";
    if (button.dataset.action === "reject") fact.status = "rejected";
    if (button.dataset.action === "edit") {
      const next = window.prompt("수정할 값을 입력하세요.", fact.value);
      if (next && next.trim()) {
        fact.value = next.trim();
        fact.status = "approved";
      }
    }
    showToast(`${fact.label} 상태를 반영했습니다.`);
    renderAll();
  }
});

$("#saveClearFacts").addEventListener("click", () => {
  byArtifact(selectedArtifact).facts.forEach((id) => {
    if (facts[id].confidence >= 0.78 && !facts[id].sensitive) facts[id].status = "approved";
  });
  showToast("민감 정보와 직접 확인이 필요한 정보는 남겨두고 저장했습니다.");
  renderAll();
});

$("#askButton").addEventListener("click", renderAnswer);

renderAll();
renderAnswer();
