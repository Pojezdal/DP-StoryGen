from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


NodeKind = Literal[
    "surface_observation",
    "followup_observation",
    "suspect_action",
    "incorrect_assumption",
    "correct_assumption",
    "conclusion",
]


EdgeRelation = Literal["supports", "contradicts", "refines", "replaces", "triggers"]
BranchOutcome = Literal["dead_end", "confirmed_culprit", "open"]


class ClueNode(BaseModel):
    node_id: str = Field(
        description="Unique node identifier in form N<number> (example: N1)",
        pattern=r"^N[0-9]+$",
    )
    label: str = Field(description="Short node label")
    kind: NodeKind = Field(description="Node type in the reasoning graph")
    statement: str = Field(
        description=(
            "Concrete content of the node: an observed fact or an interpretation/assumption"
        )
    )
    acquisition_path: str = Field(
        description=(
            "How this node became available (scene observation, interview, consent search, "
            "warrant search, routine record query, voluntary handover, etc.)"
        )
    )
    derived_from: list[str] = Field(
        default_factory=list,
        description=(
            "Node IDs this node is based on. Must be empty only for surface_observation nodes."
        ),
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence for this node in the investigation state",
    )
    suspect_effects: list[str] = Field(
        default_factory=list,
        description="How this node changes suspicion for named suspects",
    )
    source_anchor: Optional[str] = Field(
        default=None,
        description="Optional anchor quote or concise reference to source material",
    )
    action_by_suspect: Optional[str] = Field(
        default=None,
        description="Required when kind=suspect_action: name of suspect performing the action",
    )
    action_goal: Optional[str] = Field(
        default=None,
        description="For suspect_action nodes: short intent (conceal, redirect, panic, cooperate, etc.)",
    )
    replaces_node_id: Optional[str] = Field(
        default=None,
        description="If this node corrects/replaces an older assumption, point to that node ID",
    )


class ClueEdge(BaseModel):
    source_node_id: str = Field(pattern=r"^N[0-9]+$")
    target_node_id: str = Field(pattern=r"^N[0-9]+$")
    relation: EdgeRelation = Field(
        description="How the source node relates to target node"
    )
    rationale: str = Field(description="Short explanation for the relation")


class SuspectBranch(BaseModel):
    suspect_name: str = Field(description="Suspect name exactly as used in story data")
    entry_node_ids: list[str] = Field(
        default_factory=list,
        description="Early nodes that make this suspect meaningfully plausible",
    )
    key_assumption_node_ids: list[str] = Field(
        default_factory=list,
        description="Assumption nodes used while this branch is active",
    )
    suspect_statement_node_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Nodes based primarily on what the suspect claims (confession, explanation, denial, alibi details)"
        ),
    )
    verification_node_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Independent corroboration/contradiction nodes (forensic, witness, records, physical checks)"
        ),
    )
    outcome: BranchOutcome = Field(
        description="How this suspect branch resolves in the investigation",
    )
    resolution_node_id: Optional[str] = Field(
        default=None,
        description="Node that resolves this branch (dead-end, confirmation, or open status)",
    )
    notes: str = Field(
        default="",
        description="Short explanation of branch trajectory",
    )



