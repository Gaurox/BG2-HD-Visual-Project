/**
 * Generate the disposable human-facing BG2EE HD tracking workbook.
 *
 * Sources are generated projections of canonical authorities. This script never
 * writes domain catalogues, QA approvals, release manifests, payloads, or site files.
 */

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import os from "node:os";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";
import JSZip from "jszip";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_ROOT = path.resolve(path.dirname(SCRIPT_PATH), "../..");
const GENERATOR = "pipeline/scripts/generate_human_tracking_xlsx.mjs";
const METRICS_SCHEMA = "bg2-upscale-human-progress-v1";
const OUTPUT_RELATIVE = "outputs/bg2ee-hd-human-tracking/BG2EE-HD-suivi-global.xlsx";
const METRICS_RELATIVE = "asset-tracking/dashboard-metrics.json";
const DATA_HEADER_ROW = 4;
const DATA_FIRST_ROW = DATA_HEADER_ROW + 1;

const DOMAIN_CONFIG = [
  { domain: "maps", label: "Maps", sheet: "Maps", table: "MapsAssets" },
  { domain: "animations", label: "Animations", sheet: "Animations", table: "AnimationsAssets" },
  { domain: "sprites", label: "Sprites", sheet: "Sprites", table: "SpritesAssets" },
  { domain: "ui", label: "UI / HUD / polices", sheet: "UI-HUD-Polices", table: "UiAssets" },
  { domain: "portraits", label: "Portraits", sheet: "Portraits", table: "PortraitsAssets" },
  { domain: "videos", label: "Vidéos", sheet: "Videos", table: "VideosAssets" },
  { domain: "icons", label: "Icônes", sheet: "Icones", table: "IconsAssets" },
  { domain: "effects", label: "Effets", sheet: "Effets", table: "EffectsAssets" },
  { domain: "projectiles", label: "Projectiles", sheet: "Projectiles", table: "ProjectilesAssets" },
  { domain: "cursors", label: "Curseurs", sheet: "Curseurs", table: "CursorsAssets" },
];

const HEADERS = [
  "Identifiant",
  "Type",
  "Source",
  "Production",
  "QA",
  "Installation",
  "Release",
  "Provenance",
  "Sélection retenue",
  "Source canonique",
  "Localisateur",
  "Preuves",
  "Note / statut historique",
];

const INDICATORS = {
  produced: {
    axis: "production",
    includedStates: ["produced", "verified"],
    denominatorExcludes: ["not-applicable"],
    description: "Assets dont la production est produite ou vérifiée.",
  },
  qaPassed: {
    axis: "qa",
    includedStates: ["passed"],
    denominatorExcludes: ["not-applicable"],
    description: "Assets avec décision QA explicitement passée.",
  },
  releaseEligibleOrBeyond: {
    axis: "release",
    includedStates: ["eligible", "approved", "integrated", "published"],
    denominatorExcludes: ["not-applicable"],
    description: "Assets éligibles, approuvés, intégrés ou publiés.",
  },
};

function parseArgs(argv) {
  const args = {
    root: DEFAULT_ROOT,
    output: null,
    metricsOutput: null,
    renderDir: null,
    verifyDeterminism: false,
    check: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--root") args.root = path.resolve(argv[++index]);
    else if (arg === "--output") args.output = path.resolve(argv[++index]);
    else if (arg === "--metrics-output") args.metricsOutput = path.resolve(argv[++index]);
    else if (arg === "--render-dir") args.renderDir = path.resolve(argv[++index]);
    else if (arg === "--verify-determinism") args.verifyDeterminism = true;
    else if (arg === "--check") args.check = true;
    else if (arg === "--help") {
      console.log(
        [
          "Usage: node pipeline/scripts/generate_human_tracking_xlsx.mjs [options]",
          "  --root PATH                 Workspace root",
          "  --output PATH               XLSX output",
          "  --metrics-output PATH       Structured dashboard metrics JSON",
          "  --render-dir PATH           Render every sheet to PNG for visual QA",
          "  --verify-determinism        Build twice and compare XLSX bytes",
          "  --check                     Verify existing outputs without rewriting",
        ].join("\n"),
      );
      process.exit(0);
    } else throw new Error(`Unknown argument: ${arg}`);
  }
  args.output ??= path.join(args.root, OUTPUT_RELATIVE);
  args.metricsOutput ??= path.join(args.root, METRICS_RELATIVE);
  return args;
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex").toUpperCase();
}

