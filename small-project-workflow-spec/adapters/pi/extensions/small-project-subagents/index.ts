import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { ALLOWED_ROLES, type AllowedRole, discoverProjectAgents, isAllowedRole } from "./agents.ts";

const PROJECT_AGENT_SCOPE = "project" as const;

const RoleSchema = Type.Union([
	Type.Literal("decision"),
	Type.Literal("implementer"),
	Type.Literal("reviewer"),
	Type.Literal("test-planner"),
	Type.Literal("test-runner"),
	Type.Literal("reporter"),
]);

const SmallProjectSubagentParams = Type.Object({
	role: RoleSchema,
	task: Type.String({ description: "One bounded task packet for the selected role." }),
});

interface PiInvocation {
	command: string;
	args: string[];
}

interface PiRun {
	exitCode: number | null;
	stdout: string;
	stderr: string;
	aborted: boolean;
	spawnError?: string;
}

function resolvePiInvocation(args: string[]): PiInvocation {
	const entrypoint = process.argv[1];
	if (entrypoint && !entrypoint.includes("$bunfs") && existsSync(entrypoint)) {
		return { command: process.execPath, args: [entrypoint, ...args] };
	}

	const runtimeName = path.basename(process.execPath).toLowerCase();
	if (!/^(node|bun)(\.exe)?$/.test(runtimeName)) return { command: process.execPath, args };

	return { command: "pi", args };
}

function splitModelSelector(selector: string): { provider: string; id: string } | null {
	const slash = selector.indexOf("/");
	if (slash <= 0 || slash === selector.length - 1) return null;
	const provider = selector.slice(0, slash).trim();
	const id = selector.slice(slash + 1).trim();
	return provider && id ? { provider, id } : null;
}

function assistantResultFromJson(stdout: string): { text: string; stopReason?: string; errorMessage?: string } {
	let lastAssistantText = "";
	let stopReason: string | undefined;
	let errorMessage: string | undefined;
	for (const line of stdout.split(/\r?\n/)) {
		if (!line.trim()) continue;
		try {
			const event = JSON.parse(line) as {
				message?: { role?: string; content?: unknown; stopReason?: string; errorMessage?: string };
			};
			if (event.message?.role !== "assistant") continue;
			stopReason = event.message.stopReason ?? stopReason;
			errorMessage = event.message.errorMessage ?? errorMessage;
			const content = event.message.content;
			if (typeof content === "string") {
				lastAssistantText = content;
				continue;
			}
			if (Array.isArray(content)) {
				lastAssistantText = content
					.filter((part): part is { type?: string; text?: string } => typeof part === "object" && part !== null)
					.filter((part) => part.type === "text" && typeof part.text === "string")
					.map((part) => part.text!)
					.join("");
			}
		} catch {
			// JSON mode can emit non-protocol diagnostics; only message events are relevant.
		}
	}
	return { text: lastAssistantText.trim(), stopReason, errorMessage };
}

async function runPi(args: string[], cwd: string, signal: AbortSignal | undefined): Promise<PiRun> {
	if (signal?.aborted) return { exitCode: null, stdout: "", stderr: "", aborted: true };

	const invocation = resolvePiInvocation(args);
	return new Promise((resolve) => {
		let stdout = "";
		let stderr = "";
		let aborted = false;
		let settled = false;
		let forceKill: ReturnType<typeof setTimeout> | undefined;
		let abortListener: (() => void) | undefined;

		const finish = (result: Omit<PiRun, "stdout" | "stderr" | "aborted">) => {
			if (settled) return;
			settled = true;
			if (forceKill) clearTimeout(forceKill);
			if (abortListener) signal?.removeEventListener("abort", abortListener);
			resolve({ ...result, stdout, stderr, aborted });
		};

		let child;
		try {
			child = spawn(invocation.command, invocation.args, {
				cwd,
				shell: false,
				windowsHide: true,
				stdio: ["ignore", "pipe", "pipe"],
			});
		} catch (error) {
			finish({ exitCode: null, spawnError: String(error) });
			return;
		}

		child.stdout.on("data", (chunk: Buffer | string) => {
			stdout += chunk.toString();
		});
		child.stderr.on("data", (chunk: Buffer | string) => {
			stderr += chunk.toString();
		});
		child.once("error", (error) => finish({ exitCode: null, spawnError: error.message }));
		child.once("close", (code) => finish({ exitCode: code }));

		abortListener = () => {
			aborted = true;
			if (!child.killed) child.kill();
			forceKill = setTimeout(() => {
				if (!settled) child.kill("SIGKILL");
			}, 2_000);
		};
		if (signal?.aborted) abortListener();
		else signal?.addEventListener("abort", abortListener, { once: true });
	});
}

