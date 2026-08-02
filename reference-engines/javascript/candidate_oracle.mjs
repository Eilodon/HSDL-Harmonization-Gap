import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const TRUE = "TRUE";
const FALSE = "FALSE";
const UNKNOWN = "UNKNOWN";
const MISSING = Symbol("MISSING");

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      throw new Error(`unexpected argument: ${token}`);
    }
    const key = token.slice(2);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith("--")) {
      throw new Error(`missing value for --${key}`);
    }
    args[key] = value;
    index += 1;
  }
  for (const required of ["hsdl", "corpus", "assumptions", "expected"]) {
    if (!args[required]) {
      throw new Error(`missing required --${required}`);
    }
  }
  return args;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function canonicalise(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalise);
  }
  if (value !== null && typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      result[key] = canonicalise(value[key]);
    }
    return result;
  }
  return value;
}

function contentSha256(value) {
  const encoded = JSON.stringify(canonicalise(value));
  return `sha256:${createHash("sha256").update(encoded, "utf8").digest("hex")}`;
}

function decodeLine(line, keyword, lineNumber) {
  const prefix = `${keyword} `;
  if (!line.startsWith(prefix)) {
    throw new Error(`line ${lineNumber}: expected ${keyword}`);
  }
  return JSON.parse(line.slice(prefix.length));
}

