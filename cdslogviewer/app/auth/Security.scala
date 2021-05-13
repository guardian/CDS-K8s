/*
 * Copyright (C) 2015 Jason Mar
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Modified by Andy Gallagher to provide extra IsAuthenticated implementations for async actions etc.
 */

package auth

import com.nimbusds.jwt.JWTClaimsSet
import org.slf4j.Logger
import play.api.mvc._
import play.api.libs.Files.TemporaryFile

import scala.jdk.CollectionConverters._
import play.api.{ConfigLoader, Configuration}
import play.api.cache.SyncCacheApi
import play.api.libs.json._
import play.api.libs.streams.Accumulator
import play.api.libs.typedmap.TypedKey

import scala.concurrent.Future
import scala.concurrent.ExecutionContext.Implicits.global
import scala.util.{Failure, Success, Try}

sealed trait LoginResult

final case class LoginResultOK[A](content:A) extends LoginResult
final case class LoginResultInvalid[A](content:A) extends LoginResult
final case class LoginResultExpired[A](content:A) extends LoginResult
final case class LoginResultMisconfigured[A](content:A) extends LoginResult
case object LoginResultNotPresent extends LoginResult

object Security {
  /**
   * this is a copy of the regular Security.Authenticated method from Play, adjusted to use an Either instead of an
   * Option so we can pass on information about why a login failed
   * @param userinfo a function that takes the request header and must return either a Left with a LoginResult
   *                 indicating failure or Right with a LoginResult indicating success
   * @param onUnauthorized a function that takes the request header and the login status returned by `userinfo`,
   *                       if it was a failure. It must return a Play response that will get returned to the client.
   * @param action the play action being wrapped
   * @tparam A the type of data that the LoginResult will contain
   * @return the wrapped Play action
   */
  def MyAuthenticated[A](
                          userinfo: RequestHeader => Either[LoginResult, LoginResultOK[A]],
                          onUnauthorized: (RequestHeader, LoginResult) => Result
                        )(action: A => EssentialAction): EssentialAction = {
    EssentialAction { request =>
      userinfo(request) match {
        case Right(result) =>
          action(result.content)(request)
        case Left(loginProblem) =>
          Accumulator.done(onUnauthorized(request, loginProblem))
      }
    }
  }
}

trait Security extends BaseController {
  implicit val cache:SyncCacheApi
  val bearerTokenAuth:BearerTokenAuth //this needs to be injected from the user

  val logger:Logger

  implicit val config:Configuration

  /**
   * look up an hmac user
   * @param header HTTP request object
   * @param auth Authorization token as passed from the client
   */
  private def hmacUsername(header: RequestHeader, auth: String):Either[LoginResult, LoginResultOK[String]] = {
    logger.debug(s"headers: ${header.headers.toSimpleMap.toString}")
    if(Conf.sharedSecret.isEmpty){
      logger.error("Unable to process server->server request, shared_secret is not set in application.conf")
      Left(LoginResultMisconfigured(auth))
    } else {
      HMAC
        .calculateHmac(header, Conf.sharedSecret)
        .map(calculatedSig => {
          if ("HMAC "+calculatedSig == auth) Right(LoginResultOK("hmac")) else Left(LoginResultInvalid("hmac"))
        })
        .map({
          case loginOk @ Right(_)=>loginOk
          case Left(_)=>
            HMAC.calculateHmac(header, Conf.sharedSecret, false)
              .map(calculatedSig=>{
                if("HMAC "+calculatedSig==auth) Right(LoginResultOK("hmac")) else Left(LoginResultInvalid("hmac"))
              }).getOrElse(Left(LoginResultInvalid("")))
        })
        .getOrElse(Left(LoginResultInvalid("")))
    }
  }

  object AuthType extends Enumeration {
    val AuthHmac, AuthJWT, AuthSession = Value
  }
  final val AuthTypeKey = TypedKey[AuthType.Value]("auth_type")

  /**
   * get a username from the claim.  This is determined from the first string entry of a list of claim fields.
   * if none of them match (wrong data type or not present) then `subject` is used as a fallback
   * @param claim the `JwtClaimsSet` to inspect
   * @return a string the gives the user id for the given claims set
   */
  private def usernameFromClaim(claim:JWTClaimsSet) = {
    val possibleFields = Array("preferred_username","username")
    val possibleNames = possibleFields.map(name=>Try {Option(claim.getStringClaim(name))})
    val successfulNames = possibleNames.collect({case Success(Some(username))=>username})

    successfulNames.headOption.getOrElse(claim.getSubject)
  }

  //if this returns something, then we are logged in
  private def username(request:RequestHeader):Either[LoginResult, LoginResultOK[String]] = request.headers.get("Authorization") match {
    case Some(auth)=>
      if(auth.contains("HMAC")) {
        logger.debug("got HMAC Authorization header, doing hmac auth")
        val updatedRequest = request.addAttr(AuthTypeKey, AuthType.AuthHmac)
        hmacUsername(updatedRequest, auth)
      } else {
        logger.debug("got Authorization header, doing bearer auth")
        bearerTokenAuth(request).map(result => {
          LoginResultOK(usernameFromClaim(result.content))
        })
      }
    case None=>
      logger.debug("no Auth header, can't authenticate")
      Left(LoginResultNotPresent)
  }

