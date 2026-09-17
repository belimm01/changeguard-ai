"""Scoped Kubernetes risky-manifest-change rule over base/head content.

The rule only reads manifests. It never runs kubectl, Helm, Kustomize, Jsonnet,
admission controllers or repository scripts, and it makes no cluster calls.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from changeguard.domain.content import FileContent
from changeguard.domain.findings import RiskFinding, RiskLevel
from changeguard.domain.reports import Coverage, CoverageState
from changeguard.parsing.kubernetes import parse_kubernetes

RULE_ID = "kubernetes-risk"

_WORKLOAD_KINDS = frozenset({"Deployment", "StatefulSet"})
_SUPPORTED_KINDS = frozenset({"Deployment", "StatefulSet", "Service"})
_RISKY_SERVICE_TYPES = frozenset({"LoadBalancer", "NodePort"})

# Object identity: apiVersion, kind, namespace, name.
_ObjectKey = tuple[str, str, str, str]


@dataclass(frozen=True, slots=True)
class KubernetesRuleResult:
    findings: tuple[RiskFinding, ...]
    coverage: tuple[Coverage, ...]


def evaluate_kubernetes_change(
    path: str, base: FileContent | None, head: FileContent | None
) -> KubernetesRuleResult:
    if base is None or head is None:
        return _coverage_only(
            path, CoverageState.PARTIAL, "missing base or head content"
        )

    parsed_base = parse_kubernetes(base.text)
    parsed_head = parse_kubernetes(head.text)
    for parsed in (parsed_base, parsed_head):
        if parsed.documents is None:
            state = (
                CoverageState.UNSUPPORTED
                if parsed.problem is not None and parsed.problem.name == "TEMPLATE"
                else CoverageState.PARTIAL
            )
            return _coverage_only(path, state, str(parsed.problem))

    assert parsed_base.documents is not None
    assert parsed_head.documents is not None
    base_objects = _index(parsed_base.documents)
    head_objects = _index(parsed_head.documents)

    findings: list[RiskFinding] = []
    unsupported: set[str] = set()

    for key in sorted(base_objects.keys() | head_objects.keys()):
        _, kind, _, _ = key
        if kind not in _SUPPORTED_KINDS:
            unsupported.add(kind)
            continue
        base_doc = base_objects.get(key)
        head_doc = head_objects.get(key)
        if base_doc is None or head_doc is None:
            continue
        name = f"{kind}/{key[2]}/{key[3]}"
        if kind in _WORKLOAD_KINDS:
            findings.extend(_workload_findings(path, name, base_doc, head_doc))
        elif kind == "Service":
            findings.extend(_service_findings(path, name, base_doc, head_doc))

    coverage = (
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.SUPPORTED,
            reason="compared workload image tags, security context and service exposure",
        ),
    ) + tuple(
        Coverage(
            rule_id=RULE_ID,
            target=path,
            state=CoverageState.UNSUPPORTED,
            reason=f"unsupported Kubernetes kind not evaluated: {kind}",
        )
        for kind in sorted(unsupported)
    )
    return KubernetesRuleResult(findings=tuple(findings), coverage=coverage)


def _coverage_only(
    path: str, state: CoverageState, reason: str
) -> KubernetesRuleResult:
    return KubernetesRuleResult(
        findings=(),
        coverage=(Coverage(rule_id=RULE_ID, target=path, state=state, reason=reason),),
    )


def _index(
    documents: tuple[Mapping[str, object], ...],
) -> dict[_ObjectKey, Mapping[str, object]]:
    result: dict[_ObjectKey, Mapping[str, object]] = {}
    for doc in documents:
        api_version = doc.get("apiVersion")
        kind = doc.get("kind")
        metadata = doc.get("metadata")
        if not isinstance(api_version, str) or not isinstance(kind, str):
            continue
        namespace = "default"
        name = ""
        if isinstance(metadata, Mapping):
            raw_ns = metadata.get("namespace")
            raw_name = metadata.get("name")
            if isinstance(raw_ns, str):
                namespace = raw_ns
            if isinstance(raw_name, str):
                name = raw_name
        if not name:
            continue
        result[(api_version, kind, namespace, name)] = doc
    return result


def _workload_findings(
    path: str,
    name: str,
    base_doc: Mapping[str, object],
    head_doc: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    base_containers = _containers(base_doc)
    head_containers = _containers(head_doc)
    for container in sorted(base_containers.keys() & head_containers.keys()):
        findings.extend(
            _image_findings(
                path,
                name,
                container,
                base_containers[container],
                head_containers[container],
            )
        )
        findings.extend(
            _security_findings(
                path,
                name,
                container,
                base_containers[container],
                head_containers[container],
            )
        )
    findings.extend(_pod_host_findings(path, name, base_doc, head_doc))
    return tuple(findings)


def _image_findings(
    path: str,
    name: str,
    container: str,
    base_container: Mapping[str, object],
    head_container: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    base_image = base_container.get("image")
    head_image = head_container.get("image")
    if not isinstance(base_image, str) or not isinstance(head_image, str):
        return ()
    if base_image == head_image:
        return ()
    head_tag = _image_tag(head_image)
    if head_tag in (None, "latest"):
        return (
            _finding(
                path,
                RiskLevel.HIGH,
                f"container {container} image tag changed to latest in {name}",
            ),
        )
    return (
        _finding(
            path,
            RiskLevel.MEDIUM,
            f"container {container} image changed from {base_image} "
            f"to {head_image} in {name}",
        ),
    )


def _security_findings(
    path: str,
    name: str,
    container: str,
    base_container: Mapping[str, object],
    head_container: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    findings: list[RiskFinding] = []
    base_ctx = _mapping(base_container.get("securityContext"))
    head_ctx = _mapping(head_container.get("securityContext"))
    for field, label in (
        ("privileged", "privileged"),
        ("allowPrivilegeEscalation", "privilege escalation"),
    ):
        if head_ctx.get(field) is True and base_ctx.get(field) is not True:
            findings.append(
                _finding(
                    path,
                    RiskLevel.HIGH,
                    f"container {container} enabled {label} in {name}",
                )
            )
    return tuple(findings)


def _pod_host_findings(
    path: str,
    name: str,
    base_doc: Mapping[str, object],
    head_doc: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    base_pod = _pod_spec(base_doc)
    head_pod = _pod_spec(head_doc)
    findings: list[RiskFinding] = []
    for field, label in (
        ("hostNetwork", "host network"),
        ("hostPID", "host PID"),
        ("hostIPC", "host IPC"),
    ):
        if head_pod.get(field) is True and base_pod.get(field) is not True:
            findings.append(
                _finding(path, RiskLevel.HIGH, f"enabled {label} in {name}")
            )
    return tuple(findings)


def _service_findings(
    path: str,
    name: str,
    base_doc: Mapping[str, object],
    head_doc: Mapping[str, object],
) -> tuple[RiskFinding, ...]:
    base_type = _mapping(base_doc.get("spec")).get("type")
    head_type = _mapping(head_doc.get("spec")).get("type")
    if (
        isinstance(head_type, str)
        and head_type in _RISKY_SERVICE_TYPES
        and base_type != head_type
    ):
        return (
            _finding(
                path,
                RiskLevel.HIGH,
                f"service type changed to {head_type} in {name}",
            ),
        )
    return ()


def _pod_spec(doc: Mapping[str, object]) -> Mapping[str, object]:
    template = _mapping(_mapping(doc.get("spec")).get("template"))
    return _mapping(template.get("spec"))


def _containers(doc: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    raw = _pod_spec(doc).get("containers")
    result: dict[str, Mapping[str, object]] = {}
    if not isinstance(raw, list):
        return result
    for container in raw:
        if isinstance(container, Mapping):
            name = container.get("name")
            if isinstance(name, str):
                result[name] = container
    return result


def _image_tag(image: str) -> str | None:
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return last_segment.rsplit(":", 1)[-1]
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _finding(path: str, level: RiskLevel, summary: str) -> RiskFinding:
    return RiskFinding(
        rule_id=RULE_ID,
        level=level,
        summary=summary,
        evidence_paths=(path,),
    )
