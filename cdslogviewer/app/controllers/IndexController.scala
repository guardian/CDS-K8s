package controllers

import play.api.Configuration
import play.api.mvc.{AbstractController, ControllerComponents}

import javax.inject.{Inject, Singleton}
import views._

@Singleton
class IndexController @Inject() (cc:ControllerComponents, config:Configuration) extends AbstractController(cc) {
  def index = Action {
    Ok(views.index)
  }
}