function sortedJson(value) {
  const normalize = (item) => {
    if (Array.isArray(item)) return item.map(normalize);
    if (item && typeof item === "object") {
      return Object.fromEntries(
        Object.keys(item)
          .sort()
          .map((key) => [key, normalize(item[key])]),
      );
    }
    return item;
  };
  return `${JSON.stringify(normalize(value), null, 2)}\n`;
}

function countStates(records, axis, includedStates) {
  const included = new Set(includedStates);
  return records.filter((record) => included.has(record.states[axis])).length;
}

function applicableCount(records, axis) {
  return records.filter((record) => record.states[axis] !== "not-applicable").length;
}

function percent(numerator, denominator) {
  return denominator === 0 ? null : numerator / denominator;
}

function progressRow(config, records, coverageDomain) {
  const productionApplicable = applicableCount(records, "production");
  const produced = countStates(records, "production", INDICATORS.produced.includedStates);
  const qaApplicable = applicableCount(records, "qa");
  const qaPassed = countStates(records, "qa", INDICATORS.qaPassed.includedStates);
  const releaseApplicable = applicableCount(records, "release");
  const releaseEligibleOrBeyond = countStates(
    records,
    "release",
    INDICATORS.releaseEligibleOrBeyond.includedStates,
  );
  return {
    domain: config.domain,
    label: config.label,
    sheet: config.sheet,
    knownAssets: records.length,
    productionApplicable,
    produced,
    producedPercent: percent(produced, productionApplicable),
    qaApplicable,
    qaPassed,
    qaPassedPercent: percent(qaPassed, qaApplicable),
    releaseApplicable,
    releaseEligibleOrBeyond,
    releaseEligiblePercent: percent(releaseEligibleOrBeyond, releaseApplicable),
    coverageStatus: coverageDomain.coverage_status,
    authority: coverageDomain.authority,
    note: coverageDomain.note,
  };
}

function aggregateProgress(rows) {
  const total = rows.reduce(
    (accumulator, row) => {
      for (const field of [
        "knownAssets",
        "productionApplicable",
        "produced",
        "qaApplicable",
        "qaPassed",
        "releaseApplicable",
        "releaseEligibleOrBeyond",
      ]) accumulator[field] += row[field];
      return accumulator;
    },
    {
      knownAssets: 0,
      productionApplicable: 0,
      produced: 0,
      qaApplicable: 0,
      qaPassed: 0,
      releaseApplicable: 0,
      releaseEligibleOrBeyond: 0,
    },
  );
  return {
    ...total,
    producedPercent: percent(total.produced, total.productionApplicable),
    qaPassedPercent: percent(total.qaPassed, total.qaApplicable),
    releaseEligiblePercent: percent(total.releaseEligibleOrBeyond, total.releaseApplicable),
  };
}

function selectionsText(record) {
  return (record.selections ?? []).map((selection) => `${selection.role}: ${selection.id}`).join(" | ");
}

function legacyText(record) {
  return (record.legacy ?? []).map((entry) => `${entry.field}=${entry.value}`).join(" | ");
}

function assetRow(record) {
  return [
    record.asset_id,
    record.asset_type,
    record.states.source,
    record.states.production,
    record.states.qa,
    record.states.installation,
    record.states.release,
    record.provenance.state,
    selectionsText(record),
    record.canonical_source.path,
    record.canonical_source.locator,
    record.provenance.evidence.length,
    legacyText(record),
  ];
}

