package responses

import play.api.Configuration

import java.nio.file.Path
import java.time.{Instant, ZoneId, ZonedDateTime}
import scala.util.Try

case class LogInfo(name:String, size:Long, lastModified:ZonedDateTime)

object LogInfo {
  def fromPath(filePath: Path)(implicit timezone:ZoneId): Option[LogInfo] = {
    val f = filePath.toFile

    if(!f.exists()) {
      return None
    }

    Try { LogInfo(
      f.getName,
      f.length(),
      ZonedDateTime.ofInstant(Instant.ofEpochMilli(f.lastModified()), timezone)
    ) }.toOption
  }
}
