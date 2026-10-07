@echo off
@REM PulseCart Maven Wrapper Script
setlocal
set "MAVEN_HOME=C:\Users\hp\apache-maven-3.9.9"
if exist "%MAVEN_HOME%\bin\mvn.cmd" (
    call "%MAVEN_HOME%\bin\mvn.cmd" %*
) else (
    mvn %*
)
