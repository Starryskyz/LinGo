organization := "fgramemfp"
version := "1.0.0"
name := "LinGo"
scalaVersion := "2.13.10"

scalacOptions ++= Seq(
  "-language:reflectiveCalls",
  "-deprecation",
  "-feature",
  "-Xcheckinit"
)

addCompilerPlugin(
  "edu.berkeley.cs" % "chisel3-plugin" % "3.6.0" cross CrossVersion.full
)

libraryDependencies ++= Seq(
  "edu.berkeley.cs" %% "chisel3" % "3.6.0",
  "com.fasterxml.jackson.core" % "jackson-core" % "2.14.2",
  "com.fasterxml.jackson.core" % "jackson-annotations" % "2.14.2",
  "com.fasterxml.jackson.core" % "jackson-databind" % "2.14.2",
  "com.fasterxml.jackson.module" %% "jackson-module-scala" % "2.14.2"
)
