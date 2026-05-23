# Action Plan Checklist (3 Roles)

Status markers: [ ] not started, [~] in progress, [x] done

## Backend/Agents Lead : Gaspard

- [ ] Define agent behavior tweaks: parsing, recommendation constraints, fallback logic, retries, error paths
- [ ] Implement inventory + sales write endpoints (transactions, stock updates) with agent trigger events
- [ ] Add structured logging for LLM calls and agent steps (trace IDs, input/output summaries)
- [ ] Implement SSE endpoint for agent event stream (thought/action/observation/final)

## Data/Integration Engineer : Jun

- [x] Align DB schema with MVP (decide which spec tables to implement now vs defer)
- [ ] Replace in-memory event queue with persistent event storage
- [ ] Add low-stock watcher background job (configurable thresholds)
- [ ] Seed realistic demo data for sales + stock trend coverage
- [ ] Add API tests for CRUD and agent analysis endpoints
- [ ] Add operational metrics hooks (LLM latency, errors, SSE throughput)

## Frontend/UX Engineer : Sam

- [ ] Replace dashboard mock data with live API calls
- [ ] Implement Agent Activity Stream UI fed by SSE
- [ ] Build Inventory page (add/edit/sell flows tied to backend)
- [ ] Build Recommendations page consuming SalesAnalysis + WineCellar outputs
- [ ] Add error/empty/loading states for agent calls and SSE disconnects
