#!/usr/bin/env python3
"""Compress 458 intelligence objects into 30-50 operational patterns."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent
INPUT = ROOT / "reality-check-intelligence.json"
OUTPUT = ROOT / "normalized-intelligence-patterns.json"

# Hand-curated meta-pattern taxonomy: keyword signals → pattern id
# Each pattern is psychologically/operationally specific (not generic buckets).
META_PATTERNS: list[dict] = [
    {
        "id": "coordination_pm_obsolescence",
        "pattern_name": "PMs collapse into coordinators when build cost drops",
        "description": "When shipping gets cheap, PM work that only moves information between people gets automated or absorbed by engineers; the surviving PM must build prototypes, tools, and decisions—not run status theater.",
        "core_tension": "Coordination was the PM job; AI and eng velocity make coordination worthless without builder output.",
        "keywords": ["information-mover", "coordinator pm", "status report", "builder pm", "non-builder", "ticket writer", "information between", "pm squeeze", "mid-career pm", "pm headcount", "prd blocker", "build internal tools"],
        "priority": 2,
        "contradicts": ["design-led", "deferred pm", "minimal prd"],
    },
    {
        "id": "eng_velocity_pm_design_bottleneck",
        "pattern_name": "Engineering velocity turns PM and design into bottlenecks",
        "description": "When eng ships daily with AI, traditional PRD/design cadences break; PM becomes integrator and design becomes post-ship cohesion unless roles are explicitly resized.",
        "core_tension": "Speed upstream creates quality and alignment debt downstream.",
        "keywords": ["bottleneck", "eng ships", "pm/design squeeze", "integrator", "two-week", "eng-led", "let them cook", "design forced", "surface area", "daily launch", "research preview", "eng velocity"],
        "contradicts": ["design bottleneck deliberate", "gate all"],
    },
    {
        "id": "design_intentional_bottleneck",
        "pattern_name": "Design as deliberate shipping bottleneck for cohesion",
        "description": "Some orgs intentionally gate customer-facing work through a small design team, accepting slower velocity for unified product grammar—especially when AI makes everyone a builder.",
        "core_tension": "Cohesion vs raw ship speed; bottleneck creates political friction.",
        "keywords": ["design approval", "design bottleneck", "cohesion", "design-led", "taste", "deferred pm", "designer-engineer", "portfolio hiring", "gate", "frankenstein"],
        "contradicts": ["let them cook", "eng-led ship"],
    },
    {
        "id": "cheap_code_judgment_qa_shift",
        "pattern_name": "Cheap code shifts the bottleneck to judgment and verification",
        "description": "When implementation is nearly free, ideation explodes and QA/review becomes the binding constraint; organizations must invest in taste, evals, and automated verification—not more coders.",
        "core_tension": "Generation is cheap; knowing what to ship and proving it's safe is expensive.",
        "keywords": ["code cheap", "implementation cheap", "implementation ridiculously", "typing speed bottleneck", "review code not", "dark factory", "code is cheap", "cheap shifts"],
        "priority": 2,
        "contradicts": [],
    },
    {
        "id": "agentic_cognitive_burnout",
        "pattern_name": "Parallel agents exhaust humans before compute",
        "description": "Running multiple AI agents in parallel hits cognitive bandwidth by mid-day; sustainable agentic work requires capped parallelism and time-boxed review, not heroic 4x agent mornings.",
        "core_tension": "Compute scales linearly; human attention does not.",
        "keywords": ["burnout", "11am", "parallel agent", "cognitive", "wiped", "agent supervision", "dark factory", "unread code", "exhaustion", "human limit"],
        "contradicts": ["10x output"],
    },
    {
        "id": "research_preview_shipping",
        "pattern_name": "Research preview as default lowers cost of being wrong",
        "description": "AI-native teams ship almost everything labeled early with short cycles, trading polish for feedback velocity; preview branding is honesty infrastructure, not excuse for neglect.",
        "core_tension": "Speed requires public imperfection; enterprise trust still demands GA discipline.",
        "keywords": ["research preview", "preview", "may change", "week-or-two", "labeled early", "cowork preview", "trust-through-speed", "branded early"],
        "contradicts": ["enterprise quarterly", "polish first"],
    },
    {
        "id": "goals_principles_over_prd",
        "pattern_name": "Goals and principles replace heavy PRD coordination",
        "description": "When build cost drops, weekly metrics plus explicit tradeoff principles let teams decide without PM approval gates; PRDs survive only for ambiguous or infra-heavy bets.",
        "core_tension": "Documentation volume was a coordination substitute; clarity of goals replaces it.",
        "keywords": ["principles", "weekly metrics", "minimal prd", "goals", "no pm blocker", "two-week project", "prd death", "strategy clarity"],
        "contradicts": ["heavy prd", "spec discipline"],
    },
    {
        "id": "barrel_throughput_limit",
        "pattern_name": "Barrels cap parallel initiative throughput",
        "description": "Organizations can only run as many important initiatives in parallel as they have outcome-owning operators; hiring more people without new barrels increases coordination tax, not output.",
        "core_tension": "Headcount illusion vs barrel-limited throughput.",
        "keywords": ["barrel", "ammunition", "outcome ownership", "parallel", "254 people", "12-17", "hell or high water", "take an idea"],
        "contradicts": ["hire spree"],
    },
    {
        "id": "high_performance_no_safety",
        "pattern_name": "High-performance cultures trade psychological safety for winning",
        "description": "Operator cultures critique in public, skip failure retros that chill risk, and reward bold attempts—winning over comfort, with real attrition and silent disengagement failure modes.",
        "core_tension": "Collective learning via public critique vs individual willingness to raise hand.",
        "keywords": ["psychological safety", "critique in public", "winning", "failure retro", "ambitious failure", "facts not sandwich", "high performance", "candor"],
        "contradicts": ["psychological safety", "learning mindset"],
    },
    {
        "id": "influence_not_politics",
        "pattern_name": "Influence fails when treated as politics—or when buy-in is externalized",
        "description": "Getting ideas to survive requires mapping exec incentives and timing, not manipulation; failed buy-in is owned by the pitcher, and exec calendars are strobe lights of fragmented attention.",
        "core_tension": "Good ideas die without empathy for stakeholder incentives; blaming execs prevents learning.",
        "keywords": ["influence", "politics", "exec calendar", "strobe", "buy-in", "three options", "goldilocks", "kill projects", "trust", "simulate exec", "pushback", "your fault"],
        "contradicts": [],
    },
    {
        "id": "success_disaster_firefighting",
        "pattern_name": "Success disasters consume growth leadership",
        "description": "Hypergrowth breaks things that went well—activation, monetization, infra—so most leader time is firefighting lucky problems, not proactive bets; log-linear growth feels like failure to exponential-trained investors.",
        "core_tension": "Green charts hide operational pain; firefighting becomes permanent.",
        "keywords": ["success disaster", "70%", "firefighting", "log-linear", "lucky problem", "hypergrowth", "breaking"],
        "contradicts": [],
    },
    {
        "id": "growth_safety_tiers",
        "pattern_name": "Growth teams need red-line vs testable controversy tiers",
        "description": "Growth naturally pressure-tests boundaries; orgs must pre-commit to values-based never-ship zones separate from metric outcomes, while still allowing ugly-but-learnable tests.",
        "core_tension": "Metric pressure vs brand/values constraints.",
        "keywords": ["red line", "controversial test", "growth safety", "dark pattern", "never ship", "brand gate", "cash growth"],
        "contradicts": [],
    },
    {
        "id": "dual_org_loonshots",
        "pattern_name": "Dual-org tension between flat innovation and hierarchical ops",
        "description": "Scale requires incompatible structures—flat innovation teams and hierarchical reliability orgs—held in productive tension by leadership as translator, not merger.",
        "core_tension": "Innovators resent bureaucracy; operators dismiss innovators.",
        "keywords": ["loonshots", "dual-org", "flat innovation", "hierarchical", "design team presents", "translator", "jokers and bureaucrats"],
        "contradicts": [],
    },
    {
        "id": "gm_fiefdom_platform",
        "pattern_name": "GM fiefdoms block platform integration",
        "description": "When success is defined as owning a mini-empire ($40M silo), platform integration dies; AI-first transformation requires integrated data and cross-product motion.",
        "core_tension": "Entrepreneurial GM ambition vs customer expectation of one platform.",
        "keywords": ["gm fiefdom", "fiefdom", "holding company", "251 acquisition", "platform not holding", "silo", "packet loss", "permission to play"],
        "contradicts": [],
    },
    {
        "id": "ai_first_mandate",
        "pattern_name": "AI-first mandate is non-debatable at leadership level",
        "description": "Leaders declare AI-first operating models explicitly; debating whether to adopt wastes calories while pilot-only mentality leaves value on table—though safety/regulatory paths still need human gates.",
        "core_tension": "Mandate without workflow change is theater; mandate with bad pacing is unsafe.",
        "keywords": ["ai-first", "non-debatable", "not optional", "mandate", "teammate not tool", "codex teammate", "megatrend"],
        "contradicts": ["skeptic", "thoughtful pacing"],
    },
    {
        "id": "agency_control_ladder",
        "pattern_name": "Autonomy collapses under escalation without a control ladder",
        "description": "Agentic systems require earned trust: copilot suggest → logged corrections → expanded actions; day-one full autonomy causes hot-fix spirals and shutdowns.",
        "core_tension": "Marketing wants full autonomy; production needs calibrated control.",
        "keywords": ["agency-control", "control ladder", "human-in-the-loop", "progressive trust", "read-only first", "permission", "autonomy", "relinquishing control", "day-one full access"],
        "contradicts": ["full autonomy demo"],
    },
    {
        "id": "evals_production_duality",
        "pattern_name": "Evals define good; production monitoring catches drift",
        "description": "When code is cheap, defining good via high-signal evals becomes PM/engineering work; production monitoring catches what evals miss—both are required, neither alone suffices.",
        "core_tension": "Eval theater vs vibe checks; metrics vs character.",
        "keywords": ["eval iteration", "four-part judge", "calibration bar", "step-level mapping", "evals as final", "evals define", "production monitoring", "vibe eval", "10 great evals", "eval pod", "dataset", "traces"],
        "priority": 2,
        "contradicts": [],
    },
    {
        "id": "experimentation_theater",
        "pattern_name": "Experimentation theater without insight propagation",
        "description": "Teams run many experiments but fail to propagate learnings—swarm exploitation before new explore, thousand experiments aspiration without synthesis, or automated growth tests without human judgment on red lines.",
        "core_tension": "Experiment volume ≠ organizational learning.",
        "keywords": ["thousand experiment", "explore-exploit", "swarm exploitation", "experimentation", "insight level", "pattern scanner", "a/b", "growth hack"],
        "contradicts": [],
    },
    {
        "id": "consumer_vision_vs_research",
        "pattern_name": "Consumer vision tempo vs enterprise research split",
        "description": "Consumer product playbooks favor founder taste and ship-measure loops; enterprise requires customer research and spec discipline—the same PM identity cannot serve both without explicit separation.",
        "core_tension": "Listening deeply vs not building requested features; Rabois vs Spiegel.",
        "keywords": ["customer research", "anti-research", "consumer vs enterprise", "vision-driven", "don't build requested", "listen deeply", "jobs and feelings"],
        "contradicts": [],
    },
    {
        "id": "distribution_over_product",
        "pattern_name": "Distribution beats product in consumer social",
        "description": "In consumer social, distribution access matters more than feature novelty; mid-scale players must bet on differentiated moats (ecosystem, hardware) not head-on incumbent wars.",
        "core_tension": "Building great product vs being copied before monetizing.",
        "keywords": ["distribution", "moat", "network effect insufficient", "close-friend", "copy cycle", "threads", "tiktok distribution", "middle-child"],
        "contradicts": [],
    },
    {
        "id": "software_moat_erosion",
        "pattern_name": "Software moat erosion drives ecosystem and hardware pivots",
        "description": "When software copies instantly—accelerated by AI—moats shift to platforms, ecosystems, and vertically integrated stacks; patents and features alone don't defend.",
        "core_tension": "Shipping AI software while claiming software isn't the moat.",
        "keywords": ["software not a moat", "ecosystem", "hardware pivot", "vertical integration", "ar platform", "copy instantly"],
        "contradicts": [],
    },
    {
        "id": "ceo_ai_literacy_gate",
        "pattern_name": "CEO AI literacy gates enterprise adoption",
        "description": "Transformation fails when leader intuitions outpace understanding of non-determinism; exec learning blocks and practitioner questions beat bottom-only-up adoption and FOMO vendor purchases.",
        "core_tension": "Top-down buy-in vs grassroots building; hype vs fluency.",
        "keywords": ["ceo ai literacy", "ceo blocked", "top-down", "leader learning", "non-determinism", "augmentation not replacement"],
        "contradicts": [],
    },
    {
        "id": "humanity_adoption_pushback",
        "pattern_name": "Humanity and societal pushback gate AI deployment",
        "description": "Technology capability outruns human comfort; consumer and enterprise adoption is bounded by societal acceptance, not lab benchmarks—especially in social and sensitive contexts.",
        "core_tension": "Lab optimism vs consumer realism; deploy fast vs creepy.",
        "keywords": ["societal pushback", "humanity", "adoption curve", "human comfort", "parent/teen", "pushback underrated"],
        "contradicts": ["ai-first mandate"],
    },
    {
        "id": "multi_agent_context_partition",
        "pattern_name": "Multi-agent by context window, not one mega-agent",
        "description": "Reliable personal and enterprise agents partition by domain/context; monolithic agents suffer pollution, injection, and failure cascades—progressive trust mirrors hiring an EA.",
        "core_tension": "Users want one assistant; reliability requires many bounded ones.",
        "keywords": ["multi-agent", "context window", "partition", "separate agent", "soul", "cron", "heartbeat", "progressive trust", "sam sdr", "life os", "openclaw"],
        "contradicts": ["one agent"],
    },
    {
        "id": "automation_100_reliability",
        "pattern_name": "Partial automation creates more work than manual",
        "description": "95% automation isn't automation—users abandon at partial reliability; personal and enterprise workflows need last-mile preference teaching before trust.",
        "core_tension": "Demo magic vs production trust bar.",
        "keywords": ["95%", "100% reliability", "partial automation", "abandon", "inbox automation", "last mile"],
        "contradicts": [],
    },
    {
        "id": "mission_over_local_okr",
        "pattern_name": "Mission sacrifice beats local OKR optimization",
        "description": "In mission-driven orgs, teams deprioritize local metrics for company-level wins—accepting product-line ego hits when global mission demands it.",
        "core_tension": "Mission rhetoric often fake; local KPIs still drive behavior unless enforced.",
        "keywords": ["mission-over-okr", "local kr", "company mission", "deprioritize", "anthropic succeeded"],
        "contradicts": ["revenue", "subscription conflict"],
    },
    {
        "id": "portfolio_velocity_mess",
        "pattern_name": "Portfolio mess accepted for velocity, consolidated later",
        "description": "AI races reward overlapping experiments and form factors; user confusion is accepted cost until winners emerge—then education and /powerup-style onboarding catch up.",
        "core_tension": "Learning speed vs portfolio elegance and brand coherence.",
        "keywords": ["overlapping feature", "portfolio mess", "product consistency sacrificed", "user confusion", "powerup", "multiple surfaces"],
        "contradicts": [],
    },
    {
        "id": "joy_drives_adoption",
        "pattern_name": "Joy unlocks AI adoption more than mandates",
        "description": "People adopt tools that feel joyful, not just productive; enterprise rollouts need voluntary usage and smiles before compliance metrics—though regulated paths still need mandates.",
        "core_tension": "Joy without security creates shadow IT; mandates without joy create resistance.",
        "keywords": ["joy", "delight", "voluntary usage", "adoption", "smiles", "fomo", "skeptic-to-believer"],
        "contradicts": ["mandate"],
    },
    {
        "id": "resume_brand_hiring_trap",
        "pattern_name": "Resume brands select for coasting; undiscovered talent has alpha",
        "description": "Prestige credentials anti-correlate with hunger in tight markets; work samples and non-obvious pools beat logo hiring—though screening cost is higher.",
        "core_tension": "Brand signals baseline skill vs hunger and slope.",
        "keywords": ["resume brand", "undiscovered talent", "pedigree", "work sample", "barrel trial", "intern pipeline", "prestige"],
        "contradicts": [],
    },
    {
        "id": "workforce_shed_rehire",
        "pattern_name": "Shed coordination layers, rehire AI-first builders",
        "description": "Hyperscalers cut broad headcount then rehire smaller AI-fluent builder-dense teams—structural recomposition, not cyclical layoffs.",
        "core_tension": "Survivor overload vs knowledge loss; rehire same profiles without behavior change.",
        "keywords": ["30k shed", "8k rehire", "ai-first rehire", "shed coordination", "smaller denser teams", "structural recomposition"],
        "priority": 2,
        "contradicts": [],
    },
    {
        "id": "operating_tempo_signal",
        "pattern_name": "Operating tempo is a leading indicator before outcomes",
        "description": "Cycle time, decision speed, and shipping cadence predict winning more than current metrics—though busywork tempo and burnout tempo are failure modes.",
        "core_tension": "Speed without direction burns cash; fake velocity destroys trust.",
        "keywords": ["operating tempo", "cadence", "cycle time", "decision speed", "compress planning"],
        "contradicts": [],
    },
    {
        "id": "crucible_profitability_pressure",
        "pattern_name": "Crucible moments under profitability proof pressure",
        "description": "Scale without durable profitability narrative fails in public markets; parallel tracks must prove foundation (ads, SMB) while funding long-horizon bets without street panic.",
        "core_tension": "Growth/engagement masks P&L weakness; future bets delay profitability.",
        "keywords": ["crucible", "profitability", "net income", "fortune 500 scale", "activist", "prove durable"],
        "contradicts": [],
    },
    {
        "id": "ceo_communicator_role",
        "pattern_name": "CEO job becomes explainer-in-chief at scale",
        "description": "Narrative alignment rivals product decisions; packet loss through hierarchy requires direct frontline storytelling and structured signal detection (e.g. CEO agents).",
        "core_tension": "Builder identity vs communicator role; middle managers feel bypassed.",
        "keywords": ["explainer in chief", "communication", "all-hands", "packet loss", "narrative", "glean ceo", "3+3"],
        "contradicts": [],
    },
    {
        "id": "strategy_clarity_scarce",
        "pattern_name": "Strategy clarity becomes binding when everyone can ship",
        "description": "Democratized building makes unclear strategy produce faster chaos; leadership invests in blast-radius tiers and documented use cases, not PRD bureaucracy for low-risk ships.",
        "core_tension": "Fast shipping vs ungoverned chaos; strategy work becomes abstract theater.",
        "keywords": ["strategy clarity", "blast radius", "democratized", "skills democratize", "prd death", "design review tier", "use cases documented"],
        "contradicts": [],
    },
    {
        "id": "dont_trust_process",
        "pattern_name": "Preserved design process becomes liability under eng velocity",
        "description": "Research diverge/converge cycles are too slow; design splits into execution support now and 3-6 month prototype vision—embedded support over phase gates.",
        "core_tension": "Craft identity vs irrelevance; accessibility suffers without any process.",
        "keywords": ["don't trust the process", "design process dead", "embedded support", "3-6mo vision", "legibility", "block-shaped designer"],
        "contradicts": ["rigorous research"],
    },
    {
        "id": "agi_pilled_vs_today_model",
        "pattern_name": "Building for super-AGI while under-harnessing today's model",
        "description": "Easy to roadmap for future models; hard to elicit max from current ceiling—ship for today, prototype for tomorrow, strip crutches each release.",
        "core_tension": "AGI-pilled roadmap never ships vs overfit to today's failures.",
        "keywords": ["agi-pilled", "today's model", "model release", "crutch", "harness", "system prompt audit", "model-coupled"],
        "contradicts": [],
    },
    {
        "id": "blur_pm_tl_partnership",
        "pattern_name": "Blurred PM/tech-lead partnership beats rigid RACI",
        "description": "Visionary eng lead plus integrator PM with intentional 20% ownership splits moves faster than perfect role clarity in AI cadence environments.",
        "core_tension": "Blur causes dropped launches vs slow RACI.",
        "keywords": ["blurred pm", "tech lead", "mind meld", "20% ownership", "boris", "integrator", "launch room"],
        "contradicts": [],
    },
    {
        "id": "engineer_taste_over_pm_headcount",
        "pattern_name": "Engineers with product taste beat PM headcount expansion",
        "description": "End-to-end engineer shipping from feedback to deploy reduces coordination tax; PMs reserved for ambiguous, infra-heavy, or cross-functional blockers.",
        "core_tension": "PM-less chaos on big bets vs PM overhead on small bets.",
        "keywords": ["engineer taste", "mini-pm", "hire engineers", "almost no pm", "end-to-end", "twitter feedback to ship"],
        "contradicts": ["needs more pms"],
    },
    {
        "id": "playbook_half_life",
        "pattern_name": "Half of inherited operating playbooks must be thrown out",
        "description": "AI-era orgs invalidate 50-70% of prior company growth/PM practices; weekly unlearning is required—though some fundamentals still apply and adaptation fatigue is real.",
        "core_tension": "Expertise identity vs constant reinvention.",
        "keywords": ["throw out", "50%", "playbook", "unlearn", "hardest job", "anti-prd", "inherited"],
        "contradicts": [],
    },
    {
        "id": "constraints_freedom",
        "pattern_name": "Underfunding constraints force strategic clarity",
        "description": "Being smallest funded player eliminates excess choice; abundance after funding risks path dependency and scarcity-mindset hangover.",
        "core_tension": "Constraints as freedom vs excuse for underinvestment.",
        "keywords": ["constraints brought freedom", "smallest least funded", "underdog", "eliminate excess choice"],
        "contradicts": ["well-funded"],
    },
    {
        "id": "vibe_vs_agentic_distinction",
        "pattern_name": "Vibe coding and agentic engineering must stay distinct",
        "description": "Collapsing terms destroys safety distinctions: vibe coding for personal throwaway scope; agentic engineering for reviewed production—with tiered quality bars by blast radius.",
        "core_tension": "Pressure to ship fast blurs personal vs prod boundaries.",
        "keywords": ["vibe coding", "agentic engineering", "hands-off", "professional", "self-harm-only", "blast radius", "tiered quality"],
        "contradicts": [],
    },
    {
        "id": "prototype_free_ideation",
        "pattern_name": "Triple prototype ideation becomes economically free",
        "description": "Working UI prototypes replace spec debate; require multiple variants before commit—but prototype abundance can delay decisions or mislead on prod feasibility.",
        "core_tension": "Demo-driven design vs prototype paralysis.",
        "keywords": ["triple prototype", "three different", "prototype three", "demo-driven", "figma-only"],
        "contradicts": [],
    },
    {
        "id": "calm_under_chaos_hiring",
        "pattern_name": "Calm optimism under chaos as hiring filter",
        "description": "Sustainable AI speed requires people who lean into exponential change without burning out; brutal prioritization (P0→P000) without perfectionism on non-core paths.",
        "core_tension": "External chill perception vs internal severity inflation.",
        "keywords": ["calm", "chaos", "smile", "p000", "burnout", "imperfect ship", "team lunch vibe"],
        "contradicts": [],
    },
    {
        "id": "hour_turnaround_exec_test",
        "pattern_name": "Exec subtle invitations test organizational alignment speed",
        "description": "Repeated exec questions signal strategic anxiety; hour-turnaround frameworks and unprompted loom responses build trust—missing cues until blowup destroys it.",
        "core_tension": "Speed of response vs depth of thought; unsustainable for ICs.",
        "keywords": ["hour-turnaround", "fourth time", "subtle cue", "loom framework", "frustrated", "top 10 use cases", "rachel"],
        "contradicts": [],
    },
    {
        "id": "kill_to_build_trust",
        "pattern_name": "Killing own projects builds executive trust",
        "description": "Proactive deprioritization signals company-first senior thinking; never killing reads as not senior—though over-killing erodes team morale.",
        "core_tension": "Innovation need vs visible killing as aligned incentives.",
        "keywords": ["kill projects", "deprioritize", "kill things", "build trust", "company-first"],
        "contradicts": [],
    },
    {
        "id": "hard_problem_talent_magnet",
        "pattern_name": "Hard problems attract best teams; easy problems don't",
        "description": "Problem difficulty is talent magnet when permission-to-play exists; easy wins attract mediocre teams and fail to compound—paired with route-to-market filter.",
        "core_tension": "Hard without permission wastes talent; easy with permission is lemonade stand.",
        "keywords": ["hard problem", "permission to play", "route to market", "99% no", "lemonade stand", "team sport"],
        "contradicts": [],
    },
    {
        "id": "platform_career_compound",
        "pattern_name": "Platform access compounds outcomes more than individual brilliance",
        "description": "Choosing high-leverage platforms is career compound interest; don't confuse ability with platform access—luck plus preparation matters.",
        "core_tension": "Merit narrative vs unequal platform distribution.",
        "keywords": ["platform choice", "springboard", "compound interest", "luck plus preparation", "career platform"],
        "contradicts": [],
    },
    {
        "id": "retention_over_day_one_paywall",
        "pattern_name": "Retention gold beats day-one paywall optimization",
        "description": "Monetization and growth loops that optimize first-session conversion without retention insight propagate short-term revenue and long-term churn.",
        "core_tension": "Day-one metrics vs longitudinal value.",
        "keywords": ["retention gold", "day-one paywall", "retention", "churn", "longitudinal"],
        "contradicts": [],
    },
    {
        "id": "positive_framing_coaching",
        "pattern_name": "Positive framing beats cold coach for behavior change",
        "description": "Reframing and curiosity ('what led you to believe that?') disarm defensiveness better than argument in influence and coaching contexts.",
        "core_tension": "Performative curiosity vs need to drive closure.",
        "keywords": ["positive framing", "cold coach", "so interesting", "learning mindset", "curiosity"],
        "contradicts": ["critique in public"],
    },
    {
        "id": "grow_market_not_share",
        "pattern_name": "Grow the market, not only share",
        "description": "Category creation and market expansion beats zero-sum share fights—especially for platforms and dev tools where ecosystem health matters.",
        "core_tension": "Share fights vs ecosystem investment.",
        "keywords": ["grow the market", "not only share", "category", "ecosystem health", "zero-sum"],
        "contradicts": [],
    },
    {
        "id": "right_ai_for_job",
        "pattern_name": "Right AI for the job resists tool FOMO",
        "description": "Not every workflow needs the newest model or agent; match capability to risk, cost, and latency—resist one-click vendor purchases and shiny tool churn.",
        "core_tension": "Tool FOMO vs workflow depth.",
        "keywords": ["right ai", "tool fomo", "shiny", "match capability", "workflow", "vendor purchase"],
        "contradicts": ["ai-first"],
    },
    {
        "id": "accelerate_humans_not_confuse",
        "pattern_name": "Accelerate humans, don't confuse them",
        "description": "AI products should augment human workflow clarity, not add cognitive load, ambiguous autonomy, or feature overwhelm without onboarding relief.",
        "core_tension": "Capability showcase vs human comprehension.",
        "keywords": ["accelerate humans", "confuse", "cognitive load", "feature overwhelm", "onboarding"],
        "contradicts": [],
    },
    {
        "id": "codex_teammate_framing",
        "pattern_name": "AI as teammate reframing changes usage patterns",
        "description": "Tool framing underutilizes AI; teammate framing changes collaboration—after experimentation period, assign work like onboarding a new hire with accountability for outputs.",
        "core_tension": "Teammate metaphor overtrusts vs tool-only leaves value on table.",
        "keywords": ["teammate", "not tool", "codex teammate", "three-month experimentation", "onboarding playbooks"],
        "contradicts": ["tool only"],
    },
    {
        "id": "human_typing_bottleneck",
        "pattern_name": "Human typing speed becomes the shipping bottleneck",
        "description": "When agents generate faster than humans can specify/review, prompting and review interfaces—not raw generation—determine throughput.",
        "core_tension": "Generation unlimited; specification and review finite.",
        "keywords": ["typing speed", "human bottleneck", "prompting", "review interface", "proactivity"],
        "contradicts": [],
    },
    {
        "id": "openai_bottoms_up_empiricism",
        "pattern_name": "Bottom-up empiricism over top-down AI product doctrine",
        "description": "Let usage data and internal dogfooding drive product decisions rather than executive feature mandates—especially in fast-moving model capability environments.",
        "core_tension": "Empiricism vs speed of top-down bets.",
        "keywords": ["bottoms up", "empiricism", "dogfooding", "usage data", "internal belief"],
        "contradicts": ["top-down mandate"],
    },
    {
        "id": "sora_speed_case_study",
        "pattern_name": "AI speed creates review and governance bottlenecks",
        "description": "Case-study speed (e.g. Sora-like generation cycles) outpaces legal, brand, and design review—creating new organizational bottlenecks unrelated to engineering capacity.",
        "core_tension": "Generation speed vs institutional review bandwidth.",
        "keywords": ["sora", "review bottleneck", "governance", "legal review", "brand review", "speed case"],
        "contradicts": [],
    },
    {
        "id": "any_agent_coding_agent",
        "pattern_name": "Any agent should be able to act as coding agent",
        "description": "Generalist agents that can read repos, run tests, and ship PRs reduce tool fragmentation—but increase security and scope-boundary requirements.",
        "core_tension": "Generalist convenience vs least-privilege security.",
        "keywords": ["any agent should", "coding agent", "generalist agent"],
        "contradicts": [],
    },
    {
        "id": "reinvention_career_decay",
        "pattern_name": "Career capital decays without reinvention every 2-3 years",
        "description": "Past employer brand becomes liability; reinvention is emotionally costly but survival requirement in AI transition—cycle compressing to months.",
        "core_tension": "Brand opens doors short-term vs hunger and skills long-term.",
        "keywords": ["reinvention", "2-3 years", "career survival", "resume", "cosmetic upskilling"],
        "contradicts": [],
    },
    {
        "id": "build_internal_tools_not_meetings",
        "pattern_name": "Build internal tools that replace meetings and decks",
        "description": "Highest-leverage PM work automates coordination: dashboards and agents replace recurring syncs; PM maintains systems not slides.",
        "core_tension": "Politics lives in meetings; not all context fits tools.",
        "keywords": ["internal tool", "status report", "dashboard", "agent-generated status", "replace meeting", "replace sync"],
        "contradicts": [],
    },
    {
        "id": "ai_search_replaces_google",
        "pattern_name": "AI-mediated research replaces direct search workflows",
        "description": "Models with search synthesize parallel queries faster than manual Googling—but hallucination requires verify-before-publish discipline.",
        "core_tension": "Research speed vs factual accuracy.",
        "keywords": ["ai search", "google", "research workflow", "hallucination", "verify-before-publish", "synthesized"],
        "contradicts": [],
    },
    {
        "id": "executive_time_roi_agents",
        "pattern_name": "Executive time reclamation is the agent adoption wedge",
        "description": "Executives adopt agents when calendar hours return—not when features impress; quantify 10hr/week style ROI before org rollout.",
        "core_tension": "Personal ROI may not transfer to team; security bar higher for exec data.",
        "keywords": ["executive time", "10hr", "calendar", "time reclamation", "hours saved", "sdr agent"],
        "contradicts": [],
    },
    {
        "id": "physical_partition_security",
        "pattern_name": "Software permissions insufficient for sensitive agent data",
        "description": "Highest-sensitivity workflows need hardware or VM tenant isolation—separate machines for financial/legal/health vs daily-driver general agent.",
        "core_tension": "Convenience vs compartmentalization; most users won't buy second machine.",
        "keywords": ["physical machine", "separate machine", "compartmentalize", "air-gap", "vm tenant", "sensitive data"],
        "contradicts": [],
    },
    {
        "id": "large_swing_growth",
        "pattern_name": "Growth flips from small bets to large swings",
        "description": "AI markets reward step-change bets over marginal funnel tweaks; allocate 50-70% to larger swings while not neglecting core funnel maintenance.",
        "core_tension": "Large swing failures visible vs small bet compounding ignored.",
        "keywords": ["large swing", "50-50", "70% larger", "small bet", "step-change", "swing-heavy"],
        "contradicts": [],
    },
    {
        "id": "cash_growth_automation",
        "pattern_name": "Growth teams must eat their own AI cooking",
        "description": "Internal Claude/automation for experiment design and analysis scales throughput—but automated tests can cross brand red lines without human gates.",
        "core_tension": "Automation confidence vs brand-sensitive judgment.",
        "keywords": ["cash", "claude accelerates", "growth automation", "automated experiment", "growth platform"],
        "contradicts": [],
    },
    {
        "id": "enterprise_ai_maturity_ladder",
        "pattern_name": "Enterprise AI maturity climbs rungs, not leapfrogs",
        "description": "Large orgs move through maturity stages—experimentation, workflow embedding, governance, scale—rather than jumping to full autonomy; code-native defaults beat GUI-first for builders.",
        "core_tension": "Executive mandate for transformation vs institutional readiness at each rung.",
        "keywords": ["enterprise ai maturity", "maturity ladder", "code-native", "gui default", "loop not lane", "maturity stages"],
        "priority": 2,
        "contradicts": ["ai-first mandate"],
    },
    {
        "id": "season_planning_not_roadmaps",
        "pattern_name": "Season-based planning replaces static roadmaps",
        "description": "In fast AI markets, planning horizons compress into seasons with explicit bets and kill criteria—not annual roadmaps that are obsolete on publication.",
        "core_tension": "Need for direction vs futility of long-range commitment.",
        "keywords": ["season-based", "season based", "planning season", "static roadmap", "quarterly bet"],
        "priority": 2,
        "contradicts": [],
    },
    {
        "id": "purpose_over_financial_rationality",
        "pattern_name": "Irrational purpose beats money-maximizing defaults",
        "description": "Founders and leaders sometimes choose purpose, craft, or mission over economically 'rational' paths—especially when academia or conventional career ladders undervalue ambition.",
        "core_tension": "Investor rationality vs founder meaning-making.",
        "keywords": ["irrational purpose", "over money", "think bigger than academia", "purpose over", "unpopular decisions", "chained hard decisions"],
        "priority": 2,
        "contradicts": ["crucible profitability"],
    },
    {
        "id": "under_resource_force_focus",
        "pattern_name": "Under-resourcing forces agentification and focus",
        "description": "Scarcity of headcount and budget forces teams toward automation and ruthless prioritization—constraints as creative pressure, not just deprivation.",
        "core_tension": "Under-resourcing as strategy vs excuse for quality collapse.",
        "keywords": ["under-resource", "under resource", "force agentification", "blind reference", "leading indicators in fast"],
        "priority": 2,
        "contradicts": ["constraints freedom"],
    },
    {
        "id": "confidence_gap_paradox",
        "pattern_name": "Confidence gap paradox in AI adoption",
        "description": "Leaders overestimate org AI readiness while practitioners underestimate their own capability—or the reverse—creating adoption stalls that look like tool problems but are belief problems.",
        "core_tension": "Perceived readiness vs actual workflow fit.",
        "keywords": ["confidence gap", "adoption paradox", "readiness gap", "belief problem"],
        "priority": 2,
        "contradicts": [],
    },
    {
        "id": "feedback_velocity_moat",
        "pattern_name": "Feedback velocity becomes the product moat",
        "description": "When build is cheap, the org that learns fastest from usage—tight feedback loops, short cycle review—outcompetes feature copyists.",
        "core_tension": "Shipping volume vs learning rate.",
        "keywords": ["feedback velocity", "learning loop", "cycle review", "insight propagation", "pattern scanner"],
        "priority": 2,
        "contradicts": ["experimentation theater"],
    },
    {
        "id": "work_chart_over_org_chart",
        "pattern_name": "Work charts replace org charts for execution",
        "description": "Accountability maps to flows of work and outcomes, not reporting lines—especially when AI dissolves role boundaries and matrix confusion grows.",
        "core_tension": "Clear ownership vs fluid cross-functional work.",
        "keywords": ["work chart", "org chart", "flows of work", "accountability map"],
        "priority": 2,
        "contradicts": ["gm fiefdom"],
    },
]


def norm_text(s: str) -> str:
    s = re.sub(r"[^\w\s]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def obj_blob(obj: dict) -> str:
    parts = [
        obj.get("pattern_name", ""),
        obj.get("core_belief", ""),
        obj.get("operational_pattern", ""),
        obj.get("organizational_archetype", ""),
        obj.get("source_quote_or_context", ""),
        obj.get("category", ""),
    ]
    for k in (
        "hidden_assumptions",
        "pressure_scenarios",
        "failure_modes",
        "contradictions",
        "behavioral_signals",
        "emotional_political_dynamics",
        "operational_adaptations",
        "ai_era_implications",
    ):
        v = obj.get(k, [])
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
    return norm_text(" ".join(parts))


def kw_in_blob(kw: str, blob: str) -> bool:
    """Phrase or word-boundary match; avoid 'pr' matching 'product'."""
    kw = norm_text(kw)
    if len(kw) < 4:
        return False
    if " " in kw:
        return kw in blob
    return bool(re.search(rf"\b{re.escape(kw)}\b", blob))


def score_meta(obj: dict, meta: dict) -> float:
    blob = obj_blob(obj)
    score = 0.0
    for kw in meta["keywords"]:
        if kw_in_blob(kw, blob):
            score += 2.0
    name = norm_text(obj.get("pattern_name", ""))
    for kw in meta["keywords"]:
        if kw_in_blob(kw, name):
            score += 2.5
    belief = norm_text(obj.get("core_belief", ""))
    for kw in meta["keywords"][:8]:
        if kw_in_blob(kw, belief):
            score += 1.0
            break
    return score


def top_items(items: list[str], n: int = 8) -> list[str]:
    c = Counter(norm_text(x) for x in items if x)
    # return original casing from first occurrence
    seen = {}
    for x in items:
        k = norm_text(x)
        if k and k not in seen:
            seen[k] = x.strip()
    return [seen[k] for k, _ in c.most_common(n) if k in seen]


def merge_cluster(objs: list[dict], meta: dict) -> dict:
    pressures, failures, signals, contexts, adaptations, contradictions = [], [], [], [], [], []
    for o in objs:
        pressures.extend(o.get("pressure_scenarios") or [])
        failures.extend(o.get("failure_modes") or [])
        signals.extend(o.get("behavioral_signals") or [])
        contexts.extend(o.get("organizational_archetype", "") or "")
        if isinstance(contexts, str):
            contexts = [contexts]
        adaptations.extend(o.get("operational_adaptations") or [])
        contradictions.extend(o.get("contradictions") or [])

    supporting = []
    for o in objs:
        supporting.append(
            {
                "intelligence_id": o.get("intelligence_id"),
                "pattern_name": o.get("pattern_name"),
                "source_guest": o.get("source_guest"),
            }
        )

    return {
        "pattern_name": meta["pattern_name"],
        "description": meta["description"],
        "derived_from_count": len(objs),
        "supporting_objects": supporting,
        "core_tension": meta["core_tension"],
        "behavioral_signals": top_items(signals, 10),
        "pressure_behaviors": top_items(pressures, 10),
        "failure_modes": top_items(failures, 10),
        "organizational_contexts": top_items(
            [o.get("organizational_archetype", "") for o in objs], 8
        ),
        "contradicting_patterns": meta.get("contradicts", []),
        "adaptation_directions": top_items(adaptations, 10),
    }


MIN_SCORE = 3.0
MIN_PATTERN_SIZE = 4
TARGET_PATTERNS = 42


def fingerprint(obj: dict) -> set[str]:
    blob = obj_blob(obj)
    return set(re.findall(r"[a-z0-9]{4,}", blob))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_objects(objs: list[dict], k: int) -> list[list[dict]]:
    """Greedy agglomerative clustering to ~k clusters."""
    n = len(objs)
    fps = [fingerprint(o) for o in objs]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((jaccard(fps[i], fps[j]), i, j))
    pairs.sort(reverse=True)

    active = {find(i) for i in range(n)}
    for sim, i, j in pairs:
        if len(active) <= k:
            break
        if sim < 0.18:
            break
        ri, rj = find(i), find(j)
        if ri != rj:
            union(i, j)
            active = {find(x) for x in range(n)}

    groups: dict[int, list[dict]] = defaultdict(list)
    for i, obj in enumerate(objs):
        groups[find(i)].append(obj)
    return list(groups.values())


def medoid_object(members: list[dict]) -> dict:
    fps = [fingerprint(o) for o in members]
    if len(members) == 1:
        return members[0]
    best_idx, best_avg = 0, -1.0
    for i, fi in enumerate(fps):
        avg = sum(jaccard(fi, fj) for j, fj in enumerate(fps) if j != i) / (len(fps) - 1)
        if avg > best_avg:
            best_avg, best_idx = avg, i
    return members[best_idx]


def best_meta_for_object(obj: dict) -> tuple[str, float]:
    scores = [(score_meta(obj, m) * m.get("priority", 1), m["id"]) for m in META_PATTERNS]
    scores.sort(reverse=True)
    if scores[0][0] > 0:
        return scores[0][1], scores[0][0]
    # zero keyword hits: match operational pattern name to meta pattern name
    oname = norm_text(obj.get("pattern_name", ""))
    best_ratio, best_id = 0.0, scores[0][1]
    for m in META_PATTERNS:
        ratio = SequenceMatcher(None, oname, norm_text(m["pattern_name"])).ratio()
        if ratio > best_ratio:
            best_ratio, best_id = ratio, m["id"]
    return best_id, best_ratio


def assign_objects(objs: list[dict]) -> dict[str, list[dict]]:
    """Two-pass: score objects, cluster, label clusters from strong seeds."""
    obj_labels: dict[str, str] = {}
    strong: list[dict] = []
    weak: list[dict] = []

    for obj in objs:
        mid, sc = best_meta_for_object(obj)
        oid = obj.get("intelligence_id", "")
        if sc >= MIN_SCORE:
            obj_labels[oid] = mid
            strong.append(obj)
        else:
            weak.append(obj)

    # weak objects: best keyword match (even below threshold)
    for obj in weak:
        mid, _ = best_meta_for_object(obj)
        obj_labels[obj["intelligence_id"]] = mid

    clusters: dict[str, list[dict]] = defaultdict(list)
    for obj in objs:
        clusters[obj_labels[obj["intelligence_id"]]].append(obj)
    return clusters


def merge_small_clusters(
    clusters: dict[str, list[dict]], meta_by_id: dict[str, dict]
) -> dict[str, list[dict]]:
    """Fold patterns below MIN_PATTERN_SIZE into semantically best neighbor."""
    changed = True
    while changed:
        changed = False
        small = [pid for pid, m in clusters.items() if len(m) < MIN_PATTERN_SIZE]
        if not small:
            break
        for pid in small:
            members = clusters.pop(pid)
            if not members:
                continue
            target = None
            best_total = -1.0
            for tid in clusters:
                total = sum(score_meta(o, meta_by_id[tid]) for o in members)
                if total > best_total:
                    best_total = total
                    target = tid
            if target is None:
                clusters[pid] = members
                continue
            clusters[target].extend(members)
            changed = True
    return clusters


def main():
    with open(INPUT) as f:
        data = json.load(f)
    objs = data["intelligence"]
    assert len(objs) == 458, len(objs)

    meta_by_id = {m["id"]: m for m in META_PATTERNS}
    clusters = assign_objects(objs)
    clusters = merge_small_clusters(clusters, meta_by_id)

    patterns = []
    for meta in META_PATTERNS:
        members = clusters.get(meta["id"], [])
        if len(members) < MIN_PATTERN_SIZE:
            continue
        patterns.append(merge_cluster(members, meta))

    patterns.sort(key=lambda p: -p["derived_from_count"])

    name_by_id = {m["id"]: m["pattern_name"] for m in META_PATTERNS}
    for p in patterns:
        p["contradicting_patterns"] = [
            name_by_id.get(c, c) if c in name_by_id else c
            for c in p.get("contradicting_patterns", [])
        ]

    # coverage report
    assigned_ids = set()
    for p in patterns:
        for s in p["supporting_objects"]:
            assigned_ids.add(s["intelligence_id"])
    missing = [o for o in objs if o.get("intelligence_id") not in assigned_ids]

    out = {
        "schema_version": "1.0",
        "source": "reality-check-intelligence.json (458 objects)",
        "note": "User-requested normalized-intelligence compression; source file is reality-check-intelligence.json",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_object_count": 458,
        "pattern_count": len(patterns),
        "unassigned_count": len(missing),
        "patterns": patterns,
    }

    with open(OUTPUT, "w") as f:
        json.dump(out, f, indent=2)

    # flat array alias for downstream consumers
    with open(ROOT / "normalized-intelligence-patterns.compact.json", "w") as f:
        json.dump(patterns, f, separators=(",", ":"))

    print(f"Patterns: {len(patterns)}")
    print(f"Unassigned: {len(missing)}")
    print("\nTop patterns by count:")
    for p in patterns[:15]:
        print(f"  {p['derived_from_count']:3d}  {p['pattern_name'][:60]}")


if __name__ == "__main__":
    main()
