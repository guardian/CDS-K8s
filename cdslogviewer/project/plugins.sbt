logLevel := Level.Warn

resolvers += "Typesafe repository" at "https://repo.typesafe.com/typesafe/releases/"

addSbtPlugin("com.typesafe.play" % "sbt-plugin" % "2.8.19")

// sbt native packager

addSbtPlugin("com.typesafe.sbt" % "sbt-native-packager" % "1.7.3")

// for snyk
addSbtPlugin("net.virtual-void" % "sbt-dependency-graph" % "0.10.0-RC1")