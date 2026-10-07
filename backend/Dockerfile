# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Stage 1: Build the Application with Official Maven 3.9 + Java 21 Image
# -----------------------------------------------------------------------------
FROM maven:3.9.9-eclipse-temurin-21-jammy AS builder

WORKDIR /build

# Cache Maven dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B || true

# Copy application source and build executable JAR
COPY src ./src
RUN mvn clean package -DskipTests -B

# -----------------------------------------------------------------------------
# Stage 2: Minimal Production JRE Runtime Container
# -----------------------------------------------------------------------------
FROM eclipse-temurin:21-jre-jammy AS runner

WORKDIR /app

# Create unprivileged application user
RUN groupadd -r pulsecart && useradd -r -g pulsecart -s /bin/false pulsecart

# Copy executable jar from builder stage
COPY --from=builder /build/target/pulsecart-backend-*.jar app.jar

RUN chown -R pulsecart:pulsecart /app

USER pulsecart

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-XX:+UseZGC", "-XX:MaxRAMPercentage=75.0", "-jar", "app.jar"]
