import textwrap
from pathlib import Path

from changeguard.domain.content import FileContent, Revision
from changeguard.domain.findings import RiskLevel
from changeguard.domain.reports import CoverageState
from changeguard.rules.kubernetes import (
    RULE_ID,
    KubernetesRuleResult,
    evaluate_kubernetes_change,
)

_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "kubernetes"


def _content(name: str, revision: Revision) -> FileContent:
    text = (_FIXTURES / name).read_text()
    return FileContent(sha=name, text=text, revision=revision, size=len(text.encode()))


def _inline(text: str, revision: Revision) -> FileContent:
    body = textwrap.dedent(text).lstrip()
    return FileContent(
        sha=revision.value, text=body, revision=revision, size=len(body.encode())
    )


def _evaluate(base: str, head: str) -> KubernetesRuleResult:
    return evaluate_kubernetes_change(
        "deploy/app.yaml",
        base=_inline(base, Revision.BASE),
        head=_inline(head, Revision.HEAD),
    )


def test_image_tag_change_to_latest_from_fixtures() -> None:
    result = evaluate_kubernetes_change(
        "deploy/app.yaml",
        base=_content("base.yaml", Revision.BASE),
        head=_content("head.yaml", Revision.HEAD),
    )
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "latest" in high[0].summary
    assert high[0].rule_id == RULE_ID
    assert high[0].evidence_paths == ("deploy/app.yaml",)


def test_service_exposure_to_loadbalancer() -> None:
    base = """
        apiVersion: v1
        kind: Service
        metadata: {name: api, namespace: default}
        spec: {type: ClusterIP}
        """
    head = """
        apiVersion: v1
        kind: Service
        metadata: {name: api, namespace: default}
        spec: {type: LoadBalancer}
        """
    result = _evaluate(base, head)
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "LoadBalancer" in high[0].summary


def test_privileged_container_change() -> None:
    base = """
        apiVersion: apps/v1
        kind: Deployment
        metadata: {name: web, namespace: default}
        spec:
          template:
            spec:
              containers:
                - name: app
                  image: web:1.0
                  securityContext: {privileged: false}
        """
    head = """
        apiVersion: apps/v1
        kind: Deployment
        metadata: {name: web, namespace: default}
        spec:
          template:
            spec:
              containers:
                - name: app
                  image: web:1.0
                  securityContext: {privileged: true}
        """
    result = _evaluate(base, head)
    high = [f for f in result.findings if f.level is RiskLevel.HIGH]
    assert len(high) == 1
    assert "privileged" in high[0].summary


def test_unchanged_manifest_has_no_findings() -> None:
    manifest = """
        apiVersion: apps/v1
        kind: Deployment
        metadata: {name: web, namespace: default}
        spec:
          template:
            spec:
              containers:
                - name: app
                  image: web:1.0
        """
    result = _evaluate(manifest, manifest)
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.SUPPORTED


def test_unsupported_kind_is_coverage() -> None:
    manifest = """
        apiVersion: apiextensions.k8s.io/v1
        kind: CustomResourceDefinition
        metadata: {name: widgets.example.com}
        """
    result = _evaluate(manifest, manifest)
    unsupported = [c for c in result.coverage if c.state is CoverageState.UNSUPPORTED]
    assert any("CustomResourceDefinition" in c.reason for c in unsupported)


def test_helm_template_is_unsupported_coverage() -> None:
    base = "apiVersion: v1\nkind: Service\nmetadata: {name: api}\nspec: {type: ClusterIP}\n"
    head = "kind: Service\nmetadata:\n  name: {{ .Values.name }}\n"
    result = _evaluate(base, head)
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.UNSUPPORTED


def test_invalid_yaml_is_partial_coverage() -> None:
    base = "apiVersion: v1\nkind: Service\nmetadata: {name: api}\nspec: {type: ClusterIP}\n"
    result = _evaluate(base, "kind: Service\n  bad: [")
    assert result.findings == ()
    assert result.coverage[0].state is CoverageState.PARTIAL