class ClueGraph(BaseModel):
    total_phases: int = Field(
        default=4,
        ge=3,
        description="Total phase count used by the clue graph",
    )
    nodes: list[ClueNode] = Field(
        default_factory=list,
        description="All clue and inference nodes in the graph",
    )
    edges: list[ClueEdge] = Field(
        default_factory=list,
        description="Directed reasoning links between nodes",
    )
    primary_proof_chain_node_ids: list[str] = Field(
        default_factory=list,
        description="Ordered node IDs that form the final proof chain",
    )
    final_solution_node_ids: list[str] = Field(
        default_factory=list,
        description="Node IDs that encode the final true model",
    )
    suspect_branches: list[SuspectBranch] = Field(
        default_factory=list,
        description="Per-suspect branch tracking including dead ends and culprit confirmation",
    )
    unused_trace_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Traces from ground truth or suspect briefs that were intentionally not used "
            "as major clue drivers"
        ),
    )

    @model_validator(mode="after")
    def _validate_graph(self) -> "ClueGraph":
        errors: list[str] = []
        warnings: list[str] = []

        def _add_error(message: str) -> None:
            errors.append(message)

        def _add_warning(message: str) -> None:
            warnings.append(message)

        node_ids = [node.node_id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            _add_error("All node_id values must be unique")

        node_map = {node.node_id: node for node in self.nodes}
        outgoing_edges: dict[str, list[ClueEdge]] = {}
        incoming_edges: dict[str, list[ClueEdge]] = {}

        for node in self.nodes:
            if node.kind == "surface_observation":
                if node.derived_from:
                    _add_error(
                        f"{node.node_id}: surface_observation must not have derived_from references"
                    )
            else:
                if not node.derived_from:
                    _add_error(
                        f"{node.node_id}: non-surface nodes must reference prior nodes in derived_from"
                    )

            for dep in node.derived_from:
                dep_node = node_map.get(dep)
                if dep_node is None:
                    _add_error(
                        f"{node.node_id}: derived_from contains unknown node id {dep}"
                    )
                    continue
                if dep == node.node_id:
                    _add_error(f"{node.node_id}: node cannot derive from itself")

            if node.replaces_node_id:
                replaced = node_map.get(node.replaces_node_id)
                if replaced is None:
                    _add_error(
                        f"{node.node_id}: replaces_node_id points to unknown node"
                    )
                elif replaced.kind not in ("incorrect_assumption", "correct_assumption"):
                    _add_error(
                        f"{node.node_id}: replaces_node_id must reference an assumption node"
                    )

            if node.kind == "correct_assumption" and not node.replaces_node_id:
                _add_error(
                    f"{node.node_id}: correct_assumption must set replaces_node_id"
                )

            if node.kind == "suspect_action":
                if not node.action_by_suspect:
                    _add_error(
                        f"{node.node_id}: suspect_action must set action_by_suspect"
                    )
                if not node.action_goal:
                    _add_warning(
                        f"{node.node_id}: suspect_action should set action_goal for better interpretability"
                    )

        for edge in self.edges:
            if edge.source_node_id not in node_map:
                _add_error(
                    f"Edge source {edge.source_node_id} does not exist in nodes"
                )
            if edge.target_node_id not in node_map:
                _add_error(
                    f"Edge target {edge.target_node_id} does not exist in nodes"
                )
            outgoing_edges.setdefault(edge.source_node_id, []).append(edge)
            incoming_edges.setdefault(edge.target_node_id, []).append(edge)

        for node_id in self.primary_proof_chain_node_ids:
            if node_id not in node_map:
                _add_error(
                    f"primary_proof_chain_node_ids contains unknown node id {node_id}"
                )

        for node_id in self.final_solution_node_ids:
            if node_id not in node_map:
                _add_error(
                    f"final_solution_node_ids contains unknown node id {node_id}"
                )

        culprit_branches = 0
        dead_end_branches = 0
        for branch in self.suspect_branches:
            for node_id in (
                branch.entry_node_ids
                + branch.key_assumption_node_ids
                + branch.suspect_statement_node_ids
                + branch.verification_node_ids
            ):
                if node_id not in node_map:
                    _add_error(
                        f"Suspect branch for {branch.suspect_name} references unknown node id {node_id}"
                    )

            if branch.resolution_node_id and branch.resolution_node_id not in node_map:
                _add_error(
                    f"Suspect branch for {branch.suspect_name} has unknown resolution_node_id"
                )

            if branch.outcome in ("dead_end", "confirmed_culprit") and not branch.resolution_node_id:
                _add_error(
                    f"Suspect branch for {branch.suspect_name} with outcome {branch.outcome} must set resolution_node_id"
                )

            if branch.outcome == "confirmed_culprit":
                culprit_branches += 1
            if branch.outcome == "dead_end":
                dead_end_branches += 1

            if branch.outcome == "dead_end":
                if len(branch.key_assumption_node_ids) < 2:
                    _add_error(
                        f"Suspect branch for {branch.suspect_name} dead_end should include at least two assumption nodes"
                    )
                if not branch.suspect_statement_node_ids:
                    _add_error(
                        f"Suspect branch for {branch.suspect_name} dead_end must include suspect_statement_node_ids"
                    )
                if not branch.verification_node_ids:
                    _add_error(
                        f"Suspect branch for {branch.suspect_name} dead_end must include verification_node_ids"
                    )
                if branch.resolution_node_id and branch.resolution_node_id in branch.suspect_statement_node_ids:
                    _add_error(
                        f"Suspect branch for {branch.suspect_name} dead_end cannot resolve directly on suspect statement alone"
                    )

        if self.suspect_branches:
            if culprit_branches != 1:
                _add_error(
                    "suspect_branches must include exactly one confirmed_culprit outcome"
                )
            if dead_end_branches < 2:
                _add_error(
                    "suspect_branches must include at least two dead_end outcomes"
                )

        suspect_action_ids = [n.node_id for n in self.nodes if n.kind == "suspect_action"]
        if not suspect_action_ids:
            _add_warning(
                "No suspect_action nodes present: graph may feel static and less dynamically reactive"
            )
        else:
            triggered_actions = 0
            action_to_consequence = 0
            action_chain_links = 0

            for node_id in suspect_action_ids:
                incoming = incoming_edges.get(node_id, [])
                outgoing = outgoing_edges.get(node_id, [])

                if incoming:
                    triggered_actions += 1

                if any(
                    node_map.get(edge.target_node_id)
                    and node_map[edge.target_node_id].kind in (
                        "followup_observation",
                        "incorrect_assumption",
                        "correct_assumption",
                        "conclusion",
                    )
                    for edge in outgoing
                ):
                    action_to_consequence += 1

                if any(
                    node_map.get(edge.target_node_id)
                    and node_map[edge.target_node_id].kind == "suspect_action"
                    for edge in outgoing
                ):
                    action_chain_links += 1

            if triggered_actions < len(suspect_action_ids):
                _add_warning(
                    "Some suspect_action nodes are not clearly triggered by prior graph events"
                )

            if action_to_consequence == 0:
                _add_warning(
                    "suspect_action nodes do not produce downstream evidence/inference consequences"
                )

            if action_chain_links == 0:
                _add_warning(
                    "No suspect_action -> suspect_action chain found; consider adding cascading reactions"
                )

        if errors:
            print("[ClueGraph validation] Found validation issues:")
            for err in errors:
                print(f"- {err}")

        if warnings:
            print("[ClueGraph validation] Advisory warnings:")
            for warning in warnings:
                print(f"- {warning}")

        return self
