import { readFile, readdir } from "node:fs/promises";

const directory = new URL("../n8n/workflows/", import.meta.url);
const files = (await readdir(directory)).filter((name) => name.endsWith(".json")).sort();
const failures = [];

for (const file of files) {
  const workflow = JSON.parse(await readFile(new URL(file, directory), "utf8"));
  const nodes = workflow.nodes ?? [];
  const names = nodes.map((node) => node.name);
  const nameSet = new Set(names);

  if (!workflow.description || workflow.description.trim().length < 60) {
    failures.push(`${file}: workflow description is missing or too short`);
  }
  if (nameSet.size !== names.length) failures.push(`${file}: duplicate node names`);

  for (const [source, outputs] of Object.entries(workflow.connections ?? {})) {
    if (!nameSet.has(source)) failures.push(`${file}: connection source ${source} does not exist`);
    for (const branch of outputs.main ?? []) {
      for (const edge of branch ?? []) {
        if (!nameSet.has(edge.node)) failures.push(`${file}: connection target ${edge.node} does not exist`);
      }
    }
  }

  for (const node of nodes) {
    const outputs = workflow.connections?.[node.name]?.main ?? [];
    if (node.onError === "continueErrorOutput" && !(outputs[1]?.length > 0)) {
      failures.push(`${file}: ${node.name} enables an error output but does not connect it`);
    }
    if (node.type === "n8n-nodes-base.webhook") {
      if (!node.parameters?.authentication || node.parameters.authentication === "none") {
        failures.push(`${file}: ${node.name} webhook is unauthenticated`);
      }
    }
    if (node.type === "n8n-nodes-base.httpRequest") {
      if (String(node.parameters?.url ?? "").includes("$env")) {
        failures.push(`${file}: ${node.name} uses unsupported $env expression access`);
      }
      if (node.parameters?.authentication !== "genericCredentialType" || !node.credentials?.httpHeaderAuth) {
        failures.push(`${file}: ${node.name} does not bind Header Auth credentials`);
      }
      if (!(Number(node.parameters?.options?.timeout) > 0)) {
        failures.push(`${file}: ${node.name} has no explicit timeout`);
      }
      if (node.retryOnFail !== true || !(Number(node.maxTries) >= 2)) {
        failures.push(`${file}: ${node.name} has no bounded retry policy`);
      }
      const headers = node.parameters?.headerParameters?.parameters ?? [];
      if (headers.some((header) => String(header.name).toLowerCase() === "authorization")) {
        failures.push(`${file}: ${node.name} hard-codes Authorization outside the credential system`);
      }
    }
    if (
      node.type === "n8n-nodes-base.respondToWebhook" &&
      String(node.parameters?.responseBody ?? "").includes("JSON.stringify")
    ) {
      failures.push(`${file}: ${node.name} double-encodes its JSON response`);
    }
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Validated ${files.length} n8n workflows: JSON, graph, auth, timeouts, retries, and error outputs.`);