function parseHsdl(document) {
  const lines = document.split(/\r?\n/);
  if (lines.at(-1) === "") {
    lines.pop();
  }
  if (lines[0] !== "@hsdl-core 0.2") {
    throw new Error("candidate document must begin with @hsdl-core 0.2");
  }
  const profile = decodeLine(lines[1], "profile", 2);
  if (profile.claim_class !== "MODEL_RELATIVE" || profile.legal_validation !== "NOT_ASSERTED") {
    throw new Error("profile claim boundary is invalid");
  }
  const rules = [];
  const seenRules = new Set();
  let index = 2;
  while (index < lines.length && lines[index] !== "endprofile") {
    const rule = decodeLine(lines[index], "rule", index + 1);
    if (seenRules.has(rule.rule_id)) {
      throw new Error(`duplicate rule ID: ${rule.rule_id}`);
    }
    seenRules.add(rule.rule_id);
    index += 1;
    const factpaths = decodeLine(lines[index], "factpaths", index + 1);
    index += 1;
    const readiness_condition = decodeLine(lines[index], "readiness", index + 1);
    index += 1;
    const structural_condition = decodeLine(lines[index], "structural", index + 1);
    index += 1;
    const uncompiled_predicate_facts = decodeLine(lines[index], "uncompiled", index + 1);
    index += 1;
    const duties = [];
    const dutyIds = new Set();
    while (index < lines.length && lines[index].startsWith("duty ")) {
      const duty = decodeLine(lines[index], "duty", index + 1);
      if (dutyIds.has(duty.duty_id)) {
        throw new Error(`duplicate duty ID: ${duty.duty_id}`);
      }
      dutyIds.add(duty.duty_id);
      duties.push(duty);
      index += 1;
    }
    if (duties.length === 0 || lines[index] !== "endrule") {
      throw new Error(`rule ${rule.rule_id} is incomplete`);
    }
    index += 1;
    const required = [...rule.required_facts].sort();
    const bound = Object.keys(factpaths).sort();
    if (JSON.stringify(required) !== JSON.stringify(bound)) {
      throw new Error(`rule ${rule.rule_id}: required facts and fact paths differ`);
    }
    rules.push({
      ...rule,
      factpaths,
      readiness_condition,
      structural_condition,
      uncompiled_predicate_facts,
      duties,
    });
  }
  if (lines[index] !== "endprofile" || index !== lines.length - 1) {
    throw new Error("candidate document must end at endprofile");
  }
  if (rules.length !== profile.rule_count) {
    throw new Error("declared rule count differs from parsed rule count");
  }
  return { profile, rules };
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function getPath(context, fieldPath) {
  let current = context;
  for (const part of fieldPath.split(".")) {
    if (current === null || typeof current !== "object" || !(part in current)) {
      return MISSING;
    }
    current = current[part];
  }
  return current;
}

function setPath(context, fieldPath, value) {
  const parts = fieldPath.split(".");
  let current = context;
  for (const part of parts.slice(0, -1)) {
    if (!(part in current)) {
      current[part] = {};
    }
    if (current[part] === null || typeof current[part] !== "object" || Array.isArray(current[part])) {
      throw new Error(`cannot apply assumption through non-object path ${fieldPath}`);
    }
    current = current[part];
  }
  current[parts.at(-1)] = value;
}

function uniqueSorted(values) {
  return [...new Set(values)].sort();
}

function triNot(value) {
  if (value === TRUE) return FALSE;
  if (value === FALSE) return TRUE;
  return UNKNOWN;
}

function triAnd(values) {
  if (values.includes(FALSE)) return FALSE;
  if (values.includes(UNKNOWN)) return UNKNOWN;
  return TRUE;
}

function triOr(values) {
  if (values.includes(TRUE)) return TRUE;
  if (values.includes(UNKNOWN)) return UNKNOWN;
  return FALSE;
}

function operand(node, context) {
  const keys = Object.keys(node);
  if (keys.length === 1 && keys[0] === "field") {
    const actual = getPath(context, node.field);
    if (actual === MISSING) {
      return {
        value: MISSING,
        missing: [node.field],
        detail: { kind: "field", field: node.field },
      };
    }
    return {
      value: actual,
      missing: [],
      detail: { kind: "field", field: node.field, actual },
    };
  }
  if (keys.length === 1 && keys[0] === "literal") {
    return {
      value: node.literal,
      missing: [],
      detail: { kind: "literal", literal: node.literal },
    };
  }
  throw new Error("operand must contain exactly field or literal");
}

function trace(op, value, path, detail = {}, children = [], missingFacts = []) {
  return {
    op,
    value,
    path,
    detail,
    missing_facts: uniqueSorted(missingFacts),
    children,
  };
}

function deepEqual(left, right) {
  return JSON.stringify(canonicalise(left)) === JSON.stringify(canonicalise(right));
}

function evaluateCondition(condition, context, path = "$") {
  const op = condition.op;
  const args = condition.args ?? [];
  if (op === "all") {
    if (args.length !== 0) throw new Error("all expects zero arguments");
    return trace(op, TRUE, path);
  }
  if (op === "and" || op === "or") {
    if (args.length < 1) throw new Error(`${op} expects at least one argument`);
    const children = args.map((item, index) => evaluateCondition(item, context, `${path}.args[${index}]`));
    const value = op === "and" ? triAnd(children.map((item) => item.value)) : triOr(children.map((item) => item.value));
    return trace(op, value, path, {}, children, children.flatMap((item) => item.missing_facts));
  }
  if (op === "not") {
    if (args.length !== 1) throw new Error("not expects one argument");
    const child = evaluateCondition(args[0], context, `${path}.args[0]`);
    return trace(op, triNot(child.value), path, {}, [child], child.missing_facts);
  }
  if (["exists", "missing", "known"].includes(op)) {
    if (args.length !== 1 || Object.keys(args[0]).length !== 1 || !("field" in args[0])) {
      throw new Error(`${op} expects one field operand`);
    }
    const field = args[0].field;
    const actual = getPath(context, field);
    const present = actual !== MISSING;
    let result;
    if (op === "exists") result = present;
    else if (op === "missing") result = !present;
    else result = present && actual !== null;
    return trace(
      op,
      result ? TRUE : FALSE,
      path,
      { field, present, actual: present ? actual : null },
      [],
      op === "known" && !result ? [field] : [],
    );
  }
  if (["eq", "ne", "in", "not_in"].includes(op)) {
    if (args.length !== 2) throw new Error(`${op} expects two arguments`);
    const left = operand(args[0], context);
    const right = operand(args[1], context);
    const missing = uniqueSorted([...left.missing, ...right.missing]);
    const detail = { left: left.detail, right: right.detail };
    if (missing.length > 0) {
      return trace(op, UNKNOWN, path, detail, [], missing);
    }
    let result;
    if (op === "eq") result = deepEqual(left.value, right.value);
    else if (op === "ne") result = !deepEqual(left.value, right.value);
    else {
      if (!Array.isArray(right.value)) throw new Error(`${op} right operand must be an array`);
      const included = right.value.some((item) => deepEqual(item, left.value));
      result = op === "in" ? included : !included;
    }
    return trace(op, result ? TRUE : FALSE, path, detail);
  }
  throw new Error(`unsupported independent-oracle condition op: ${op}`);
}

function missingRequiredFacts(rule, readinessTrace) {
  const paths = new Set(readinessTrace.missing_facts);
  return Object.entries(rule.factpaths)
    .filter(([, path]) => paths.has(path))
    .map(([fact]) => fact)
    .sort();
}

function applicableState(rule) {
  const empty = rule.duties.filter((duty) => duty.obligors.length === 0).length;
  if (empty === rule.duties.length) return "APPLICABLE_UNSPECIFIED_OBLIGOR";
  if (empty > 0) return "APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR";
  return "APPLICABLE_DETERMINATE";
}

function projectDuties(rule, state) {
  let dutyState;
  if (state === "NOT_APPLICABLE") dutyState = "NOT_APPLICABLE";
  else if (state.startsWith("INDETERMINATE_")) dutyState = "APPLICABILITY_UNKNOWN";
  return rule.duties.map((duty) => ({
    duty_id: duty.duty_id,
    normative_slot: duty.normative_slot,
    state: dutyState ?? (duty.obligors.length > 0 ? "APPLICABLE_DETERMINATE" : "APPLICABLE_UNSPECIFIED_OBLIGOR"),
    obligors: duty.obligors,
  }));
}

function evaluateRule(rule, contextRecord, assumption) {
  const facts = deepClone(contextRecord.facts);
  const assumptionsUsed = [];
  for (const fact of Object.keys(assumption.values ?? {}).sort()) {
    if (!(fact in rule.factpaths)) continue;
    setPath(facts, rule.factpaths[fact], assumption.values[fact]);
    assumptionsUsed.push(fact);
  }
  const structuralTrace = evaluateCondition(rule.structural_condition, facts);
  const readinessTrace = evaluateCondition(rule.readiness_condition, facts);
  let missingFacts = missingRequiredFacts(rule, readinessTrace);
  let state;
  if (structuralTrace.value === FALSE) {
    state = "NOT_APPLICABLE";
  } else if (structuralTrace.value === UNKNOWN) {
    state = "INDETERMINATE_MISSING_FACTS";
    missingFacts = uniqueSorted([...missingFacts, ...structuralTrace.missing_facts]);
  } else if (rule.compilation_mode === "UNCONDITIONAL_DECLARED") {
    state = applicableState(rule);
  } else if (readinessTrace.value !== TRUE) {
    state = "INDETERMINATE_MISSING_FACTS";
  } else if (rule.compilation_mode === "REQUIRED_FACTS_READINESS_ONLY") {
    state = "INDETERMINATE_PREDICATE_NOT_COMPILED";
  } else {
    const satisfied = new Set(assumption.satisfied_required_facts ?? []);
    const unresolved = rule.uncompiled_predicate_facts.filter((fact) => !satisfied.has(fact));
    state = unresolved.length > 0 ? "INDETERMINATE_PREDICATE_NOT_COMPILED" : applicableState(rule);
  }
  return {
    state,
    missing_facts: missingFacts,
    assumptions_used: assumptionsUsed,
    duties: projectDuties(rule, state),
    structural_trace: structuralTrace,
    readiness_trace: readinessTrace,
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const { profile, rules } = parseHsdl(readFileSync(args.hsdl, "utf8"));
  const corpus = readJson(args.corpus);
  const assumptionsPayload = readJson(args.assumptions);
  const expected = readJson(args.expected);
  if (!Array.isArray(corpus.contexts) || !Array.isArray(assumptionsPayload.assumption_sets)) {
    throw new Error("corpus and assumptions inputs are malformed");
  }
  const assumptions = new Map(
    assumptionsPayload.assumption_sets.map((item) => [item.id, item]),
  );
  const projections = [];
  const stateCounts = {};
  const byAssumption = {};
  for (const assumptionId of [...assumptions.keys()].sort()) {
    const assumption = assumptions.get(assumptionId);
    for (const rule of rules) {
      for (const context of corpus.contexts) {
        const evaluation = evaluateRule(rule, context, assumption);
        projections.push({
          assumption_set_id: assumptionId,
          rule_id: rule.rule_id,
          context_id: context.context_id,
          evaluation,
        });
        stateCounts[evaluation.state] = (stateCounts[evaluation.state] ?? 0) + 1;
        byAssumption[assumptionId] = (byAssumption[assumptionId] ?? 0) + 1;
      }
    }
  }
  const actualHash = contentSha256(projections);
  const expectedHash = expected.projection_hash;
  const report = {
    schema_version: "1.0.0",
    status: actualHash === expectedHash ? "EQUIVALENT" : "MISMATCH",
    implementation: "INDEPENDENT_JAVASCRIPT_ORACLE_V1",
    runtime: `node-${process.versions.node}`,
    claim_class: "MODEL_RELATIVE",
    legal_validation: "NOT_ASSERTED",
    profile_id: profile.profile_id,
    rule_count: rules.length,
    context_count: corpus.contexts.length,
    assumption_set_count: assumptions.size,
    projection_count: projections.length,
    expected_projection_hash: expectedHash,
    actual_projection_hash: actualHash,
    projection_hash_match: actualHash === expectedHash,
    state_counts: Object.fromEntries(Object.entries(stateCounts).sort()),
    projections_by_assumption_set: Object.fromEntries(Object.entries(byAssumption).sort()),
    implementation_boundary: {
      shared_python_evaluator_code: false,
      shared_hsdl_document: true,
      shared_context_corpus: true,
      shared_assumption_fixture: true,
      upstream_hsdl_compatibility: "NOT_CLAIMED",
      notice: "The JavaScript parser, tri-state condition evaluator and rule evaluator are implemented independently; test fixtures remain shared by design.",
    },
  };
  process.stdout.write(`${JSON.stringify(canonicalise(report), null, 2)}\n`);
  if (!report.projection_hash_match) {
    process.exitCode = 13;
  }
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 14;
}
