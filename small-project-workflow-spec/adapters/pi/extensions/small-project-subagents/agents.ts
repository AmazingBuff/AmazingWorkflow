import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

/**
 * Pi's user-level config directory (honors PI_CODING_AGENT_DIR override).
 * User-level agents are a fallback only; project .pi/agents always win.
 */
export const USER_AGENTS_DIR = path.join(
	process.env.PI_CODING_AGENT_DIR ?? path.join(os.homedir(), ".pi", "agent"),
	"agents"
);

export const ALLOWED_ROLES = [
	"decision",
	"implementer",
	"reviewer",
	"test-planner",
	"test-runner",
	"reporter",
] as const;

export type AllowedRole = (typeof ALLOWED_ROLES)[number];

export interface ProjectAgent {
	role: AllowedRole;
	name: string;
	description: string;
	tools: string[];
	model: string;
	thinking: string;
	systemPrompt: string;
	filePath: string;
}

export interface ProjectAgentDiscovery {
	agents: Map<AllowedRole, ProjectAgent>;
	projectAgentsDir: string | null;
	userAgentsDir: string;
	scope: "project" | "user" | null;
	errors: string[];
}

export function isAllowedRole(value: string): value is AllowedRole {
	return (ALLOWED_ROLES as readonly string[]).includes(value);
}

function expectedName(role: AllowedRole): string {
	return `small-project-${role}`;
}

function removeQuotes(value: string): string {
	const trimmed = value.trim();
	if (
		trimmed.length >= 2 &&
		((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'")))
	) {
		return trimmed.slice(1, -1).trim();
	}
	return trimmed;
}

function splitFrontmatter(content: string): { fields: Map<string, string>; body: string } | null {
	const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
	if (!match) return null;

	const fields = new Map<string, string>();
	for (const line of match[1].split(/\r?\n/)) {
		const separator = line.indexOf(":");
		if (separator < 1) continue;
		fields.set(line.slice(0, separator).trim(), removeQuotes(line.slice(separator + 1)));
	}
	return { fields, body: match[2].trim() };
}

function containsTemplateToken(value: string): boolean {
	return /{{[^}]+}}/.test(value);
}

function parseProjectAgent(filePath: string): { agent?: ProjectAgent; error?: string } {
	let content: string;
	try {
		content = fs.readFileSync(filePath, "utf8");
	} catch (error) {
		return { error: `cannot read ${filePath}: ${String(error)}` };
	}

	const parsed = splitFrontmatter(content);
	if (!parsed) return { error: `${filePath}: expected YAML frontmatter` };

	const name = parsed.fields.get("name") ?? "";
	const description = parsed.fields.get("description") ?? "";
	const model = parsed.fields.get("model") ?? "";
	const thinking = parsed.fields.get("thinking") ?? "";
	const role = ALLOWED_ROLES.find((candidate) => name === expectedName(candidate));
	if (!role) return { error: `${filePath}: name must be one of the small-project role names` };

	const tools = (parsed.fields.get("tools") ?? "")
		.split(",")
		.map((tool) => tool.trim())
		.filter(Boolean);
	if (!description || !model || !thinking || tools.length === 0 || !parsed.body) {
		return { error: `${filePath}: name, description, tools, model, thinking, and body are required` };
	}
	if ([model, thinking].some(containsTemplateToken)) {
		return { error: `${filePath}: unresolved template value` };
	}

	return {
		agent: { role, name, description, tools, model, thinking, systemPrompt: parsed.body, filePath },
	};
}

function directoryExists(candidate: string): boolean {
	try {
		return fs.statSync(candidate).isDirectory();
	} catch {
		return false;
	}
}

function findNearestProjectAgentsDir(cwd: string): string | null {
	let current = path.resolve(cwd);
	while (true) {
		const candidate = path.join(current, ".pi", "agents");
		if (directoryExists(candidate)) return candidate;

		const parent = path.dirname(current);
		if (parent === current) return null;
		current = parent;
	}
}

/**
 * Discover role agents for the current project. Project-controlled
 * `.pi/agents` (nearest ancestor) takes precedence; when no project agents
 * directory exists, falls back to the user-level agents directory so the
 * workflow works in brand-new projects without per-project setup.
 */
export function discoverProjectAgents(cwd: string): ProjectAgentDiscovery {
	const projectAgentsDir = findNearestProjectAgentsDir(cwd);
	const userAgentsDir = USER_AGENTS_DIR;
	const preferredDir = projectAgentsDir ?? userAgentsDir;
	const scope: "project" | "user" | null = projectAgentsDir
		? "project"
		: fs.existsSync(userAgentsDir)
			? "user"
			: null;
	const agents = new Map<AllowedRole, ProjectAgent>();
	const errors: string[] = [];
	const invalidRoles = new Set<AllowedRole>();
	if (!preferredDir || !scope) return { agents, projectAgentsDir, userAgentsDir, scope, errors };

	let entries: fs.Dirent[];
	try {
		entries = fs.readdirSync(preferredDir, { withFileTypes: true });
	} catch (error) {
		return { agents, projectAgentsDir, userAgentsDir, scope, errors: [`cannot list ${preferredDir}: ${String(error)}`] };
	}

	for (const entry of entries) {
		if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
		const result = parseProjectAgent(path.join(preferredDir, entry.name));
		if (result.error) {
			errors.push(result.error);
			continue;
		}
		const agent = result.agent!;
		if (invalidRoles.has(agent.role)) continue;
		if (agents.has(agent.role)) {
			agents.delete(agent.role);
			invalidRoles.add(agent.role);
			errors.push(`${preferredDir}: duplicate ${agent.name} definitions`);
			continue;
		}
		agents.set(agent.role, agent);
	}

	return { agents, projectAgentsDir, userAgentsDir, scope, errors };
}
