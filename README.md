# MedDataMCP

A unified [MCP](https://modelcontextprotocol.io) query layer over public
medical / biosignal dataset repositories. Instead of manually browsing
PhysioNet, NSRR, and Zenodo for every research task, this server exposes tools
that let an LLM (Claude Desktop, Cursor, or any MCP client) run **one** search
across all sources and get back ranked, normalized results.

Built for sleep-staging / biosignal dataset discovery — e.g. "find every public
dataset with paired polysomnography and wrist accelerometry".

## Sources (v1)

| Source | Access | What it provides |
| --- | --- | --- |
| **Zenodo** | Public API | Broad open-access research datasets |
| **PhysioNet** | Public | Physiological signal databases (ECG, EEG, PSG) via the PhysioBank index |
| **NSRR** | Public list / DUA for data | Sleep studies (PSG, actigraphy) |
| **HuggingFace** | Public API | ML-ready datasets on the Hub, incl. biosignal collections |
| **OpenNeuro** | Public GraphQL API | BIDS neuroimaging/electrophysiology (EEG, MEG, fMRI) with subject counts |

The architecture is connector-based — adding IEEE DataPort, Mendeley, Kaggle,
etc. is a single new file in `src/med_dataset_mcp/connectors/` plus one line in the
registry. (Mendeley and Kaggle need OAuth/API keys, so they're deferred.)

## Tools

| Tool | Purpose |
| --- | --- |
| `search_datasets(query, sources?, modalities?, per_source_limit?)` | Federated search across all sources, ranked by relevance |
| `find_paired_datasets(modality_a, modality_b, sources?)` | Datasets containing **both** modalities (e.g. PSG + IMU) |
| `get_dataset_details(source, dataset_id)` | Full record for one dataset |
| `list_sources()` | Registered sources and their access tiers |
| `list_modalities()` | Canonical modality keywords for filtering |

Results are normalized to a shared `DatasetRecord` (id, source, title,
description, url, modalities, license, tags, access).

## Setup

```bash
uv sync
uv run pytest        # run the test suite
```

### Run the server

```bash
uv run med-dataset-mcp
```

### Use with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "med-data": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/med-dataset-mcp", "run", "med-dataset-mcp"]
    }
  }
}
```

## Configuration

- `NSRR_TOKEN` — optional. If set, the NSRR connector forwards your personal
  token for authorized (DUA-approved) access. Without it, NSRR datasets are
  still listed (name + URL) and tagged `access="dua"`.

## Design notes

- **Caching:** in-memory TTL cache (15 min default) keyed per source+query, so
  fanned-out and repeated searches don't hammer upstream APIs.
- **Error isolation:** one source failing (timeout, API change) returns empty
  for that source — the rest of the results still come back.
- **Modality inference:** sources rarely expose structured modality fields, so
  modalities are inferred from titles/descriptions with boundary-aware keyword
  matching (avoids false positives like "stimulation" → IMU).
- **TLS:** uses the OS trust store via `truststore` so sources that omit
  intermediate certs (e.g. NSRR) verify correctly.

## Project layout

```
src/med_dataset_mcp/
  schema.py            # DatasetRecord (shared normalized model)
  modalities.py        # keyword-based modality detection
  cache.py             # in-memory TTL cache
  registry.py          # owns connectors, fan-out, caching, ranking
  server.py            # FastMCP tool definitions
  connectors/
    base.py            # Connector interface
    zenodo.py
    physionet.py
    nsrr.py
    huggingface.py
    openneuro.py
tests/
```