async function loadModel(root) {
  const [registry, coverage, anomalies, contract] = await Promise.all([
    readJson(path.join(root, "asset-tracking/registry.json")),
    readJson(path.join(root, "asset-tracking/coverage.json")),
    readJson(path.join(root, "asset-tracking/anomalies.json")),
    readJson(path.join(root, "docs/asset-tracking-record.schema.json")),
  ]);

  for (const projection of [coverage, anomalies]) {
    if (projection.asset_records_sha256 !== registry.asset_records_sha256) {
      throw new Error("Registry, coverage and anomalies do not describe the same asset records.");
    }
    if (projection.source_fingerprint_sha256 !== registry.source_fingerprint_sha256) {
      throw new Error("Registry, coverage and anomalies do not share the same source fingerprint.");
    }
  }
  if (registry.asset_count !== registry.assets.length) {
    throw new Error(`Registry cardinality mismatch: ${registry.asset_count} != ${registry.assets.length}.`);
  }
  const ids = registry.assets.map((record) => record.asset_id);
  if (new Set(ids).size !== ids.length) throw new Error("Duplicate asset_id in registry projection.");

  const allowedDomains = new Set(contract.properties.domain.enum);
  const allowedStates = Object.fromEntries(
    Object.entries(contract.properties.states.properties).map(([axis, schema]) => [axis, new Set(schema.enum)]),
  );
  const allowedProvenance = new Set(contract.properties.provenance.properties.state.enum);
  for (const record of registry.assets) {
    if (!allowedDomains.has(record.domain)) throw new Error(`Unknown domain in registry: ${record.domain}`);
    for (const [axis, states] of Object.entries(allowedStates)) {
      if (!states.has(record.states[axis])) {
        throw new Error(`Invalid ${axis} state for ${record.asset_id}: ${record.states[axis]}`);
      }
    }
    if (!allowedProvenance.has(record.provenance.state)) {
      throw new Error(`Invalid provenance state for ${record.asset_id}: ${record.provenance.state}`);
    }
  }

  const configuredDomains = new Set(DOMAIN_CONFIG.map((item) => item.domain));
  const projectedDomains = new Set(registry.assets.map((record) => record.domain));
  const unconfigured = [...projectedDomains].filter((domain) => !configuredDomains.has(domain));
  if (unconfigured.length) throw new Error(`Unconfigured workbook domains: ${unconfigured.join(", ")}`);

  const coverageByDomain = new Map(coverage.domains.map((domain) => [domain.domain, domain]));
  const recordsByDomain = new Map();
  for (const config of DOMAIN_CONFIG) {
    const records = registry.assets
      .filter((record) => record.domain === config.domain)
      .sort((left, right) => left.asset_id.localeCompare(right.asset_id, "en"));
    const coverageDomain = coverageByDomain.get(config.domain);
    if (!coverageDomain) throw new Error(`Missing coverage row for domain ${config.domain}.`);
    if (coverageDomain.asset_count !== records.length) {
      throw new Error(`Coverage cardinality mismatch for ${config.domain}.`);
    }
    recordsByDomain.set(config.domain, records);
  }

  const domains = DOMAIN_CONFIG.map((config) =>
    progressRow(config, recordsByDomain.get(config.domain), coverageByDomain.get(config.domain)),
  );
  const global = aggregateProgress(domains);
  if (global.knownAssets !== registry.asset_count) throw new Error("Workbook domain total differs from registry.");
  if (global.produced !== coverage.metrics.produced) throw new Error("Produced metric differs from coverage.json.");
  if (global.qaPassed !== coverage.metrics.qa_passed) throw new Error("QA metric differs from coverage.json.");
  if (global.releaseEligibleOrBeyond !== coverage.metrics.release_eligible_or_beyond) {
    throw new Error("Release metric differs from coverage.json.");
  }

  const metrics = {
    schema: METRICS_SCHEMA,
    generated_by: GENERATOR,
    sources: {
      registry: "asset-tracking/registry.json",
      coverage: "asset-tracking/coverage.json",
      anomalies: "asset-tracking/anomalies.json",
      contract: "docs/asset-tracking-record.schema.json",
      canonical_input_count: registry.inputs.length,
    },
    source_snapshot_at_utc: registry.source_snapshot_at_utc,
    source_fingerprint_sha256: registry.source_fingerprint_sha256,
    asset_records_sha256: registry.asset_records_sha256,
    definitions: {
      known_assets: {
        description: "Enregistrements du registre global, sans estimation des périmètres non inventoriés.",
      },
      production_applicable: { axis: "production", excluded_states: ["not-applicable"] },
      produced: {
        ...INDICATORS.produced,
        percent: "produced / production_applicable; null si aucun asset applicable",
      },
      qa_applicable: { axis: "qa", excluded_states: ["not-applicable"] },
      qa_passed: {
        ...INDICATORS.qaPassed,
        percent: "qa_passed / qa_applicable; null si aucun asset applicable",
      },
      release_applicable: { axis: "release", excluded_states: ["not-applicable"] },
      release_eligible_or_beyond: {
        ...INDICATORS.releaseEligibleOrBeyond,
        percent: "release_eligible_or_beyond / release_applicable; null si aucun asset applicable",
      },
    },
    global,
    domains,
    coverage_gaps: coverage.uninventoried_scopes,
    anomaly_summary: anomalies.summary,
  };
  return { registry, coverage, anomalies, recordsByDomain, metrics };
}

