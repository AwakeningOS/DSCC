"""Generate synthetic signed examples in a caller-provided temporary DSCC node.

No real experiences or performance measurements are used. No keys are exported.
"""
from __future__ import annotations

from copy import deepcopy
from dscc.models import manifest

PROFILE = "dscc.atlas/0.1-draft"
PRODUCER = {"id": "dscc.synthetic-fixture", "revision": "1"}


def build(node):
    examples, cids = {}, {}
    narratives = {
        "gpu": ["Reduce arithmetic in an inference kernel.", "Overall delay changes little.",
                "Inspect time spent moving data.", "Try reducing transfers.", "Record the new latency trace."],
        "model": ["Increase repeated model layers.", "The target task changes little.",
                  "Inspect whether required input reaches later stages.", "Try another information path.", "Record the new evaluation."],
        "relationship": ["Suggest meeting more often.", "The narrator still reports misunderstandings.",
                         "Ask what each person prefers, without inferring hidden motives.", "Both agree to try a different plan.", "Record each person's account separately."],
        "trial": ["Try an idea inspired by another exploration.", "Inspect the first observation.",
                  "Revise the interpretation.", "Run the agreed follow-up.", "The fixture leaves usefulness unresolved."],
    }
    roles = ["action", "observation", "revision", "action", "observation"]
    for name, events in narratives.items():
        src = node.record(manifest("MemoryCapsule", "Synthetic source: " + name,
                                   {"synthetic": True, "events": events}, license="MIT"))
        nodes = [{"id": f"n{i}", "role": role, "text": events[i],
                  "stage": "performed" if role == "action" else "not_applicable",
                  "origin": "synthetic", "sources": [{"cid": src, "pointer": f"/body/data/events/{i}"}]}
                 for i, role in enumerate(roles)]
        links = [{"id": f"e{i}", "from": f"n{i}", "to": f"n{i+1}", "relation": "precedes",
                  "origin": "synthetic", "sources": [{"cid": src, "pointer": "/body/data/events"}]}
                 for i in range(len(nodes)-1)]
        ep = {"schema": PROFILE, "type": "Episode", "title": "Synthetic exploration: " + name,
              "topic_tags": [name], "goal": "Illustrate a record contract, not demonstrate a real outcome.",
              "conditions": ["Entirely fictional fixture; not evidence of transfer efficacy."],
              "nodes": nodes, "links": links, "open_questions": ["Would this analogy help in a real task?"],
              "extractor": PRODUCER, "extensions": {"dscc:synthetic": True}}
        examples[name] = ep
        cids[name] = node.record(manifest("MemoryCapsule", ep["title"], {"atlas": ep}, parents=[src], license="MIT"))
    bridge = {"schema": PROFILE, "type": "Bridge", "source_episode": cids["gpu"], "target_episode": cids["model"],
              "mapping": [{"from": f"n{i}", "to": f"n{i}"} for i in range(5)],
              "matched_edges": [{"from": f"e{i}", "to": f"e{i}"} for i in range(4)],
              "common_structure": "Revisit an assumed constraint after an intervention has little observed effect.",
              "gaps": ["The actual mechanisms and outcome measures differ."],
              "next_question": "What observation could distinguish the candidate constraints?",
              "generator": PRODUCER, "extensions": {"dscc:synthetic": True}}
    examples["bridge"] = bridge
    cids["bridge"] = node.record(manifest("EvidenceLink", "Synthetic analogy proposal", {"atlas": bridge},
                                         parents=[cids["gpu"], cids["model"]], license="MIT"))
    assessment = {"schema": PROFILE, "type": "TransferAssessment", "bridge": cids["bridge"],
                  "trial_episode": cids["trial"], "verdict": "inconclusive", "method": "Synthetic contract exercise only.",
                  "limitations": ["No real transfer was tested."], "origin": "synthetic",
                  "sources": [{"cid": cids["trial"], "pointer": "/body/data/atlas"}],
                  "evaluator": PRODUCER, "extensions": {"dscc:synthetic": True}}
    examples["assessment"] = assessment
    pattern = deepcopy(examples["gpu"])
    motif = {"schema": PROFILE, "type": "Motif", "title": "Synthetic shared path pattern",
             "nodes": pattern["nodes"], "links": pattern["links"],
             "members": [{"episode": cids[n], "mapping": [{"from": f"n{i}", "to": f"n{i}"} for i in range(5)]}
                         for n in ("gpu", "model", "relationship")],
             "counterexamples": [], "conditions": ["Fictional inputs chosen to illustrate a common path shape."],
             "unresolved_differences": ["Matching topology does not establish matching mechanisms."],
             "generator": PRODUCER, "extensions": {"dscc:synthetic": True}}
    examples["motif"] = motif
    return examples, cids
