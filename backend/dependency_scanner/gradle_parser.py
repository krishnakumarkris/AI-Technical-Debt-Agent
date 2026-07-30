"""
Gradle build.gradle / build.gradle.kts Parser
-----------------------------------------------
Gradle's build files are Groovy or Kotlin scripts, not structured data, so
there's no proper AST parser available the way javalang gives us one for
Java (short of embedding a real Groovy/Kotlin parser). Instead, this uses
targeted regexes for the handful of ways dependencies are commonly written:

    implementation 'org.springframework:spring-core:5.3.20'
    testImplementation "junit:junit:4.13.2"
    api group: 'com.google.guava', name: 'guava', version: '31.1-jre'

And plugins:
    id 'org.springframework.boot' version '2.7.0'
    apply plugin: 'java'

This intentionally will NOT resolve version catalogs (libs.versions.toml)
or variables (e.g. "junit:junit:$junitVersion") - those are flagged as
warnings rather than silently skipped, since guessing a version would be
worse than admitting we don't know it.
"""

import re

from dependency_scanner.models import DependencyModel, PluginModel

CONFIGURATIONS = (
    "implementation|api|compile|compileOnly|runtimeOnly|runtime|"
    "testImplementation|testCompile|testRuntimeOnly|annotationProcessor"
)

# implementation 'group:artifact:version'
_SHORT_FORM = re.compile(
    rf"""(?P<config>{CONFIGURATIONS})\s*
        \(?\s*['"](?P<group>[\w\.\-]+):(?P<artifact>[\w\.\-]+):(?P<version>[\w\.\-\+]+)['"]""",
    re.VERBOSE,
)

# implementation group: 'x', name: 'y', version: 'z'
_MAP_FORM = re.compile(
    rf"""(?P<config>{CONFIGURATIONS})\s*\(?\s*
        group:\s*['"](?P<group>[^'"]+)['"]\s*,\s*
        name:\s*['"](?P<artifact>[^'"]+)['"]\s*,\s*
        version:\s*['"](?P<version>[^'"]+)['"]""",
    re.VERBOSE,
)

# Dependencies that reference a Gradle variable instead of a literal version,
# e.g. "junit:junit:$junitVersion" - can't resolve these without evaluating
# the whole build script, so just warn instead of guessing.
_UNRESOLVED_VERSION = re.compile(
    rf"""(?P<config>{CONFIGURATIONS})\s*\(?\s*
        ['"](?P<group>[\w\.\-]+):(?P<artifact>[\w\.\-]+):\$\{{?(?P<var>[\w\.]+)\}}?['"]""",
    re.VERBOSE,
)

_PLUGIN_ID_FORM = re.compile(
    r"""id\s*\(?\s*['"](?P<name>[\w\.\-]+)['"]\)?\s*(?:version\s*['"](?P<version>[\w\.\-]+)['"])?"""
)
_PLUGIN_APPLY_FORM = re.compile(r"""apply\s+plugin:\s*['"](?P<name>[\w\.\-]+)['"]""")


def parse_gradle(gradle_path):
    """
    Returns (dependencies: list[DependencyModel], plugins: list[PluginModel],
    warnings: list[str])
    """
    warnings = []

    try:
        with open(gradle_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        return [], [], [f"Could not read {gradle_path}: {e}"]

    dependencies = []
    seen_spans = set()

    for pattern in (_SHORT_FORM, _MAP_FORM):
        for match in pattern.finditer(content):
            if match.span() in seen_spans:
                continue
            seen_spans.add(match.span())
            dependencies.append(
                DependencyModel(
                    group=match.group("group"),
                    artifact=match.group("artifact"),
                    version=match.group("version"),
                    scope=match.group("config"),
                    source_file=str(gradle_path),
                )
            )

    for match in _UNRESOLVED_VERSION.finditer(content):
        warnings.append(
            f"{match.group('group')}:{match.group('artifact')} uses a Gradle "
            f"variable for its version (${{{match.group('var')}}}); this parser "
            f"only reads literal versions, so this dependency was skipped."
        )

    plugins = []
    for match in _PLUGIN_ID_FORM.finditer(content):
        plugins.append(
            PluginModel(name=match.group("name"), version=match.group("version") or "")
        )
    for match in _PLUGIN_APPLY_FORM.finditer(content):
        plugins.append(PluginModel(name=match.group("name")))

    if not dependencies:
        warnings.append(
            "No dependencies matched the supported Gradle declaration styles "
            "(literal short-form or map-form). Version catalogs "
            "(libs.versions.toml) are not yet supported."
        )

    return dependencies, plugins, warnings
