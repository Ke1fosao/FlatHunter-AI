# Stage 8 - AI Layer

Stage 8 adds a safe AI layer above the deterministic FlatHunter pipeline.

## Implemented

- `AIProvider` abstraction with `structured_completion`.
- Local deterministic `local_rules` provider for portfolio/demo operation without a paid AI key.
- Structured pydantic schemas for natural-language search parsing, listing summary, owner question generation, and listing comparison.
- `AIRequest` audit records for enabled AI runs and fallbacks.
- `AIPromptVersion` model for future prompt registry.
- Fallback behavior when AI is disabled or a provider is not configured.
- Sanitized `input_summary` hashes instead of raw prompt text in audit records.

## API

```text
POST /api/v1/search-profiles/parse-natural-language/
POST /api/v1/ai/listings/{listing_id}/summary/
POST /api/v1/ai/listings/{listing_id}/owner-questions/
POST /api/v1/ai/listings/compare/
```

`compare` accepts:

```json
{
  "listing_ids": ["uuid-1", "uuid-2"]
}
```

The endpoint requires 2 to 5 unique listing IDs.

## Provider Modes

Default local/demo mode:

```env
AI_ENABLED=false
AI_PROVIDER=local_rules
AI_MODEL=local-rules-v1
AI_DAILY_BUDGET=0
AI_TIMEOUT_SECONDS=15
```

When `AI_ENABLED=false`, the system returns deterministic results and does not create `AIRequest` rows.

When `AI_ENABLED=true` and `AI_PROVIDER=local_rules`, the same validated deterministic provider is executed through the AI provider contract and creates audit rows.

When an unconfigured provider is selected, the request falls back to deterministic output and writes an `AIRequest` row with `status=fallback`.

## Safety Rules

- AI output is validated before returning to the client.
- AI does not invent exact addresses, contacts, or legal conclusions.
- AI does not send messages to landlords.
- Raw user text is not stored in `AIRequest.input_summary`; only a short hash and character count are stored.
- The deterministic search, matching, listing, and map flows continue to work without AI.

## Next Provider Step

To connect a real provider later:

1. Add a provider class implementing `AIProvider`.
2. Keep structured schema validation.
3. Add timeout, retry, and cost metadata.
4. Set `AI_PROVIDER`, `AI_MODEL`, and `AI_API_KEY` through environment variables or a secret manager.
5. Keep `local_rules` as fallback.
