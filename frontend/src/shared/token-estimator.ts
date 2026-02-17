type EncLike = {
  encode: (value: string) => number[];
};

const DEFAULT_ENCODING = 'o200k_base';
const FALLBACK_ENCODING = 'cl100k_base';

let modulePromise: Promise<typeof import('js-tiktoken')> | null = null;
const encoderCache = new Map<string, EncLike>();

function normalizeModel(model?: string | null): string {
  const value = String(model || '').trim();
  if (!value) {
    return '';
  }
  if (value.includes('/')) {
    return value.split('/').pop() || value;
  }
  return value;
}

function getHeuristicTextEstimate(text: string): number {
  const value = String(text || '');
  if (!value) {
    return 0;
  }
  return Math.max(Math.floor(value.length / 4), 1);
}

export function countTextTokensHeuristic(text: string): number {
  return getHeuristicTextEstimate(text);
}

export function countChatTokensHeuristic(
  messages: Array<{ role?: string | null; content?: string | null; name?: string | null }>
): number {
  if (!messages.length) {
    return 0;
  }
  let total = 0;
  for (const message of messages) {
    total += 4;
    total += getHeuristicTextEstimate(String(message.role || ''));
    total += getHeuristicTextEstimate(String(message.content || ''));
    if (message.name) {
      total += Math.max(getHeuristicTextEstimate(String(message.name || '')) - 1, 0);
    }
  }
  total += 2;
  return Math.max(total, 0);
}

async function loadModule(): Promise<typeof import('js-tiktoken')> {
  if (!modulePromise) {
    modulePromise = import('js-tiktoken');
  }
  return modulePromise;
}

async function resolveEncoder(model?: string | null): Promise<EncLike | null> {
  const normalizedModel = normalizeModel(model);
  const cacheKey = normalizedModel || DEFAULT_ENCODING;
  const cached = encoderCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const { encodingForModel, getEncoding } = await loadModule();

  if (normalizedModel) {
    try {
      const encoder = encodingForModel(normalizedModel as Parameters<typeof encodingForModel>[0]);
      encoderCache.set(cacheKey, encoder);
      return encoder;
    } catch {
      // fall through to encoding fallback
    }
  }

  for (const encodingName of [DEFAULT_ENCODING, FALLBACK_ENCODING]) {
    try {
      const encoder = getEncoding(encodingName as Parameters<typeof getEncoding>[0]);
      encoderCache.set(cacheKey, encoder);
      return encoder;
    } catch {
      continue;
    }
  }

  return null;
}

export async function countTextTokensEstimate(text: string, model?: string | null): Promise<number> {
  const value = String(text || '');
  if (!value) {
    return 0;
  }

  const encoder = await resolveEncoder(model);
  if (!encoder) {
    return getHeuristicTextEstimate(value);
  }
  return encoder.encode(value).length;
}

export async function countChatTokensEstimate(
  messages: Array<{ role?: string | null; content?: string | null; name?: string | null }>,
  model?: string | null
): Promise<number> {
  if (!messages.length) {
    return 0;
  }

  const encoder = await resolveEncoder(model);
  if (!encoder) {
    return countChatTokensHeuristic(messages);
  }

  const countText = (value: string): number => encoder.encode(String(value || '')).length;
  let total = 0;
  for (const message of messages) {
    total += 4;
    total += countText(String(message.role || ''));
    total += countText(String(message.content || ''));
    if (message.name) {
      total += countText(String(message.name || '')) - 1;
    }
  }
  total += 2;
  return Math.max(total, 0);
}
