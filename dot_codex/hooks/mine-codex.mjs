// Codex rollout adapter. Extraction and capture policy stay in ai-brain.
import { readFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export function readSession(path, hook) {
  const events = [], fallback = [];
  let id = hook.session_id, cwd = hook.cwd, endedAt = 0;
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    let entry;
    try { entry = JSON.parse(line); } catch { continue; }
    if (!entry || typeof entry !== 'object') continue;
    const p = entry.payload;
    if (!p || typeof p !== 'object') continue;
    endedAt = Math.max(endedAt, Date.parse(entry.timestamp) || 0);
    if (entry.type === 'session_meta') {
      id ||= p.id || p.session_id;
      cwd ||= p.cwd;
      if (p.parent_thread_id || p.source?.subagent) return null;
    }
    // Event messages exclude system/developer instructions and tool output.
    // Prefer them over response_item copies so each message is counted once.
    if (entry.type === 'event_msg' && ['user_message', 'agent_message'].includes(p.type)
        && typeof p.message === 'string' && p.message.trim()) {
      events.push({role: p.type === 'user_message' ? 'user' : 'assistant', text: p.message});
    }
    if (entry.type === 'response_item' && p.type === 'message'
        && ['user', 'assistant'].includes(p.role) && Array.isArray(p.content)) {
      const text = p.content.filter(b => ['input_text', 'output_text', 'text'].includes(b.type))
        .map(b => b.text || '').join('\n').trim();
      if (text) fallback.push({role: p.role, text});
    }
  }
  if (typeof id !== 'string' || !id) return null;
  return {id, cwd, endedAt: endedAt || statSync(path).mtimeMs,
    messages: events.length ? events : fallback};
}

async function main() {
  const hook = JSON.parse(readFileSync(0, 'utf8'));
  if (!hook || typeof hook.transcript_path !== 'string') return;
  const session = readSession(hook.transcript_path, hook);
  if (!session || session.messages.length < 6) return;
  const moduleOf = name => import(pathToFileURL(join(homedir(), 'projects/ai-brain/scripts/miner', name)).href);
  const {loadEnv} = await moduleOf('env.ts');
  const {projectOf} = await moduleOf('cursor.ts');
  const {renderTranscript} = await moduleOf('transcript.ts');
  const {EXTRACTOR_VERSION, extractCandidates, labelFor} = await moduleOf('extract.ts');
  const {minedSessions, captureThought, recordMined} = await moduleOf('ledger.ts');
  loadEnv();
  if (!process.env.OPENAI_API_KEY) return;
  const corpus = 'codex';
  if ((await minedSessions(corpus, EXTRACTOR_VERSION)).has(session.id)) return;
  const project = projectOf(session.cwd || '') || '(unattributed)';
  const validFrom = new Date(session.endedAt).toISOString();
  const name = session.messages.find(m => m.role === 'user')?.text.slice(0, 120) || '(untitled)';
  const candidates = await extractCandidates({apiKey: process.env.OPENAI_API_KEY,
    transcript: renderTranscript(session.messages), project: labelFor(project),
    conversationName: name, date: validFrom.slice(0, 10)});
  let stored = 0;
  for (const candidate of candidates) {
    const result = await captureThought({content: candidate.content,
      source: `codex-tail v${EXTRACTOR_VERSION} ${project}`, validFrom, trust: 'agent_inferred',
      metadata: {mined_from: {corpus, session_id: session.id}, extractor_version: EXTRACTOR_VERSION}});
    if (result.ok) stored++;
    else if (result.status !== 409) throw new Error(`capture failed: ${result.status}`);
  }
  await recordMined({corpus, session_id: session.id, extractor_version: EXTRACTOR_VERSION,
    candidates_found: candidates.length, candidates_kept: stored});
  console.log(`${stored}/${candidates.length} codex ${session.id}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