function applyTitleStyle(range) {
  range.format = {
    fill: "#17324D",
    font: { name: "Aptos Display", size: 20, bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
  };
  range.format.rowHeight = 34;
}

function applySectionStyle(range) {
  range.format = {
    fill: "#DCE8F1",
    font: { name: "Aptos", size: 11, bold: true, color: "#17324D" },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: "#AFC3D4" },
  };
  range.format.rowHeight = 24;
}

function dashboardFormulaRange(config, records, columnLetter) {
  const lastRow = DATA_FIRST_ROW + records.length - 1;
  return `'${config.sheet}'!$${columnLetter}$${DATA_FIRST_ROW}:$${columnLetter}$${lastRow}`;
}

function addDashboard(workbook, model) {
  const sheet = workbook.worksheets.getItem("Dashboard");
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(8);

  sheet.getRange("A1:K1").merge();
  sheet.getRange("A1").values = [["BG2EE HD — suivi global des assets"]];
  applyTitleStyle(sheet.getRange("A1:K1"));
  sheet.getRange("A2:K2").merge();
  sheet.getRange("A2").values = [[
    `Projection jetable du registre — snapshot ${model.registry.source_snapshot_at_utc} — ${model.registry.asset_count.toLocaleString("fr-FR")} assets`,
  ]];
  sheet.getRange("A2:K2").format = {
    fill: "#EAF1F6",
    font: { name: "Aptos", size: 10, color: "#40586D" },
    verticalAlignment: "center",
  };
  sheet.getRange("A2:K2").format.rowHeight = 24;

  const cards = [
    { range: "A4:B4", value: "Assets connus", formulaRange: "A5:B5", formula: "=B19" },
    { range: "D4:E4", value: "Produits", formulaRange: "D5:E5", formula: "=D19" },
    { range: "G4:H4", value: "QA validés", formulaRange: "G5:H5", formula: "=G19" },
    { range: "J4:K4", value: "Release éligible+", formulaRange: "J5:K5", formula: "=J19" },
  ];
  for (const card of cards) {
    sheet.getRange(card.range).merge();
    sheet.getRange(card.range.split(":")[0]).values = [[card.value]];
    sheet.getRange(card.range).format = {
      fill: "#2F6F78",
      font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
      horizontalAlignment: "center",
      verticalAlignment: "center",
    };
    sheet.getRange(card.formulaRange).merge();
    sheet.getRange(card.formulaRange.split(":")[0]).formulas = [[card.formula]];
    sheet.getRange(card.formulaRange).format = {
      fill: "#F3F7FA",
      font: { name: "Aptos Display", size: 20, bold: true, color: "#17324D" },
      horizontalAlignment: "center",
      verticalAlignment: "center",
      borders: { preset: "outside", style: "thin", color: "#AFC3D4" },
      numberFormat: "#,##0",
    };
    sheet.getRange(card.formulaRange).format.rowHeight = 34;
  }

  sheet.getRange("A7:K7").merge();
  sheet.getRange("A7").values = [["Avancement par domaine"]];
  applySectionStyle(sheet.getRange("A7:K7"));
  sheet.getRange("A8:K8").values = [[
    "Domaine", "Assets connus", "Prod. applicables", "Produits", "% produits",
    "QA applicables", "QA validés", "% QA", "Release applicables", "Éligibles+", "% release",
  ]];
  sheet.getRange("A8:K8").format = {
    fill: "#17324D",
    font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange("A8:K8").format.rowHeight = 34;

  for (let index = 0; index < DOMAIN_CONFIG.length; index += 1) {
    const config = DOMAIN_CONFIG[index];
    const records = model.recordsByDomain.get(config.domain);
    const row = 9 + index;
    const idRange = dashboardFormulaRange(config, records, "A");
    const productionRange = dashboardFormulaRange(config, records, "D");
    const qaRange = dashboardFormulaRange(config, records, "E");
    const releaseRange = dashboardFormulaRange(config, records, "G");
    sheet.getRange(`A${row}`).values = [[config.label]];
    sheet.getRange(`B${row}:K${row}`).formulas = [[
      `=COUNTA(${idRange})`,
      `=COUNTIF(${productionRange},"<>not-applicable")`,
      `=COUNTIF(${productionRange},"produced")+COUNTIF(${productionRange},"verified")`,
      `=IF(C${row}=0,"N/A",D${row}/C${row})`,
      `=COUNTIF(${qaRange},"<>not-applicable")`,
      `=COUNTIF(${qaRange},"passed")`,
      `=IF(F${row}=0,"N/A",G${row}/F${row})`,
      `=COUNTIF(${releaseRange},"<>not-applicable")`,
      `=COUNTIF(${releaseRange},"eligible")+COUNTIF(${releaseRange},"approved")+COUNTIF(${releaseRange},"integrated")+COUNTIF(${releaseRange},"published")`,
      `=IF(I${row}=0,"N/A",J${row}/I${row})`,
    ]];
  }

  sheet.getRange("A19").values = [["TOTAL PROJET"]];
  sheet.getRange("B19:D19").formulas = [["=SUM(B9:B18)", "=SUM(C9:C18)", "=SUM(D9:D18)"]];
  sheet.getRange("E19").formulas = [["=IF(C19=0,\"N/A\",D19/C19)"]];
  sheet.getRange("F19:G19").formulas = [["=SUM(F9:F18)", "=SUM(G9:G18)"]];
  sheet.getRange("H19").formulas = [["=IF(F19=0,\"N/A\",G19/F19)"]];
  sheet.getRange("I19:J19").formulas = [["=SUM(I9:I18)", "=SUM(J9:J18)"]];
  sheet.getRange("K19").formulas = [["=IF(I19=0,\"N/A\",J19/I19)"]];
  sheet.getRange("A9:K18").format = {
    font: { name: "Aptos", size: 10, color: "#263746" },
    borders: { insideHorizontal: { style: "thin", color: "#D9E2E8" } },
    verticalAlignment: "center",
  };
  sheet.getRange("A19:K19").format = {
    fill: "#DCE8F1",
    font: { name: "Aptos", size: 10, bold: true, color: "#17324D" },
    borders: { preset: "doubleBottom", style: "medium", color: "#68869B" },
  };
  for (const range of ["B9:D19", "F9:G19", "I9:J19"]) sheet.getRange(range).format.numberFormat = "#,##0";
  for (const range of ["E9:E19", "H9:H19", "K9:K19"]) {
    sheet.getRange(range).format.numberFormat = "0.0%";
    sheet.getRange(range).conditionalFormats.add("dataBar", {
      color: "#4F9DA6", thresholds: [0, 1], gradient: true,
    });
  }

  sheet.getRange("A22:K22").merge();
  sheet.getRange("A22").values = [["Définitions des indicateurs"]];
  applySectionStyle(sheet.getRange("A22:K22"));
  const definitionRows = [
    ["Produits", "production ∈ {produced, verified}; ready et in-progress ne comptent pas comme produits."],
    ["QA validés", "qa = passed uniquement; pending, failed et blocked restent distincts et ne sont pas des succès."],
    ["Release éligible+", "release ∈ {eligible, approved, integrated, published}; ineligible n'est pas un succès."],
    ["Pourcentages", "numérateur / assets applicables à l'axe; not-applicable est exclu; aucun applicable = N/A."],
  ];
  for (let index = 0; index < definitionRows.length; index += 1) {
    const row = 23 + index;
    sheet.getRange(`A${row}:B${row}`).merge();
    sheet.getRange(`A${row}`).values = [[definitionRows[index][0]]];
    sheet.getRange(`C${row}:K${row}`).merge();
    sheet.getRange(`C${row}`).values = [[definitionRows[index][1]]];
  }
  sheet.getRange("A23:K26").format = {
    font: { name: "Aptos", size: 10, color: "#40586D" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { insideHorizontal: { style: "thin", color: "#E2E8ED" } },
  };
  sheet.getRange("A23:B26").format.font = { name: "Aptos", size: 10, bold: true, color: "#17324D" };
  sheet.getRange("A23:K26").format.rowHeight = 27;

  sheet.getRange("A29:K29").merge();
  sheet.getRange("A29").values = [["Traçabilité et couverture"]];
  applySectionStyle(sheet.getRange("A29:K29"));
  const gaps = model.coverage.uninventoried_scopes;
  sheet.getRange("A30:C33").values = [
    ["Registre", "asset-tracking/registry.json", model.registry.asset_records_sha256],
    ["Empreinte sources", `${model.registry.inputs.length} entrées déclarées`, model.registry.source_fingerprint_sha256],
    ["Anomalies", `${model.anomalies.summary.total} signalement(s), ${model.anomalies.summary.by_severity.error ?? 0} erreur(s)`, "asset-tracking/anomalies.json"],
    ["Périmètres non inventoriés", gaps.length, gaps.length ? gaps.map((gap) => `${gap.scope}: ${gap.reason}`).join(" | ") : "Aucun"],
  ];
  for (const row of [30, 31, 32, 33]) sheet.getRange(`C${row}:K${row}`).merge();
  sheet.getRange("A30:K33").format = {
    font: { name: "Aptos", size: 9, color: "#40586D" },
    verticalAlignment: "top",
    wrapText: true,
  };
  sheet.getRange("A30:A33").format.font = { name: "Aptos", size: 10, bold: true, color: "#17324D" };
  sheet.getRange("A30:K33").format.rowHeight = 32;

  sheet.getRange("A:A").format.columnWidth = 23;
  for (const column of ["B", "C", "D", "F", "G", "I", "J"]) sheet.getRange(`${column}:${column}`).format.columnWidth = 14;
  for (const column of ["E", "H", "K"]) sheet.getRange(`${column}:${column}`).format.columnWidth = 13;
  return sheet;
}

function addStateConditionalFormatting(range) {
  for (const text of ["verified", "passed", "eligible", "approved", "integrated", "published", "installed", "complete"]) {
    range.conditionalFormats.add("containsText", {
      text, format: { fill: "#DDEFE3", font: { color: "#1E5934" } },
    });
  }
  for (const text of ["available", "extracted", "ready", "in-progress", "produced", "pending", "staged", "partial"]) {
    range.conditionalFormats.add("containsText", {
      text, format: { fill: "#FFF1CC", font: { color: "#725413" } },
    });
  }
  for (const text of ["unavailable", "rejected", "blocked", "failed", "drifted"]) {
    range.conditionalFormats.add("containsText", {
      text, format: { fill: "#F9DDDA", font: { color: "#8C2C25" } },
    });
  }
}

function addDomainSheet(workbook, config, records, registry) {
  const sheet = workbook.worksheets.getItem(config.sheet);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(DATA_HEADER_ROW);
  sheet.freezePanes.freezeColumns(2);
  sheet.getRange("A1:M1").merge();
  sheet.getRange("A1").values = [[`${config.label} — suivi par asset`]];
  applyTitleStyle(sheet.getRange("A1:M1"));
  sheet.getRange("A2:M2").merge();
  sheet.getRange("A2").values = [[
    `${records.length.toLocaleString("fr-FR")} assets — projection ${registry.asset_records_sha256.slice(0, 12)} — états canoniques non réinterprétés`,
  ]];
  sheet.getRange("A2:M2").format = {
    fill: "#EAF1F6", font: { name: "Aptos", size: 9, color: "#40586D" }, verticalAlignment: "center",
  };
  sheet.getRange("A2:M2").format.rowHeight = 22;

  const lastRow = DATA_HEADER_ROW + records.length;
  sheet.getRange(`A${DATA_HEADER_ROW}:M${lastRow}`).values = [HEADERS, ...records.map(assetRow)];
  const table = sheet.tables.add(`A${DATA_HEADER_ROW}:M${lastRow}`, true, config.table);
  table.style = "TableStyleMedium2";
  table.showBandedRows = true;
  table.showFilterButton = true;
  sheet.getRange(`A${DATA_FIRST_ROW}:M${lastRow}`).format = {
    font: { name: "Aptos", size: 9, color: "#263746" }, verticalAlignment: "top",
  };
  sheet.getRange(`C${DATA_FIRST_ROW}:H${lastRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`L${DATA_FIRST_ROW}:L${lastRow}`).format.numberFormat = "#,##0";
  addStateConditionalFormatting(sheet.getRange(`C${DATA_FIRST_ROW}:H${lastRow}`));

  const widths = [34, 24, 16, 18, 16, 18, 18, 16, 38, 42, 38, 10, 42];
  for (let index = 0; index < widths.length; index += 1) {
    sheet.getRangeByIndexes(0, index, lastRow, 1).format.columnWidth = widths[index];
  }
  sheet.getRange(`I${DATA_FIRST_ROW}:K${lastRow}`).format.wrapText = true;
  sheet.getRange(`M${DATA_FIRST_ROW}:M${lastRow}`).format.wrapText = true;
  return sheet;
}

function buildWorkbook(model) {
  const workbook = Workbook.create();
  workbook.worksheets.add("Dashboard");
  for (const config of DOMAIN_CONFIG) workbook.worksheets.add(config.sheet);
  addDashboard(workbook, model);
  for (const config of DOMAIN_CONFIG) {
    addDomainSheet(workbook, config, model.recordsByDomain.get(config.domain), model.registry);
  }
  return workbook;
}

async function workbookBytes(workbook) {
  const blob = await SpreadsheetFile.exportXlsx(workbook);
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "bg2ee-hd-tracking-"));
  const tempFile = path.join(tempDir, "workbook.xlsx");
  try {
    await blob.save(tempFile);
    return canonicalizeXlsx(new Uint8Array(await fs.readFile(tempFile)));
  } finally {
    await fs.unlink(tempFile).catch(() => {});
    await fs.rmdir(tempDir).catch(() => {});
  }
}

function relationshipSourcePath(relationshipPath) {
  if (relationshipPath === "_rels/.rels") return null;
  const match = relationshipPath.match(/^(.*)\/_rels\/([^/]+)[.]rels$/);
  return match ? `${match[1]}/${match[2]}` : null;
}

async function canonicalizeXlsx(bytes) {
  const input = await JSZip.loadAsync(bytes);
  const replacements = new Map();
  const relationshipPaths = Object.keys(input.files)
    .filter((name) => name.endsWith(".rels") && !input.files[name].dir)
    .sort();
  for (const relationshipPath of relationshipPaths) {
    const xml = await input.file(relationshipPath).async("string");
    const tags = xml.match(/<Relationship\b[^>]*\/>/g) ?? [];
    const relationships = tags
      .map((tag) => ({
        tag,
        id: tag.match(/\bId="([^"]+)"/)?.[1],
        target: tag.match(/\bTarget="([^"]+)"/)?.[1] ?? "",
        type: tag.match(/\bType="([^"]+)"/)?.[1] ?? "",
      }))
      .filter((relationship) => relationship.id)
      .sort((left, right) => `${left.target}|${left.type}`.localeCompare(`${right.target}|${right.type}`, "en"));
    let normalized = xml;
    const idMap = new Map();
    for (let index = 0; index < relationships.length; index += 1) {
      const relationship = relationships[index];
      const canonicalId = `rId${index + 1}`;
      idMap.set(relationship.id, canonicalId);
      normalized = normalized.replace(
        relationship.tag,
        relationship.tag.replace(`Id="${relationship.id}"`, `Id="${canonicalId}"`),
      );
    }
    replacements.set(relationshipPath, normalized);
    const sourcePath = relationshipSourcePath(relationshipPath);
    if (sourcePath && input.file(sourcePath)) {
      let sourceXml = await input.file(sourcePath).async("string");
      for (const [oldId, canonicalId] of idMap) {
        sourceXml = sourceXml.replaceAll(`="${oldId}"`, `="${canonicalId}"`);
      }
      replacements.set(sourcePath, sourceXml);
    }
  }

  const output = new JSZip();
  const fixedDate = new Date("1980-01-01T00:00:00.000Z");
  const fileNames = Object.keys(input.files).filter((name) => !input.files[name].dir).sort();
  for (const name of fileNames) {
    const content = replacements.has(name)
      ? new TextEncoder().encode(replacements.get(name))
      : await input.file(name).async("uint8array");
    output.file(name, content, { binary: true, createFolders: false, date: fixedDate });
  }
  return output.generateAsync({
    type: "uint8array",
    compression: "DEFLATE",
    compressionOptions: { level: 9 },
    platform: "DOS",
    streamFiles: false,
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

async function verifyWorkbook(workbook, model) {
  const dashboard = await workbook.inspect({
    kind: "table", range: "Dashboard!A1:K33", include: "values,formulas",
    tableMaxRows: 33, tableMaxCols: 11, maxChars: 12000,
  });
  const errorScan = await workbook.inspect({
    kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan", maxChars: 4000,
  });
  const dashboardText = dashboard.ndjson ?? "";
  const errorText = errorScan.ndjson ?? "";
  for (const expected of [
    model.metrics.global.knownAssets,
    model.metrics.global.produced,
    model.metrics.global.qaPassed,
    model.metrics.global.releaseEligibleOrBeyond,
  ]) {
    if (!dashboardText.includes(String(expected))) {
      throw new Error(`Dashboard inspection does not contain expected metric ${expected}.`);
    }
  }
  if (/"match"\s*:\s*"#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A)"/i.test(errorText)) {
    throw new Error(`Formula error detected: ${errorText}`);
  }
  console.log(dashboardText.slice(0, 6000));
  console.log(errorText.slice(0, 2000));
}

async function renderAllSheets(workbook, renderDir) {
  await fs.mkdir(renderDir, { recursive: true });
  for (const name of ["Dashboard", ...DOMAIN_CONFIG.map((config) => config.sheet)]) {
    const preview = await workbook.render({
      sheetName: name,
      range: name === "Dashboard" ? "A1:K33" : "A1:M30",
      scale: name === "Dashboard" ? 1.2 : 0.8,
      format: "png",
    });
    const safeName = name.replace(/[^A-Za-z0-9-]+/g, "-");
    await fs.writeFile(path.join(renderDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

async function checkExisting(args, model) {
  if ((await fs.readFile(args.metricsOutput, "utf8")) !== sortedJson(model.metrics)) {
    throw new Error("dashboard-metrics.json is stale.");
  }
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(args.output));
  for (const sheetName of ["Dashboard", ...DOMAIN_CONFIG.map((config) => config.sheet)]) {
    workbook.worksheets.getItem(sheetName);
  }
  for (const config of DOMAIN_CONFIG) {
    const records = model.recordsByDomain.get(config.domain);
    const values = workbook.worksheets
      .getItem(config.sheet)
      .getRangeByIndexes(DATA_FIRST_ROW - 1, 0, records.length, 1).values;
    const actual = values.map((row) => row[0]);
    const expected = records.map((record) => record.asset_id);
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      throw new Error(`Workbook asset rows differ from registry for ${config.domain}.`);
    }
  }
  await verifyWorkbook(workbook, model);
  console.log(`OK ${path.relative(args.root, args.output)} matches ${model.registry.asset_records_sha256}.`);
}

async function generate(args, model) {
  const workbook = buildWorkbook(model);
  await verifyWorkbook(workbook, model);
  if (args.renderDir) await renderAllSheets(workbook, args.renderDir);
  const bytes = await workbookBytes(workbook);
  if (args.verifyDeterminism) {
    const secondBytes = await workbookBytes(buildWorkbook(model));
    if (sha256(bytes) !== sha256(secondBytes)) throw new Error("XLSX byte output is not deterministic.");
  }
  await fs.mkdir(path.dirname(args.output), { recursive: true });
  await fs.mkdir(path.dirname(args.metricsOutput), { recursive: true });
  await fs.writeFile(args.output, bytes);
  await fs.writeFile(args.metricsOutput, sortedJson(model.metrics), "utf8");
  console.log(`WROTE ${path.relative(args.root, args.output)} ${bytes.length} bytes SHA256=${sha256(bytes)}`);
  console.log(`WROTE ${path.relative(args.root, args.metricsOutput)} from ${model.registry.asset_records_sha256}`);
}

const args = parseArgs(process.argv.slice(2));
const model = await loadModel(args.root);
if (args.check) await checkExisting(args, model);
else await generate(args, model);