function capabilityFailure(message: string, details: Record<string, unknown> = {}) {
	return {
		content: [{ type: "text" as const, text: `CAPABILITY_UNSATISFIED: ${message}` }],
		details: { agentScope: PROJECT_AGENT_SCOPE, ...details },
		isError: true,
	};
}

export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "small_project_subagent",
		label: "Small Project Subagent",
		description:
			"Run one approved small-project role in an isolated Pi process. Only project-local .pi/agents roles are accepted; no fallback model is used.",
		promptSnippet: "small_project_subagent(role, task): run one isolated, project-scoped workflow role.",
		promptGuidelines: [
			"Use small_project_subagent only for a complete bounded task packet and only with its listed fixed roles.",
			"Treat CAPABILITY_UNSATISFIED from small_project_subagent as a blocker; do not retry with a different model or role.",
		],
		parameters: SmallProjectSubagentParams,
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const requestedRole = params.role as string;
			if (!isAllowedRole(requestedRole)) {
				return capabilityFailure(`role ${JSON.stringify(requestedRole)} is not permitted`, {
					allowedRoles: ALLOWED_ROLES,
				});
			}
			const role: AllowedRole = requestedRole;

			if (!ctx.isProjectTrusted()) {
				return capabilityFailure("project trust is required before loading workflow agents", { role });
			}

			const discovery = discoverProjectAgents(ctx.cwd);
			const agent = discovery.agents.get(role);
			if (!agent) {
				return capabilityFailure(`role ${JSON.stringify(role)} is not installed (project .pi/agents or user-level agents)`, {
					role,
					projectAgentsDir: discovery.projectAgentsDir,
					userAgentsDir: discovery.userAgentsDir,
					agentScope: discovery.scope,
					discoveryErrors: discovery.errors,
				});
			}

			const selector = splitModelSelector(agent.model);
			if (!selector) {
				return capabilityFailure(`agent ${agent.name} has invalid model selector ${JSON.stringify(agent.model)}; use provider/model-id`, {
					role,
					filePath: agent.filePath,
				});
			}
			const registeredModel = ctx.modelRegistry.find(selector.provider, selector.id);
			const available = ctx.modelRegistry
				.getAvailable()
				.some((candidate) => candidate.provider === selector.provider && candidate.id === selector.id);
			if (!registeredModel || !available) {
				return capabilityFailure(`configured model ${agent.model} is unavailable for ${agent.name}`, {
					role,
					provider: selector.provider,
					model: selector.id,
					filePath: agent.filePath,
				});
			}

			let temporaryDirectory: string | undefined;
			try {
				temporaryDirectory = await mkdtemp(path.join(os.tmpdir(), "small-project-pi-"));
				const systemPromptPath = path.join(temporaryDirectory, `${role}.md`);
				await writeFile(systemPromptPath, agent.systemPrompt, { encoding: "utf8", mode: 0o600 });

				const args = [
					"--mode",
					"json",
					"-p",
					"--no-session",
					"--approve",
					"--model",
					agent.model,
					"--thinking",
					agent.thinking,
					"--tools",
					agent.tools.join(","),
					"--append-system-prompt",
					systemPromptPath,
					`Task:\n${params.task}`,
				];
				const run = await runPi(args, ctx.cwd, signal);
				const details = {
					agentScope: discovery.scope ?? "none",
					role,
					agent: agent.name,
					filePath: agent.filePath,
					model: agent.model,
					thinking: agent.thinking,
					exitCode: run.exitCode,
					stderr: run.stderr,
				};
				if (run.aborted) {
					return { content: [{ type: "text" as const, text: "SUBAGENT_ABORTED: Pi subagent was aborted." }], details, isError: true };
				}
				if (run.spawnError) {
					return {
						content: [{ type: "text" as const, text: `SUBAGENT_FAILED: could not start Pi: ${run.spawnError}` }],
						details,
						isError: true,
					};
				}
				if (run.exitCode !== 0) {
					return {
						content: [{ type: "text" as const, text: `SUBAGENT_FAILED: Pi exited with code ${run.exitCode}.` }],
						details,
						isError: true,
					};
				}

				const result = assistantResultFromJson(run.stdout);
				if (result.stopReason === "error" || result.stopReason === "aborted" || result.errorMessage) {
					return {
						content: [
							{
								type: "text" as const,
								text: `SUBAGENT_FAILED: ${result.errorMessage ?? `Pi stopped with ${result.stopReason}`}`,
							},
						],
						details: { ...details, stopReason: result.stopReason, errorMessage: result.errorMessage },
						isError: true,
					};
				}
				if (!result.text) {
					return {
						content: [{ type: "text" as const, text: "SUBAGENT_FAILED: Pi produced no final assistant message." }],
						details,
						isError: true,
					};
				}
				return { content: [{ type: "text" as const, text: result.text }], details };
			} finally {
				if (temporaryDirectory) await rm(temporaryDirectory, { recursive: true, force: true }).catch(() => undefined);
			}
		},
	});
}
