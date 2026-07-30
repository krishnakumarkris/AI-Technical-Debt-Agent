"""
Maps known Maven groupId / Gradle group prefixes to a friendly framework
name, so the dependency scanner can answer "what frameworks does this
project use?" without needing any external lookup.

This list is intentionally small and easy to extend - add a line whenever
you hit a library that should be recognized.
"""

FRAMEWORK_SIGNATURES = {
    "org.springframework.boot": "Spring Boot",
    "org.springframework": "Spring",
    "org.hibernate": "Hibernate",
    "io.micronaut": "Micronaut",
    "io.quarkus": "Quarkus",
    "junit": "JUnit",
    "org.junit.jupiter": "JUnit 5",
    "org.mockito": "Mockito",
    "org.testng": "TestNG",
    "com.fasterxml.jackson": "Jackson",
    "org.apache.logging.log4j": "Log4j",
    "ch.qos.logback": "Logback",
    "org.slf4j": "SLF4J",
    "com.google.guava": "Guava",
    "org.projectlombok": "Lombok",
    "javax.persistence": "JPA",
    "jakarta.persistence": "Jakarta Persistence",
    "org.apache.commons": "Apache Commons",
    "com.google.dagger": "Dagger",
    "io.grpc": "gRPC",
    "org.apache.kafka": "Kafka",
}


def detect_frameworks(dependencies):
    """
    dependencies: list[DependencyModel]
    Returns a sorted list of unique framework names detected.
    """
    found = set()
    for dep in dependencies:
        for prefix, framework_name in FRAMEWORK_SIGNATURES.items():
            if dep.group == prefix or dep.group.startswith(prefix + "."):
                found.add(framework_name)
    return sorted(found)
