package controllers

import org.slf4j.LoggerFactory
import play.api.Configuration
import play.api.mvc.{AbstractController, ControllerComponents}
import javax.inject.{Inject, Singleton}
import java.util.Properties
import scala.util.{Failure, Success, Try}

@Singleton
class IndexController @Inject() (cc:ControllerComponents, config:Configuration) extends AbstractController(cc) {
  private val logger = LoggerFactory.getLogger(getClass)

  def index(any:String) = Action {
    val cbVersionString = Try {
      val prop = new Properties()
      prop.load(getClass.getClassLoader.getResourceAsStream("version.properties"))
      prop.getProperty("build-sha")
    } match {
      case Success(v)=>Some(v)
      case Failure(err)=>
        logger.warn("Could not get build-sha property: ", err)
        None
    }
    Ok(views.html.index(cbVersionString.getOrElse("none"), config.getOptional[String]("deployment-root").getOrElse("")))
  }

  def root = index("")

}
