"""
create_diagrams.py
------------------
Generates publication-grade architectural and security flow diagrams for SecureCode AI.
Outputs high-resolution PNGs for embedding directly into the academic DOCX and PDF documents.
"""

import os
os.environ["MPLCONFIGDIR"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mplcache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def generate_architecture_diagram(output_path: str):
    """Generates the comprehensive SecureCode AI System Architecture diagram."""
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Colors (Navy Blue Academic Theme)
    c_navy = "#1B365D"
    c_blue = "#0969DA"
    c_light_blue = "#EBF3FA"
    c_slate = "#F0F4F8"
    c_green = "#1A7F37"
    c_red = "#CF222E"
    c_amber = "#9A6700"
    c_dark = "#24292E"

    # Title Banner
    title_box = patches.FancyBboxPatch((4, 91), 92, 7.5, boxstyle="round,pad=1.0",
                                       facecolor=c_navy, edgecolor=c_blue, linewidth=2)
    ax.add_patch(title_box)
    ax.text(50, 95.8, "SECURECODE AI - MULTI-TIER DEFENSE-IN-DEPTH ARCHITECTURE",
            fontsize=12, fontweight="bold", ha="center", va="center", color="#FFFFFF")
    ax.text(50, 92.5, "Domain-Specific AI Agent for Secure Code Review & Risk Detection | Unit 5 (CO-5)",
            fontsize=8.5, ha="center", va="center", color="#D0D7DE")

    # Layer 1: Ingestion & Input Boundary Gate (Left Column / Top Entry)
    l1_box = patches.FancyBboxPatch((4, 69), 28, 19, boxstyle="round,pad=1.0",
                                    facecolor=c_light_blue, edgecolor=c_navy, linewidth=1.8)
    ax.add_patch(l1_box)
    ax.text(18, 85, "LAYER 1: INPUT GATEWAY", fontsize=9.5, fontweight="bold", ha="center", color=c_navy)
    ax.text(18, 77, "• File Size Limit (<512 KB)\n• UTF-8 / Binary Check\n• Path Traversal Blocker\n• AST Syntax Verification\n• Line Length & Count Caps",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Layer 2: Untrusted Content & Injection Detector (Middle Column / Top Entry)
    l2_box = patches.FancyBboxPatch((36, 69), 28, 19, boxstyle="round,pad=1.0",
                                    facecolor="#FFF8E7", edgecolor=c_amber, linewidth=1.8)
    ax.add_patch(l2_box)
    ax.text(50, 85, "LAYER 2: INJECTION DETECTOR", fontsize=9.5, fontweight="bold", ha="center", color=c_amber)
    ax.text(50, 77, "• Comment Tokenizer\n• Jailbreak Signatures\n• Override Filter ('ignore rules')\n• Exfiltration Trigger Detection\n• Threat Scoring (0.0 - 1.0)",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Layer 3: Static Analysis Engines (Right Column / Top Entry)
    l3_box = patches.FancyBboxPatch((68, 69), 28, 19, boxstyle="round,pad=1.0",
                                    facecolor=c_slate, edgecolor=c_blue, linewidth=1.8)
    ax.add_patch(l3_box)
    ax.text(82, 85, "LAYER 3: STATIC ANALYZERS", fontsize=9.5, fontweight="bold", ha="center", color=c_blue)
    ax.text(82, 77, "• SecretScanner (Regex/Entropy)\n• Fake AWS/Stripe Keys\n• AST Dangerous Sinks (eval/exec)\n• OS Shell Command Sinks\n• SQL Injection Formatting",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Connecting Arrows to Central Orchestration Engine
    ax.annotate("", xy=(50, 61), xytext=(18, 69), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))
    ax.annotate("", xy=(50, 61), xytext=(50, 69), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))
    ax.annotate("", xy=(50, 61), xytext=(82, 69), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))

    # Central Core: SecureCodeAgent Orchestrator
    core_box = patches.FancyBboxPatch((12, 45), 76, 16, boxstyle="round,pad=1.2",
                                      facecolor=c_navy, edgecolor=c_blue, linewidth=2.5)
    ax.add_patch(core_box)
    ax.text(50, 56.5, "CENTRAL ORCHESTRATOR: SecureCodeAgent (agent.py)", fontsize=11, fontweight="bold",
            ha="center", va="center", color="#FFFFFF")
    ax.text(50, 50, "Pydantic State Management • Severity Tier Aggregation (CRITICAL / HIGH / MEDIUM / LOW)\n"
                     "Automated Incident Containment • Defense-in-Depth Coordination • Zero External API Vulnerability",
            fontsize=8.2, ha="center", va="center", color="#EBF3FA")

    # Arrows to Lower Control Layers
    ax.annotate("", xy=(20, 37), xytext=(32, 45), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))
    ax.annotate("", xy=(50, 37), xytext=(50, 45), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))
    ax.annotate("", xy=(80, 37), xytext=(68, 45), arrowprops=dict(arrowstyle="->", lw=1.6, color=c_navy))

    # Lower Left: Least Privilege & Tool Dispatcher
    lp_box = patches.FancyBboxPatch((4, 18), 28, 19, boxstyle="round,pad=1.0",
                                    facecolor=c_slate, edgecolor=c_blue, linewidth=1.8)
    ax.add_patch(lp_box)
    ax.text(18, 33.5, "LEAST PRIVILEGE GATE", fontsize=9.5, fontweight="bold", ha="center", color=c_blue)
    ax.text(18, 25.5, "• Role-Based Access Control\n• Tool Registration Registry\n• Parameter Type Validation\n• Unauthorized Caller Block\n• SimulatedOutboundTool Gate",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Lower Middle: Human-in-the-Loop Approval Manager
    hitl_box = patches.FancyBboxPatch((36, 18), 28, 19, boxstyle="round,pad=1.0",
                                      facecolor="#FDF2F2", edgecolor=c_red, linewidth=1.8)
    ax.add_patch(hitl_box)
    ax.text(50, 33.5, "HUMAN APPROVAL GATE", fontsize=9.5, fontweight="bold", ha="center", color=c_red)
    ax.text(50, 25.5, "• Mandatory Outbound Review\n• Sanitized Payload Preview\n• Zero-Trust Default Denial\n• Auto-Deny on Prompt Injection\n• Ephemeral Auth Token",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Lower Right: Output Guard & Secret Redaction
    og_box = patches.FancyBboxPatch((68, 18), 28, 19, boxstyle="round,pad=1.0",
                                    facecolor="#F0FFF4", edgecolor=c_green, linewidth=1.8)
    ax.add_patch(og_box)
    ax.text(82, 33.5, "OUTPUT GUARD LAYER", fontsize=9.5, fontweight="bold", ha="center", color=c_green)
    ax.text(82, 25.5, "• Automatic Secret Redaction\n• Mask [REDACTED_API_KEY]\n• Schema Integrity Validation\n• Strip Injection Artifacts\n• Markdown Report Builder",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    # Bottom Foundation: Tamper-Evident Audit Trail
    audit_box = patches.FancyBboxPatch((4, 2), 92, 12, boxstyle="round,pad=1.0",
                                       facecolor="#F9FAFB", edgecolor=c_navy, linewidth=1.8)
    ax.add_patch(audit_box)
    ax.text(50, 10, "CROSS-CUTTING AUDIT INFRASTRUCTURE: AuditLogger (audit_logger.py)",
            fontsize=10, fontweight="bold", ha="center", va="center", color=c_navy)
    ax.text(50, 5.5, "Immutable JSONL Log (outputs/audit_log.jsonl) • Human-Readable Plaintext Audit Trail (outputs/audit_trail.log)\n"
                     "Complete Event Telemetry: Validations, Injection Detections, Tool Blocks, Redactions, and Approval Decisions",
            fontsize=7.8, ha="center", va="center", color=c_dark)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Architecture diagram generated: {output_path}")


def generate_workflow_diagram(output_path: str):
    """Generates the step-by-step SecureCode AI agent execution pipeline flowchart."""
    fig, ax = plt.subplots(figsize=(10, 7.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    c_navy = "#1B365D"
    c_blue = "#0969DA"
    c_green = "#1A7F37"
    c_red = "#CF222E"
    c_amber = "#9A6700"

    # Header
    hdr = patches.FancyBboxPatch((5, 91), 90, 7, boxstyle="round,pad=1.0",
                                 facecolor=c_navy, edgecolor=c_blue, linewidth=2)
    ax.add_patch(hdr)
    ax.text(50, 94.5, "SECURECODE AI - END-TO-END EXECUTION WORKFLOW & DEFENSE PIPELINE",
            fontsize=11, fontweight="bold", ha="center", va="center", color="#FFFFFF")

    steps = [
        ("1. Input Ingestion & Boundary Check", "File size (<512KB), UTF-8 encoding, directory bounds, and AST syntax validity", 81, c_blue, "#EBF3FA"),
        ("2. Untrusted Comment & Prompt Injection Scan", "Tokenizes comments/docstrings; flags override keywords ('ignore rules') & exfil triggers", 67, c_amber, "#FFF8E7"),
        ("3. Static Secret & AST Vulnerability Analysis", "Detects hardcoded cloud keys (AKIA/sk_live) and dangerous sinks (eval, os.system, SQLi)", 53, c_navy, "#F0F4F8"),
        ("4. Threat Classification & Tool-Call Validation", "Assigns CRITICAL/HIGH/MED/LOW risk tiers; validates caller role permissions (RBAC)", 39, c_navy, "#F0F4F8"),
        ("5. Human-in-the-Loop Outbound Gate", "Intercepts simulated outbound dispatch; auto-denies if injection is suspected or unapproved", 25, c_red, "#FDF2F2"),
        ("6. Output Sanitization & Audit Archival", "Masks credentials to [REDACTED], verifies report schema, writes JSONL & text audit trail", 11, c_green, "#F0FFF4"),
    ]

    for title, desc, y_pos, border_col, bg_col in steps:
        box = patches.FancyBboxPatch((10, y_pos - 4), 80, 8.5, boxstyle="round,pad=1.0",
                                     facecolor=bg_col, edgecolor=border_col, linewidth=1.8)
        ax.add_patch(box)
        ax.text(14, y_pos + 1.5, title, fontsize=9.5, fontweight="bold", ha="left", va="center", color=border_col)
        ax.text(14, y_pos - 1.5, desc, fontsize=8.0, ha="left", va="center", color="#24292E")

        # Down arrow to next step (except last)
        if y_pos > 15:
            ax.annotate("", xy=(50, y_pos - 5.5), xytext=(50, y_pos - 4),
                        arrowprops=dict(arrowstyle="->", lw=2, color=c_navy))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Workflow diagram generated: {output_path}")


def generate_three_ingredients_diagram(output_path: str):
    """Generates the Three Ingredients Data Exfiltration Risk and Defense Diagram."""
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    c_navy = "#1B365D"
    c_blue = "#0969DA"
    c_red = "#CF222E"
    c_green = "#1A7F37"
    c_amber = "#9A6700"

    # Header
    hdr = patches.FancyBboxPatch((5, 91), 90, 7.5, boxstyle="round,pad=1.0",
                                 facecolor=c_navy, edgecolor=c_blue, linewidth=2)
    ax.add_patch(hdr)
    ax.text(50, 94.7, "THE THREE INGREDIENTS OF AI AGENT DATA EXFILTRATION",
            fontsize=11.5, fontweight="bold", ha="center", va="center", color="#FFFFFF")

    # Three Ingredient Boxes
    # 1. Private Data
    b1 = patches.FancyBboxPatch((4, 60), 28, 24, boxstyle="round,pad=1.2",
                                facecolor="#F0F4F8", edgecolor=c_navy, linewidth=2)
    ax.add_patch(b1)
    ax.text(18, 79, "INGREDIENT A:\nPRIVATE DATA", fontsize=10, fontweight="bold", ha="center", va="center", color=c_navy)
    ax.text(18, 68, "• Synthetic Cloud Keys\n  (AWS AKIA...)\n• Stripe API Secret\n  (sk_live_...)\n• Internal DB URIs\n• Proprietary Code",
            fontsize=7.8, ha="center", va="center", color="#24292E")

    # 2. Untrusted Content
    b2 = patches.FancyBboxPatch((36, 60), 28, 24, boxstyle="round,pad=1.2",
                                facecolor="#FFF8E7", edgecolor=c_amber, linewidth=2)
    ax.add_patch(b2)
    ax.text(50, 79, "INGREDIENT B:\nUNTRUSTED CONTENT", fontsize=10, fontweight="bold", ha="center", va="center", color=c_amber)
    ax.text(50, 68, "• Malicious Comments\n• Prompt Injection Strings\n• 'Ignore previous rules'\n• Hidden Exfil Commands\n• External Code PRs",
            fontsize=7.8, ha="center", va="center", color="#24292E")

    # 3. Outbound Transmission
    b3 = patches.FancyBboxPatch((68, 60), 28, 24, boxstyle="round,pad=1.2",
                                facecolor="#FDF2F2", edgecolor=c_red, linewidth=2)
    ax.add_patch(b3)
    ax.text(82, 79, "INGREDIENT C:\nOUTBOUND CHANNEL", fontsize=10, fontweight="bold", ha="center", va="center", color=c_red)
    ax.text(82, 68, "• Webhook Dispatch\n• Email Reporting Tool\n• HTTP POST Request\n• Remote File Upload\n• External DNS Queries",
            fontsize=7.8, ha="center", va="center", color="#24292E")

    # Plus signs between ingredients
    ax.text(33.5, 72, "+", fontsize=20, fontweight="bold", ha="center", va="center", color=c_navy)
    ax.text(65.5, 72, "+", fontsize=20, fontweight="bold", ha="center", va="center", color=c_navy)

    # Danger Convergence Alert
    danger_box = patches.FancyBboxPatch((15, 38), 70, 14, boxstyle="round,pad=1.2",
                                        facecolor="#FFF5F5", edgecolor=c_red, linewidth=2)
    ax.add_patch(danger_box)
    ax.text(50, 47, "COMBINED SYSTEMIC THREAT: COVERT DATA EXFILTRATION",
            fontsize=10.5, fontweight="bold", ha="center", va="center", color=c_red)
    ax.text(50, 42, "If all 3 ingredients coincide without controls, an untrusted comment hijacks agent logic,\n"
                     "reads private synthetic credentials, and triggers outbound dispatch to an attacker server.",
            fontsize=8.0, ha="center", va="center", color="#333333")

    # Arrows converging to defense shield
    ax.annotate("", xy=(50, 31), xytext=(50, 38), arrowprops=dict(arrowstyle="->", lw=2, color=c_red))

    # Defense Shield Layer
    defense_box = patches.FancyBboxPatch((8, 5), 84, 25, boxstyle="round,pad=1.5",
                                         facecolor="#F0FFF4", edgecolor=c_green, linewidth=2.5)
    ax.add_patch(defense_box)
    ax.text(50, 25, "SECURECODE AI DEFENSE SHIELD - THWARTING THE ATTACK CHAIN",
            fontsize=11, fontweight="bold", ha="center", va="center", color=c_green)
    ax.text(50, 15, "1. Prompt Injection Detector: Flags malicious comments & quarantines instructions (Score: 0.95)\n"
                     "2. Least Privilege (RBAC): Denies untrusted executor access to SimulatedOutboundTool\n"
                     "3. Human-in-the-Loop Gate: Mandatory human approval + automatic refusal on injection alerts\n"
                     "4. Secret Redaction & Output Guard: Plaintext keys masked to [REDACTED_API_KEY] everywhere\n"
                     "RESULT: 0 bytes exfiltrated, attack neutralized, complete audit logged in outputs/audit_log.jsonl",
            fontsize=8.2, ha="center", va="center", color="#1B365D")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Three ingredients diagram generated: {output_path}")


if __name__ == "__main__":
    generate_architecture_diagram("architecture_diagram.png")
    generate_workflow_diagram("workflow_diagram.png")
    generate_three_ingredients_diagram("three_ingredients_diagram.png")

