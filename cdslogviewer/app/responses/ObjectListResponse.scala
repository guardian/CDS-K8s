package responses

case class ObjectListResponse[T](status:String,entries:Seq[T])
