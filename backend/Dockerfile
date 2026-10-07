# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Stage 1: Build the Application
# -----------------------------------------------------------------------------
FROM eclipse-temurin:21-jdk-jammy AS builder

WORKDIR /build

# Copy Maven descriptor and download dependencies (layer caching)
COPY pom.xml .
COPY mvnw* .
COPY .mvn .mvn

RUN ./mvnw dependency:go-offline -B || true

# Copy source code and package
COPY src ./src
RUN ./mvnw clean package -DskipTests -B

# -----------------------------------------------------------------------------
# Stage 2: Runtime Container
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
