import com.typesafe.sbt.packager.docker.DockerPermissionStrategy.CopyChown
import com.typesafe.sbt.packager.docker._

name := "cdslogviewer"
 
version := "1.0" 
      
lazy val `cdslogviewer` = (project in file(".")).enablePlugins(PlayScala)

val circeVersion = "0.12.3"

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

libraryDependencies += "com.dripower" %% "play-circe" % "2812.0"

//authentication
libraryDependencies += "com.nimbusds" % "nimbus-jose-jwt" % "8.21"
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
