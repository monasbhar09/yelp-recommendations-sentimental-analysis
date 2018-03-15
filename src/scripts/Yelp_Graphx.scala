// Databricks notebook source
import org.apache.spark.graphx._
import org.apache.spark.rdd.RDD

// COMMAND ----------

val userdf = sqlContext.read.json("/FileStore/tables/user.json")


// COMMAND ----------

import org.apache.spark.sql.functions.explode

val userdf_exploded = userdf.withColumn("friends", explode($"friends"))


// COMMAND ----------

userdf_exploded.createGlobalTempView("userdatatable")

// COMMAND ----------

// val userVertices = userdf_exploded.selectExpr("float(user_id) as user_id", "user_id").distinct()

// COMMAND ----------

// val friendsEdges = userdf_exploded
//   .withColumnRenamed("station_id", "start_station_id")
//   .withColumnRenamed("station_id", "end_station_id")
 

// COMMAND ----------



// COMMAND ----------

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.IntegerType

val usergraph_df = userdf_exploded.withColumn("user_id", $"user_id".cast(IntegerType)).withColumn("friends", $"friends".cast(IntegerType))

usergraph_df.show()


// COMMAND ----------

val users = usergraph_df
  .select("user_id", "fr")
  .rdd
  .distinct() // helps filter out duplicate trips
  .flatMap(x => Iterable(x(0).asInstanceOf[Number].longValue, x(1).asInstanceOf[Number].longValue)) // helps us maintain types
  .distinct()
  .toDF() // return to a DF to make merging + joining easier

stations.take(1)

// COMMAND ----------

val userVertices: RDD[(VertexId, String)] = usergraph_df
  .select("user_id", "name")
  .rdd
  .map(row => (row(0).asInstanceOf[Number].longValue, row(1).asInstanceOf[String])) 

// maintain type information

println(userVertices.count())

// COMMAND ----------

val friendEdges:RDD[Edge[Long]] = userData
  .select("user_id","friend_id")
  .rdd
  .map(row => Edge(row(0).asInstanceOf[Number].longValue, row(1).asInstanceOf[Number].longValue, 1))

println(friendEdges)

// COMMAND ----------

val defaultStation = ("Missing Link") 
val friendsGraph = Graph(userVertices, friendEdges, defaultStation)

// COMMAND ----------

println("Total Number of Stations: " + friendsGraph.numVertices)
println("Total Number of Trips: " + friendsGraph.numEdges)

// COMMAND ----------


