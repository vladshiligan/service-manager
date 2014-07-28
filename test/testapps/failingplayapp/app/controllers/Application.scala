package controllers

import play.api._
import play.api.mvc._
import scala.concurrent._
import ExecutionContext.Implicits.global

object Application extends Controller {

  def index = Action {
    Ok(views.html.index("Your new application is ready."))
  }

  val die = Action {
    Future { Thread.sleep(100); System.exit(-1) }
    InternalServerError("fail")
  }

}