package controllers

import akka.actor.ActorSystem
import akka.stream.Materializer
import akka.stream.scaladsl.{FileIO, Framing, Keep, Sink, Source}
import akka.util.ByteString
import auth.{BearerTokenAuth, Security}
import org.slf4j.LoggerFactory
import play.api.Configuration
import play.api.mvc.{AbstractController, ControllerComponents, ResponseHeader, Result}

import java.nio.file.{Files, Paths}
import javax.inject.{Inject, Singleton}
import scala.concurrent.ExecutionContext
import scala.jdk.CollectionConverters._
import io.circe.generic.auto._
import io.circe.syntax._
import play.api.cache.SyncCacheApi
import play.api.http.HttpEntity
import play.api.libs.circe.Circe
import responses.{GenericErrorResponse, LogInfo}

import java.nio.file.attribute.PosixFileAttributeView
import java.time.format.DateTimeFormatter
import java.time.{ZoneId, ZonedDateTime}

@Singleton
class LogsController @Inject() (cc:ControllerComponents,
                                override val bearerTokenAuth:BearerTokenAuth,
                                override implicit val config:Configuration,
                                override implicit val cache:SyncCacheApi)
                               (implicit system:ActorSystem, mat:Materializer)
  extends AbstractController(cc) with Security with Circe {
  override val logger = LoggerFactory.getLogger(getClass)
  private implicit val ec:ExecutionContext = system.dispatcher
  private implicit val tz:ZoneId = config.getOptional[String]("timezone").map(ZoneId.of).getOrElse(ZoneId.systemDefault())

  def listRoutes = IsAdminAsync { uid=> request=>
    val path = Paths.get(config.get[String]("cds.logbase"))
    logger.debug(s"Logs base path is $path")

    Source.fromIterator(()=>Files.newDirectoryStream(path).asScala.iterator)
      .filter(_.toFile.isDirectory)
      .map(path.relativize) //convert to a path relative to the log base
      .map(_.toString)
      .filter(! _.startsWith("."))
      .toMat(Sink.seq)(Keep.right)
      .run()
      .map(dirs=>Ok(dirs.asJson))
      .recover({
        case err:Throwable=>
          logger.error(s"Could not list directories: ${err.getMessage}",err)
          InternalServerError(GenericErrorResponse("config_error", "Could not list directories, see server logs").asJson)
      })
  }

  def listLogs(route:String) = IsAdmin { uid=> request=>
    val base = config.get[String]("cds.logbase")
    val path = Paths.get(base, route)
    if(!path.toString.startsWith(base)) {
      BadRequest(GenericErrorResponse("bad_request","That is not a valid log").asJson)
    } else if(!path.toFile.exists()) {
      NotFound(GenericErrorResponse("not_found","The given route logs do not exist").asJson)
    } else {
      val stream = Source.fromIterator(()=>Files.newDirectoryStream(path).asScala.iterator)
        .map(LogInfo.fromPath)
        .collect({case Some(logInfo)=>logInfo})
        .map(_.asJson.noSpaces + "\n")
        .map(ByteString.apply)
      Result(
        header = ResponseHeader(200, Map.empty),
        body = HttpEntity.Streamed(stream, None, Some("application/x-ndjson"))
      )
    }
  }

  def streamLog(route:String, logname:String, fromLine:Long) = IsAdmin { uid=> request=>
    val base = config.get[String]("cds.logbase")
    val path = Paths.get(base, route, logname)
    if(!path.toString.startsWith(base)) {
      BadRequest(GenericErrorResponse("bad_request","That is not a valid log").asJson)
    } else if(!path.toFile.exists()) {
      NotFound(GenericErrorResponse("not_found","The given log file does not exist").asJson)
    } else {
      try {
        val view = Files.getFileAttributeView(path, classOf[PosixFileAttributeView])
        val modTime = ZonedDateTime.ofInstant(view.readAttributes().lastModifiedTime().toInstant, tz)

        val stream = FileIO.fromPath(path)
          .via(Framing.delimiter(ByteString("\n"), 32768, true))
          .drop(fromLine)
          .map(_ ++ ByteString("\n"))
        //setting Content-Length to the length of the file does not make sense, since we may have skipped an unknown
        //number of characters if fromLine != 0
        Result(
          header = ResponseHeader(200, Map("X-Logfile-Modified"->modTime.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME))),
          body = HttpEntity.Streamed(stream, None, Some("text/plain"))
        )
      } catch {
        case err:Throwable=>
          logger.error(s"Could not stream log '$logname' from '$route': ${err.getMessage}", err)
          InternalServerError(GenericErrorResponse("error", err.getMessage).asJson)
      }
    }
  }

  def logByJobName(name:String) = IsAdmin { uid=> request=>
    val base = config.get[String]("cds.logbase")
    val path = Paths.get(base, "podnames", name+".txt")
    logger.debug(s"Path used: ${path.toString}")
    if(!path.toFile.exists()) {
      NotFound(GenericErrorResponse("not_found","The given file does not exist").asJson)
    } else {
      val fileSource = scala.io.Source.fromFile(base + "/podnames/" + name + ".txt")
      val fileData = try fileSource.mkString finally fileSource.close()
      val uRLToUse = fileData.replace("/var/log/cds_backend/", "/cds/log/").filterNot(_.isWhitespace)
      Result(
        header = ResponseHeader(200, Map.empty),
        body = HttpEntity.Strict(ByteString("{"log_url":"${uRLToUse}"}"), Some("application/json"))
      )
    }
  }
}