  private def onUnauthorized(request: RequestHeader, loginResult: LoginResult) = loginResult match {
    case LoginResultInvalid(_)=>
      Results.Forbidden(Json.obj("status"->"error","detail"->"Invalid credentials"))
    case LoginResultExpired(user:String)=>
      Results.Unauthorized(Json.obj("status"->"expired","detail"->"Your login has expired","username"->user))
    case LoginResultExpired(_)=>  //this shouldn't happen, but it keeps the compiler happy
      Results.Unauthorized(Json.obj("status"->"expired"))
    case LoginResultMisconfigured(_)=>
      Results.InternalServerError(Json.obj("status"->"error","detail"->"Server configuration error, please check the logs"))
    case LoginResultNotPresent=>
      Results.Forbidden(Json.obj("status"->"error","detail"->"No credentials provided"))
    case LoginResultOK(user)=>
      logger.error(s"LoginResultOK passed to onUnauthorized! This must be a bug. Username is $user.")
      Results.InternalServerError(Json.obj("status"->"logic_error","detail"->"Login should have succeeded but error handler called. This is a server bug."))
  }

  def IsAuthenticated(f: => String => Request[AnyContent] => Result) = Security.MyAuthenticated(username, onUnauthorized) {
    uid => Action(request => f(uid)(request))
  }

  def IsAuthenticatedAsync(f: => String => Request[AnyContent] => Future[Result]) = Security.MyAuthenticated(username, onUnauthorized) {
    uid => Action.async(request => f(uid)(request))
  }

  def IsAuthenticatedAsync[A](b: BodyParser[A])(f: => String => Request[A] => Future[Result]) = Security.MyAuthenticated(username, onUnauthorized) {
    uid=> Action.async(b)(request => f(uid)(request))
  }

  def IsAuthenticated(b: BodyParser[MultipartFormData[TemporaryFile]] = parse.multipartFormData)(f: => String => Request[MultipartFormData[TemporaryFile]] => Result) = {
    Security.MyAuthenticated(username, onUnauthorized) { uid => Action(b)(request => f(uid)(request)) }
  }


  def checkAdmin[A](uid:String, request:Request[A]) = Seq("X-Hmac-Authorization","Authorization").map(request.headers.get) match {
    case Seq(Some(hmac),_)=>
      logger.debug("hmac auth is never admin")
      false //server-server never requires admin
    case Seq(None,Some(bearer))=>
      //FIXME: seems a bit rubbish to validate the token twice, once for login and once for admin
      val adminClaimContent = for {
        tok <- bearerTokenAuth.extractAuthorization(bearer)
        maybeClaims <- bearerTokenAuth.validateToken(tok)
        maybeAdminClaim <- Option(maybeClaims.content.getStringClaim(bearerTokenAuth.isAdminClaimName())) match {
          case Some(str)=>Right(LoginResultOK(str))
          case None=>Left(LoginResultNotPresent)
        }
      } yield maybeAdminClaim

      adminClaimContent match {
        case Right(LoginResultOK(stringValue))=>
          logger.debug(s"got value for isAdminClaim ${bearerTokenAuth.isAdminClaimName()}: $stringValue, downcasing and testing for 'true' or 'yes'")
          val downcased = stringValue.toLowerCase()
          downcased == "true" || downcased == "yes"
        case Left(_)=>
          logger.debug(s"got nothing for isAdminClaim ${bearerTokenAuth.isAdminClaimName()}")
          false
      }
    case _=>
      false
  }

  /**
   * determine if the given user is an admin.  This implies an IsAuthenticated check.
   * if the X-Hmac-Authorization header is present, then the request is server-server and the user is not an admin
   * if the Authoriztion header is present, then the request is a bearer token. The user is considered an admin
   * if a string claim with the name given by the config key auth.adminClaim is present and has a value of either "true" or "yes"
   * @param f the action function
   * @return the result of the action function or Forbidden
   */
  def IsAdmin(f: => String => Request[AnyContent] => Result) = IsAuthenticated { uid=> request=>
    if(checkAdmin(uid, request)){
      f(uid)(request)
    } else {
      logger.warn(s"Admin request rejected for $uid to ${request.uri}")
      Forbidden(Json.obj("status"->"forbidden","detail"->"You need admin rights to perform this action"))
    }

  }

  def IsAdminAsync[A](b: BodyParser[A])(f: => String => Request[A] => Future[Result]) = IsAuthenticatedAsync(b) { uid=> request=>
    if(checkAdmin(uid,request)) {
      f(uid)(request)
    } else {
      logger.warn(s"Admin request rejected for $uid to ${request.uri}")
      Future(Forbidden(Json.obj("status"->"forbidden","detail"->"You need admin rights to perform this action")))
    }
  }

  def IsAdminAsync(f: => String => Request[AnyContent] => Future[Result]) = IsAuthenticatedAsync { uid=> request=>
    if(checkAdmin(uid,request)) {
      f(uid)(request)
    } else {
      logger.warn(s"Admin request rejected for $uid to ${request.uri}")
      Future(Forbidden(Json.obj("status"->"forbidden","detail"->"You need admin rights to perform this action")))
    }
  }

}
