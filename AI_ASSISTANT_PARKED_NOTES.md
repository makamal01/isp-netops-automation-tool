# AI Assistant — Parked Notes

**Status: parked (2026-09-28).** Do not start until the core app (without AI)
is refined into a small, solid, useful version. These notes capture the
research and decisions so far so the work can resume without redoing it.

## Idea

An optional in-app assistant that explains command output and failed
validation layers, and suggests read-only troubleshooting steps. It is an
add-on on top of a working product, not the product itself.

## Key constraint: device output is sensitive

Safe mode does not block `show running-config` / `display
current-configuration`, and validation itself runs `display
current-configuration | section bgp`. Output can contain password hashes,
SNMP communities, TACACS/RADIUS keys, BGP neighbours, and addressing. Where
that text is allowed to go decides the design, more than model choice does.

## Direction agreed

1. **One provider-agnostic assistant interface**, with adapters for:
   - Claude API, customer brings their own key (default recommendation).
   - Any OpenAI-compatible endpoint (covers Ollama on-prem).
   - Later, on demand: Claude via the customer's own AWS Bedrock / Google
     Cloud / Microsoft Foundry account.
2. **Customer brings their own key first**; a managed-key tier can come later.
3. **Sell it as a paid add-on**, not bundled into the base licence.
4. **Build it from the app's own context** (vendor, command, validation layer,
   evidence), not a generic chat box. Turn common questions into
   rule-based explanations over time.
5. **Non-negotiable trust rules:**
   - Off by default; enabled via deployment policy.
   - Redact secrets before sending (even to a local model) and show the
     operator what will be sent.
   - Advisory only; never executes. Suggested commands go through
     `is_command_safe` and a human click.
   - Audit-log every request (user, provider, size).
   - Worker thread + streaming; never freeze the UI.
   - Never bundle a model in the exe.
   - Label answers "AI-generated — verify before acting".
   - Maintain an eval set (real outputs + correct explanations) and re-run on
     every model/prompt change.

## Before building: validate with customers

Ask 3–5 target customers:
- Is device output allowed to go to a cloud AI provider?
- Would you pay extra for an assistant?

## Verified facts (checked 2026-09-28; re-check before relying on them)

**Claude API pricing** (per million tokens, input / output):
Haiku 4.5 $1 / $5, Sonnet 5 $2 / $10, Opus 5.5 $4 / $20. Batch API is 50% off.
Cache reads are 0.1× input (0.05× on Opus 5.5). US-only inference is 1.1×.
Claude 4.7+ models use a tokenizer that produces about 30% more tokens.

**Claude data handling (commercial API):** not used for training by default;
inputs/outputs deleted within 30 days; zero data retention by agreement.

**Ollama:**
- MIT licence.
- Native on Windows.
- API on `localhost:11434`, plus OpenAI-compatible `/v1`.
- Default context is 4,096 tokens, too small for device output; raise
  `OLLAMA_CONTEXT_LENGTH`.
- Memory scales with `OLLAMA_NUM_PARALLEL` × context.
- Binds to 127.0.0.1 by default and is exposed via `OLLAMA_HOST`. The docs
  describe no built-in auth, so firewall it or put an authenticating proxy
  in front.
- Windows ROCm support is RX 7600 XT and newer only. Vulkan is on by
  default, but it is untested on the RX 6700 XT.

**Model sizes:** qwen3:8b 5.2 GB, qwen3:14b 9.3 GB, qwen3:32b 20 GB,
llama3.1:8b 4.9 GB.

**Proxmox:**
- The default CPU type `x86-64-v2-AES` lacks AVX/AVX2; use `host`.
- GPU passthrough needs IOMMU, and q35 + OVMF is recommended.
- A passed-through GPU is exclusive to that VM, and the VM can't migrate.

## Estimates (not verified; measure before deciding)

- Cost per question at ~8k tokens in / 1k out: Haiku 4.5 ≈ $0.013,
  Sonnet 5 ≈ $0.03. So 1,000 questions/month ≈ $13 or ≈ $30.
- Local VM sizing for Ollama:
  - Minimum: 8 vCPU / 16 GB / 60 GB SSD, CPU-only 8B model; slow.
  - Recommended: add a 12 GB+ VRAM GPU with 24–32 GB RAM.
- On cost alone, Claude is cheaper than buying a GPU at NOC-team volumes.
  Local wins only on data policy or offline needs.

## First step when resuming

Run a side-by-side test: 5–10 real outputs from `isp_netops_export_*` through
a local Ollama model and Claude Haiku 4.5. Compare quality, speed, and cost.

## Sources

- https://platform.claude.com/docs/en/about-claude/pricing
- https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
- https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- https://github.com/ollama/ollama
- https://docs.ollama.com/gpu
- https://docs.ollama.com/faq
- https://docs.ollama.com/api/openai-compatibility
- https://ollama.com/library/qwen3
- https://ollama.com/library/llama3.1
- https://pve.proxmox.com/wiki/Qemu/KVM_Virtual_Machines
- https://pve.proxmox.com/wiki/PCI_Passthrough
