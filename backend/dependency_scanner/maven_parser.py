"""
Maven pom.xml Parser
--------------------
Parses a pom.xml into a list of DependencyModel + PluginModel objects using
lxml. Handles two Maven-specific quirks that trip up naive parsers:

  1. The default Maven POM namespace (xmlns="http://maven.apache.org/POM/4.0.0")
     - every tag lookup needs that namespace prefixed, or lxml finds nothing.
  2. Property placeholders like ${spring.version} inside <version> tags -
     resolved against whatever is declared in <properties>.

Limitations (documented rather than silently guessed at):
  - Does not resolve versions inherited from a parent POM or a
    <dependencyManagement> block - only versions written directly on each
    <dependency>. A missing version is reported as "unspecified" with a
    warning rather than invented.
  - Does not fetch anything from Maven Central; this is a static-file parse.
"""

import re
from lxml import etree

from dependency_scanner.models import DependencyModel, PluginModel


def _namespace_uri(root):
    match = re.match(r"\{(.*)\}", root.tag)
    return match.group(1) if match else ""


def _tag(name, ns_uri):
    return f"{{{ns_uri}}}{name}" if ns_uri else name


def _text(element, name, ns_uri, default=""):
    child = element.find(_tag(name, ns_uri))
    return child.text.strip() if child is not None and child.text else default


def _resolve_property(value, properties):
    """Resolve a single ${prop.name} placeholder against the properties dict."""
    if not value:
        return value
    match = re.fullmatch(r"\$\{([^}]+)\}", value.strip())
    if not match:
        return value
    prop_name = match.group(1)
    return properties.get(prop_name, value)  # leave literal if unresolvable


def parse_pom(pom_path):
    """
    Returns (dependencies: list[DependencyModel], plugins: list[PluginModel],
    warnings: list[str])
    """
    warnings = []

    try:
        tree = etree.parse(str(pom_path))
    except etree.XMLSyntaxError as e:
        return [], [], [f"Could not parse {pom_path}: {e}"]

    root = tree.getroot()
    ns_uri = _namespace_uri(root)

    # --- Properties, for ${...} resolution ---
    properties = {}
    props_el = root.find(_tag("properties", ns_uri))
    if props_el is not None:
        for prop in props_el:
            local_name = etree.QName(prop.tag).localname
            if prop.text:
                properties[local_name] = prop.text.strip()

    # --- Dependencies (direct <dependencies><dependency> children only) ---
    dependencies = []
    deps_el = root.find(_tag("dependencies", ns_uri))
    if deps_el is not None:
        for dep_el in deps_el.findall(_tag("dependency", ns_uri)):
            group = _text(dep_el, "groupId", ns_uri)
            artifact = _text(dep_el, "artifactId", ns_uri)
            raw_version = _text(dep_el, "version", ns_uri)
            version = _resolve_property(raw_version, properties)
            scope = _text(dep_el, "scope", ns_uri, default="compile")

            if not version:
                warnings.append(
                    f"{group}:{artifact} has no explicit <version> "
                    f"(likely inherited from a parent POM / dependencyManagement, "
                    f"which this parser does not resolve)."
                )
                version = "unspecified"

            dependencies.append(
                DependencyModel(
                    group=group,
                    artifact=artifact,
                    version=version,
                    scope=scope,
                    source_file=str(pom_path),
                )
            )
    else:
        warnings.append("No <dependencies> block found in pom.xml.")

    # --- Build plugins ---
    plugins = []
    build_el = root.find(_tag("build", ns_uri))
    if build_el is not None:
        plugins_el = build_el.find(_tag("plugins", ns_uri))
        if plugins_el is not None:
            for plugin_el in plugins_el.findall(_tag("plugin", ns_uri)):
                artifact = _text(plugin_el, "artifactId", ns_uri)
                raw_version = _text(plugin_el, "version", ns_uri)
                version = _resolve_property(raw_version, properties)
                plugins.append(PluginModel(name=artifact, version=version))

    return dependencies, plugins, warnings
