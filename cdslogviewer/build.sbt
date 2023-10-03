import com.typesafe.sbt.packager.docker.DockerPermissionStrategy.CopyChown
import com.typesafe.sbt.packager.docker._

name := "cdslogviewer"
 
version := "1.0" 
      
lazy val `cdslogviewer` = (project in file(".")).enablePlugins(PlayScala)

val circeVersion = "0.14.2"

resolvers += "Akka Snapshot Repository" at "https://repo.akka.io/snapshots/"
      
scalaVersion := "2.13.9"

libraryDependencies ++= Seq( ehcache , ws , specs2 % Test , guice )

unmanagedResourceDirectories in Test +=  (baseDirectory ( _ /"target/web/public/test" )).value

//nice json parsing
libraryDependencies ++= Seq(
  "io.circe" %% "circe-core",
  "io.circe" %% "circe-generic",
  "io.circe" %% "circe-parser"
).map(_ % circeVersion)

libraryDependencies += "com.typesafe.akka" %% "akka-actor" % "2.8.1"
libraryDependencies += "com.fasterxml.jackson.core" % "jackson-databind" % "2.15.2"
libraryDependencies += "com.fasterxml.jackson.module" %% "jackson-module-scala" % "2.15.2"

libraryDependencies ++= Seq(
  "com.typesafe.akka" %% "akka-actor" % "2.8.1",
  "com.typesafe.akka" %% "akka-slf4j" % "2.8.1",
  "com.typesafe.akka" %% "akka-actor-typed" % "2.8.1",
  "com.typesafe.akka" %% "akka-protobuf-v3" % "2.8.1",
  "com.typesafe.akka" %% "akka-stream" % "2.8.1",
  "com.typesafe.akka" %% "akka-serialization-jackson" % "2.8.1"
)

libraryDependencies += "com.dripower" %% "play-circe" % "2814.2"


//authentication
libraryDependencies += "com.nimbusds" % "nimbus-jose-jwt" % "9.30.2"
libraryDependencies += "commons-codec" % "commons-codec" % "1.15"

//packaging
dockerExposedPorts := Seq(9000)
dockerUsername := sys.props.get("docker.username")
dockerRepository := Some("guardianmultimedia")
packageName in Docker := "guardianmultimedia/cdslogviewer"
packageName := "cdslogviewer"
dockerBaseImage := "docker.io/openjdk:11.0.10-jre"
dockerPermissionStrategy := CopyChown
dockerAlias := com.typesafe.sbt.packager.docker.DockerAlias(None,Some("guardianmultimedia"),"cdslogviewer",Some(sys.props.getOrElse("build.number","DEV")))
